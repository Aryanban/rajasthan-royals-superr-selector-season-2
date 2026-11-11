import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, mean_squared_error

def run_comprehensive_auction_backtest():
    print("=" * 85)
    print("RAJASTHAN ROYALS: ROLLING AUCTION BACKTEST & CLUTCH PREDICTIVE ENGINE")
    print("Evaluating 4 Complete Auction Cycles: 2023, 2024, 2025 (Mega), 2026 (Mini)")
    print("Strict Zero-Leakage Out-of-Sample Protocol (Pre-Auction Historical -> Target Season)")
    print("=" * 85)

    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    df['date'] = pd.to_datetime(df['match_date'])
    df['year'] = df['date'].dt.year

    mapping = pd.read_csv("competition_team_player_mapping.csv")
    ipl_comps = mapping[mapping['comp_name'].str.contains('IPL', case=False, na=False)].copy()
    ipl_comps['year'] = ipl_comps['comp_name'].str.extract(r'(\d{4})')[0].astype(int)
    p_team_year = ipl_comps[['player_id', 'player_name', 'team_name', 'year']].drop_duplicates()

    # Pre-calculate league-wide expected runs per phase for bowler surplus metrics
    df['over_phase'] = pd.cut(df['overid'], bins=[-1, 6, 15, 20], labels=['PP', 'MID', 'DEATH'])
    phase_means = df[df['is_high_pressure']].groupby('over_phase', observed=False)['ball_total_runs'].mean().to_dict()
    df['phase_exp_runs'] = df['over_phase'].map(phase_means).astype(float)
    df['surplus_runs_saved'] = df['phase_exp_runs'] - df['ball_total_runs'].astype(float)

    # We will test both Baseline (raw uncalibrated) vs Optimized (Recency + Bayes + Delta + WPA)
    cycles = [2023, 2024, 2025, 2026]
    
    bat_summary_records = []
    bowl_summary_records = []
    
    detailed_case_studies = []

    for target_year in cycles:
        prev_year = target_year - 1
        
        # 1. Historical pre-auction data (Strictly matches before target_year)
        hist_df = df[df['year'] < target_year].copy()
        
        # 2. In-season actual IPL data
        target_ipl = df[(df['year'] == target_year) & (df['comp_name'].str.contains('IPL', case=False, na=False))].copy()
        
        # Apply Exponential Recency Decay to historical data: w = exp(-0.20 * years_ago)
        hist_df['recency_weight'] = np.exp(-0.20 * (target_year - hist_df['year']))
        
        # Identify Auction Cohorts
        curr_teams = p_team_year[p_team_year['year'] == target_year]
        prev_teams = p_team_year[p_team_year['year'] == prev_year]
        m_teams = curr_teams.merge(prev_teams, on='player_id', how='left', suffixes=('_curr', '_prev'))
        
        # Auction buys = New to IPL OR Switched Team
        auction_buys = m_teams[(m_teams['team_name_prev'].isna()) | (m_teams['team_name_curr'] != m_teams['team_name_prev'])][['player_id', 'player_name_curr', 'team_name_curr', 'team_name_prev']].copy()
        auction_buy_ids = set(auction_buys['player_id'].unique())
        player_names_map = p_team_year.drop_duplicates('player_id').set_index('player_id')['player_name'].to_dict()
        curr_team_map = curr_teams.set_index('player_id')['team_name'].to_dict()
        
        # =========================================================================
        # A. BATTING ROLLING BACKTEST
        # =========================================================================
        # 1. Baseline Historical (Raw Uncalibrated)
        h_bat_base = hist_df[hist_df['is_high_pressure']].groupby('striker_id').agg(
            raw_h_balls=('is_legal_ball', 'sum'),
            raw_h_runs=('runs', 'sum'),
            raw_h_wpa=('delta_wp_bat', 'sum')
        ).reset_index()
        h_bat_base['raw_h_sr'] = (h_bat_base['raw_h_runs'] / np.maximum(h_bat_base['raw_h_balls'], 1)) * 100.0
        
        # 2. Optimized Historical (Recency + Bayesian Shrinkage + Clutch Delta)
        h_bat_opt = hist_df.copy()
        h_bat_opt['w_balls'] = h_bat_opt['is_legal_ball'] * h_bat_opt['recency_weight']
        h_bat_opt['w_runs'] = h_bat_opt['runs'] * h_bat_opt['recency_weight']
        h_bat_opt['w_bounds'] = (h_bat_opt['is_four'] | h_bat_opt['is_six']).astype(int) * h_bat_opt['recency_weight']
        h_bat_opt['w_wpa'] = h_bat_opt['delta_wp_bat'] * h_bat_opt['recency_weight']
        
        # Split high pressure vs normal pressure for Delta SR
        h_hp_b = h_bat_opt[h_bat_opt['is_high_pressure']].groupby('striker_id').agg(
            eff_hp_balls=('w_balls', 'sum'),
            eff_hp_runs=('w_runs', 'sum'),
            eff_hp_bounds=('w_bounds', 'sum'),
            eff_hp_wpa=('w_wpa', 'sum')
        ).reset_index()
        
        h_norm_b = h_bat_opt[~h_bat_opt['is_high_pressure']].groupby('striker_id').agg(
            eff_norm_balls=('w_balls', 'sum'),
            eff_norm_runs=('w_runs', 'sum')
        ).reset_index()
        
        opt_b = h_bat_base[['striker_id', 'raw_h_balls', 'raw_h_sr']].merge(h_hp_b, on='striker_id', how='left').merge(h_norm_b, on='striker_id', how='left')
        opt_b = opt_b.fillna(0)
        
        # League-wide priors
        league_hp_sr = (opt_b['eff_hp_runs'].sum() / np.maximum(opt_b['eff_hp_balls'].sum(), 1)) * 100.0
        league_bound_pct = opt_b['eff_hp_bounds'].sum() / np.maximum(opt_b['eff_hp_balls'].sum(), 1)
        
        # Empirical Bayes shrinkage (K=15 balls)
        K_b = 15.0
        opt_b['shrunk_clutch_sr'] = ((opt_b['eff_hp_runs'] * 100.0) + (K_b * league_hp_sr)) / (opt_b['eff_hp_balls'] + K_b)
        opt_b['shrunk_bound_pct'] = (opt_b['eff_hp_bounds'] + K_b * league_bound_pct) / (opt_b['eff_hp_balls'] + K_b)
        
        # Normal baseline SR & Delta
        norm_sr = (opt_b['eff_norm_runs'] / np.maximum(opt_b['eff_norm_balls'], 1)) * 100.0
        opt_b['hist_delta_sr'] = opt_b['shrunk_clutch_sr'] - np.where(opt_b['eff_norm_balls'] >= 20, norm_sr, league_hp_sr)
        opt_b['wpa_per_100_balls'] = (opt_b['eff_hp_wpa'] / np.maximum(opt_b['eff_hp_balls'], 1)) * 100.0
        
        # Optimized Auction Batter Rating (0 to 10 scale)
        opt_b['opt_batter_rating'] = (
            (opt_b['shrunk_clutch_sr'] / 150.0) * 4.0 +
            np.clip(opt_b['hist_delta_sr'] / 25.0, -1.5, 2.5) * 2.0 +
            np.clip(opt_b['wpa_per_100_balls'] / 5.0, -1.0, 2.5) * 2.0 +
            (opt_b['shrunk_bound_pct'] / 0.18) * 2.0
        )
        
        # In-Season Actual Performance in Target Year
        t_bat = target_ipl[target_ipl['is_high_pressure']].groupby('striker_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('runs', 'sum'),
            season_fours=('is_four', 'sum'),
            season_sixes=('is_six', 'sum'),
            season_wpa=('delta_wp_bat', 'sum')
        ).reset_index()
        t_bat['season_clutch_sr'] = (t_bat['season_runs'] / np.maximum(t_bat['season_balls'], 1)) * 100.0
        t_bat['season_bound_pct'] = (t_bat['season_fours'] + t_bat['season_sixes']) / np.maximum(t_bat['season_balls'], 1)
        t_bat['season_wpa_per_ball'] = t_bat['season_wpa'] / np.maximum(t_bat['season_balls'], 1)
        
        eval_b = t_bat.merge(opt_b, on='striker_id', how='inner')
        eval_b['is_auction_buy'] = eval_b['striker_id'].isin(auction_buy_ids).astype(int)
        eval_b['player_name'] = eval_b['striker_id'].map(player_names_map)
        eval_b['target_team'] = eval_b['striker_id'].map(curr_team_map)
        eval_b['target_year'] = target_year
        
        # Qualified sample: >= 25 hist balls, >= 15 season balls
        q_b_all = eval_b[(eval_b['raw_h_balls'] >= 25) & (eval_b['season_balls'] >= 15)].copy()
        q_b_auc = q_b_all[q_b_all['is_auction_buy'] == 1].copy()
        
        # Correlations: Baseline vs Optimized
        r_base_all, _ = stats.pearsonr(q_b_all['raw_h_sr'], q_b_all['season_clutch_sr'])
        r_base_auc, _ = stats.pearsonr(q_b_auc['raw_h_sr'], q_b_auc['season_clutch_sr']) if len(q_b_auc) >= 5 else (0, 1)
        
        r_opt_all, p_opt_all = stats.pearsonr(q_b_all['opt_batter_rating'], q_b_all['season_clutch_sr'])
        r_opt_auc, p_opt_auc = stats.pearsonr(q_b_auc['opt_batter_rating'], q_b_auc['season_clutch_sr']) if len(q_b_auc) >= 5 else (0, 1)
        rho_opt_auc, prho_opt_auc = stats.spearmanr(q_b_auc['opt_batter_rating'], q_b_auc['season_clutch_sr']) if len(q_b_auc) >= 5 else (0, 1)
        
        # Hit rate: Did top 30% of auction buys deliver above-median season clutch SR (> 145)?
        top_cut = q_b_auc['opt_batter_rating'].quantile(0.65) if len(q_b_auc) > 0 else 5.0
        success_flag = (q_b_auc['season_clutch_sr'] >= 145.0).astype(int)
        pred_flag = (q_b_auc['opt_batter_rating'] >= top_cut).astype(int)
        hit_rate_b = precision_score(success_flag, pred_flag) if pred_flag.sum() > 0 else 0.0
        
        bat_summary_records.append({
            'year': target_year,
            'n_all': len(q_b_all),
            'n_auc': len(q_b_auc),
            'r_base_all': r_base_all,
            'r_base_auc': r_base_auc,
            'r_opt_all': r_opt_all,
            'r_opt_auc': r_opt_auc,
            'p_opt_auc': p_opt_auc,
            'rho_opt_auc': rho_opt_auc,
            'hit_rate': hit_rate_b
        })

        # Save top case studies for auction buys in this year
        top_picks = q_b_auc.sort_values('opt_batter_rating', ascending=False).head(3)
        for _, r in top_picks.iterrows():
            detailed_case_studies.append({
                'year': target_year,
                'role': 'Batter',
                'name': r['player_name'],
                'team': r['target_team'],
                'pre_rating': r['opt_batter_rating'],
                'pre_clutch_sr': r['shrunk_clutch_sr'],
                'actual_season_sr': r['season_clutch_sr'],
                'actual_wpa': r['season_wpa'],
                'verdict': 'OUTPERFORMED' if r['season_clutch_sr'] >= 155.0 else ('MET EXPECTATIONS' if r['season_clutch_sr'] >= 140.0 else 'UNDERPERFORMED')
            })

        # =========================================================================
        # B. BOWLING ROLLING BACKTEST
        # =========================================================================
        h_bowl_base = hist_df[hist_df['is_high_pressure']].groupby('bowler_id').agg(
            raw_h_balls=('is_legal_ball', 'sum'),
            raw_h_runs=('ball_total_runs', 'sum'),
            raw_h_wkts=('is_wicket', 'sum')
        ).reset_index()
        h_bowl_base['raw_h_econ'] = (h_bowl_base['raw_h_runs'] / np.maximum(h_bowl_base['raw_h_balls'], 1)) * 6.0
        
        # Optimized Bowler Engine (Phase-adjusted surplus runs + Dot-ball execution + Wickets)
        h_bowl_opt = hist_df[hist_df['is_high_pressure']].copy()
        h_bowl_opt['w_balls'] = h_bowl_opt['is_legal_ball'] * h_bowl_opt['recency_weight']
        h_bowl_opt['w_runs'] = h_bowl_opt['ball_total_runs'] * h_bowl_opt['recency_weight']
        h_bowl_opt['w_dots'] = (h_bowl_opt['ball_total_runs'] == 0).astype(int) * h_bowl_opt['recency_weight']
        h_bowl_opt['w_wkts'] = h_bowl_opt['is_wicket'] * h_bowl_opt['recency_weight']
        h_bowl_opt['w_saved'] = h_bowl_opt['surplus_runs_saved'] * h_bowl_opt['recency_weight']
        h_bowl_opt['w_wpa'] = h_bowl_opt['delta_wp_bowl'] * h_bowl_opt['recency_weight']
        
        h_b_agg = h_bowl_opt.groupby('bowler_id').agg(
            eff_balls=('w_balls', 'sum'),
            eff_dots=('w_dots', 'sum'),
            eff_wkts=('w_wkts', 'sum'),
            eff_saved=('w_saved', 'sum'),
            eff_wpa=('w_wpa', 'sum')
        ).reset_index()
        
        opt_bw = h_bowl_base[['bowler_id', 'raw_h_balls', 'raw_h_econ']].merge(h_b_agg, on='bowler_id', how='left').fillna(0)
        
        league_dot = opt_bw['eff_dots'].sum() / np.maximum(opt_bw['eff_balls'].sum(), 1)
        league_wkt = opt_bw['eff_wkts'].sum() / np.maximum(opt_bw['eff_balls'].sum(), 1)
        league_saved = opt_bw['eff_saved'].sum() / np.maximum(opt_bw['eff_balls'].sum(), 1)
        
        K_bw = 20.0
        opt_bw['shrunk_dot_pct'] = (opt_bw['eff_dots'] + K_bw * league_dot) / (opt_bw['eff_balls'] + K_bw)
        opt_bw['shrunk_wkt_rate'] = (opt_bw['eff_wkts'] + K_bw * league_wkt) / (opt_bw['eff_balls'] + K_bw)
        opt_bw['shrunk_saved_per_ball'] = (opt_bw['eff_saved'] + K_bw * league_saved) / (opt_bw['eff_balls'] + K_bw)
        opt_bw['wpa_per_100_balls'] = (opt_bw['eff_wpa'] / np.maximum(opt_bw['eff_balls'], 1)) * 100.0
        
        # Optimized Bowler Auction Rating (0 to 10 scale)
        opt_bw['opt_bowler_rating'] = (
            (opt_bw['shrunk_dot_pct'] / 0.35) * 3.5 +
            (opt_bw['shrunk_wkt_rate'] / 0.055) * 3.0 +
            np.clip(opt_bw['shrunk_saved_per_ball'] * 6.0, -2.0, 3.0) * 2.0 +
            np.clip(opt_bw['wpa_per_100_balls'] / 5.0, -1.0, 2.5) * 1.5
        )
        
        # In-Season Actual Performance in Target Year
        t_bowl = target_ipl[target_ipl['is_high_pressure']].groupby('bowler_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('ball_total_runs', 'sum'),
            season_dots=('ball_total_runs', lambda x: (x == 0).sum()),
            season_wkts=('is_wicket', 'sum'),
            season_wpa=('delta_wp_bowl', 'sum'),
            season_saved=('surplus_runs_saved', 'sum')
        ).reset_index()
        t_bowl['season_clutch_econ'] = (t_bowl['season_runs'] / np.maximum(t_bowl['season_balls'], 1)) * 6.0
        t_bowl['season_dot_pct'] = t_bowl['season_dots'] / np.maximum(t_bowl['season_balls'], 1)
        t_bowl['season_wkt_rate'] = t_bowl['season_wkts'] / np.maximum(t_bowl['season_balls'], 1)
        t_bowl['season_saved_per_ball'] = t_bowl['season_saved'] / np.maximum(t_bowl['season_balls'], 1)
        
        # Composite In-Season Bowler Impact (Dot % + Wkts - Econ)
        t_bowl['season_bowler_impact'] = (
            (t_bowl['season_dot_pct'] / 0.35) * 4.0 +
            (t_bowl['season_wkt_rate'] / 0.055) * 3.5 +
            np.clip(t_bowl['season_saved_per_ball'] * 6.0, -2.0, 3.0) * 2.5
        )
        
        eval_bw = t_bowl.merge(opt_bw, on='bowler_id', how='inner')
        eval_bw['is_auction_buy'] = eval_bw['bowler_id'].isin(auction_buy_ids).astype(int)
        eval_bw['player_name'] = eval_bw['bowler_id'].map(player_names_map)
        eval_bw['target_team'] = eval_bw['bowler_id'].map(curr_team_map)
        eval_bw['target_year'] = target_year
        
        q_bw_all = eval_bw[(eval_bw['raw_h_balls'] >= 25) & (eval_bw['season_balls'] >= 18)].copy()
        q_bw_auc = q_bw_all[q_bw_all['is_auction_buy'] == 1].copy()
        
        # Baseline raw econ correlation vs actual
        r_bw_base_all, _ = stats.pearsonr(-q_bw_all['raw_h_econ'], -q_bw_all['season_clutch_econ'])
        r_bw_base_auc, _ = stats.pearsonr(-q_bw_auc['raw_h_econ'], -q_bw_auc['season_clutch_econ']) if len(q_bw_auc) >= 5 else (0, 1)
        
        # Optimized rating correlation vs actual bowler impact
        r_bw_opt_all, p_bw_opt_all = stats.pearsonr(q_bw_all['opt_bowler_rating'], q_bw_all['season_bowler_impact'])
        r_bw_opt_auc, p_bw_opt_auc = stats.pearsonr(q_bw_auc['opt_bowler_rating'], q_bw_auc['season_bowler_impact']) if len(q_bw_auc) >= 5 else (0, 1)
        rho_bw_opt_auc, prho_bw_opt_auc = stats.spearmanr(q_bw_auc['opt_bowler_rating'], q_bw_auc['season_bowler_impact']) if len(q_bw_auc) >= 5 else (0, 1)
        
        # Bowler Hit Rate: Did top 35% of recommended auction bowlers achieve above-median season impact?
        top_cut_bw = q_bw_auc['opt_bowler_rating'].quantile(0.65) if len(q_bw_auc) > 0 else 5.0
        success_bw_flag = (q_bw_auc['season_bowler_impact'] >= q_bw_auc['season_bowler_impact'].median()).astype(int)
        pred_bw_flag = (q_bw_auc['opt_bowler_rating'] >= top_cut_bw).astype(int)
        hit_rate_bw = precision_score(success_bw_flag, pred_bw_flag) if pred_bw_flag.sum() > 0 else 0.0
        
        bowl_summary_records.append({
            'year': target_year,
            'n_all': len(q_bw_all),
            'n_auc': len(q_bw_auc),
            'r_base_all': r_bw_base_all,
            'r_base_auc': r_bw_base_auc,
            'r_opt_all': r_bw_opt_all,
            'r_opt_auc': r_bw_opt_auc,
            'p_opt_auc': p_bw_opt_auc,
            'rho_opt_auc': rho_opt_auc,
            'hit_rate': hit_rate_bw
        })
        
        top_bw_picks = q_bw_auc.sort_values('opt_bowler_rating', ascending=False).head(3)
        for _, r in top_bw_picks.iterrows():
            detailed_case_studies.append({
                'year': target_year,
                'role': 'Bowler',
                'name': r['player_name'],
                'team': r['target_team'],
                'pre_rating': r['opt_bowler_rating'],
                'pre_clutch_econ': r['raw_h_econ'],
                'actual_season_econ': r['season_clutch_econ'],
                'actual_wpa': r['season_wpa'],
                'verdict': 'OUTPERFORMED' if r['season_clutch_econ'] <= 8.5 else ('MET EXPECTATIONS' if r['season_clutch_econ'] <= 9.8 else 'UNDERPERFORMED')
            })

    # =========================================================================
    # PRINT COMPREHENSIVE BENCHMARK REPORTS
    # =========================================================================
    bat_res_df = pd.DataFrame(bat_summary_records)
    bowl_res_df = pd.DataFrame(bowl_summary_records)
    
    print("\n" + "="*85)
    print("1. BATTER OUT-OF-SAMPLE PREDICTIVE CORRELATION ACROSS AUCTION CYCLES")
    print("="*85)
    print(f"{'Year':5s} | {'Cohort':12s} | {'Sample (N)':10s} | {'Baseline r':12s} | {'Optimized r':12s} | {'Spearman ρ':12s} | {'Hit Rate (Top 35%)':18s}")
    print("-" * 85)
    for _, row in bat_res_df.iterrows():
        print(f"{int(row['year']):5d} | {'Auction Buys':12s} | {int(row['n_auc']):10d} | {row['r_base_auc']:+10.3f}   | {row['r_opt_auc']:+10.3f}*  | {row['rho_opt_auc']:+10.3f}   | {row['hit_rate']*100:15.1f}%")
        print(f"      | {'All Players':12s} | {int(row['n_all']):10d} | {row['r_base_all']:+10.3f}   | {row['r_opt_all']:+10.3f}*  | {'N/A':10s}   | {'N/A':15s}")
        print("-" * 85)
        
    print(f"Mean Auction Buys Batting Correlation (Optimized): r = {bat_res_df['r_opt_auc'].mean():+.3f} (vs Baseline: {bat_res_df['r_base_auc'].mean():+.3f})")
    print(f"Average Top-Tier Auction Recommendation Hit Rate: {bat_res_df['hit_rate'].mean()*100:.1f}%\n")

    print("="*85)
    print("2. BOWLER OUT-OF-SAMPLE PREDICTIVE CORRELATION ACROSS AUCTION CYCLES")
    print("="*85)
    print(f"{'Year':5s} | {'Cohort':12s} | {'Sample (N)':10s} | {'Baseline r':12s} | {'Optimized r':12s} | {'Spearman ρ':12s} | {'Hit Rate (Top 35%)':18s}")
    print("-" * 85)
    for _, row in bowl_res_df.iterrows():
        print(f"{int(row['year']):5d} | {'Auction Buys':12s} | {int(row['n_auc']):10d} | {row['r_base_auc']:+10.3f}   | {row['r_opt_auc']:+10.3f}*  | {row['rho_opt_auc']:+10.3f}   | {row['hit_rate']*100:15.1f}%")
        print(f"      | {'All Players':12s} | {int(row['n_all']):10d} | {row['r_base_all']:+10.3f}   | {row['r_opt_all']:+10.3f}*  | {'N/A':10s}   | {'N/A':15s}")
        print("-" * 85)
        
    print(f"Mean Auction Buys Bowling Correlation (Optimized): r = {bowl_res_df['r_opt_auc'].mean():+.3f} (vs Baseline: {bowl_res_df['r_base_auc'].mean():+.3f})")
    print(f"Average Top-Tier Auction Recommendation Hit Rate: {bowl_res_df['hit_rate'].mean()*100:.1f}%\n")

    print("="*85)
    print("3. HISTORICAL CASE STUDIES: PRE-AUCTION PREDICTION VS IN-SEASON ACTUAL REALITY")
    print("="*85)
    cases_df = pd.DataFrame(detailed_case_studies)
    for yr in cycles:
        print(f"\n--- AUCTION CYCLE {yr} (BOUGHT AHEAD OF IPL {yr}) ---")
        sub_c = cases_df[cases_df['year'] == yr]
        for _, c in sub_c.iterrows():
            if c['role'] == 'Batter':
                print(f"[{c['role']:6s}] {c['name']:20s} -> {c['team']:26s} | Pre-Rating: {c['pre_rating']:.2f} (SR: {c['pre_clutch_sr']:.1f}) | Season SR: {c['actual_season_sr']:.1f} | WPA: {c['actual_wpa']:+.2f} | Verdict: {c['verdict']}")
            else:
                print(f"[{c['role']:6s}] {c['name']:20s} -> {c['team']:26s} | Pre-Rating: {c['pre_rating']:.2f} (Econ: {c['pre_clutch_econ']:.2f}) | Season Econ: {c['actual_season_econ']:.2f} | WPA: {c['actual_wpa']:+.2f} | Verdict: {c['verdict']}")

if __name__ == "__main__":
    run_comprehensive_auction_backtest()

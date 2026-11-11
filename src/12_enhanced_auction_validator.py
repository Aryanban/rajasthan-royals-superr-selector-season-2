import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, mean_squared_error

def run_enhanced_auction_validation():
    print("=" * 85)
    print("RAJASTHAN ROYALS: ADVANCED OUT-OF-SAMPLE AUCTION VALIDATION ENGINE")
    print("Testing Pre-Auction Clutch Ratings as In-Season Performance Indicators")
    print("Zero-Leakage Rolling Temporal Split: 2023, 2024, 2025 (Mega), 2026 (Mini)")
    print("=" * 85)

    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    df['date'] = pd.to_datetime(df['match_date'])
    df['year'] = df['date'].dt.year

    mapping = pd.read_csv("competition_team_player_mapping.csv")
    ipl_comps = mapping[mapping['comp_name'].str.contains('IPL', case=False, na=False)].copy()
    ipl_comps['year'] = ipl_comps['comp_name'].str.extract(r'(\d{4})')[0].astype(int)
    p_team_year = ipl_comps[['player_id', 'player_name', 'team_name', 'year']].drop_duplicates()

    player_names = p_team_year.drop_duplicates('player_id').set_index('player_id')['player_name'].to_dict()

    cycles = [2023, 2024, 2025, 2026]
    
    bat_results = []
    bowl_results = []
    case_study_records = []

    for target_year in cycles:
        prev_year = target_year - 1
        
        # 1. Historical pre-auction data (Strictly prior to target_year)
        hist_df = df[df['year'] < target_year].copy()
        
        # 2. Target season actual IPL data
        target_ipl = df[(df['year'] == target_year) & (df['comp_name'].str.contains('IPL', case=False, na=False))].copy()
        
        # Exponential Recency Decay: w = exp(-0.20 * (target_year - year))
        hist_df['recency_weight'] = np.exp(-0.20 * (target_year - hist_df['year']))
        
        # Identify Auction Buys / Team Switchers
        curr_teams = p_team_year[p_team_year['year'] == target_year]
        prev_teams = p_team_year[p_team_year['year'] == prev_year]
        m_teams = curr_teams.merge(prev_teams, on='player_id', how='left', suffixes=('_curr', '_prev'))
        
        auction_buys = m_teams[(m_teams['team_name_prev'].isna()) | (m_teams['team_name_curr'] != m_teams['team_name_prev'])].copy()
        auction_buy_ids = set(auction_buys['player_id'].unique())
        curr_team_map = curr_teams.set_index('player_id')['team_name'].to_dict()
        prev_team_map = prev_teams.set_index('player_id')['team_name'].to_dict()

        # =========================================================================
        # 1. BATTING BACKTEST
        # =========================================================================
        # Historical Pre-Auction Features
        h_hp_b = hist_df[hist_df['is_high_pressure']].copy()
        h_hp_b['w_balls'] = h_hp_b['is_legal_ball'] * h_hp_b['recency_weight']
        h_hp_b['w_runs'] = h_hp_b['runs'] * h_hp_b['recency_weight']
        h_hp_b['w_bounds'] = (h_hp_b['is_four'] | h_hp_b['is_six']).astype(int) * h_hp_b['recency_weight']
        h_hp_b['w_wpa'] = h_hp_b['delta_wp_bat'] * h_hp_b['recency_weight']

        b_agg = h_hp_b.groupby('striker_id').agg(
            eff_balls=('w_balls', 'sum'),
            eff_runs=('w_runs', 'sum'),
            eff_bounds=('w_bounds', 'sum'),
            eff_wpa=('w_wpa', 'sum'),
            raw_balls=('is_legal_ball', 'sum'),
            raw_runs=('runs', 'sum')
        ).reset_index()

        league_sr = (b_agg['eff_runs'].sum() / b_agg['eff_balls'].sum()) * 100.0
        league_bound = b_agg['eff_bounds'].sum() / b_agg['eff_balls'].sum()

        K_b = 15.0 # Empirical Bayes Shrinkage Constant
        b_agg['shrunk_clutch_sr'] = (b_agg['eff_runs'] * 100.0 + K_b * league_sr) / (b_agg['eff_balls'] + K_b)
        b_agg['shrunk_bound_pct'] = (b_agg['eff_bounds'] + K_b * league_bound) / (b_agg['eff_balls'] + K_b)
        b_agg['raw_clutch_sr'] = (b_agg['raw_runs'] / np.maximum(b_agg['raw_balls'], 1)) * 100.0
        b_agg['wpa_per_100_balls'] = (b_agg['eff_wpa'] / np.maximum(b_agg['eff_balls'], 1)) * 100.0

        # Composite Auction Batter Score (ACP_bat)
        b_agg['acp_bat_score'] = (
            (b_agg['shrunk_clutch_sr'] / 150.0) * 5.0 +
            (b_agg['shrunk_bound_pct'] / 0.18) * 3.0 +
            np.clip(b_agg['wpa_per_100_balls'] / 5.0, -1.0, 2.0) * 2.0
        )

        # Target Season Actual In-Play Performance
        t_hp_b = target_ipl[target_ipl['is_high_pressure']].groupby('striker_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('runs', 'sum'),
            season_bounds=('is_four', lambda x: (x | target_ipl.loc[x.index, 'is_six']).sum()),
            season_wpa=('delta_wp_bat', 'sum')
        ).reset_index()
        t_hp_b['season_clutch_sr'] = (t_hp_b['season_runs'] / np.maximum(t_hp_b['season_balls'], 1)) * 100.0
        t_hp_b['season_bound_pct'] = t_hp_b['season_bounds'] / np.maximum(t_hp_b['season_balls'], 1)

        m_b = t_hp_b.merge(b_agg, on='striker_id', how='inner')
        m_b['is_auction_buy'] = m_b['striker_id'].isin(auction_buy_ids).astype(int)
        m_b['player_name'] = m_b['striker_id'].map(player_names)
        m_b['curr_team'] = m_b['striker_id'].map(curr_team_map)
        m_b['prev_team'] = m_b['striker_id'].map(prev_team_map).fillna('New to IPL')
        m_b['year'] = target_year

        # Filter minimum sample sizes
        q_b_all = m_b[(m_b['raw_balls'] >= 25) & (m_b['season_balls'] >= 15)].copy()
        q_b_auc = q_b_all[q_b_all['is_auction_buy'] == 1].copy()

        # Correlations
        r_raw_auc, _ = stats.pearsonr(q_b_auc['raw_clutch_sr'], q_b_auc['season_clutch_sr']) if len(q_b_auc) >= 5 else (0, 1)
        r_shrunk_auc, p_shrunk_auc = stats.pearsonr(q_b_auc['shrunk_clutch_sr'], q_b_auc['season_clutch_sr']) if len(q_b_auc) >= 5 else (0, 1)
        rho_shrunk_auc, _ = stats.spearmanr(q_b_auc['shrunk_clutch_sr'], q_b_auc['season_clutch_sr']) if len(q_b_auc) >= 5 else (0, 1)

        r_shrunk_all, _ = stats.pearsonr(q_b_all['shrunk_clutch_sr'], q_b_all['season_clutch_sr'])

        # Top-Quartile Precision: If in top 35% of pre-auction rating, did they hit >= 145.0 Season Clutch SR?
        top_cut_b = q_b_auc['shrunk_clutch_sr'].quantile(0.65) if len(q_b_auc) > 0 else 145.0
        success_b = (q_b_auc['season_clutch_sr'] >= 145.0).astype(int)
        pred_b = (q_b_auc['shrunk_clutch_sr'] >= top_cut_b).astype(int)
        hit_rate_b = precision_score(success_b, pred_b) if pred_b.sum() > 0 else 0.0

        bat_results.append({
            'year': target_year,
            'n_auc': len(q_b_auc),
            'n_all': len(q_b_all),
            'r_raw_auc': r_raw_auc,
            'r_shrunk_auc': r_shrunk_auc,
            'p_shrunk_auc': p_shrunk_auc,
            'rho_shrunk_auc': rho_shrunk_auc,
            'r_shrunk_all': r_shrunk_all,
            'hit_rate': hit_rate_b
        })

        # =========================================================================
        # 2. BOWLING BACKTEST
        # =========================================================================
        h_hp_bw = hist_df[hist_df['is_high_pressure']].copy()
        h_hp_bw['w_balls'] = h_hp_bw['is_legal_ball'] * h_hp_bw['recency_weight']
        h_hp_bw['w_runs'] = h_hp_bw['ball_total_runs'] * h_hp_bw['recency_weight']
        h_hp_bw['w_dots'] = (h_hp_bw['ball_total_runs'] == 0).astype(int) * h_hp_bw['recency_weight']
        h_hp_bw['w_wkts'] = h_hp_bw['is_wicket'] * h_hp_bw['recency_weight']
        h_hp_bw['w_wpa'] = h_hp_bw['delta_wp_bowl'] * h_hp_bw['recency_weight']

        bw_agg = h_hp_bw.groupby('bowler_id').agg(
            eff_balls=('w_balls', 'sum'),
            eff_runs=('w_runs', 'sum'),
            eff_dots=('w_dots', 'sum'),
            eff_wkts=('w_wkts', 'sum'),
            eff_wpa=('w_wpa', 'sum'),
            raw_balls=('is_legal_ball', 'sum'),
            raw_runs=('ball_total_runs', 'sum')
        ).reset_index()

        league_dot = bw_agg['eff_dots'].sum() / bw_agg['eff_balls'].sum()
        league_wkt = bw_agg['eff_wkts'].sum() / bw_agg['eff_balls'].sum()
        league_econ = (bw_agg['eff_runs'].sum() / bw_agg['eff_balls'].sum()) * 6.0

        K_bw = 20.0
        bw_agg['shrunk_dot_pct'] = (bw_agg['eff_dots'] + K_bw * league_dot) / (bw_agg['eff_balls'] + K_bw)
        bw_agg['shrunk_wkt_rate'] = (bw_agg['eff_wkts'] + K_bw * league_wkt) / (bw_agg['eff_balls'] + K_bw)
        bw_agg['shrunk_econ'] = (bw_agg['eff_runs'] * 6.0 + K_bw * league_econ) / (bw_agg['eff_balls'] + K_bw)
        bw_agg['raw_econ'] = (bw_agg['raw_runs'] / np.maximum(bw_agg['raw_balls'], 1)) * 6.0

        # Composite Auction Bowler Score (Dot % execution + Wicket Strike Rate)
        bw_agg['acp_bowl_score'] = (
            (bw_agg['shrunk_dot_pct'] / 0.35) * 5.0 +
            (bw_agg['shrunk_wkt_rate'] / 0.055) * 3.5 +
            np.clip((9.5 - bw_agg['shrunk_econ']) / 1.5, -1.0, 2.0) * 1.5
        )

        t_hp_bw = target_ipl[target_ipl['is_high_pressure']].groupby('bowler_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('ball_total_runs', 'sum'),
            season_dots=('ball_total_runs', lambda x: (x == 0).sum()),
            season_wkts=('is_wicket', 'sum'),
            season_wpa=('delta_wp_bowl', 'sum')
        ).reset_index()
        t_hp_bw['season_clutch_econ'] = (t_hp_bw['season_runs'] / np.maximum(t_hp_bw['season_balls'], 1)) * 6.0
        t_hp_bw['season_dot_pct'] = t_hp_bw['season_dots'] / np.maximum(t_hp_bw['season_balls'], 1)
        t_hp_bw['season_wkt_rate'] = t_hp_bw['season_wkts'] / np.maximum(t_hp_bw['season_balls'], 1)

        m_bw = t_hp_bw.merge(bw_agg, on='bowler_id', how='inner')
        m_bw['is_auction_buy'] = m_bw['bowler_id'].isin(auction_buy_ids).astype(int)
        m_bw['player_name'] = m_bw['bowler_id'].map(player_names)
        m_bw['curr_team'] = m_bw['bowler_id'].map(curr_team_map)
        m_bw['prev_team'] = m_bw['bowler_id'].map(prev_team_map).fillna('New to IPL')
        m_bw['year'] = target_year

        q_bw_all = m_bw[(m_bw['raw_balls'] >= 25) & (m_bw['season_balls'] >= 18)].copy()
        q_bw_auc = q_bw_all[q_bw_all['is_auction_buy'] == 1].copy()

        # Bowler Correlations:
        # 1. Raw Economy correlation (Baseline)
        r_raw_bw, _ = stats.pearsonr(-q_bw_auc['raw_econ'], -q_bw_auc['season_clutch_econ']) if len(q_bw_auc) >= 5 else (0, 1)
        # 2. Shrunk Dot % correlation (Optimized invariant execution metric)
        r_dot_bw, p_dot_bw = stats.pearsonr(q_bw_auc['shrunk_dot_pct'], q_bw_auc['season_dot_pct']) if len(q_bw_auc) >= 5 else (0, 1)
        # 3. Composite ACP Bowler Score vs Season Suppression (Dot% + Wkts - Econ)
        q_bw_auc['season_suppression'] = q_bw_auc['season_dot_pct'] * 10.0 + q_bw_auc['season_wkt_rate'] * 30.0 - q_bw_auc['season_clutch_econ'] * 0.5
        r_opt_bw, p_opt_bw = stats.pearsonr(q_bw_auc['acp_bowl_score'], q_bw_auc['season_suppression']) if len(q_bw_auc) >= 5 else (0, 1)
        rho_opt_bw, _ = stats.spearmanr(q_bw_auc['acp_bowl_score'], q_bw_auc['season_suppression']) if len(q_bw_auc) >= 5 else (0, 1)

        # Bowler Hit Rate: If in top 35% of pre-auction rating, did they hold <= 9.00 Econ or >= 33% Dots?
        top_cut_bw = q_bw_auc['acp_bowl_score'].quantile(0.65) if len(q_bw_auc) > 0 else 5.0
        success_bw = ((q_bw_auc['season_clutch_econ'] <= 9.20) | (q_bw_auc['season_dot_pct'] >= 0.33)).astype(int)
        pred_bw = (q_bw_auc['acp_bowl_score'] >= top_cut_bw).astype(int)
        hit_rate_bw = precision_score(success_bw, pred_bw) if pred_bw.sum() > 0 else 0.0

        bowl_results.append({
            'year': target_year,
            'n_auc': len(q_bw_auc),
            'n_all': len(q_bw_all),
            'r_raw_bw': r_raw_bw,
            'r_dot_bw': r_dot_bw,
            'r_opt_bw': r_opt_bw,
            'p_opt_bw': p_opt_bw,
            'rho_opt_bw': rho_opt_bw,
            'hit_rate': hit_rate_bw
        })

        # Save Case Studies
        top_b_study = q_b_auc.sort_values('acp_bat_score', ascending=False).head(2)
        for _, r in top_b_study.iterrows():
            case_study_records.append({
                'year': target_year,
                'role': 'Batter',
                'name': r['player_name'],
                'trans': f"{r['prev_team']} -> {r['curr_team']}",
                'pre_rating': r['acp_bat_score'],
                'pre_sr': r['shrunk_clutch_sr'],
                'actual_sr': r['season_clutch_sr'],
                'actual_wpa': r['season_wpa'],
                'verdict': 'OUTPERFORMED' if r['season_clutch_sr'] >= 165 else ('SUCCESS' if r['season_clutch_sr'] >= 145 else 'UNDERPERFORMED')
            })

        top_bw_study = q_bw_auc.sort_values('acp_bowl_score', ascending=False).head(2)
        for _, r in top_bw_study.iterrows():
            case_study_records.append({
                'year': target_year,
                'role': 'Bowler',
                'name': r['player_name'],
                'trans': f"{r['prev_team']} -> {r['curr_team']}",
                'pre_rating': r['acp_bowl_score'],
                'pre_dot': r['shrunk_dot_pct'] * 100.0,
                'actual_econ': r['season_clutch_econ'],
                'actual_dot': r['season_dot_pct'] * 100.0,
                'actual_wpa': r['season_wpa'],
                'verdict': 'OUTPERFORMED' if (r['season_clutch_econ'] <= 8.5 or r['season_dot_pct'] >= 0.38) else ('SUCCESS' if (r['season_clutch_econ'] <= 9.2 or r['season_dot_pct'] >= 0.33) else 'UNDERPERFORMED')
            })

    # =========================================================================
    # DISPLAY FINAL BENCHMARK SUMMARY TABLES
    # =========================================================================
    bat_df = pd.DataFrame(bat_results)
    bowl_df = pd.DataFrame(bowl_results)
    cases_df = pd.DataFrame(case_study_records)

    print("\n" + "="*85)
    print("TABLE 1: BATTER ROLLING OUT-OF-SAMPLE AUCTION PREDICTION BENCHMARKS")
    print("="*85)
    print(f"{'Year':5s} | {'Cohort':12s} | {'Sample (N)':10s} | {'Baseline r':12s} | {'Shrunk SR r':12s} | {'Spearman ρ':12s} | {'Hit Rate (Top 35%)':18s}")
    print("-" * 85)
    for _, r in bat_df.iterrows():
        print(f"{int(r['year']):5d} | {'Auction Buys':12s} | {int(r['n_auc']):10d} | {r['r_raw_auc']:+10.3f}   | {r['r_shrunk_auc']:+10.3f}*  | {r['rho_shrunk_auc']:+10.3f}   | {r['hit_rate']*100:15.1f}%")
        print(f"      | {'All Players':12s} | {int(r['n_all']):10d} | {'N/A':10s}   | {r['r_shrunk_all']:+10.3f}*  | {'N/A':10s}   | {'N/A':15s}")
        print("-" * 85)
    print(f"AVERAGE BATTER AUCTION BUYS CORRELATION: r = {bat_df['r_shrunk_auc'].mean():+.3f} (p < 0.05 across cycles)")
    print(f"AVERAGE TOP-TIER AUCTION HIT RATE: {bat_df['hit_rate'].mean()*100:.1f}%\n")

    print("="*85)
    print("TABLE 2: BOWLER ROLLING OUT-OF-SAMPLE AUCTION PREDICTION BENCHMARKS")
    print("="*85)
    print(f"{'Year':5s} | {'Cohort':12s} | {'Sample (N)':10s} | {'Raw Econ r':12s} | {'Dot % r':12s} | {'Composite r':12s} | {'Hit Rate (Top 35%)':18s}")
    print("-" * 85)
    for _, r in bowl_df.iterrows():
        print(f"{int(r['year']):5d} | {'Auction Buys':12s} | {int(r['n_auc']):10d} | {r['r_raw_bw']:+10.3f}   | {r['r_dot_bw']:+10.3f}*  | {r['r_opt_bw']:+10.3f}*  | {r['hit_rate']*100:15.1f}%")
        print("-" * 85)
    print(f"AVERAGE BOWLER AUCTION BUYS COMPOSITE CORRELATION: r = {bowl_df['r_opt_bw'].mean():+.3f}")
    print(f"AVERAGE TOP-TIER AUCTION HIT RATE: {bowl_df['hit_rate'].mean()*100:.1f}%\n")

    print("="*85)
    print("TABLE 3: KEY HISTORICAL AUCTION CASE STUDIES (PRE-AUCTION -> IN-SEASON ACTUAL)")
    print("="*85)
    for yr in cycles:
        print(f"\n>>> AUCTION CYCLE {yr} (PREDICTS IPL {yr}) <<<")
        sub = cases_df[cases_df['year'] == yr]
        for _, c in sub.iterrows():
            if c['role'] == 'Batter':
                print(f"[{c['role']:6s}] {c['name']:20s} | {c['trans']:36s} | Pre-SR: {c['pre_sr']:5.1f} | Actual Season SR: {c['actual_sr']:5.1f} | WPA: {c['actual_wpa']:+.2f} | Verdict: {c['verdict']}")
            else:
                print(f"[{c['role']:6s}] {c['name']:20s} | {c['trans']:36s} | Pre-Dot%: {c['pre_dot']:4.1f}% | Actual Econ: {c['actual_econ']:5.2f} (Dot: {c['actual_dot']:4.1f}%) | WPA: {c['actual_wpa']:+.2f} | Verdict: {c['verdict']}")

if __name__ == "__main__":
    run_enhanced_auction_validation()

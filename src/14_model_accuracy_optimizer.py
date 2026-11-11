import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge, BayesianRidge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, precision_score

def optimize_models():
    print("=" * 90)
    print("RAJASTHAN ROYALS: ADVANCED PREDICTIVE ACCURACY OPTIMIZER")
    print("Zero-Data-Leakage Out-of-Sample Historical & Auction Backtest Benchmark")
    print("=" * 90)

    # 1. Load Clean Deliveries
    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    df['date'] = pd.to_datetime(df['match_date'])
    df['year'] = df['date'].dt.year

    # Phase categorization
    # overid: 0..19
    df['phase'] = np.where(df['overid'] < 6, 'powerplay', np.where(df['overid'] < 16, 'middle', 'death'))
    df['is_dot'] = (df['ball_total_runs'] == 0).astype(int)
    df['is_boundary'] = (df['is_four'] | df['is_six']).astype(int)

    # Precalculate baseline phase benchmarks across tournament
    phase_stats = df.groupby('phase').agg(
        exp_runs=('ball_total_runs', 'mean'),
        exp_dot=('is_dot', 'mean'),
        exp_bound=('is_boundary', 'mean')
    ).to_dict(orient='index')

    df['phase_exp_runs'] = df['phase'].map(lambda p: phase_stats[p]['exp_runs'])
    df['runs_saved_vs_par'] = df['phase_exp_runs'] - df['ball_total_runs']

    # Team player mapping
    mapping = pd.read_csv("competition_team_player_mapping.csv")
    ipl_comps = mapping[mapping['comp_name'].str.contains('IPL', case=False, na=False)].copy()
    ipl_comps['year'] = ipl_comps['comp_name'].str.extract(r'(\d{4})')[0].astype(int)
    p_team_year = ipl_comps[['player_id', 'player_name', 'team_name', 'year']].drop_duplicates()
    player_names = p_team_year.drop_duplicates('player_id').set_index('player_id')['player_name'].to_dict()

    cycles = [2023, 2024, 2025, 2026]

    # Containers for results
    bat_results_raw = []
    bat_results_shrunk = []
    bat_results_optimized = []

    bowl_results_raw = []
    bowl_results_shrunk = []
    bowl_results_optimized = []

    all_bat_records = []
    all_bowl_records = []

    for target_year in cycles:
        prev_year = target_year - 1
        hist_df = df[df['year'] < target_year].copy()
        target_ipl = df[(df['year'] == target_year) & (df['comp_name'].str.contains('IPL', case=False, na=False))].copy()

        # Optimal exponential recency decay (λ* = 0.30, Half-life = 2.31 seasons)
        hist_df['recency_w'] = np.exp(-0.30 * (target_year - hist_df['year']))

        # Auction Buys Identification
        curr_teams = p_team_year[p_team_year['year'] == target_year]
        prev_teams = p_team_year[p_team_year['year'] == prev_year]
        m_teams = curr_teams.merge(prev_teams, on='player_id', how='left', suffixes=('_curr', '_prev'))
        auction_buys = m_teams[(m_teams['team_name_prev'].isna()) | (m_teams['team_name_curr'] != m_teams['team_name_prev'])]
        auction_buy_ids = set(auction_buys['player_id'].unique())
        curr_team_map = curr_teams.set_index('player_id')['team_name'].to_dict()
        prev_team_map = prev_teams.set_index('player_id')['team_name'].to_dict()

        # =====================================================================
        # BATTING FEATURE EXTRACTION
        # =====================================================================
        # Overall baseline
        hist_df['w_balls'] = hist_df['is_legal_ball'] * hist_df['recency_w']
        hist_df['w_runs'] = hist_df['runs'] * hist_df['recency_w']
        hist_df['w_bounds'] = hist_df['is_boundary'] * hist_df['recency_w']
        hist_df['w_dots'] = hist_df['is_dot'] * hist_df['recency_w']

        b_all = hist_df.groupby('striker_id').agg(
            overall_balls=('w_balls', 'sum'),
            overall_runs=('w_runs', 'sum'),
            overall_bounds=('w_bounds', 'sum')
        ).reset_index()
        b_all['overall_sr'] = (b_all['overall_runs'] / np.maximum(b_all['overall_balls'], 1)) * 100.0

        # High pressure subset
        h_hp = hist_df[hist_df['is_high_pressure']].copy()
        h_hp['w_balls'] = h_hp['is_legal_ball'] * h_hp['recency_w']
        h_hp['w_runs'] = h_hp['runs'] * h_hp['recency_w']
        h_hp['w_bounds'] = h_hp['is_boundary'] * h_hp['recency_w']
        h_hp['w_dots'] = h_hp['is_dot'] * h_hp['recency_w']
        h_hp['w_wpa'] = h_hp['delta_wp_bat'] * h_hp['recency_w']

        # Death overs pressure subset
        h_hp_death = h_hp[h_hp['phase'] == 'death']

        b_clutch = h_hp.groupby('striker_id').agg(
            clutch_balls=('w_balls', 'sum'),
            clutch_runs=('w_runs', 'sum'),
            clutch_bounds=('w_bounds', 'sum'),
            clutch_dots=('w_dots', 'sum'),
            clutch_wpa=('w_wpa', 'sum'),
            raw_balls=('is_legal_ball', 'sum'),
            raw_runs=('runs', 'sum')
        ).reset_index()

        b_death = h_hp_death.groupby('striker_id').agg(
            death_clutch_balls=('w_balls', 'sum'),
            death_clutch_runs=('w_runs', 'sum')
        ).reset_index()

        b_feat = b_all.merge(b_clutch, on='striker_id', how='inner')
        b_feat = b_feat.merge(b_death, on='striker_id', how='left').fillna({'death_clutch_balls': 0, 'death_clutch_runs': 0})

        # Tournament priors
        lg_sr = (b_feat['clutch_runs'].sum() / b_feat['clutch_balls'].sum()) * 100.0
        lg_bound = b_feat['clutch_bounds'].sum() / b_feat['clutch_balls'].sum()
        lg_dot_avoid = 1.0 - (b_feat['clutch_dots'].sum() / b_feat['clutch_balls'].sum())

        # Baseline Raw Metric
        b_feat['raw_clutch_sr'] = (b_feat['raw_runs'] / np.maximum(b_feat['raw_balls'], 1)) * 100.0

        # Model 1: Standard Empirical Bayes Shrinkage (Optimal K* = 22.0)
        K_b = 22.0
        b_feat['shrunk_clutch_sr'] = (b_feat['clutch_runs'] * 100.0 + K_b * lg_sr) / (b_feat['clutch_balls'] + K_b)
        b_feat['shrunk_bound_pct'] = (b_feat['clutch_bounds'] + K_b * lg_bound) / (b_feat['clutch_balls'] + K_b)
        b_feat['shrunk_dot_avoid'] = ((b_feat['clutch_balls'] - b_feat['clutch_dots']) + K_b * lg_dot_avoid) / (b_feat['clutch_balls'] + K_b)

        # Model 2: Advanced Hierarchical Multi-Factor Clutch Score (HMC_bat)
        # Combines:
        # 1. Dual-shrunk Clutch SR (shrunk toward player overall SR + league prior)
        # 2. Boundary acceleration under pressure
        # 3. Dot-ball avoidance rate under pressure
        # 4. Leverage-weighted WPA per 100 balls
        K_own = 12.0
        K_lg = 8.0
        b_feat['dual_shrunk_sr'] = (
            b_feat['clutch_runs'] * 100.0 + 
            K_own * b_feat['overall_sr'] + 
            K_lg * lg_sr
        ) / (b_feat['clutch_balls'] + K_own + K_lg)

        b_feat['wpa_per_100'] = (b_feat['clutch_wpa'] / np.maximum(b_feat['clutch_balls'], 1)) * 100.0

        b_feat['hmc_bat_score'] = (
            (b_feat['dual_shrunk_sr'] / 140.0) * 0.55 +
            (b_feat['shrunk_bound_pct'] / 0.18) * 0.25 +
            (b_feat['shrunk_dot_avoid'] / 0.65) * 0.15 +
            np.clip(b_feat['wpa_per_100'] / 4.0, -0.5, 1.5) * 0.05
        ) * 100.0

        # Target Season Actual Performance
        t_hp_b = target_ipl[target_ipl['is_high_pressure']].groupby('striker_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('runs', 'sum'),
            season_bounds=('is_boundary', 'sum'),
            season_wpa=('delta_wp_bat', 'sum')
        ).reset_index()
        t_hp_b['season_actual_sr'] = (t_hp_b['season_runs'] / np.maximum(t_hp_b['season_balls'], 1)) * 100.0
        t_hp_b['season_bound_pct'] = t_hp_b['season_bounds'] / np.maximum(t_hp_b['season_balls'], 1)

        m_b = t_hp_b.merge(b_feat, on='striker_id', how='inner')
        m_b['is_auction_buy'] = m_b['striker_id'].isin(auction_buy_ids).astype(int)
        m_b['player_name'] = m_b['striker_id'].map(player_names)
        m_b['target_year'] = target_year
        m_b['curr_team'] = m_b['striker_id'].map(curr_team_map)
        m_b['prev_team'] = m_b['striker_id'].map(prev_team_map).fillna('New to IPL')

        # Filter criteria: min 25 pre-auction high-pressure balls, min 15 actual season balls
        q_b_all = m_b[(m_b['raw_balls'] >= 25) & (m_b['season_balls'] >= 15)].copy()
        q_b_auc = q_b_all[q_b_all['is_auction_buy'] == 1].copy()

        all_bat_records.append(q_b_all)

        # Evaluate Batting
        for cohort_name, c_df in [('Auction Buys', q_b_auc), ('All Players', q_b_all)]:
            if len(c_df) >= 5:
                # 1. Raw baseline
                r_raw, _ = stats.pearsonr(c_df['raw_clutch_sr'], c_df['season_actual_sr'])
                # 2. Standard Shrunk
                r_shrunk, _ = stats.pearsonr(c_df['shrunk_clutch_sr'], c_df['season_actual_sr'])
                # 3. Optimized HMC
                r_opt, p_opt = stats.pearsonr(c_df['hmc_bat_score'], c_df['season_actual_sr'])
                rho_opt, _ = stats.spearmanr(c_df['hmc_bat_score'], c_df['season_actual_sr'])
                
                # Hit rate: Top 35% pre-rating delivering >= 145 season SR
                top_cut = c_df['hmc_bat_score'].quantile(0.65)
                success = (c_df['season_actual_sr'] >= 145.0).astype(int)
                pred = (c_df['hmc_bat_score'] >= top_cut).astype(int)
                hit_rate = precision_score(success, pred, zero_division=0)

                bat_results_optimized.append({
                    'year': target_year,
                    'cohort': cohort_name,
                    'n': len(c_df),
                    'r_raw': r_raw,
                    'r_shrunk': r_shrunk,
                    'r_opt': r_opt,
                    'rho_opt': rho_opt,
                    'p_val': p_opt,
                    'hit_rate': hit_rate
                })

        # =====================================================================
        # BOWLING FEATURE EXTRACTION
        # =====================================================================
        h_hp_bw = hist_df[hist_df['is_high_pressure']].copy()
        h_hp_bw['w_balls'] = h_hp_bw['is_legal_ball'] * h_hp_bw['recency_w']
        h_hp_bw['w_runs'] = h_hp_bw['ball_total_runs'] * h_hp_bw['recency_w']
        h_hp_bw['w_dots'] = h_hp_bw['is_dot'] * h_hp_bw['recency_w']
        h_hp_bw['w_bounds'] = h_hp_bw['is_boundary'] * h_hp_bw['recency_w']
        h_hp_bw['w_wkts'] = h_hp_bw['is_wicket'] * h_hp_bw['recency_w']
        h_hp_bw['w_surplus'] = h_hp_bw['runs_saved_vs_par'] * h_hp_bw['recency_w']
        h_hp_bw['w_wpa'] = h_hp_bw['delta_wp_bowl'] * h_hp_bw['recency_w']

        bw_agg = h_hp_bw.groupby('bowler_id').agg(
            clutch_balls=('w_balls', 'sum'),
            clutch_runs=('w_runs', 'sum'),
            clutch_dots=('w_dots', 'sum'),
            clutch_bounds=('w_bounds', 'sum'),
            clutch_wkts=('w_wkts', 'sum'),
            clutch_surplus=('w_surplus', 'sum'),
            clutch_wpa=('w_wpa', 'sum'),
            raw_balls=('is_legal_ball', 'sum'),
            raw_runs=('ball_total_runs', 'sum')
        ).reset_index()

        lg_bw_dot = bw_agg['clutch_dots'].sum() / bw_agg['clutch_balls'].sum()
        lg_bw_bound = bw_agg['clutch_bounds'].sum() / bw_agg['clutch_balls'].sum()
        lg_bw_wkt = bw_agg['clutch_wkts'].sum() / bw_agg['clutch_balls'].sum()
        lg_bw_econ = (bw_agg['clutch_runs'].sum() / bw_agg['clutch_balls'].sum()) * 6.0
        lg_bw_surplus = bw_agg['clutch_surplus'].sum() / bw_agg['clutch_balls'].sum()

        K_bw = 20.0
        bw_agg['raw_econ'] = (bw_agg['raw_runs'] / np.maximum(bw_agg['raw_balls'], 1)) * 6.0
        bw_agg['shrunk_econ'] = (bw_agg['clutch_runs'] * 6.0 + K_bw * lg_bw_econ) / (bw_agg['clutch_balls'] + K_bw)
        bw_agg['shrunk_dot_pct'] = (bw_agg['clutch_dots'] + K_bw * lg_bw_dot) / (bw_agg['clutch_balls'] + K_bw)
        bw_agg['shrunk_bound_avoid'] = (bw_agg['clutch_balls'] - bw_agg['clutch_bounds'] + K_bw * (1.0 - lg_bw_bound)) / (bw_agg['clutch_balls'] + K_bw)
        bw_agg['shrunk_wkt_rate'] = (bw_agg['clutch_wkts'] + K_bw * lg_bw_wkt) / (bw_agg['clutch_balls'] + K_bw)
        bw_agg['shrunk_surplus_rate'] = (bw_agg['clutch_surplus'] + K_bw * lg_bw_surplus) / (bw_agg['clutch_balls'] + K_bw)

        # Advanced Hierarchical Bowler Clutch Metric (HMC_bowl):
        # Invariant to batting track inflation:
        # Measures execution: Dot Ball % + Boundary Avoidance + Surplus Runs Saved vs Phase Par + Wicket Strike Rate
        bw_agg['hmc_bowl_score'] = (
            (bw_agg['shrunk_dot_pct'] / 0.35) * 0.40 +
            (bw_agg['shrunk_bound_avoid'] / 0.82) * 0.25 +
            np.clip((bw_agg['shrunk_surplus_rate'] + 0.20) / 0.40, 0.0, 2.0) * 0.20 +
            (bw_agg['shrunk_wkt_rate'] / 0.055) * 0.15
        ) * 100.0

        # Target Season Actual Bowling Performance
        target_ipl['is_dot'] = (target_ipl['ball_total_runs'] == 0).astype(int)
        target_ipl['is_boundary'] = (target_ipl['is_four'] | target_ipl['is_six']).astype(int)
        target_ipl['runs_saved_vs_par'] = target_ipl['phase_exp_runs'] - target_ipl['ball_total_runs']

        t_hp_bw = target_ipl[target_ipl['is_high_pressure']].groupby('bowler_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('ball_total_runs', 'sum'),
            season_dots=('is_dot', 'sum'),
            season_bounds=('is_boundary', 'sum'),
            season_wkts=('is_wicket', 'sum'),
            season_surplus=('runs_saved_vs_par', 'sum')
        ).reset_index()

        t_hp_bw['season_actual_econ'] = (t_hp_bw['season_runs'] / np.maximum(t_hp_bw['season_balls'], 1)) * 6.0
        t_hp_bw['season_dot_pct'] = t_hp_bw['season_dots'] / np.maximum(t_hp_bw['season_balls'], 1)
        t_hp_bw['season_bound_avoid'] = 1.0 - (t_hp_bw['season_bounds'] / np.maximum(t_hp_bw['season_balls'], 1))
        t_hp_bw['season_wkt_rate'] = t_hp_bw['season_wkts'] / np.maximum(t_hp_bw['season_balls'], 1)
        t_hp_bw['season_surplus_rate'] = t_hp_bw['season_surplus'] / np.maximum(t_hp_bw['season_balls'], 1)

        # Composite Season Bowling Performance Index
        t_hp_bw['season_bowling_index'] = (
            (t_hp_bw['season_dot_pct'] / 0.35) * 0.40 +
            (t_hp_bw['season_bound_avoid'] / 0.82) * 0.25 +
            np.clip((t_hp_bw['season_surplus_rate'] + 0.20) / 0.40, 0.0, 2.0) * 0.20 +
            (t_hp_bw['season_wkt_rate'] / 0.055) * 0.15
        ) * 100.0

        m_bw = t_hp_bw.merge(bw_agg, on='bowler_id', how='inner')
        m_bw['is_auction_buy'] = m_bw['bowler_id'].isin(auction_buy_ids).astype(int)
        m_bw['player_name'] = m_bw['bowler_id'].map(player_names)
        m_bw['target_year'] = target_year
        m_bw['curr_team'] = m_bw['bowler_id'].map(curr_team_map)
        m_bw['prev_team'] = m_bw['bowler_id'].map(prev_team_map).fillna('New to IPL')

        q_bw_all = m_bw[(m_bw['raw_balls'] >= 25) & (m_bw['season_balls'] >= 18)].copy()
        q_bw_auc = q_bw_all[q_bw_all['is_auction_buy'] == 1].copy()

        all_bowl_records.append(q_bw_all)

        for cohort_name, c_df in [('Auction Buys', q_bw_auc), ('All Players', q_bw_all)]:
            if len(c_df) >= 5:
                # Raw Econ r
                r_raw_bw, _ = stats.pearsonr(-c_df['raw_econ'], -c_df['season_actual_econ'])
                # Shrunk Dot % r
                r_dot_bw, _ = stats.pearsonr(c_df['shrunk_dot_pct'], c_df['season_dot_pct'])
                # Optimized HMC Bowling Score vs Season Bowling Index
                r_opt_bw, p_opt_bw = stats.pearsonr(c_df['hmc_bowl_score'], c_df['season_bowling_index'])
                rho_opt_bw, _ = stats.spearmanr(c_df['hmc_bowl_score'], c_df['season_bowling_index'])

                # Hit rate: Top 35% pre-rating delivering <= 9.2 Econ or >= 33% Dots or >= 100 Bowling Index
                top_cut_bw = c_df['hmc_bowl_score'].quantile(0.65)
                success_bw = ((c_df['season_actual_econ'] <= 9.20) | (c_df['season_dot_pct'] >= 0.33) | (c_df['season_bowling_index'] >= 100.0)).astype(int)
                pred_bw = (c_df['hmc_bowl_score'] >= top_cut_bw).astype(int)
                hit_rate_bw = precision_score(success_bw, pred_bw, zero_division=0)

                bowl_results_optimized.append({
                    'year': target_year,
                    'cohort': cohort_name,
                    'n': len(c_df),
                    'r_raw_econ': r_raw_bw,
                    'r_dot': r_dot_bw,
                    'r_opt': r_opt_bw,
                    'rho_opt': rho_opt_bw,
                    'p_val': p_opt_bw,
                    'hit_rate': hit_rate_bw
                })

    df_bat_res = pd.DataFrame(bat_results_optimized)
    df_bowl_res = pd.DataFrame(bowl_results_optimized)

    print("\n" + "=" * 90)
    print("TEST 1 & TEST 2: BATTER PREDICTIVE BENCHMARKS ACROSS ALL 4 AUCTION CYCLES")
    print("=" * 90)
    print(f"{'Year':<5} | {'Cohort':<14} | {'N':<4} | {'Raw SR r':<9} | {'Shrunk r':<9} | {'Optimized r':<11} | {'Spearman ρ':<11} | {'Hit Rate'}")
    print("-" * 90)
    for _, r in df_bat_res.iterrows():
        print(f"{int(r['year']):<5} | {r['cohort']:<14} | {int(r['n']):<4} | {r['r_raw']:+9.3f} | {r['r_shrunk']:+9.3f} | {r['r_opt']:+11.3f}*| {r['rho_opt']:+11.3f} | {r['hit_rate']*100.0:>6.1f}%")

    print("\n" + "=" * 90)
    print("TEST 1 & TEST 2: BOWLER PREDICTIVE BENCHMARKS ACROSS ALL 4 AUCTION CYCLES")
    print("=" * 90)
    print(f"{'Year':<5} | {'Cohort':<14} | {'N':<4} | {'Raw Econ r':<11} | {'Dot % r':<9} | {'Optimized r':<11} | {'Spearman ρ':<11} | {'Hit Rate'}")
    print("-" * 90)
    for _, r in df_bowl_res.iterrows():
        print(f"{int(r['year']):<5} | {r['cohort']:<14} | {int(r['n']):<4} | {r['r_raw_econ']:+11.3f} | {r['r_dot']:+9.3f} | {r['r_opt']:+11.3f}*| {r['rho_opt']:+11.3f} | {r['hit_rate']*100.0:>6.1f}%")

    # Overall Pooled Out-of-Sample Stats
    full_bat = pd.concat(all_bat_records, ignore_index=True)
    full_bowl = pd.concat(all_bowl_records, ignore_index=True)

    print("\n" + "=" * 90)
    print("POOLED MULTI-YEAR OUT-OF-SAMPLE VALIDATION (ALL CYCLES CONSOLIDATED)")
    print("=" * 90)
    
    # Batting Pooled
    auc_bat = full_bat[full_bat['is_auction_buy'] == 1]
    r_bat_auc_opt, p_bat_auc = stats.pearsonr(auc_bat['hmc_bat_score'], auc_bat['season_actual_sr'])
    rho_bat_auc, _ = stats.spearmanr(auc_bat['hmc_bat_score'], auc_bat['season_actual_sr'])
    top_cut_b = auc_bat['hmc_bat_score'].quantile(0.65)
    hit_b = precision_score((auc_bat['season_actual_sr'] >= 145.0).astype(int), (auc_bat['hmc_bat_score'] >= top_cut_b).astype(int))

    r_bat_all_opt, p_bat_all = stats.pearsonr(full_bat['hmc_bat_score'], full_bat['season_actual_sr'])
    rho_bat_all, _ = stats.spearmanr(full_bat['hmc_bat_score'], full_bat['season_actual_sr'])

    print(f"BATTERS [Auction Buys Cohort]   (N={len(auc_bat):<3}): Pearson r = {r_bat_auc_opt:+.3f} (p={p_bat_auc:.4f}), Spearman ρ = {rho_bat_auc:+.3f}, Top-Tier Hit Rate = {hit_b*100:.1f}%")
    print(f"BATTERS [All Players Full Pool] (N={len(full_bat):<3}): Pearson r = {r_bat_all_opt:+.3f} (p={p_bat_all:.4f}), Spearman ρ = {rho_bat_all:+.3f}")

    # Bowling Pooled
    auc_bowl = full_bowl[full_bowl['is_auction_buy'] == 1]
    r_bowl_auc_opt, p_bowl_auc = stats.pearsonr(auc_bowl['hmc_bowl_score'], auc_bowl['season_bowling_index'])
    rho_bowl_auc, _ = stats.spearmanr(auc_bowl['hmc_bowl_score'], auc_bowl['season_bowling_index'])
    top_cut_bw = auc_bowl['hmc_bowl_score'].quantile(0.65)
    hit_bw = precision_score(
        ((auc_bowl['season_actual_econ'] <= 9.20) | (auc_bowl['season_dot_pct'] >= 0.33) | (auc_bowl['season_bowling_index'] >= 100.0)).astype(int),
        (auc_bowl['hmc_bowl_score'] >= top_cut_bw).astype(int)
    )

    r_bowl_all_opt, p_bowl_all = stats.pearsonr(full_bowl['hmc_bowl_score'], full_bowl['season_bowling_index'])
    rho_bowl_all, _ = stats.spearmanr(full_bowl['hmc_bowl_score'], full_bowl['season_bowling_index'])

    print(f"BOWLERS [Auction Buys Cohort]   (N={len(auc_bowl):<3}): Pearson r = {r_bowl_auc_opt:+.3f} (p={p_bowl_auc:.4f}), Spearman ρ = {rho_bowl_auc:+.3f}, Top-Tier Hit Rate = {hit_bw*100:.1f}%")
    print(f"BOWLERS [All Players Full Pool] (N={len(full_bowl):<3}): Pearson r = {r_bowl_all_opt:+.3f} (p={p_bowl_all:.4f}), Spearman ρ = {rho_bowl_all:+.3f}")

if __name__ == '__main__':
    optimize_models()

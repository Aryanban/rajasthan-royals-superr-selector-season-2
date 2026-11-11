import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import precision_score

def run_detailed_report():
    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    df['date'] = pd.to_datetime(df['match_date'])
    df['year'] = df['date'].dt.year

    df['phase'] = np.where(df['overid'] < 6, 'powerplay', np.where(df['overid'] < 16, 'middle', 'death'))
    df['is_dot'] = (df['ball_total_runs'] == 0).astype(int)
    df['is_boundary'] = (df['is_four'] | df['is_six']).astype(int)

    phase_stats = df.groupby('phase').agg(
        exp_runs=('ball_total_runs', 'mean')
    ).to_dict(orient='index')
    df['phase_exp_runs'] = df['phase'].map(lambda p: phase_stats[p]['exp_runs'])
    df['runs_saved_vs_par'] = df['phase_exp_runs'] - df['ball_total_runs']

    mapping = pd.read_csv("competition_team_player_mapping.csv")
    ipl_comps = mapping[mapping['comp_name'].str.contains('IPL', case=False, na=False)].copy()
    ipl_comps['year'] = ipl_comps['comp_name'].str.extract(r'(\d{4})')[0].astype(int)
    p_team_year = ipl_comps[['player_id', 'player_name', 'team_name', 'year']].drop_duplicates()
    player_names = p_team_year.drop_duplicates('player_id').set_index('player_id')['player_name'].to_dict()

    cycles = [2023, 2024, 2025, 2026]

    bat_records = []
    bowl_records = []

    for target_year in cycles:
        prev_year = target_year - 1
        hist_df = df[df['year'] < target_year].copy()
        target_ipl = df[(df['year'] == target_year) & (df['comp_name'].str.contains('IPL', case=False, na=False))].copy()

        hist_df['recency_w'] = np.exp(-0.20 * (target_year - hist_df['year']))

        curr_teams = p_team_year[p_team_year['year'] == target_year]
        prev_teams = p_team_year[p_team_year['year'] == prev_year]
        m_teams = curr_teams.merge(prev_teams, on='player_id', how='left', suffixes=('_curr', '_prev'))
        auction_buys = m_teams[(m_teams['team_name_prev'].isna()) | (m_teams['team_name_curr'] != m_teams['team_name_prev'])]
        auction_buy_ids = set(auction_buys['player_id'].unique())
        curr_team_map = curr_teams.set_index('player_id')['team_name'].to_dict()
        prev_team_map = prev_teams.set_index('player_id')['team_name'].to_dict()

        # Batting
        hist_df['w_balls'] = hist_df['is_legal_ball'] * hist_df['recency_w']
        hist_df['w_runs'] = hist_df['runs'] * hist_df['recency_w']
        hist_df['w_bounds'] = hist_df['is_boundary'] * hist_df['recency_w']
        hist_df['w_dots'] = hist_df['is_dot'] * hist_df['recency_w']
        hist_df['w_wpa'] = hist_df['delta_wp_bat'] * hist_df['recency_w']

        b_all = hist_df.groupby('striker_id').agg(
            overall_balls=('w_balls', 'sum'),
            overall_runs=('w_runs', 'sum')
        ).reset_index()
        b_all['overall_sr'] = (b_all['overall_runs'] / np.maximum(b_all['overall_balls'], 1)) * 100.0

        h_hp = hist_df[hist_df['is_high_pressure']].copy()
        b_clutch = h_hp.groupby('striker_id').agg(
            clutch_balls=('w_balls', 'sum'),
            clutch_runs=('w_runs', 'sum'),
            clutch_bounds=('w_bounds', 'sum'),
            clutch_dots=('w_dots', 'sum'),
            clutch_wpa=('w_wpa', 'sum'),
            raw_balls=('is_legal_ball', 'sum'),
            raw_runs=('runs', 'sum')
        ).reset_index()

        b_feat = b_all.merge(b_clutch, on='striker_id', how='inner')
        lg_sr = (b_feat['clutch_runs'].sum() / b_feat['clutch_balls'].sum()) * 100.0
        lg_bound = b_feat['clutch_bounds'].sum() / b_feat['clutch_balls'].sum()

        K_b = 15.0
        b_feat['raw_clutch_sr'] = (b_feat['raw_runs'] / np.maximum(b_feat['raw_balls'], 1)) * 100.0
        b_feat['shrunk_clutch_sr'] = (b_feat['clutch_runs'] * 100.0 + K_b * lg_sr) / (b_feat['clutch_balls'] + K_b)
        b_feat['shrunk_bound_pct'] = (b_feat['clutch_bounds'] + K_b * lg_bound) / (b_feat['clutch_balls'] + K_b)
        b_feat['wpa_per_100'] = (b_feat['clutch_wpa'] / np.maximum(b_feat['clutch_balls'], 1)) * 100.0

        K_own = 12.0
        K_lg = 8.0
        b_feat['dual_shrunk_sr'] = (b_feat['clutch_runs'] * 100.0 + K_own * b_feat['overall_sr'] + K_lg * lg_sr) / (b_feat['clutch_balls'] + K_own + K_lg)

        b_feat['acp_bat_score'] = (
            (b_feat['dual_shrunk_sr'] / 140.0) * 0.55 +
            (b_feat['shrunk_bound_pct'] / 0.18) * 0.25 +
            (1.0 - (b_feat['clutch_dots'] / np.maximum(b_feat['clutch_balls'], 1))) * 0.15 +
            np.clip(b_feat['wpa_per_100'] / 4.0, -0.5, 1.5) * 0.05
        ) * 100.0

        t_hp_b = target_ipl[target_ipl['is_high_pressure']].groupby('striker_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('runs', 'sum'),
            season_bounds=('is_boundary', 'sum'),
            season_wpa=('delta_wp_bat', 'sum')
        ).reset_index()
        t_hp_b['season_actual_sr'] = (t_hp_b['season_runs'] / np.maximum(t_hp_b['season_balls'], 1)) * 100.0

        m_b = t_hp_b.merge(b_feat, on='striker_id', how='inner')
        m_b['is_auction_buy'] = m_b['striker_id'].isin(auction_buy_ids).astype(int)
        m_b['player_name'] = m_b['striker_id'].map(player_names)
        m_b['target_year'] = target_year
        m_b['curr_team'] = m_b['striker_id'].map(curr_team_map)
        m_b['prev_team'] = m_b['striker_id'].map(prev_team_map).fillna('New to IPL')

        q_b = m_b[(m_b['raw_balls'] >= 25) & (m_b['season_balls'] >= 15)].copy()
        bat_records.append(q_b)

        # Bowling
        h_hp_bw = hist_df[hist_df['is_high_pressure']].copy()
        h_hp_bw['w_balls'] = h_hp_bw['is_legal_ball'] * h_hp_bw['recency_w']
        h_hp_bw['w_runs'] = h_hp_bw['ball_total_runs'] * h_hp_bw['recency_w']
        h_hp_bw['w_dots'] = h_hp_bw['is_dot'] * h_hp_bw['recency_w']
        h_hp_bw['w_bounds'] = h_hp_bw['is_boundary'] * h_hp_bw['recency_w']
        h_hp_bw['w_wkts'] = h_hp_bw['is_wicket'] * h_hp_bw['recency_w']
        h_hp_bw['w_surplus'] = h_hp_bw['runs_saved_vs_par'] * h_hp_bw['recency_w']
        
        bw_agg = h_hp_bw.groupby('bowler_id').agg(
            clutch_balls=('w_balls', 'sum'),
            clutch_runs=('w_runs', 'sum'),
            clutch_dots=('w_dots', 'sum'),
            clutch_bounds=('w_bounds', 'sum'),
            clutch_wkts=('w_wkts', 'sum'),
            clutch_surplus=('w_surplus', 'sum'),
            raw_balls=('is_legal_ball', 'sum'),
            raw_runs=('ball_total_runs', 'sum')
        ).reset_index()

        lg_bw_dot = bw_agg['clutch_dots'].sum() / bw_agg['clutch_balls'].sum()
        lg_bw_bound = bw_agg['clutch_bounds'].sum() / bw_agg['clutch_balls'].sum()
        lg_bw_wkt = bw_agg['clutch_wkts'].sum() / bw_agg['clutch_balls'].sum()
        lg_bw_econ = (bw_agg['clutch_runs'].sum() / bw_agg['clutch_balls'].sum()) * 6.0

        K_bw = 20.0
        bw_agg['raw_econ'] = (bw_agg['raw_runs'] / np.maximum(bw_agg['raw_balls'], 1)) * 6.0
        bw_agg['shrunk_econ'] = (bw_agg['clutch_runs'] * 6.0 + K_bw * lg_bw_econ) / (bw_agg['clutch_balls'] + K_bw)
        bw_agg['shrunk_dot_pct'] = (bw_agg['clutch_dots'] + K_bw * lg_bw_dot) / (bw_agg['clutch_balls'] + K_bw)
        bw_agg['shrunk_wkt_rate'] = (bw_agg['clutch_wkts'] + K_bw * lg_bw_wkt) / (bw_agg['clutch_balls'] + K_bw)

        bw_agg['acp_bowl_score'] = (
            (bw_agg['shrunk_dot_pct'] / 0.35) * 0.40 +
            ((bw_agg['clutch_balls'] - bw_agg['clutch_bounds']) / np.maximum(bw_agg['clutch_balls'], 1) / 0.82) * 0.25 +
            np.clip((9.5 - bw_agg['shrunk_econ']) / 1.5, -0.5, 1.5) * 0.20 +
            (bw_agg['shrunk_wkt_rate'] / 0.055) * 0.15
        ) * 100.0

        target_ipl['is_dot'] = (target_ipl['ball_total_runs'] == 0).astype(int)
        target_ipl['is_boundary'] = (target_ipl['is_four'] | target_ipl['is_six']).astype(int)
        t_hp_bw = target_ipl[target_ipl['is_high_pressure']].groupby('bowler_id').agg(
            season_balls=('is_legal_ball', 'sum'),
            season_runs=('ball_total_runs', 'sum'),
            season_dots=('is_dot', 'sum'),
            season_bounds=('is_boundary', 'sum'),
            season_wkts=('is_wicket', 'sum')
        ).reset_index()

        t_hp_bw['season_actual_econ'] = (t_hp_bw['season_runs'] / np.maximum(t_hp_bw['season_balls'], 1)) * 6.0
        t_hp_bw['season_dot_pct'] = t_hp_bw['season_dots'] / np.maximum(t_hp_bw['season_balls'], 1)
        t_hp_bw['season_bowling_index'] = (
            (t_hp_bw['season_dot_pct'] / 0.35) * 0.40 +
            ((1.0 - (t_hp_bw['season_bounds'] / np.maximum(t_hp_bw['season_balls'], 1))) / 0.82) * 0.25 +
            np.clip((9.5 - t_hp_bw['season_actual_econ']) / 1.5, -0.5, 1.5) * 0.20 +
            ((t_hp_bw['season_wkts'] / np.maximum(t_hp_bw['season_balls'], 1)) / 0.055) * 0.15
        ) * 100.0

        m_bw = t_hp_bw.merge(bw_agg, on='bowler_id', how='inner')
        m_bw['is_auction_buy'] = m_bw['bowler_id'].isin(auction_buy_ids).astype(int)
        m_bw['player_name'] = m_bw['bowler_id'].map(player_names)
        m_bw['target_year'] = target_year
        m_bw['curr_team'] = m_bw['bowler_id'].map(curr_team_map)
        m_bw['prev_team'] = m_bw['bowler_id'].map(prev_team_map).fillna('New to IPL')

        q_bw = m_bw[(m_bw['raw_balls'] >= 25) & (m_bw['season_balls'] >= 18)].copy()
        bowl_records.append(q_bw)

    full_bat = pd.concat(bat_records, ignore_index=True)
    full_bowl = pd.concat(bowl_records, ignore_index=True)

    print("\n" + "=" * 105)
    print("TEST 1: AUCTION BUYS ROLLING TEMPORAL BACKTEST (OUT-OF-SAMPLE)")
    print("=" * 105)
    print(f"{'Year':<5} | {'Role':<7} | {'Buys (N)':<8} | {'Baseline r':<11} | {'Shrunk r':<9} | {'Composite r':<12} | {'Spearman ρ':<11} | {'Top Hit Rate'}")
    print("-" * 105)

    for yr in cycles:
        # Batting
        b_yr = full_bat[(full_bat['target_year'] == yr) & (full_bat['is_auction_buy'] == 1)]
        r_b_raw, _ = stats.pearsonr(b_yr['raw_clutch_sr'], b_yr['season_actual_sr'])
        r_b_shrunk, _ = stats.pearsonr(b_yr['shrunk_clutch_sr'], b_yr['season_actual_sr'])
        r_b_comp, _ = stats.pearsonr(b_yr['acp_bat_score'], b_yr['season_actual_sr'])
        rho_b_comp, _ = stats.spearmanr(b_yr['acp_bat_score'], b_yr['season_actual_sr'])
        top_cut_b = b_yr['acp_bat_score'].quantile(0.65)
        hit_b = precision_score((b_yr['season_actual_sr'] >= 145.0).astype(int), (b_yr['acp_bat_score'] >= top_cut_b).astype(int), zero_division=0)

        # Bowling
        bw_yr = full_bowl[(full_bowl['target_year'] == yr) & (full_bowl['is_auction_buy'] == 1)]
        r_bw_raw, _ = stats.pearsonr(-bw_yr['raw_econ'], -bw_yr['season_actual_econ'])
        r_bw_dot, _ = stats.pearsonr(bw_yr['shrunk_dot_pct'], bw_yr['season_dot_pct'])
        r_bw_comp, _ = stats.pearsonr(bw_yr['acp_bowl_score'], bw_yr['season_bowling_index'])
        rho_bw_comp, _ = stats.spearmanr(bw_yr['acp_bowl_score'], bw_yr['season_bowling_index'])
        top_cut_bw = bw_yr['acp_bowl_score'].quantile(0.65)
        hit_bw = precision_score(((bw_yr['season_actual_econ'] <= 9.20) | (bw_yr['season_dot_pct'] >= 0.33)).astype(int), (bw_yr['acp_bowl_score'] >= top_cut_bw).astype(int), zero_division=0)

        print(f"{yr:<5} | {'Bat':<7} | {len(b_yr):<8} | {r_b_raw:+11.3f} | {r_b_shrunk:+9.3f} | {r_b_comp:+12.3f} | {rho_b_comp:+11.3f} | {hit_b*100.0:>11.1f}%")
        print(f"{yr:<5} | {'Bowl':<7} | {len(bw_yr):<8} | {r_bw_raw:+11.3f} | {r_bw_dot:+9.3f} | {r_bw_comp:+12.3f} | {rho_bw_comp:+11.3f} | {hit_bw*100.0:>11.1f}%")
        print("-" * 105)

    print("\n" + "=" * 105)
    print("TEST 2: CUMULATIVE HISTORICAL LAGGED PREDICTIVE TEST (ALL PLAYERS FULL POOL)")
    print("=" * 105)
    print(f"{'Year':<5} | {'Role':<7} | {'Players(N)':<10} | {'Baseline r':<11} | {'Shrunk r':<9} | {'Composite r':<12} | {'Spearman ρ':<11} | {'Top Hit Rate'}")
    print("-" * 105)

    for yr in cycles:
        b_all = full_bat[full_bat['target_year'] == yr]
        r_b_raw, _ = stats.pearsonr(b_all['raw_clutch_sr'], b_all['season_actual_sr'])
        r_b_shrunk, _ = stats.pearsonr(b_all['shrunk_clutch_sr'], b_all['season_actual_sr'])
        r_b_comp, _ = stats.pearsonr(b_all['acp_bat_score'], b_all['season_actual_sr'])
        rho_b_comp, _ = stats.spearmanr(b_all['acp_bat_score'], b_all['season_actual_sr'])
        top_cut_b = b_all['acp_bat_score'].quantile(0.65)
        hit_b = precision_score((b_all['season_actual_sr'] >= 145.0).astype(int), (b_all['acp_bat_score'] >= top_cut_b).astype(int), zero_division=0)

        bw_all = full_bowl[full_bowl['target_year'] == yr]
        r_bw_raw, _ = stats.pearsonr(-bw_all['raw_econ'], -bw_all['season_actual_econ'])
        r_bw_dot, _ = stats.pearsonr(bw_all['shrunk_dot_pct'], bw_all['season_dot_pct'])
        r_bw_comp, _ = stats.pearsonr(bw_all['acp_bowl_score'], bw_all['season_bowling_index'])
        rho_bw_comp, _ = stats.spearmanr(bw_all['acp_bowl_score'], bw_all['season_bowling_index'])
        top_cut_bw = bw_all['acp_bowl_score'].quantile(0.65)
        hit_bw = precision_score(((bw_all['season_actual_econ'] <= 9.20) | (bw_all['season_dot_pct'] >= 0.33)).astype(int), (bw_all['acp_bowl_score'] >= top_cut_bw).astype(int), zero_division=0)

        print(f"{yr:<5} | {'Bat':<7} | {len(b_all):<10} | {r_b_raw:+11.3f} | {r_b_shrunk:+9.3f} | {r_b_comp:+12.3f} | {rho_b_comp:+11.3f} | {hit_b*100.0:>11.1f}%")
        print(f"{yr:<5} | {'Bowl':<7} | {len(bw_all):<10} | {r_bw_raw:+11.3f} | {r_bw_dot:+9.3f} | {r_bw_comp:+12.3f} | {rho_bw_comp:+11.3f} | {hit_bw*100.0:>11.1f}%")
        print("-" * 105)

    print("\n" + "=" * 105)
    print("DETAILED VERIFICATION: KEY AUCTION BUYS CASE STUDIES")
    print("=" * 105)
    # Print verified auction buys
    auc_bats = full_bat[full_bat['is_auction_buy'] == 1]
    for yr in [2024, 2025, 2026]:
        print(f"\n--- AUCTION CYCLE {yr} (INTO IPL {yr}) ---")
        sub_b = auc_bats[auc_bats['target_year'] == yr].sort_values('acp_bat_score', ascending=False).head(4)
        for _, r in sub_b.iterrows():
            print(f"  [Batter] {r['player_name']:<22} | {r['prev_team']} -> {r['curr_team']} | Pre-SR: {r['shrunk_clutch_sr']:.1f} | Season Actual SR: {r['season_actual_sr']:.1f} (Balls: {r['season_balls']:.0f})")

        sub_bw = full_bowl[(full_bowl['target_year'] == yr) & (full_bowl['is_auction_buy'] == 1)].sort_values('acp_bowl_score', ascending=False).head(4)
        for _, r in sub_bw.iterrows():
            print(f"  [Bowler] {r['player_name']:<22} | {r['prev_team']} -> {r['curr_team']} | Pre-Dot%: {r['shrunk_dot_pct']*100:.1f}% | Season Actual Econ: {r['season_actual_econ']:.2f} (Dot%: {r['season_dot_pct']*100:.1f}%)")


if __name__ == '__main__':
    run_detailed_report()

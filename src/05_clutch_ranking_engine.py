import os
import pandas as pd
import numpy as np

def run_clutch_ranking_engine():
    print("=" * 85)
    print("RAJASTHAN ROYALS CLUTCH RANKING ENGINE (FULLY OPTIMIZED & DECAY CALIBRATED)")
    print("Zero Outliers | 140/120-Ball Sample Confidence | 2026 Active In-Season Factor")
    print("=" * 85)

    print("--> Loading match clutch data and delivery telemetry...")
    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    df['year'] = pd.to_datetime(df['match_date']).dt.year
    df['is_dot'] = (df['ball_total_runs'] == 0).astype(int)
    df['is_boundary'] = (df['is_four'] | df['is_six']).astype(int)
    df['is_ipl'] = df['comp_name'].str.contains('IPL', case=False, na=False)

    # 1. League Quality Factor: IPL = 1.0, non-IPL = 0.10 (90% discount)
    df['comp_quality'] = np.where(df['is_ipl'], 1.0, 0.10)

    # 2. Steep Exponential Recency: Half-life = 1 season
    MAX_YEAR = 2026
    LAMBDA = 0.693147
    df['season_weight'] = np.exp(-LAMBDA * (MAX_YEAR - df['year']))
    df['deliv_w'] = df['season_weight'] * df['comp_quality']

    # Phase par benchmarking strictly on IPL environment
    ipl_df = df[df['is_ipl']].copy()
    ipl_df['phase'] = np.where(ipl_df['overid'] < 6, 'powerplay', np.where(ipl_df['overid'] < 16, 'middle', 'death'))
    phase_stats = ipl_df.groupby('phase')['ball_total_runs'].mean().to_dict()
    df['phase'] = np.where(df['overid'] < 6, 'powerplay', np.where(df['overid'] < 16, 'middle', 'death'))
    df['phase_exp_runs'] = df['phase'].map(phase_stats)
    df['runs_saved_vs_par'] = df['phase_exp_runs'] - df['ball_total_runs']

    h_hp = df[df['pressure_index'] >= 6.0].copy()

    # 2026 IPL specific telemetry
    ipl_26 = h_hp[(h_hp['is_ipl']) & (h_hp['year'] == 2026)]
    balls_26_bat = ipl_26.groupby('striker_id')['is_legal_ball'].sum().to_dict()
    runs_26_bat = ipl_26.groupby('striker_id')['runs'].sum().to_dict()
    balls_26_bowl = ipl_26.groupby('bowler_id')['is_legal_ball'].sum().to_dict()
    runs_26_bowl = ipl_26.groupby('bowler_id')['ball_total_runs'].sum().to_dict()

    # =========================================================================
    # 1. BOWLERS
    # =========================================================================
    h_hp['w_balls_bw'] = h_hp['is_legal_ball'] * h_hp['deliv_w']
    h_hp['w_runs_bw'] = h_hp['ball_total_runs'] * h_hp['deliv_w']
    h_hp['w_dots_bw'] = h_hp['is_dot'] * h_hp['deliv_w']
    h_hp['w_bounds_bw'] = h_hp['is_boundary'] * h_hp['deliv_w']
    h_hp['w_surplus_bw'] = h_hp['runs_saved_vs_par'] * h_hp['deliv_w']
    h_hp['w_wpa_bw'] = h_hp['delta_wp_bowl'] * h_hp['deliv_w']

    bowl_summary = h_hp.groupby(['bowler_id', 'bowler_name']).agg(
        pressure_matches=('match_id', 'nunique'),
        total_clutch_balls=('is_legal_ball', 'sum'),
        total_clutch_runs=('ball_total_runs', 'sum'),
        total_clutch_wickets=('is_wicket', 'sum'),
        total_clutch_wpa=('delta_wp_bowl', 'sum'),
        eff_balls=('w_balls_bw', 'sum'),
        eff_runs=('w_runs_bw', 'sum'),
        eff_dots=('w_dots_bw', 'sum'),
        eff_bounds=('w_bounds_bw', 'sum'),
        eff_surplus=('w_surplus_bw', 'sum'),
        eff_wpa=('w_wpa_bw', 'sum'),
    ).reset_index()

    bowl_summary['b26_balls'] = bowl_summary['bowler_id'].map(balls_26_bowl).fillna(0)
    bowl_summary['b26_runs'] = bowl_summary['bowler_id'].map(runs_26_bowl).fillna(0)
    bowl_summary['b26_econ'] = (bowl_summary['b26_runs'] / np.maximum(bowl_summary['b26_balls'], 1)) * 6.0

    K_SHRINKAGE = 40.0
    lg_dot = bowl_summary['eff_dots'].sum() / np.maximum(bowl_summary['eff_balls'].sum(), 1)
    lg_bound = bowl_summary['eff_bounds'].sum() / np.maximum(bowl_summary['eff_balls'].sum(), 1)
    lg_surplus = bowl_summary['eff_surplus'].sum() / np.maximum(bowl_summary['eff_balls'].sum(), 1)

    bowl_summary['shrunk_dot'] = (bowl_summary['eff_dots'] + K_SHRINKAGE * lg_dot) / (bowl_summary['eff_balls'] + K_SHRINKAGE)
    bowl_summary['shrunk_avoid'] = (bowl_summary['eff_balls'] - bowl_summary['eff_bounds'] + K_SHRINKAGE * (1.0 - lg_bound)) / (bowl_summary['eff_balls'] + K_SHRINKAGE)
    bowl_summary['shrunk_surplus'] = (bowl_summary['eff_surplus'] + K_SHRINKAGE * lg_surplus) / (bowl_summary['eff_balls'] + K_SHRINKAGE)
    bowl_summary['rec_clutch_econ'] = (bowl_summary['eff_runs'] / np.maximum(bowl_summary['eff_balls'], 1)) * 6.0
    bowl_summary['clutch_economy'] = (bowl_summary['total_clutch_runs'] / np.maximum(bowl_summary['total_clutch_balls'], 1)) * 6.0

    all_bowl = df.groupby('bowler_id').agg(
        all_balls=('is_legal_ball', 'sum'),
        all_runs=('ball_total_runs', 'sum'),
        low_balls=('is_low_pressure', 'sum'),
        low_runs=('ball_total_runs', lambda x: x[df.loc[x.index, 'is_low_pressure']].sum())
    ).reset_index()
    all_bowl['overall_economy'] = (all_bowl['all_runs'] / np.maximum(all_bowl['all_balls'], 1)) * 6.0
    all_bowl['normal_economy'] = (all_bowl['low_runs'] / np.maximum(all_bowl['low_balls'], 1)) * 6.0
    bowl_summary = bowl_summary.merge(all_bowl, on='bowler_id', how='left')
    bowl_summary['economy_delta'] = bowl_summary['normal_economy'] - bowl_summary['clutch_economy']

    death_balls = df[df['overid'] >= 16].groupby('bowler_id')['is_legal_ball'].sum().reset_index()
    death_balls.columns = ['bowler_id', 'death_balls']
    pp_balls = df[df['overid'] <= 6].groupby('bowler_id')['is_legal_ball'].sum().reset_index()
    pp_balls.columns = ['bowler_id', 'pp_balls']
    bowl_summary = bowl_summary.merge(death_balls, on='bowler_id', how='left').merge(pp_balls, on='bowler_id', how='left').fillna({'death_balls': 0, 'pp_balls': 0, 'all_balls': 1})

    def get_bowl_archetype(row):
        total = row['all_balls']
        if total == 0:
            return "Middle-Phase Hunter"
        if row['death_balls'] / total >= 0.35:
            return "Death Executioner"
        elif row['pp_balls'] / total >= 0.40:
            return "Powerplay Containment"
        else:
            return "Middle-Phase Hunter"

    bowl_summary['archetype'] = bowl_summary.apply(get_bowl_archetype, axis=1)

    norm_dot = np.clip((bowl_summary['shrunk_dot'] - 0.25) / 0.15 * 10.0, 0.0, 10.0)
    norm_avoid = np.clip((bowl_summary['shrunk_avoid'] - 0.75) / 0.15 * 10.0, 0.0, 10.0)
    norm_surplus = np.clip((bowl_summary['shrunk_surplus'] + 0.15) / 0.45 * 10.0, 0.0, 10.0)
    raw_quality_bowl = norm_dot * 0.45 + norm_avoid * 0.35 + norm_surplus * 0.20

    # 180 effective balls required for full confidence (prevents small-sample outliers like Saurabh Dubey)
    bowl_summary['sample_confidence'] = np.clip(bowl_summary['eff_balls'] / 180.0, 0.0, 1.0)

    # Proven Clutch Durability / Experience Scaling: +20% bonus for seasoned workhorses (180 to 480+ balls)
    bowl_summary['durability_bonus'] = 1.0 + 0.20 * np.clip((bowl_summary['eff_balls'] - 180.0) / 300.0, 0.0, 1.0)

    # Multi-season continuity and pedigree
    ipl_deliv = df[df['comp_name'].str.contains('IPL', na=False)]
    bowl_seasons = ipl_deliv.groupby('bowler_id')['comp_name'].nunique().to_dict()
    bowl_24_25 = ipl_deliv[ipl_deliv['comp_name'].isin(['IPL 2024', 'IPL 2025'])].groupby('bowler_id')['is_legal_ball'].sum().to_dict()
    bowl_summary['ipl_seasons'] = bowl_summary['bowler_id'].map(bowl_seasons).fillna(0)
    bowl_summary['balls_24_25'] = bowl_summary['bowler_id'].map(bowl_24_25).fillna(0)

    def get_bowl_continuity(row):
        if row['b26_balls'] >= 30 and row['balls_24_25'] == 0:
            if row['ipl_seasons'] > 1: # Absent during 2024-2025 hiatus (Holder)
                return 0.80
        return 1.00

    bowl_summary['continuity_factor'] = bowl_summary.apply(get_bowl_continuity, axis=1)
    bowl_summary['pedigree_bonus'] = 1.0 + 0.05 * np.clip(bowl_summary['ipl_seasons'] - 1.0, 0.0, 3.0)
    bowl_summary['reg_factor'] = np.clip(bowl_summary['b26_balls'] / 140.0, 0.70, 1.0)

    def get_bowl_factor(row):
        if row['b26_balls'] >= 140:
            if row['b26_econ'] > 11.0:
                return 0.70 # Severe collapse (Harshal Patel 12.56)
            elif row['b26_econ'] > 10.0:
                return 0.85
            elif row['b26_econ'] < 8.0:
                return 1.10 # Surge bonus (Narine 6.91, Bhuvi 7.76)
            else:
                return 1.00
        elif row['b26_balls'] >= 40:
            if row['b26_econ'] > 11.0:
                return 0.70
            else:
                return 1.00
        else:
            return 0.60 # Inactive in 2026 IPL (Mustafizur, Wood, Gowtham)

    bowl_summary['form_factor'] = bowl_summary.apply(get_bowl_factor, axis=1)
    bowl_summary['composite_score_a'] = (
        raw_quality_bowl * bowl_summary['sample_confidence'] * bowl_summary['form_factor'] *
        bowl_summary['durability_bonus'] * bowl_summary['reg_factor'] *
        bowl_summary['continuity_factor'] * bowl_summary['pedigree_bonus']
    )
    bowl_summary['composite_score_b'] = bowl_summary['composite_score_a']

    # Backwards compatibility
    bowl_summary['mean_mcr'] = bowl_summary['eff_wpa'] / np.maximum(bowl_summary['eff_balls'], 1)
    bowl_summary['std_mcr'] = 1.0
    bowl_summary['win_matches'] = (bowl_summary['pressure_matches'] * 0.55).astype(int)
    bowl_summary['motm_count'] = 0
    bowl_summary['clutch_win_rate'] = 0.55
    bowl_summary['shrunk_mcr_model_a'] = bowl_summary['composite_score_a']
    bowl_summary['shrunk_mcr_model_b'] = bowl_summary['composite_score_b']
    bowl_summary['composite_score_career'] = norm_dot * 0.60 + norm_avoid * 0.40
    bowl_summary['composite_score_recency'] = bowl_summary['composite_score_a']

    # =========================================================================
    # 2. BATTERS
    # =========================================================================
    h_hp['w_balls_bat'] = h_hp['is_legal_ball'] * h_hp['deliv_w']
    h_hp['w_runs_bat'] = h_hp['runs'] * h_hp['deliv_w']
    h_hp['w_wpa_bat'] = h_hp['delta_wp_bat'] * h_hp['deliv_w']

    bat_summary = h_hp.groupby(['striker_id', 'striker_name']).agg(
        pressure_matches=('match_id', 'nunique'),
        total_clutch_balls=('is_legal_ball', 'sum'),
        total_clutch_runs=('runs', 'sum'),
        total_clutch_wpa=('delta_wp_bat', 'sum'),
        eff_balls=('w_balls_bat', 'sum'),
        eff_runs=('w_runs_bat', 'sum'),
        eff_wpa=('w_wpa_bat', 'sum'),
    ).reset_index()

    bat_summary['b26_balls'] = bat_summary['striker_id'].map(balls_26_bat).fillna(0)
    bat_summary['b26_runs'] = bat_summary['striker_id'].map(runs_26_bat).fillna(0)
    bat_summary['b26_sr'] = (bat_summary['b26_runs'] / np.maximum(bat_summary['b26_balls'], 1)) * 100.0

    lg_sr = (bat_summary['eff_runs'].sum() / np.maximum(bat_summary['eff_balls'].sum(), 1)) * 100.0
    bat_summary['rec_clutch_sr'] = (bat_summary['eff_runs'] / np.maximum(bat_summary['eff_balls'], 1)) * 100.0
    bat_summary['shrunk_rec_sr'] = (bat_summary['eff_runs'] * 100.0 + K_SHRINKAGE * lg_sr) / (bat_summary['eff_balls'] + K_SHRINKAGE)
    bat_summary['wpa_rate_per_100'] = (bat_summary['eff_wpa'] / np.maximum(bat_summary['eff_balls'], 1)) * 100.0

    all_bat = df.groupby('striker_id').agg(
        all_balls=('is_legal_ball', 'sum'),
        all_runs=('runs', 'sum'),
        low_balls=('is_low_pressure', 'sum'),
        low_runs=('runs', lambda x: x[df.loc[x.index, 'is_low_pressure']].sum())
    ).reset_index()
    all_bat['overall_strike_rate'] = (all_bat['all_runs'] / np.maximum(all_bat['all_balls'], 1)) * 100.0
    all_bat['normal_strike_rate'] = (all_bat['low_runs'] / np.maximum(all_bat['low_balls'], 1)) * 100.0
    bat_summary = bat_summary.merge(all_bat, on='striker_id', how='left')
    bat_summary['clutch_strike_rate'] = (bat_summary['total_clutch_runs'] / np.maximum(bat_summary['total_clutch_balls'], 1)) * 100.0
    bat_summary['strike_rate_delta'] = bat_summary['clutch_strike_rate'] - bat_summary['normal_strike_rate']

    primary_order = df.groupby('striker_id')['batting_order'].median().reset_index()
    primary_order.columns = ['striker_id', 'median_batting_order']
    bat_summary = bat_summary.merge(primary_order, on='striker_id', how='left')

    def get_bat_archetype(order):
        if order <= 3.0:
            return "Top-Order Accelerator"
        elif order <= 5.5:
            return "Middle-Order Crisis Rebuilder"
        else:
            return "Death Finisher"

    bat_summary['archetype'] = bat_summary['median_batting_order'].apply(get_bat_archetype)

    norm_sr = np.clip((bat_summary['shrunk_rec_sr'] - 120.0) / 8.0, 0.0, 10.0)
    norm_wpa = np.clip((bat_summary['wpa_rate_per_100'] + 0.5) * 4.0, 0.0, 10.0)
    raw_quality_bat = norm_sr * 0.70 + norm_wpa * 0.30

    # 180 effective balls required for full confidence (prevents small-sample outliers)
    bat_summary['sample_confidence'] = np.clip(bat_summary['eff_balls'] / 180.0, 0.0, 1.0)

    # Proven Clutch Durability / Experience Scaling: +20% bonus for seasoned workhorses (180 to 480+ balls)
    bat_summary['durability_bonus'] = 1.0 + 0.20 * np.clip((bat_summary['eff_balls'] - 180.0) / 300.0, 0.0, 1.0)

    # Multi-season continuity and pedigree
    ipl_deliv = df[df['comp_name'].str.contains('IPL', na=False)]
    bat_seasons = ipl_deliv.groupby('striker_id')['comp_name'].nunique().to_dict()
    bat_24_25 = ipl_deliv[ipl_deliv['comp_name'].isin(['IPL 2024', 'IPL 2025'])].groupby('striker_id')['is_legal_ball'].sum().to_dict()
    bat_summary['ipl_seasons'] = bat_summary['striker_id'].map(bat_seasons).fillna(0)
    bat_summary['balls_24_25'] = bat_summary['striker_id'].map(bat_24_25).fillna(0)

    def get_bat_continuity(row):
        if row['b26_balls'] >= 30 and row['balls_24_25'] == 0:
            if row['ipl_seasons'] > 1: # Absent during hiatus
                return 0.80
        return 1.00

    bat_summary['continuity_factor'] = bat_summary.apply(get_bat_continuity, axis=1)
    bat_summary['pedigree_bonus'] = 1.0 + 0.05 * np.clip(bat_summary['ipl_seasons'] - 1.0, 0.0, 3.0)
    bat_summary['reg_factor'] = np.clip(bat_summary['b26_balls'] / 140.0, 0.70, 1.0)

    def get_bat_factor(row):
        if row['b26_balls'] >= 120:
            if row['b26_sr'] >= 200.0:
                return 1.10 # Surge bonus (Arya, Abhishek, Patidar, Sooryavanshi)
            elif row['b26_sr'] < 160.0:
                return 0.80 # Slump penalty (Suryakumar Yadav 157)
            else:
                return 1.00
        elif row['b26_balls'] >= 40:
            if row['b26_sr'] < 150.0:
                return 0.80
            else:
                return 1.00
        else:
            return 0.60 # Inactive in 2026 IPL (Russell, Jake Fraser-McGurk)

    bat_summary['form_factor'] = bat_summary.apply(get_bat_factor, axis=1)
    bat_summary['composite_score_a'] = (
        raw_quality_bat * bat_summary['sample_confidence'] * bat_summary['form_factor'] *
        bat_summary['durability_bonus'] * bat_summary['reg_factor'] *
        bat_summary['continuity_factor'] * bat_summary['pedigree_bonus']
    )
    bat_summary['composite_score_b'] = bat_summary['composite_score_a']

    # Backwards compatibility
    bat_summary['mean_mcr'] = bat_summary['eff_wpa'] / np.maximum(bat_summary['eff_balls'], 1)
    bat_summary['std_mcr'] = 1.0
    bat_summary['win_matches'] = (bat_summary['pressure_matches'] * 0.55).astype(int)
    bat_summary['motm_count'] = 0
    bat_summary['clutch_win_rate'] = 0.55
    bat_summary['shrunk_mcr_model_a'] = bat_summary['composite_score_a']
    bat_summary['shrunk_mcr_model_b'] = bat_summary['composite_score_b']
    bat_summary['composite_score_career'] = norm_sr * 0.70 + norm_wpa * 0.30
    bat_summary['composite_score_recency'] = bat_summary['composite_score_a']

    # Save parquets
    bat_summary.to_parquet("data/player_clutch_batting.parquet", index=False)
    bowl_summary.to_parquet("data/player_clutch_bowling.parquet", index=False)
    print("--> Successfully updated and saved fully optimized clutch ratings!")

if __name__ == '__main__':
    run_clutch_ranking_engine()

import os
import pandas as pd
import numpy as np

def run_clutch_ranking_engine():
    print("=" * 85)
    print("RAJASTHAN ROYALS CLUTCH RANKING ENGINE (FULLY CALIBRATED & BIAS/VARIANCE OPTIMIZED)")
    print("Zero Outliers | Wicket Quality | Opponent Scaling | Consistency CV | Dot-Ball Control | Era-Norm")
    print("Non-Boundary SR (Calib 6) | Superlinear Over 19-20 Leverage (Calib 7) | Dew Index (Calib 8)")
    print("Fielding-Independent Pitching xFIP (Calib 10) | Matchup Versatility (Calib 11) | Elasticity (Calib 12)")
    print("=" * 85)

    print("--> Loading match clutch data and delivery telemetry...")
    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    df['year'] = pd.to_datetime(df['match_date']).dt.year
    df['is_dot'] = (df['ball_total_runs'] == 0).astype(int)
    df['is_boundary'] = (df['is_four'] | df['is_six']).astype(int)
    df['is_non_boundary'] = (~df['is_boundary'].astype(bool) & df['is_legal_ball'].astype(bool)).astype(int)
    df['non_boundary_runs'] = np.where(df['is_non_boundary'] == 1, df['runs'], 0)
    df['is_ipl'] = df['comp_name'].str.contains('IPL', case=False, na=False)

    # 1. League Quality Factor: IPL = 1.0, non-IPL = 0.10 (90% discount)
    df['comp_quality'] = np.where(df['is_ipl'], 1.0, 0.10)

    # 2. Steep Exponential Recency: Half-life = 1 season
    MAX_YEAR = 2026
    LAMBDA = 0.693147
    df['season_weight'] = np.exp(-LAMBDA * (MAX_YEAR - df['year']))

    # 3. High-Stakes Match-Importance Leverage (Playoffs 1.2x, Finals 1.5x)
    df['match_importance_weight'] = df['match_importance'].fillna(1.0)

    # 4. Innings 2 Chasing Asymmetry Factor (1.15x for chasing targets)
    df['chase_multiplier'] = np.where(df['innings'] == 2, 1.15, 1.00)

    # 5. Era Normalization: IPL RPO by season (Impact Player Rule Era Correction)
    season_rpo = df[df['is_ipl']].groupby('year')['ball_total_runs'].mean() * 6.0
    era_map = season_rpo.to_dict()
    mean_era = 8.80
    df['era_factor'] = df['year'].map(era_map).fillna(mean_era) / mean_era

    # 6. Opponent Quality / Strength of Schedule Facing Adjustment (kappa_opp)
    try:
        bowl_scores = pd.read_parquet('data/player_clutch_bowling.parquet').set_index('bowler_id')['composite_score_a'].to_dict()
        bat_scores = pd.read_parquet('data/player_clutch_batting.parquet').set_index('striker_id')['composite_score_a'].to_dict()
    except Exception:
        bowl_scores, bat_scores = {}, {}

    df['opp_bowl_score'] = df['bowler_id'].map(bowl_scores).fillna(2.0)
    df['opp_bat_score'] = df['striker_id'].map(bat_scores).fillna(2.5)

    df['kappa_bat'] = 1.0 + 0.05 * np.clip((df['opp_bowl_score'] - 2.0) / 4.0, -1.0, 1.0)
    df['kappa_bowl'] = 1.0 + 0.05 * np.clip((df['opp_bat_score'] - 2.5) / 4.0, -1.0, 1.0)

    # 7. Wicket Quality & Dismissal Leverage Attribution
    df['wkt_quality_weight'] = np.where(df['batting_order'] <= 4, 1.20, np.where(df['batting_order'] <= 7, 1.00, 0.60))
    df['is_striker_out'] = (df['dismissed_player_id'] == df['striker_id']).astype(int)
    df['is_bowler_wkt'] = (df['is_wicket'] & ~df['dismissal_type'].isin(['RunOut', 'Retire Out', 'Obstracting the field', 'Obstructing the field'])).astype(int)
    df['quality_bowler_wkt'] = df['is_bowler_wkt'] * df['wkt_quality_weight']

    # Calibration 10: Clean wickets (Fielding-Independent Pitching)
    clean_types = {'Bowled', 'LBW', 'Stump', 'Hit Wicket'}
    df['is_clean_wkt'] = (df['is_bowler_wkt'] == 1) & (df['dismissal_type'].isin(clean_types)).astype(int)

    # 8. Calibration 7: Continuous Superlinear Leverage Escalation for PI >= 6.0
    df['superlinear_pi'] = np.where(df['pressure_index'] >= 6.0, (df['pressure_index'] / 6.0) ** 1.20, 1.0)

    # 9. Calibration 8: Day/Night Dew & Second-Innings Ball-Slickness Index
    df['is_dew_phase'] = (df['innings'] == 2) & (df['overid'] >= 14)
    df['dew_boost'] = np.where(df['is_dew_phase'], 0.15, 0.0) # ~0.90 RPO

    # 10. Venue-Par Environmental Pitch Benchmark & Phase Benchmarking with Era & Dew adjustment
    df['venue_ball_par'] = (df['venue_par'] / 120.0) * df['era_factor'] + df['dew_boost']
    ipl_df = df[df['is_ipl']].copy()
    ipl_df['phase'] = np.where(ipl_df['overid'] < 6, 'powerplay', np.where(ipl_df['overid'] < 16, 'middle', 'death'))
    phase_stats = ipl_df.groupby('phase')['ball_total_runs'].mean().to_dict()
    df['phase'] = np.where(df['overid'] < 6, 'powerplay', np.where(df['overid'] < 16, 'middle', 'death'))
    df['phase_exp_runs'] = df['phase'].map(phase_stats) * df['era_factor'] + df['dew_boost']

    df['runs_saved_vs_par'] = (df['venue_ball_par'] * 0.50 + df['phase_exp_runs'] * 0.50) - df['ball_total_runs']
    df['runs_above_par'] = df['runs'] - (df['venue_ball_par'] * 0.50 + df['phase_exp_runs'] * 0.50)

    # Combined Delivery Weights with Superlinear Leverage
    df['deliv_w_bat'] = df['season_weight'] * df['comp_quality'] * df['match_importance_weight'] * df['chase_multiplier'] * df['kappa_bat'] * df['superlinear_pi']
    df['deliv_w_bowl'] = df['season_weight'] * df['comp_quality'] * df['match_importance_weight'] * df['chase_multiplier'] * df['kappa_bowl'] * df['superlinear_pi']

    # Granular Bowling Style (Calibration 11)
    def classify_bowler_style(bt):
        if pd.isna(bt): return 'RAP'
        bt = str(bt).lower()
        if 'left-arm leg' in bt or 'chinaman' in bt or 'wrist' in bt or 'leg-break' in bt:
            return 'WristSpin'
        elif 'offbreak' in bt or 'orthodox' in bt or 'finger' in bt:
            return 'FingerSpin'
        elif 'left-arm' in bt:
            return 'LAP'
        else:
            return 'RAP'

    df['bowl_style_gran'] = df['bowling_type'].apply(classify_bowler_style)

    h_hp = df[df['pressure_index'] >= 6.0].copy()
    low_hp = df[df['pressure_index'] < 4.5].copy()

    # Match-to-Match Consistency Telemetry (CV calculation)
    match_bat = h_hp[h_hp['is_legal_ball'] == 1].groupby(['striker_id', 'match_id']).agg(
        m_runs=('runs', 'sum'),
        m_balls=('runs', 'count')
    ).reset_index()
    match_bat = match_bat[match_bat['m_balls'] >= 6]
    match_bat['m_sr'] = (match_bat['m_runs'] / match_bat['m_balls']) * 100.0
    bat_cv = match_bat.groupby('striker_id')['m_sr'].agg(['mean', 'std']).reset_index()
    bat_cv['cv_sr'] = (bat_cv['std'] / np.maximum(bat_cv['mean'], 1.0)).fillna(0.40)
    bat_cv_map = bat_cv.set_index('striker_id')['cv_sr'].to_dict()

    match_bowl = h_hp[h_hp['is_legal_ball'] == 1].groupby(['bowler_id', 'match_id']).agg(
        m_runs=('ball_total_runs', 'sum'),
        m_balls=('is_legal_ball', 'count')
    ).reset_index()
    match_bowl = match_bowl[match_bowl['m_balls'] >= 6]
    match_bowl['m_econ'] = (match_bowl['m_runs'] / match_bowl['m_balls']) * 6.0
    bowl_cv = match_bowl.groupby('bowler_id')['m_econ'].agg(['mean', 'std']).reset_index()
    bowl_cv['cv_econ'] = (bowl_cv['std'] / np.maximum(bowl_cv['mean'], 1.0)).fillna(0.45)
    bowl_cv_map = bowl_cv.set_index('bowler_id')['cv_econ'].to_dict()

    # 2026 IPL specific telemetry
    ipl_26 = h_hp[(h_hp['is_ipl']) & (h_hp['year'] == 2026)]
    balls_26_bat = ipl_26.groupby('striker_id')['is_legal_ball'].sum().to_dict()
    runs_26_bat = ipl_26.groupby('striker_id')['runs'].sum().to_dict()
    outs_26_bat = ipl_26.groupby('striker_id')['is_striker_out'].sum().to_dict()
    balls_26_bowl = ipl_26.groupby('bowler_id')['is_legal_ball'].sum().to_dict()
    runs_26_bowl = ipl_26.groupby('bowler_id')['ball_total_runs'].sum().to_dict()
    wkts_26_bowl = ipl_26.groupby('bowler_id')['is_bowler_wkt'].sum().to_dict()

    # =========================================================================
    # 1. BOWLERS
    # =========================================================================
    h_hp['w_balls_bw'] = h_hp['is_legal_ball'] * h_hp['deliv_w_bowl']
    h_hp['w_runs_bw'] = h_hp['ball_total_runs'] * h_hp['deliv_w_bowl']
    h_hp['w_wkts_bw'] = h_hp['quality_bowler_wkt'] * h_hp['deliv_w_bowl']
    h_hp['w_clean_wkts_bw'] = h_hp['is_clean_wkt'] * h_hp['deliv_w_bowl']
    h_hp['w_dots_bw'] = h_hp['is_dot'] * h_hp['deliv_w_bowl']
    h_hp['w_bounds_bw'] = h_hp['is_boundary'] * h_hp['deliv_w_bowl']
    h_hp['w_surplus_bw'] = h_hp['runs_saved_vs_par'] * h_hp['deliv_w_bowl']
    h_hp['w_wpa_bw'] = h_hp['delta_wp_bowl'] * h_hp['deliv_w_bowl']

    # Platoon splits: vs RHB vs LHB (Calibration 11)
    h_hp['w_balls_rhb'] = (h_hp['batting_type'] == 'RHB') * h_hp['w_balls_bw']
    h_hp['w_runs_rhb'] = (h_hp['batting_type'] == 'RHB') * h_hp['w_runs_bw']
    h_hp['w_balls_lhb'] = (h_hp['batting_type'] == 'LHB') * h_hp['w_balls_bw']
    h_hp['w_runs_lhb'] = (h_hp['batting_type'] == 'LHB') * h_hp['w_runs_bw']

    bowl_summary = h_hp.groupby(['bowler_id', 'bowler_name']).agg(
        pressure_matches=('match_id', 'nunique'),
        total_clutch_balls=('is_legal_ball', 'sum'),
        total_clutch_runs=('ball_total_runs', 'sum'),
        total_clutch_wickets=('is_bowler_wkt', 'sum'),
        total_clutch_wpa=('delta_wp_bowl', 'sum'),
        eff_balls=('w_balls_bw', 'sum'),
        eff_runs=('w_runs_bw', 'sum'),
        eff_wkts=('w_wkts_bw', 'sum'),
        eff_clean_wkts=('w_clean_wkts_bw', 'sum'),
        eff_dots=('w_dots_bw', 'sum'),
        eff_bounds=('w_bounds_bw', 'sum'),
        eff_surplus=('w_surplus_bw', 'sum'),
        eff_wpa=('w_wpa_bw', 'sum'),
        eff_balls_rhb=('w_balls_rhb', 'sum'),
        eff_runs_rhb=('w_runs_rhb', 'sum'),
        eff_balls_lhb=('w_balls_lhb', 'sum'),
        eff_runs_lhb=('w_runs_lhb', 'sum'),
    ).reset_index()

    bowl_summary['b26_balls'] = bowl_summary['bowler_id'].map(balls_26_bowl).fillna(0)
    bowl_summary['b26_runs'] = bowl_summary['bowler_id'].map(runs_26_bowl).fillna(0)
    bowl_summary['b26_wkts'] = bowl_summary['bowler_id'].map(wkts_26_bowl).fillna(0)
    bowl_summary['b26_econ'] = (bowl_summary['b26_runs'] / np.maximum(bowl_summary['b26_balls'], 1)) * 6.0

    K_SHRINKAGE_BOWL = 50.0
    lg_dot = bowl_summary['eff_dots'].sum() / np.maximum(bowl_summary['eff_balls'].sum(), 1)
    lg_bound = bowl_summary['eff_bounds'].sum() / np.maximum(bowl_summary['eff_balls'].sum(), 1)
    lg_surplus = bowl_summary['eff_surplus'].sum() / np.maximum(bowl_summary['eff_balls'].sum(), 1)
    lg_wkt_rate = (bowl_summary['eff_wkts'].sum() / np.maximum(bowl_summary['eff_balls'].sum(), 1)) * 100.0
    lg_bowl_avg = bowl_summary['eff_runs'].sum() / np.maximum(bowl_summary['eff_wkts'].sum(), 1)

    K_WKTS = 5.0
    bowl_summary['shrunk_dot'] = (bowl_summary['eff_dots'] + K_SHRINKAGE_BOWL * lg_dot) / (bowl_summary['eff_balls'] + K_SHRINKAGE_BOWL)
    bowl_summary['shrunk_avoid'] = (bowl_summary['eff_balls'] - bowl_summary['eff_bounds'] + K_SHRINKAGE_BOWL * (1.0 - lg_bound)) / (bowl_summary['eff_balls'] + K_SHRINKAGE_BOWL)
    bowl_summary['shrunk_surplus'] = (bowl_summary['eff_surplus'] + K_SHRINKAGE_BOWL * lg_surplus) / (bowl_summary['eff_balls'] + K_SHRINKAGE_BOWL)
    bowl_summary['rec_clutch_econ'] = (bowl_summary['eff_runs'] / np.maximum(bowl_summary['eff_balls'], 1)) * 6.0
    bowl_summary['clutch_economy'] = (bowl_summary['total_clutch_runs'] / np.maximum(bowl_summary['total_clutch_balls'], 1)) * 6.0

    bowl_summary['shrunk_wkt_rate'] = (bowl_summary['eff_wkts'] * 100.0 + K_SHRINKAGE_BOWL * (lg_wkt_rate / 100.0) * 100.0) / (bowl_summary['eff_balls'] + K_SHRINKAGE_BOWL)
    bowl_summary['shrunk_balls_per_wkt'] = 100.0 / np.maximum(bowl_summary['shrunk_wkt_rate'], 1e-4)
    bowl_summary['rec_clutch_sr'] = bowl_summary['eff_balls'] / np.maximum(bowl_summary['eff_wkts'], 1)
    bowl_summary['rec_clutch_bowl_avg'] = bowl_summary['eff_runs'] / np.maximum(bowl_summary['eff_wkts'], 1)
    bowl_summary['shrunk_bowl_avg'] = (bowl_summary['eff_runs'] + K_WKTS * lg_bowl_avg) / (bowl_summary['eff_wkts'] + K_WKTS)

    # Calibration 10: Fielding-Independent Pitching (xFIP) & Clean Wicket Rate Factor
    lg_clean_pct = bowl_summary['eff_clean_wkts'].sum() / np.maximum(bowl_summary['eff_wkts'].sum(), 1)
    bowl_summary['shrunk_clean_wkt_pct'] = (bowl_summary['eff_clean_wkts'] + 5.0 * lg_clean_pct) / (bowl_summary['eff_wkts'] + 5.0)
    bowl_summary['xfip_factor'] = 1.0 + 0.08 * np.clip((bowl_summary['shrunk_clean_wkt_pct'] - lg_clean_pct) / lg_clean_pct, -1.0, 1.0)

    # Calibration 11: Platoon Neutrality Factor (Bowlers vs RHB/LHB)
    bowl_summary['econ_rhb'] = (bowl_summary['eff_runs_rhb'] / np.maximum(bowl_summary['eff_balls_rhb'], 1.0)) * 6.0
    bowl_summary['econ_lhb'] = (bowl_summary['eff_runs_lhb'] / np.maximum(bowl_summary['eff_balls_lhb'], 1.0)) * 6.0
    bowl_summary['platoon_split'] = np.abs(bowl_summary['econ_rhb'] - bowl_summary['econ_lhb'])
    bowl_summary['platoon_neutrality_factor'] = 1.0 + 0.05 * np.clip((2.0 - bowl_summary['platoon_split']) / 2.0, -1.0, 1.0)

    # Calibration 12: Scoreboard Pressure Elasticity (Bowlers)
    b_low = low_hp.groupby('bowler_id').agg(low_balls=('is_legal_ball', 'sum'), low_runs=('ball_total_runs', 'sum'))
    b_low['low_econ'] = (b_low['low_runs'] / np.maximum(b_low['low_balls'], 1)) * 6.0
    bowl_summary = bowl_summary.merge(b_low, on='bowler_id', how='left').fillna({'low_balls': 0, 'low_runs': 0, 'low_econ': 8.5})
    bowl_summary['raw_elasticity'] = (bowl_summary['low_econ'] - bowl_summary['rec_clutch_econ']) / np.maximum(bowl_summary['low_econ'], 6.0)
    bowl_summary['shrunk_elasticity'] = (bowl_summary['eff_balls'] / (bowl_summary['eff_balls'] + 60.0)) * bowl_summary['raw_elasticity']
    bowl_summary['elasticity_factor'] = 1.0 + 0.05 * np.clip(bowl_summary['shrunk_elasticity'], -0.30, 0.30)

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
    norm_strike = np.clip((bowl_summary['shrunk_wkt_rate'] - 3.33) / 5.0 * 10.0, 0.0, 10.0)
    norm_bowl_avg = np.clip((42.0 - bowl_summary['shrunk_bowl_avg']) / 24.0 * 10.0, 0.0, 10.0)

    raw_quality_bowl = norm_dot * 0.25 + norm_avoid * 0.20 + norm_surplus * 0.20 + norm_strike * 0.20 + norm_bowl_avg * 0.15

    # 350 effective balls required for full confidence (scaled for superlinear volume)
    bowl_summary['sample_confidence'] = np.clip(bowl_summary['eff_balls'] / 350.0, 0.0, 1.0)
    bowl_summary['durability_bonus'] = 1.0 + 0.20 * np.clip((bowl_summary['eff_balls'] - 350.0) / 450.0, 0.0, 1.0)

    ipl_deliv = df[df['comp_name'].str.contains('IPL', na=False)]
    bowl_seasons = ipl_deliv.groupby('bowler_id')['comp_name'].nunique().to_dict()
    bowl_24_25 = ipl_deliv[ipl_deliv['comp_name'].isin(['IPL 2024', 'IPL 2025'])].groupby('bowler_id')['is_legal_ball'].sum().to_dict()
    bowl_summary['ipl_seasons'] = bowl_summary['bowler_id'].map(bowl_seasons).fillna(0)
    bowl_summary['balls_24_25'] = bowl_summary['bowler_id'].map(bowl_24_25).fillna(0)

    def get_bowl_continuity(row):
        if row['b26_balls'] >= 30 and row['balls_24_25'] == 0:
            if row['ipl_seasons'] > 1: return 0.80
        return 1.00

    bowl_summary['continuity_factor'] = bowl_summary.apply(get_bowl_continuity, axis=1)
    bowl_summary['pedigree_bonus'] = 1.0 + 0.05 * np.clip(bowl_summary['ipl_seasons'] - 1.0, 0.0, 3.0)
    bowl_summary['reg_factor'] = np.clip(bowl_summary['b26_balls'] / 140.0, 0.65, 1.0)

    def get_bowl_factor(row):
        if row['b26_balls'] >= 140:
            if row['b26_econ'] > 11.0: return 0.70
            elif row['b26_econ'] > 10.0: return 0.85
            elif row['b26_econ'] < 8.0: return 1.10
            else: return 1.00
        elif row['b26_balls'] >= 40:
            if row['b26_econ'] > 11.0: return 0.70
            else: return 1.00
        else: return 0.60

    bowl_summary['form_factor'] = bowl_summary.apply(get_bowl_factor, axis=1)

    # Consistency stability factor (Variance Reduction)
    bowl_summary['cv_econ'] = bowl_summary['bowler_id'].map(bowl_cv_map).fillna(0.45)
    bowl_summary['stability_factor'] = 1.0 + 0.10 * np.clip((0.45 - bowl_summary['cv_econ']) / 0.20, -1.0, 1.0)

    # Composite Score with Calibrations 10, 11 & 12
    bowl_summary['composite_score_a'] = (
        raw_quality_bowl * bowl_summary['sample_confidence'] * bowl_summary['form_factor'] *
        bowl_summary['durability_bonus'] * bowl_summary['reg_factor'] *
        bowl_summary['continuity_factor'] * bowl_summary['pedigree_bonus'] *
        bowl_summary['stability_factor'] * bowl_summary['xfip_factor'] *
        bowl_summary['platoon_neutrality_factor'] * bowl_summary['elasticity_factor']
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
    h_hp['w_balls_bat'] = h_hp['is_legal_ball'] * h_hp['deliv_w_bat']
    h_hp['w_runs_bat'] = h_hp['runs'] * h_hp['deliv_w_bat']
    h_hp['w_outs_bat'] = h_hp['is_striker_out'] * h_hp['deliv_w_bat']
    h_hp['w_wpa_bat'] = h_hp['delta_wp_bat'] * h_hp['deliv_w_bat']
    h_hp['w_surplus_bat'] = h_hp['runs_above_par'] * h_hp['deliv_w_bat']
    h_hp['w_dots_bat'] = h_hp['is_dot'] * h_hp['deliv_w_bat']
    h_hp['w_non_bound_balls'] = h_hp['is_non_boundary'] * h_hp['deliv_w_bat']
    h_hp['w_non_bound_runs'] = h_hp['non_boundary_runs'] * h_hp['deliv_w_bat']

    # Granular Matchup Splits: RAP, LAP, WristSpin, FingerSpin (Calibration 11)
    for style in ['RAP', 'LAP', 'WristSpin', 'FingerSpin']:
        h_hp[f'w_balls_{style}'] = (h_hp['bowl_style_gran'] == style) * h_hp['w_balls_bat']
        h_hp[f'w_runs_{style}'] = (h_hp['bowl_style_gran'] == style) * h_hp['w_runs_bat']

    bat_summary = h_hp.groupby(['striker_id', 'striker_name']).agg(
        pressure_matches=('match_id', 'nunique'),
        total_clutch_balls=('is_legal_ball', 'sum'),
        total_clutch_runs=('runs', 'sum'),
        total_clutch_outs=('is_striker_out', 'sum'),
        total_clutch_wpa=('delta_wp_bat', 'sum'),
        eff_balls=('w_balls_bat', 'sum'),
        eff_runs=('w_runs_bat', 'sum'),
        eff_outs=('w_outs_bat', 'sum'),
        eff_wpa=('w_wpa_bat', 'sum'),
        eff_surplus=('w_surplus_bat', 'sum'),
        eff_dots=('w_dots_bat', 'sum'),
        eff_nb_balls=('w_non_bound_balls', 'sum'),
        eff_nb_runs=('w_non_bound_runs', 'sum'),
        eff_balls_rap=('w_balls_RAP', 'sum'),
        eff_runs_rap=('w_runs_RAP', 'sum'),
        eff_balls_lap=('w_balls_LAP', 'sum'),
        eff_runs_lap=('w_runs_LAP', 'sum'),
        eff_balls_wrist=('w_balls_WristSpin', 'sum'),
        eff_runs_wrist=('w_runs_WristSpin', 'sum'),
        eff_balls_finger=('w_balls_FingerSpin', 'sum'),
        eff_runs_finger=('w_runs_FingerSpin', 'sum'),
    ).reset_index()

    bat_summary['clutch_sr_vs_spin'] = ((bat_summary['eff_runs_wrist'] + bat_summary['eff_runs_finger']) / np.maximum(bat_summary['eff_balls_wrist'] + bat_summary['eff_balls_finger'], 1)) * 100.0
    bat_summary['clutch_sr_vs_pace'] = ((bat_summary['eff_runs_rap'] + bat_summary['eff_runs_lap']) / np.maximum(bat_summary['eff_balls_rap'] + bat_summary['eff_balls_lap'], 1)) * 100.0

    bat_summary['b26_balls'] = bat_summary['striker_id'].map(balls_26_bat).fillna(0)
    bat_summary['b26_runs'] = bat_summary['striker_id'].map(runs_26_bat).fillna(0)
    bat_summary['b26_outs'] = bat_summary['striker_id'].map(outs_26_bat).fillna(0)
    bat_summary['b26_sr'] = (bat_summary['b26_runs'] / np.maximum(bat_summary['b26_balls'], 1)) * 100.0

    K_SHRINKAGE_BAT = 35.0
    lg_sr = (bat_summary['eff_runs'].sum() / np.maximum(bat_summary['eff_balls'].sum(), 1)) * 100.0
    bat_summary['rec_clutch_sr'] = (bat_summary['eff_runs'] / np.maximum(bat_summary['eff_balls'], 1)) * 100.0
    bat_summary['shrunk_rec_sr'] = (bat_summary['eff_runs'] * 100.0 + K_SHRINKAGE_BAT * lg_sr) / (bat_summary['eff_balls'] + K_SHRINKAGE_BAT)

    # Batting Average & Wicket Preservation under high pressure
    lg_avg = bat_summary['eff_runs'].sum() / np.maximum(bat_summary['eff_outs'].sum(), 1)
    K_OUTS = 5.0
    bat_summary['rec_clutch_avg'] = bat_summary['eff_runs'] / np.maximum(bat_summary['eff_outs'], 1)
    bat_summary['shrunk_rec_avg'] = (bat_summary['eff_runs'] + K_OUTS * lg_avg) / (bat_summary['eff_outs'] + K_OUTS)
    bat_summary['wpa_rate_per_100'] = (bat_summary['eff_wpa'] / np.maximum(bat_summary['eff_balls'], 1)) * 100.0
    bat_summary['surplus_per_ball'] = bat_summary['eff_surplus'] / np.maximum(bat_summary['eff_balls'], 1)

    # Calibration 6: Non-Boundary Strike Rate Factor (Variance Reduction)
    bat_summary['sr_non_bound'] = (bat_summary['eff_nb_runs'] / np.maximum(bat_summary['eff_nb_balls'], 1)) * 100.0
    bat_summary['non_bound_factor'] = 1.0 + 0.10 * np.clip((bat_summary['sr_non_bound'] - 70.0) / 25.0, -1.0, 1.0)

    # Dot-Ball Volatility Factor (Variance Reduction)
    bat_summary['dot_pct'] = bat_summary['eff_dots'] / np.maximum(bat_summary['eff_balls'], 1)
    bat_summary['dot_suppression_factor'] = 1.0 + 0.15 * np.clip((0.35 - bat_summary['dot_pct']) / 0.15, -1.0, 1.0)

    # Match-to-Match Consistency Factor (Variance Reduction)
    bat_summary['cv_sr'] = bat_summary['striker_id'].map(bat_cv_map).fillna(0.40)
    bat_summary['stability_factor'] = 1.0 + 0.10 * np.clip((0.40 - bat_summary['cv_sr']) / 0.20, -1.0, 1.0)

    # Calibration 11: Matchup Granularity & Versatility Factor (Batters)
    for style in ['rap', 'lap', 'wrist', 'finger']:
        bat_summary[f'sr_{style}'] = (bat_summary[f'eff_runs_{style}'] * 100.0 + 30.0 * bat_summary['shrunk_rec_sr']) / (bat_summary[f'eff_balls_{style}'] + 30.0)
    
    bat_summary['min_style_sr'] = bat_summary[['sr_rap', 'sr_lap', 'sr_wrist', 'sr_finger']].min(axis=1)
    bat_summary['versatility_ratio'] = bat_summary['min_style_sr'] / np.maximum(bat_summary['shrunk_rec_sr'], 120.0)
    bat_summary['versatility_factor'] = 1.0 + 0.06 * np.clip((bat_summary['versatility_ratio'] - 0.85) / 0.15, -1.0, 1.0)

    # Calibration 12: Scoreboard Pressure Elasticity (Batters)
    bat_low = low_hp.groupby('striker_id').agg(low_balls=('is_legal_ball', 'sum'), low_runs=('runs', 'sum'))
    bat_low['low_sr'] = (bat_low['low_runs'] / np.maximum(bat_low['low_balls'], 1)) * 100.0
    bat_summary = bat_summary.merge(bat_low, on='striker_id', how='left').fillna({'low_balls': 0, 'low_runs': 0, 'low_sr': 130.0})
    bat_summary['raw_elasticity'] = (bat_summary['rec_clutch_sr'] - bat_summary['low_sr']) / np.maximum(bat_summary['low_sr'], 100.0)
    bat_summary['shrunk_elasticity'] = (bat_summary['eff_balls'] / (bat_summary['eff_balls'] + 60.0)) * bat_summary['raw_elasticity']
    bat_summary['elasticity_factor'] = 1.0 + 0.05 * np.clip(bat_summary['shrunk_elasticity'], -0.30, 0.30)

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

    norm_sr = np.clip((bat_summary['shrunk_rec_sr'] - 120.0) / 8.0, 0.0, 10.0)
    norm_avg = np.clip((bat_summary['shrunk_rec_avg'] - 15.0) / 3.0, 0.0, 10.0)
    norm_wpa = np.clip((bat_summary['wpa_rate_per_100'] + 0.5) * 4.0, 0.0, 10.0)
    norm_surplus_bat = np.clip((bat_summary['surplus_per_ball'] + 0.20) / 0.60 * 10.0, 0.0, 10.0)

    raw_quality_bat = norm_sr * 0.40 + norm_avg * 0.25 + norm_wpa * 0.20 + norm_surplus_bat * 0.15

    # Positional Opportunity Normalization (scaled for superlinear volume)
    def get_expected_bat_balls(order):
        if order <= 3.5:
            return 140.0, 280.0
        elif order <= 5.5:
            return 100.0, 200.0
        else:
            return 60.0, 120.0

    bat_summary['exp_b26'], bat_summary['exp_eff'] = zip(*bat_summary['median_batting_order'].apply(get_expected_bat_balls))

    bat_summary['sample_confidence'] = np.clip(bat_summary['eff_balls'] / bat_summary['exp_eff'], 0.0, 1.0)
    bat_summary['durability_bonus'] = 1.0 + 0.20 * np.clip((bat_summary['eff_balls'] - bat_summary['exp_eff']) / (bat_summary['exp_eff'] * 1.5), 0.0, 1.0)
    bat_summary['reg_factor'] = np.clip(bat_summary['b26_balls'] / bat_summary['exp_b26'], 0.70, 1.0)

    ipl_deliv = df[df['comp_name'].str.contains('IPL', na=False)]
    bat_seasons = ipl_deliv.groupby('striker_id')['comp_name'].nunique().to_dict()
    bat_24_25 = ipl_deliv[ipl_deliv['comp_name'].isin(['IPL 2024', 'IPL 2025'])].groupby('striker_id')['is_legal_ball'].sum().to_dict()
    bat_summary['ipl_seasons'] = bat_summary['striker_id'].map(bat_seasons).fillna(0)
    bat_summary['balls_24_25'] = bat_summary['striker_id'].map(bat_24_25).fillna(0)

    def get_bat_continuity(row):
        if row['b26_balls'] >= 25 and row['balls_24_25'] == 0:
            if row['ipl_seasons'] > 1:
                return 0.80
        return 1.00

    bat_summary['continuity_factor'] = bat_summary.apply(get_bat_continuity, axis=1)
    bat_summary['pedigree_bonus'] = 1.0 + 0.05 * np.clip(bat_summary['ipl_seasons'] - 1.0, 0.0, 3.0)

    def get_bat_factor(row):
        min_surge_balls = row['exp_b26'] * 0.85
        if row['b26_balls'] >= min_surge_balls:
            if row['b26_sr'] >= 200.0:
                return 1.10
            elif row['b26_sr'] < 160.0:
                return 0.80
            else:
                return 1.00
        elif row['b26_balls'] >= row['exp_b26'] * 0.35:
            if row['b26_sr'] < 150.0:
                return 0.80
            else:
                return 1.00
        else:
            return 0.60

    bat_summary['form_factor'] = bat_summary.apply(get_bat_factor, axis=1)

    def get_refined_bat_archetype(row):
        order = row['median_batting_order']
        sr = row['rec_clutch_sr']
        avg = row['rec_clutch_avg']
        if order <= 3.0:
            if sr >= 195.0:
                return "Top-Order Boundary Destroyer"
            elif avg >= 45.0:
                return "Top-Order Anchor / Stabilizer"
            else:
                return "Top-Order Dynamic Stroke-Maker"
        elif order <= 5.5:
            if sr >= 170.0:
                return "Middle-Order Power Enforcer"
            else:
                return "Middle-Order Crisis Rebuilder"
        else:
            return "Death Finisher / Clutch Hitter"

    bat_summary['archetype'] = bat_summary.apply(get_refined_bat_archetype, axis=1)

    # Composite Score with Calibrations 10, 11 & 12
    bat_summary['composite_score_a'] = (
        raw_quality_bat * bat_summary['sample_confidence'] * bat_summary['form_factor'] *
        bat_summary['durability_bonus'] * bat_summary['reg_factor'] *
        bat_summary['continuity_factor'] * bat_summary['pedigree_bonus'] *
        bat_summary['dot_suppression_factor'] * bat_summary['stability_factor'] *
        bat_summary['non_bound_factor'] * bat_summary['versatility_factor'] *
        bat_summary['elasticity_factor']
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
    print("--> Successfully updated and saved fully calibrated clutch ratings with Calibrations 10, 11 & 12!")

if __name__ == '__main__':
    run_clutch_ranking_engine()

import os
import pandas as pd
import numpy as np
from scipy import stats

def test_clutch_persistence():
    print("=" * 70)
    print("CLUTCH PERSISTENCE & YEAR-OVER-YEAR STABILITY BACKTEST")
    print("Testing Era 1 (2022-2024) vs Era 2 (2025-2026)")
    print("=" * 70)

    bat_match = pd.read_parquet("data/match_clutch_batting.parquet")
    bowl_match = pd.read_parquet("data/match_clutch_bowling.parquet")

    bat_match['year'] = pd.to_datetime(bat_match['match_date']).dt.year
    bowl_match['year'] = pd.to_datetime(bowl_match['match_date']).dt.year

    bat_match['era'] = np.where(bat_match['year'] <= 2024, 'Era1_2022_2024', 'Era2_2025_2026')
    bowl_match['era'] = np.where(bowl_match['year'] <= 2024, 'Era1_2022_2024', 'Era2_2025_2026')

    # ==========================================
    # 1. BATTING PERSISTENCE
    # ==========================================
    print("\n--- BATTING PERSISTENCE ANALYSIS ---")
    bat_era = bat_match.groupby(['striker_id', 'striker_name', 'era']).agg(
        matches=('match_id', 'count'),
        clutch_balls=('clutch_balls_faced', 'sum'),
        clutch_runs=('clutch_runs', 'sum'),
        clutch_wpa=('clutch_wpa', 'sum'),
        mean_mcr=('match_clutch_score', 'mean'),
        total_balls=('total_balls_faced', 'sum'),
        total_runs=('total_runs', 'sum')
    ).reset_index()

    bat_era['clutch_sr'] = (bat_era['clutch_runs'] / np.maximum(bat_era['clutch_balls'], 1)) * 100.0
    bat_era['overall_sr'] = (bat_era['total_runs'] / np.maximum(bat_era['total_balls'], 1)) * 100.0
    bat_era['delta_sr'] = bat_era['clutch_sr'] - bat_era['overall_sr']

    # Pivot to compare Era 1 vs Era 2
    era1_bat = bat_era[bat_era['era'] == 'Era1_2022_2024'].set_index('striker_id')
    era2_bat = bat_era[bat_era['era'] == 'Era2_2025_2026'].set_index('striker_id')

    bat_piv = era1_bat.join(era2_bat, lsuffix='_e1', rsuffix='_e2', how='inner')
    
    # Filter for sample size threshold (at least 5 pressure matches in both eras)
    qual_bat = bat_piv[(bat_piv['matches_e1'] >= 5) & (bat_piv['matches_e2'] >= 5)].copy()
    print(f"Qualified Batters with >=5 matches in both eras: {len(qual_bat)}")

    for metric in ['mean_mcr', 'clutch_sr', 'clutch_wpa', 'delta_sr']:
        v1 = qual_bat[f'{metric}_e1']
        v2 = qual_bat[f'{metric}_e2']
        r_p, p_p = stats.pearsonr(v1, v2)
        r_s, p_s = stats.spearmanr(v1, v2)
        print(f"Metric: {metric:12s} | Pearson r: {r_p:+.3f} (p={p_p:.4f}) | Spearman rho: {r_s:+.3f} (p={p_s:.4f})")

    # ==========================================
    # 2. BOWLING PERSISTENCE
    # ==========================================
    print("\n--- BOWLING PERSISTENCE ANALYSIS ---")
    bowl_era = bowl_match.groupby(['bowler_id', 'bowler_name', 'era']).agg(
        matches=('match_id', 'count'),
        clutch_balls=('clutch_balls_bowled', 'sum'),
        clutch_runs=('clutch_runs_conceded', 'sum'),
        clutch_wickets=('clutch_wickets', 'sum'),
        clutch_wpa=('clutch_wpa', 'sum'),
        mean_mcr=('match_clutch_score', 'mean'),
        total_balls=('total_balls_bowled', 'sum'),
        total_runs=('total_runs_conceded', 'sum')
    ).reset_index()

    bowl_era['clutch_econ'] = (bowl_era['clutch_runs'] / np.maximum(bowl_era['clutch_balls'], 1)) * 6.0
    bowl_era['overall_econ'] = (bowl_era['total_runs'] / np.maximum(bowl_era['total_balls'], 1)) * 6.0
    bowl_era['delta_econ'] = bowl_era['clutch_econ'] - bowl_era['overall_econ']

    era1_bowl = bowl_era[bowl_era['era'] == 'Era1_2022_2024'].set_index('bowler_id')
    era2_bowl = bowl_era[bowl_era['era'] == 'Era2_2025_2026'].set_index('bowler_id')

    bowl_piv = era1_bowl.join(era2_bowl, lsuffix='_e1', rsuffix='_e2', how='inner')
    qual_bowl = bowl_piv[(bowl_piv['matches_e1'] >= 5) & (bowl_piv['matches_e2'] >= 5)].copy()
    print(f"Qualified Bowlers with >=5 matches in both eras: {len(qual_bowl)}")

    for metric in ['mean_mcr', 'clutch_econ', 'clutch_wpa', 'delta_econ']:
        v1 = qual_bowl[f'{metric}_e1']
        v2 = qual_bowl[f'{metric}_e2']
        r_p, p_p = stats.pearsonr(v1, v2)
        r_s, p_s = stats.spearmanr(v1, v2)
        print(f"Metric: {metric:12s} | Pearson r: {r_p:+.3f} (p={p_p:.4f}) | Spearman rho: {r_s:+.3f} (p={p_s:.4f})")

    # Let's inspect top persistent performers
    print("\n--- TOP PERSISTENT CLUTCH BATTERS (HIGH MEAN MCR IN BOTH ERAS) ---")
    top_persistent_bat = qual_bat[['striker_name_e1', 'matches_e1', 'mean_mcr_e1', 'clutch_sr_e1', 'matches_e2', 'mean_mcr_e2', 'clutch_sr_e2']].copy()
    top_persistent_bat['avg_mcr'] = (top_persistent_bat['mean_mcr_e1'] + top_persistent_bat['mean_mcr_e2']) / 2.0
    print(top_persistent_bat.sort_values(by='avg_mcr', ascending=False).head(10).to_string())

    print("\n--- TOP PERSISTENT CLUTCH BOWLERS (HIGH MEAN MCR IN BOTH ERAS) ---")
    top_persistent_bowl = qual_bowl[['bowler_name_e1', 'matches_e1', 'mean_mcr_e1', 'clutch_econ_e1', 'matches_e2', 'mean_mcr_e2', 'clutch_econ_e2']].copy()
    top_persistent_bowl['avg_mcr'] = (top_persistent_bowl['mean_mcr_e1'] + top_persistent_bowl['mean_mcr_e2']) / 2.0
    print(top_persistent_bowl.sort_values(by='avg_mcr', ascending=False).head(10).to_string())

if __name__ == "__main__":
    test_clutch_persistence()

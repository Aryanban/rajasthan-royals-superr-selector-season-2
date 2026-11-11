import os
import pandas as pd
import numpy as np

def run_ipl_awards_and_mvp_analysis():
    print("--> Loading deliveries with pressure and WPA...")
    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    print(f"Loaded {len(df)} deliveries across {df['match_id'].nunique()} matches.")

    # Filter for IPL matches
    df['is_ipl'] = df['comp_name'].str.contains('IPL', case=False, na=False)
    ipl_df = df[df['is_ipl']].copy()
    print(f"Total IPL deliveries: {len(ipl_df)} across {ipl_df['match_id'].nunique()} IPL matches.")

    # 1. Calculate Ball-by-Ball Official IPL MVP Points & Clutch-Weighted MVP (cMVP)
    # Official BCCI Formula:
    # Four: +2.5 pts, Six: +3.5 pts
    # Wicket: +7.0 pts, Dot ball: +1.0 pt
    
    # Batting MVP points on delivery t
    ipl_df['raw_bat_mvp'] = (
        (ipl_df['is_four'] * 2.5) +
        (ipl_df['is_six'] * 3.5) +
        (ipl_df['runs'] * 1.0)
    )
    # Bowling MVP points on delivery t
    ipl_df['raw_bowl_mvp'] = (
        (ipl_df['is_wicket'] * 7.0) +
        ((ipl_df['ball_total_runs'] == 0) * 1.0)
    )

    # State-of-the-Art Clutch-Weighted MVP (cMVP)
    # Every point is scaled by (PI_t / 10.0)
    ipl_df['cmvp_bat'] = ipl_df['raw_bat_mvp'] * (ipl_df['pressure_index'] / 10.0)
    ipl_df['cmvp_bowl'] = ipl_df['raw_bowl_mvp'] * (ipl_df['pressure_index'] / 10.0)

    # ==========================================
    # 2. PLAYER-LEVEL IPL MVP AGGREGATION
    # ==========================================
    print("--> Aggregating Official IPL MVP vs. Clutch MVP (cMVP)...")
    
    bat_mvp = ipl_df.groupby(['striker_id', 'striker_name']).agg(
        ipl_matches=('match_id', 'nunique'),
        total_runs=('runs', 'sum'),
        total_fours=('is_four', 'sum'),
        total_sixes=('is_six', 'sum'),
        raw_bat_mvp=('raw_bat_mvp', 'sum'),
        clutch_bat_mvp=('cmvp_bat', 'sum'),
        clutch_wpa=('delta_wp_bat', 'sum')
    ).reset_index()

    bowl_mvp = ipl_df.groupby(['bowler_id', 'bowler_name']).agg(
        ipl_matches=('match_id', 'nunique'),
        total_wickets=('is_wicket', 'sum'),
        total_dots=('ball_total_runs', lambda x: (x == 0).sum()),
        raw_bowl_mvp=('raw_bowl_mvp', 'sum'),
        clutch_bowl_mvp=('cmvp_bowl', 'sum'),
        clutch_wpa=('delta_wp_bowl', 'sum')
    ).reset_index()

    # Combine into unified All-Round MVP table
    unified_mvp = bat_mvp.merge(
        bowl_mvp, 
        left_on='striker_id', 
        right_on='bowler_id', 
        how='outer', 
        suffixes=('_bat', '_bowl')
    )

    unified_mvp['player_name'] = unified_mvp['striker_name'].combine_first(unified_mvp['bowler_name'])
    unified_mvp['total_ipl_matches'] = np.maximum(
        unified_mvp['ipl_matches_bat'].fillna(0), 
        unified_mvp['ipl_matches_bowl'].fillna(0)
    )

    unified_mvp['total_raw_mvp'] = unified_mvp['raw_bat_mvp'].fillna(0) + unified_mvp['raw_bowl_mvp'].fillna(0)
    unified_mvp['total_clutch_mvp'] = unified_mvp['clutch_bat_mvp'].fillna(0) + unified_mvp['clutch_bowl_mvp'].fillna(0)
    unified_mvp['total_wpa'] = unified_mvp['clutch_wpa_bat'].fillna(0) + unified_mvp['clutch_wpa_bowl'].fillna(0)

    # Clutch Efficiency Ratio (cMVP / Raw MVP)
    # Higher ratio = player generates their value when the stakes are highest!
    unified_mvp['clutch_efficiency'] = unified_mvp['total_clutch_mvp'] / np.maximum(unified_mvp['total_raw_mvp'], 1.0)

    # ==========================================
    # 3. OFFICIAL BCCI EMERGING PLAYER SELECTION
    # ==========================================
    print("--> Filtering Official BCCI Emerging Player Award Candidates (<= 25 IPL matches)...")
    # BCCI Rule: Player must have played <= 25 IPL matches
    emerging_df = unified_mvp[
        (unified_mvp['total_ipl_matches'] >= 5) & 
        (unified_mvp['total_ipl_matches'] <= 25)
    ].sort_values(by='total_clutch_mvp', ascending=False)

    # Save outputs
    unified_mvp.to_parquet("data/ipl_mvp_leaderboard.parquet", index=False)
    emerging_df.to_parquet("data/ipl_emerging_players.parquet", index=False)
    print("--> Successfully generated IPL MVP and Emerging Player leaderboards!")

if __name__ == "__main__":
    run_ipl_awards_and_mvp_analysis()

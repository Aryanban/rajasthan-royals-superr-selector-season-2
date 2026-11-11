import os
import pandas as pd
import numpy as np

def analyze_match_level_clutch():
    print("--> Loading deliveries with pressure and WPA...")
    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    print(f"Loaded {len(df)} deliveries across {df['match_id'].nunique()} matches.")

    # ==========================================
    # 1. BATTING MATCH CLUTCH PERFORMANCE
    # ==========================================
    print("--> Aggregating match-level batting clutch ratings...")
    
    # Filter high-pressure deliveries for clutch calculation
    clutch_df = df[df['is_high_pressure']].copy()

    # Match-level batting summary under high pressure
    bat_clutch = clutch_df.groupby(['match_id', 'striker_id', 'striker_name']).agg(
        clutch_balls_faced=('is_legal_ball', 'sum'),
        clutch_runs=('runs', 'sum'),
        clutch_fours=('is_four', 'sum'),
        clutch_sixes=('is_six', 'sum'),
        clutch_wpa=('delta_wp_bat', 'sum'),
        clutch_dismissals=('is_wicket', 'sum'),
        clutch_pressure_avg=('pressure_index', 'mean')
    ).reset_index()

    # All-delivery batting summary for baseline comparison in that match
    bat_total = df.groupby(['match_id', 'striker_id']).agg(
        total_balls_faced=('is_legal_ball', 'sum'),
        total_runs=('runs', 'sum'),
        total_wpa=('delta_wp_bat', 'sum')
    ).reset_index()

    bat_match = bat_clutch.merge(bat_total, on=['match_id', 'striker_id'], how='left')

    # Get match context (result, knockout, MOTM)
    match_meta = df[['match_id', 'match_date', 'comp_id', 'comp_name', 'comp_weight', 'knock_out', 'win_team_id', 'man_of_the_match']].drop_duplicates(subset=['match_id'])
    bat_match = bat_match.merge(match_meta, on='match_id', how='left')

    # Check if player's team won the match
    # Merge batting_team_id
    player_team_map = df[['match_id', 'striker_id', 'batting_team_id']].drop_duplicates(subset=['match_id', 'striker_id'])
    bat_match = bat_match.merge(player_team_map, on=['match_id', 'striker_id'], how='left')
    bat_match['team_won'] = (bat_match['batting_team_id'] == bat_match['win_team_id']).astype(int)

    # Check if player was Man of the Match
    bat_match['is_motm'] = (bat_match['man_of_the_match'] == bat_match['striker_name']).astype(int)

    # Calculate Batting Match Clutch Score (MCR_bat)
    # WPA is in range [-1.0, 1.0]. 
    # High clutch innings generates +0.15 to +0.60 WPA.
    # We scale WPA to 0-10, add boundary bonuses, and scale by match importance and outcome.
    def compute_bat_mcr(row):
        wpa = row['clutch_wpa']
        balls = row['clutch_balls_faced']
        runs = row['clutch_runs']
        sr = (runs / max(balls, 1)) * 100.0
        
        # Base clutch impact: WPA * 10
        base_score = wpa * 10.0
        
        # Strike rate bonus in clutch (rewarding SR > 150)
        if sr > 150.0 and balls >= 8:
            base_score += 1.0 + (sr - 150.0) / 50.0
        elif sr < 100.0 and balls >= 10:
            base_score -= 1.0 # penalty for stalling
            
        # Win conversion multiplier
        outcome_multiplier = 1.2 if row['team_won'] == 1 else 0.9
        
        # Knockout boost
        knockout_multiplier = 1.25 if row['knock_out'] else 1.0
        
        # MOTM bonus
        motm_bonus = 1.5 if row['is_motm'] == 1 else 0.0
        
        final_score = (base_score * outcome_multiplier * knockout_multiplier) + motm_bonus
        return np.clip(final_score, -5.0, 10.0)

    bat_match['match_clutch_score'] = bat_match.apply(compute_bat_mcr, axis=1)

    # ==========================================
    # 2. BOWLING MATCH CLUTCH PERFORMANCE
    # ==========================================
    print("--> Aggregating match-level bowling clutch ratings...")
    
    bowl_clutch = clutch_df.groupby(['match_id', 'bowler_id', 'bowler_name']).agg(
        clutch_balls_bowled=('is_legal_ball', 'sum'),
        clutch_runs_conceded=('ball_total_runs', 'sum'),
        clutch_wickets=('is_wicket', 'sum'),
        clutch_wpa=('delta_wp_bowl', 'sum'),
        clutch_pressure_avg=('pressure_index', 'mean')
    ).reset_index()

    bowl_total = df.groupby(['match_id', 'bowler_id']).agg(
        total_balls_bowled=('is_legal_ball', 'sum'),
        total_runs_conceded=('ball_total_runs', 'sum'),
        total_wickets=('is_wicket', 'sum'),
        total_wpa=('delta_wp_bowl', 'sum')
    ).reset_index()

    bowl_match = bowl_clutch.merge(bowl_total, on=['match_id', 'bowler_id'], how='left')
    bowl_match = bowl_match.merge(match_meta, on='match_id', how='left')

    player_bowl_team_map = df[['match_id', 'bowler_id', 'bowling_team_id']].drop_duplicates(subset=['match_id', 'bowler_id'])
    bowl_match = bowl_match.merge(player_bowl_team_map, on=['match_id', 'bowler_id'], how='left')
    bowl_match['team_won'] = (bowl_match['bowling_team_id'] == bowl_match['win_team_id']).astype(int)
    bowl_match['is_motm'] = (bowl_match['man_of_the_match'] == bowl_match['bowler_name']).astype(int)

    def compute_bowl_mcr(row):
        wpa = row['clutch_wpa']
        balls = row['clutch_balls_bowled']
        runs = row['clutch_runs_conceded']
        wickets = row['clutch_wickets']
        econ = (runs / max(balls, 1)) * 6.0
        
        base_score = wpa * 10.0
        
        # Wicket bonus in clutch moments
        base_score += wickets * 1.2
        
        # Economy reward at the death/pressure
        if econ < 7.5 and balls >= 12:
            base_score += 1.5
        elif econ > 12.0 and balls >= 12:
            base_score -= 1.0
            
        outcome_multiplier = 1.2 if row['team_won'] == 1 else 0.9
        knockout_multiplier = 1.25 if row['knock_out'] else 1.0
        motm_bonus = 1.5 if row['is_motm'] == 1 else 0.0
        
        final_score = (base_score * outcome_multiplier * knockout_multiplier) + motm_bonus
        return np.clip(final_score, -5.0, 10.0)

    bowl_match['match_clutch_score'] = bowl_match.apply(compute_bowl_mcr, axis=1)

    # Save match-level ratings
    bat_match.to_parquet("data/match_clutch_batting.parquet", index=False)
    bowl_match.to_parquet("data/match_clutch_bowling.parquet", index=False)
    print("--> Successfully created match-level clutch ratings for batting & bowling!")

if __name__ == "__main__":
    analyze_match_level_clutch()

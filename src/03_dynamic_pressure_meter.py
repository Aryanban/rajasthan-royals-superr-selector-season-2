import os
import pandas as pd
import numpy as np

def compute_dynamic_pressure_and_wpa():
    print("--> Loading deliveries with win probabilities...")
    df = pd.read_parquet("data/ball_states_with_win_prob.parquet")
    print(f"Loaded {len(df)} deliveries.")

    # Sort strictly by match, innings, ball
    df = df.sort_values(by=['match_id', 'innings', 'innings_ball_num']).reset_index(drop=True)

    # 1. Calculate Ball-by-Ball WPA (Win Probability Added)
    print("--> Computing ball-by-ball WPA (Win Probability Added)...")
    # Previous ball win probability within same match and innings
    df['prev_win_prob'] = (
        df.groupby(['match_id', 'innings'])['win_probability']
        .shift(1)
        .fillna(0.50) # start of innings is 50% baseline
    )

    # Delta WP from batting team's perspective
    df['delta_wp_bat'] = df['win_probability'] - df['prev_win_prob']
    
    # Bowling team's WPA is the inverse (if batting win prob went down, bowling win prob went up)
    df['delta_wp_bowl'] = -df['delta_wp_bat']

    # 2. Compute the In-Play Dynamic Pressure Meter PI(t)
    print("--> Computing the Dynamic In-Play Pressure Meter PI(t)...")
    # Base Tension: Binomial variance of win probability
    # Peak at 50-50 (value = 1.0); near zero at 98-2 (value ~ 0.08)
    tension = 4.0 * df['win_probability'] * (1.0 - df['win_probability'])

    # Time-Decay Urgency Multiplier
    # In over 19 (6 balls left), multiplier is high; in over 1 (120 balls left), multiplier is normalized
    balls_factor = (120.0 / (df['balls_remaining'] + 12.0)) ** 0.65

    # Raw situational pressure (scaled to ~ 0 to 10)
    raw_pi = 6.5 * tension * balls_factor

    # Incorporate match importance (IPL = 1.2x, Knockouts = 1.25x)
    importance_factor = df['match_importance'].fillna(1.0)
    
    # Final Pressure Index (strictly clipped between 0.0 and 10.0)
    df['pressure_index'] = np.clip(raw_pi * (importance_factor / 1.1), 0.5, 10.0)

    # Discrete classification zones (Optimal Cutoff PI* >= 6.0 from empirical grid search)
    df['is_high_pressure'] = df['pressure_index'] >= 6.0
    df['is_medium_pressure'] = (df['pressure_index'] >= 3.5) & (df['pressure_index'] < 6.0)
    df['is_low_pressure'] = df['pressure_index'] < 3.5

    print(f"--> Distribution of Pressure Tiers:")
    print(f"    Low Pressure (< 3.5):       {df['is_low_pressure'].mean()*100:.1f}%")
    print(f"    Medium Pressure (3.5-6.0):  {df['is_medium_pressure'].mean()*100:.1f}%")
    print(f"    High Pressure / Clutch (>= 6.0): {df['is_high_pressure'].mean()*100:.1f}% ({df['is_high_pressure'].sum()} deliveries)")

    # 3. Save output
    out_file = "data/deliveries_with_pressure_and_wpa.parquet"
    df.to_parquet(out_file, index=False)
    print(f"--> Successfully created {out_file} with dynamic pressure scores & WPA!")

if __name__ == "__main__":
    compute_dynamic_pressure_and_wpa()

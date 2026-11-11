import os
import sys
import numpy as np
import pandas as pd

def run_rr_personalization_engine():
    print("=" * 90)
    print("RAJASTHAN ROYALS TACTICAL PERSONALIZATION & MINI-AUCTION OPTIMIZATION ENGINE")
    print("Giles Lindsay, Kumar Sangakkara & Zubin Bharucha Strategy Architecture (IPL 2027)")
    print("=" * 90)

    # 1. Load Parquets and Deliveries
    df_bat = pd.read_parquet("data/player_clutch_batting.parquet")
    df_bowl = pd.read_parquet("data/player_clutch_bowling.parquet")
    df_deliv = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")

    # Untouchable Franchise Locks (Tier 0 Control Benchmark - Retained by other franchises)
    untouchables = {
        'Suryakumar Yadav', 'Nicholas Pooran', 'Jasprit Bumrah',
        'Rashid Khan', 'Sunil Narine', 'Ruturaj Gaikwad', 'Virat Kohli',
        'Rinku Singh', 'Abhishek Sharma', 'Travis Head', 'Pat Cummins', 'Axar Patel',
        'Kuldeep Yadav', 'Shubman Gill', 'Sai Sudharsan', 'Matheesha Pathirana', 'Hardik Pandya',
        # RR Already Retained Core:
        'Sanju Samson', 'Yashasvi Jaiswal', 'Riyan Parag', 'Dhruv Jurel', 'Shimron Hetmyer',
        'Sandeep Sharma', 'Vaibhav Sooryavanshi'
    }

    # Telemetry splits on SMS-like pitches (venue_par <= 175)
    df_deliv['venue_ball_par'] = df_deliv['venue_par'] / 120.0
    df_deliv['is_sms_like'] = (df_deliv['venue_par'] <= 175.0).astype(int)
    h_hp = df_deliv[df_deliv['pressure_index'] >= 6.0].copy()

    # Batting SMS metrics
    h_hp['sms_balls_bat'] = h_hp['is_sms_like'] * h_hp['is_legal_ball']
    h_hp['sms_runs_bat'] = h_hp['is_sms_like'] * h_hp['runs']
    h_hp['sms_surplus_bat'] = h_hp['is_sms_like'] * (h_hp['runs'] - h_hp['venue_ball_par'])

    bat_sms = h_hp.groupby('striker_id').agg(
        sms_balls=('sms_balls_bat', 'sum'),
        sms_runs=('sms_runs_bat', 'sum'),
        sms_surplus=('sms_surplus_bat', 'sum')
    ).reset_index()
    bat_sms['sms_sr'] = (bat_sms['sms_runs'] / np.maximum(bat_sms['sms_balls'], 1)) * 100.0
    bat_sms['sms_surplus_rate'] = bat_sms['sms_surplus'] / np.maximum(bat_sms['sms_balls'], 1)

    # Bowling SMS metrics
    h_hp['sms_balls_bw'] = h_hp['is_sms_like'] * h_hp['is_legal_ball']
    h_hp['sms_runs_bw'] = h_hp['is_sms_like'] * h_hp['ball_total_runs']
    h_hp['sms_dots_bw'] = h_hp['is_sms_like'] * (h_hp['ball_total_runs'] == 0)
    h_hp['sms_surplus_bw'] = h_hp['is_sms_like'] * (h_hp['venue_ball_par'] - h_hp['ball_total_runs'])

    bowl_sms = h_hp.groupby('bowler_id').agg(
        sms_balls=('sms_balls_bw', 'sum'),
        sms_runs=('sms_runs_bw', 'sum'),
        sms_dots=('sms_dots_bw', 'sum'),
        sms_surplus=('sms_surplus_bw', 'sum')
    ).reset_index()
    bowl_sms['sms_econ'] = (bowl_sms['sms_runs'] / np.maximum(bowl_sms['sms_balls'], 1)) * 6.0
    bowl_sms['sms_dot_pct'] = (bowl_sms['sms_dots'] / np.maximum(bowl_sms['sms_balls'], 1)) * 100.0
    bowl_sms['sms_surplus_rate'] = bowl_sms['sms_surplus'] / np.maximum(bowl_sms['sms_balls'], 1)

    df_bat = df_bat.merge(bat_sms, on='striker_id', how='left').fillna({'sms_balls': 0, 'sms_runs': 0, 'sms_surplus': 0, 'sms_sr': 140.0, 'sms_surplus_rate': 0.0})
    df_bowl = df_bowl.merge(bowl_sms, on='bowler_id', how='left').fillna({'sms_balls': 0, 'sms_runs': 0, 'sms_dots': 0, 'sms_surplus': 0, 'sms_econ': 9.0, 'sms_dot_pct': 30.0, 'sms_surplus_rate': 0.0})

    # =========================================================================
    # 1. EVALUATE BATTERS FOR RAJASTHAN ROYALS
    # =========================================================================
    bat_target_records = []
    for _, r in df_bat.iterrows():
        name = r['striker_name']
        order = r['median_batting_order']
        clutch_score = r['composite_score_a']
        sr_spin = r.get('clutch_sr_vs_spin', r['rec_clutch_sr'])
        sr_pace = r.get('clutch_sr_vs_pace', r['rec_clutch_sr'])
        sms_surplus = r['sms_surplus_rate']

        # SMS Stadium Pitch Fit Index:
        # 1. Spin-hitting mastery (55% weight for Jaipur SMS middle overs)
        # 2. Hard length boundary power (SMS surplus rate)
        norm_spin_sr = np.clip((sr_spin - 120.0) / 8.0, 0.0, 10.0)
        norm_pace_sr = np.clip((sr_pace - 130.0) / 8.0, 0.0, 10.0)
        norm_sms_surplus = np.clip((sms_surplus + 0.20) / 0.60 * 10.0, 0.0, 10.0)
        sms_pitch_fit = norm_spin_sr * 0.45 + norm_pace_sr * 0.30 + norm_sms_surplus * 0.25

        # RR 5 Squad Voids Mapping:
        if order >= 5.5:
            deficit_category = "Void 1: RHB Death Finisher (Partner for Hetmyer)"
            deficit_multiplier = 1.35
            base_price = 8.5 if clutch_score > 7.0 else 3.5
            tier = "Tier 1: Primary Must-Acquire Target" if clutch_score > 7.5 else "Tier 2: Emerging Domestic Steal"
        elif 3.5 <= order < 5.5:
            if sr_spin >= 170.0:
                deficit_category = "Void 3: Middle-Overs Spin Enforcer (#4/5)"
                deficit_multiplier = 1.30
                base_price = 10.0 if clutch_score > 8.0 else 4.5
                tier = "Tier 1: Primary Must-Acquire Target" if clutch_score > 8.0 else "Tier 2: Emerging Domestic Steal"
            else:
                deficit_category = "Middle-Order Crisis Insurance"
                deficit_multiplier = 1.15
                base_price = 7.0
                tier = "Tier 3: Tactical Depth / Trade Option"
        else:
            deficit_category = "Top-Order Depth / Jaiswal-Samson Cover"
            deficit_multiplier = 0.85 # Redundant for starting XI
            base_price = 5.0
            tier = "Tier 3: Tactical Depth / Trade Option"

        is_targetable = name not in untouchables

        # Rajasthan Royals Compatibility Index (RR-TCI)
        rr_tci = (0.50 * clutch_score + 0.30 * sms_pitch_fit + 0.20 * (norm_spin_sr * 0.60 + norm_pace_sr * 0.40)) * deficit_multiplier

        bat_target_records.append({
            'player_name': name,
            'player_id': int(r['striker_id']),
            'discipline': 'Batter',
            'tactical_archetype': r['archetype'],
            'batting_order': order,
            'global_clutch_score': round(clutch_score, 2),
            'clutch_sr_vs_spin': round(sr_spin, 1),
            'clutch_sr_vs_pace': round(sr_pace, 1),
            'sms_jaipur_pitch_fit': round(sms_pitch_fit, 2),
            'rr_squad_deficit': deficit_category,
            'rr_deficit_multiplier': deficit_multiplier,
            'rr_compatibility_index': round(rr_tci, 2),
            'auction_targetable': is_targetable,
            'auction_priority_tier': tier if is_targetable else "Untouchable (Retained Pillar)",
            'estimated_price_cr': base_price,
            'roi_value_per_cr': round(rr_tci / base_price, 2)
        })

    # =========================================================================
    # 2. EVALUATE BOWLERS FOR RAJASTHAN ROYALS
    # =========================================================================
    bowl_target_records = []
    for _, r in df_bowl.iterrows():
        name = r['bowler_name']
        arch = r['archetype']
        clutch_score = r['composite_score_a']
        sms_econ = r['sms_econ']
        sms_dots = r['sms_dot_pct']
        sms_surplus = r['sms_surplus_rate']
        death_b = r['death_balls']
        pp_b = r['pp_balls']
        total_b = r['all_balls']

        norm_sms_econ = np.clip((11.0 - sms_econ) / 5.0 * 10.0, 0.0, 10.0)
        norm_sms_dots = np.clip((sms_dots - 25.0) / 25.0 * 10.0, 0.0, 10.0)
        norm_sms_surplus = np.clip((sms_surplus + 0.15) / 0.50 * 10.0, 0.0, 10.0)
        sms_pitch_fit = norm_sms_econ * 0.40 + norm_sms_dots * 0.35 + norm_sms_surplus * 0.25

        # RR 5 Squad Voids Mapping:
        if pp_b / total_b >= 0.40:
            deficit_category = "Void 2: Powerplay Swing/Seam Partner for Sandeep"
            deficit_multiplier = 1.30
            base_price = 7.5 if clutch_score > 7.0 else 4.0
            tier = "Tier 1: Primary Must-Acquire Target" if clutch_score > 7.0 else "Tier 2: Emerging Domestic Steal"
        elif death_b / total_b >= 0.35:
            deficit_category = "Void 4: Express Death Yorker / High-Pace Enforcer"
            deficit_multiplier = 1.25
            base_price = 8.0 if clutch_score > 6.0 else 3.5
            tier = "Tier 1: Primary Must-Acquire Target" if clutch_score > 6.5 else "Tier 2: Emerging Domestic Steal"
        else:
            deficit_category = "Void 5: Mystery Spin / Middle-Overs Squeeze"
            deficit_multiplier = 1.15
            base_price = 6.0 if clutch_score > 6.0 else 3.0
            tier = "Tier 2: Emerging Domestic Steal" if clutch_score > 6.0 else "Tier 3: Tactical Depth / Trade Option"

        is_targetable = name not in untouchables

        # Rajasthan Royals Compatibility Index (RR-TCI)
        rr_tci = (0.50 * clutch_score + 0.35 * sms_pitch_fit + 0.15 * norm_sms_dots) * deficit_multiplier

        bowl_target_records.append({
            'player_name': name,
            'player_id': int(r['bowler_id']),
            'discipline': 'Bowler',
            'tactical_archetype': arch,
            'batting_order': 11.0,
            'global_clutch_score': round(clutch_score, 2),
            'clutch_sr_vs_spin': 0.0,
            'clutch_sr_vs_pace': 0.0,
            'sms_jaipur_pitch_fit': round(sms_pitch_fit, 2),
            'rr_squad_deficit': deficit_category,
            'rr_deficit_multiplier': deficit_multiplier,
            'rr_compatibility_index': round(rr_tci, 2),
            'auction_targetable': is_targetable,
            'auction_priority_tier': tier if is_targetable else "Untouchable (Retained Pillar)",
            'estimated_price_cr': base_price,
            'roi_value_per_cr': round(rr_tci / base_price, 2)
        })

    # Combine into Master Auction Target Board
    master_df = pd.DataFrame(bat_target_records + bowl_target_records)
    master_df = master_df.sort_values(by='rr_compatibility_index', ascending=False).reset_index(drop=True)

    # Save to files
    master_df.to_parquet("data/rr_personalized_target_board.parquet", index=False)
    master_df.to_csv("data/rr_personalized_target_board.csv", index=False)
    print("SUCCESS: Built master RR Personalized Auction Target Board!")
    print(f"Total evaluated players: {len(master_df)}")
    print(f"Targetable candidates: {len(master_df[master_df['auction_targetable']])}")

    # Display Top Tier 1 Must-Back Targets
    print("\n" + "=" * 90)
    print("RAJASTHAN ROYALS: TIER 1 PRIMARY MUST-ACQUIRE AUCTION TARGET BOARD")
    print("=" * 90)
    tier1 = master_df[(master_df['auction_targetable']) & (master_df['auction_priority_tier'] == 'Tier 1: Primary Must-Acquire Target')]
    cols_show = ['player_name', 'discipline', 'tactical_archetype', 'global_clutch_score', 'sms_jaipur_pitch_fit', 'rr_squad_deficit', 'rr_compatibility_index', 'estimated_price_cr', 'roi_value_per_cr']
    print(tier1[cols_show].to_string(index=False))

    return master_df

if __name__ == '__main__':
    run_rr_personalization_engine()

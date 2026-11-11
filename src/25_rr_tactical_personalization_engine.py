import os
import pandas as pd
import numpy as np

def run_rr_tactical_personalization_engine():
    print("=" * 90)
    print("RAJASTHAN ROYALS TACTICAL PERSONALIZATION & MINI-AUCTION OPTIMIZATION ENGINE")
    print("Giles Lindsay, Kumar Sangakkara & Zubin Bharucha Strategy Architecture (IPL 2027)")
    print("SMS Jaipur Pitch Compatibility | 5 Squad Voids | 2027 Aging Curve | Workload Availability (Calib 13)")
    print("=" * 90)

    # 1. Load calibrated ratings
    df_bat = pd.read_parquet("data/player_clutch_batting.parquet")
    df_bowl = pd.read_parquet("data/player_clutch_bowling.parquet")
    deliv = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")

    # 2. Extract Sawai Mansingh Stadium (Jaipur) Venue Telemetry
    deliv['venue_ball_par'] = deliv['venue_par'] / 120.0
    deliv['is_sms_like'] = (deliv['venue_par'] <= 175.0).astype(int)
    h_hp = deliv[deliv['pressure_index'] >= 6.0].copy()

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

    df_bat = df_bat.merge(bat_sms, on='striker_id', how='left').fillna({'sms_balls': 0, 'sms_sr': 135.0, 'sms_surplus_rate': 0.0})
    df_bowl = df_bowl.merge(bowl_sms, on='bowler_id', how='left').fillna({'sms_balls': 0, 'sms_econ': 8.50, 'sms_dot_pct': 33.0, 'sms_surplus_rate': 0.0})

    # Exact ages for key targets in IPL 2027
    exact_ages_2027 = {
        50284: 16, 6281: 27, 5039: 34, 25669: 26, 6396: 31, 4260: 36, 3647: 33, 8101: 29, 953: 35, 4117: 29,
        781: 39, 360: 37, 3628: 32, 4219: 36, 6256: 36, 5944: 33, 2933: 34, 7967: 22, 3298: 32, 830: 36,
        8182: 28, 6669: 28, 7216: 28, 818: 35
    }

    def get_age_2027(pid):
        if pid in exact_ages_2027:
            return exact_ages_2027[pid]
        if pid > 20000: return 23
        elif pid > 6000: return 28
        elif pid > 3000: return 32
        else: return 35

    def get_bat_aging_factor(age):
        if age <= 21: return 1.08 # Ascending developmental ceiling
        elif age <= 25: return 1.04 # Entering prime
        elif age <= 31: return 1.00 # Prime athletic peak
        elif age <= 34: return 0.98 # Experienced veteran
        elif age <= 36: return 0.94 # Late career discount
        else: return 0.90

    def get_bowl_aging_factor(age, is_spin=False):
        if age <= 23: return 1.06 # High ascending physical upside
        elif age <= 29: return 1.00 # Prime
        elif age <= 33: return 0.98
        elif age <= 35: return 0.96 if is_spin else 0.93
        else: return 0.93 if is_spin else 0.88 # Pacer physical maintenance discount

    # Calibration 13: Workload Availability & Injury Discounting (ADF)
    ipl_deliv = deliv[deliv['comp_name'].str.contains('IPL', na=False)]
    bat_ipl_matches = ipl_deliv.groupby('striker_id')['match_id'].nunique().to_dict()
    bat_ipl_seasons = ipl_deliv.groupby('striker_id')['comp_name'].nunique().to_dict()
    bowl_ipl_matches = ipl_deliv.groupby('bowler_id')['match_id'].nunique().to_dict()
    bowl_ipl_seasons = ipl_deliv.groupby('bowler_id')['comp_name'].nunique().to_dict()

    def get_availability_metrics(pid, is_bowler=False):
        if is_bowler:
            matches = bowl_ipl_matches.get(pid, 0)
            seasons = bowl_ipl_seasons.get(pid, 0)
        else:
            matches = bat_ipl_matches.get(pid, 0)
            seasons = bat_ipl_seasons.get(pid, 0)
        
        active_seasons = max(seasons, 2)
        expected = active_seasons * 14.0
        rate = matches / expected if expected > 0 else 0.0

        min_req = 40 if is_bowler else 35
        if rate >= 0.75 and matches >= min_req:
            adf = 1.03  # Iron-man durability premium
        elif rate >= 0.55:
            adf = 1.00  # Standard reliable regular
        elif rate >= 0.40:
            adf = 0.92  # Moderate fragility / squad rotation discount (-8%)
        else:
            adf = 0.84  # High injury risk / low availability discount (-16%)

        return matches, round(rate * 100.0, 1), adf

    # Untouchable locked franchise pillars
    untouchables = [
        'Sanju Samson', 'Yashasvi Jaiswal', 'Riyan Parag', 'Shimron Hetmyer',
        'Dhruv Jurel', 'Sandeep Sharma', 'Vaibhav Sooryavanshi',
        'Jasprit Bumrah', 'Sunil Narine', 'Virat Kohli', 'Rohit Sharma',
        'Nicholas Pooran', 'Hardik Pandya', 'Rashid Khan', 'Shubman Gill',
        'Rinku Singh', 'Ruturaj Gaikwad', 'Matheesha Pathirana'
    ]

    # =========================================================================
    # 1. EVALUATE BATTERS FOR RAJASTHAN ROYALS
    # =========================================================================
    bat_target_records = []
    for _, r in df_bat.iterrows():
        name = r['striker_name']
        pid = int(r['striker_id'])
        order = r['median_batting_order']
        clutch_score = r['composite_score_a']
        sr_spin = r['clutch_sr_vs_spin']
        sr_pace = r['clutch_sr_vs_pace']
        sms_surplus = r['sms_surplus_rate']

        # Age projection & Availability Discount to 2027
        age_2027 = get_age_2027(pid)
        age_factor = get_bat_aging_factor(age_2027)
        ipl_matches, avail_pct, adf = get_availability_metrics(pid, is_bowler=False)

        projected_clutch_score = clutch_score * age_factor * adf

        # SMS Jaipur Pitch Compatibility:
        norm_spin_sr = np.clip((sr_spin - 120.0) / 8.0, 0.0, 10.0)
        norm_pace_sr = np.clip((sr_pace - 130.0) / 8.0, 0.0, 10.0)
        norm_sms_surplus = np.clip((sms_surplus + 0.20) / 0.60 * 10.0, 0.0, 10.0)
        sms_pitch_fit = norm_spin_sr * 0.45 + norm_pace_sr * 0.30 + norm_sms_surplus * 0.25

        # RR 5 Squad Voids Mapping:
        if order >= 5.5:
            deficit_category = "Void 1: RHB Death Finisher (Partner for Hetmyer)"
            deficit_multiplier = 1.35
            base_price = 8.5 if projected_clutch_score > 7.0 else 3.5
            tier = "Tier 1: Primary Must-Acquire Target" if projected_clutch_score > 7.5 else "Tier 2: Emerging Domestic Steal"
        elif 3.5 <= order < 5.5:
            if sr_spin >= 170.0:
                deficit_category = "Void 3: Middle-Overs Spin Enforcer (#4/5)"
                deficit_multiplier = 1.30
                base_price = 10.0 if projected_clutch_score > 8.0 else 4.5
                tier = "Tier 1: Primary Must-Acquire Target" if projected_clutch_score > 8.0 else "Tier 2: Emerging Domestic Steal"
            else:
                deficit_category = "Middle-Order Crisis Insurance"
                deficit_multiplier = 1.15
                base_price = 7.0
                tier = "Tier 3: Tactical Depth / Trade Option"
        else:
            deficit_category = "Top-Order Depth / Jaiswal-Samson Cover"
            deficit_multiplier = 0.85
            base_price = 5.0
            tier = "Tier 3: Tactical Depth / Trade Option"

        is_targetable = name not in untouchables

        # Rajasthan Royals Compatibility Index (RR-TCI)
        rr_tci = (0.50 * projected_clutch_score + 0.30 * sms_pitch_fit + 0.20 * (norm_spin_sr * 0.60 + norm_pace_sr * 0.40)) * deficit_multiplier

        bat_target_records.append({
            'player_name': name,
            'player_id': pid,
            'discipline': 'Batter',
            'tactical_archetype': r['archetype'],
            'batting_order': order,
            'global_clutch_score': round(clutch_score, 2),
            'age_2027': age_2027,
            'age_factor_2027': round(age_factor, 2),
            'ipl_matches_played': ipl_matches,
            'ipl_availability_pct': avail_pct,
            'availability_factor_adf': round(adf, 2),
            'projected_clutch_score_2027': round(projected_clutch_score, 2),
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
    spin_ids = [781, 4219, 6256, 7967, 32862, 2687, 838]

    for _, r in df_bowl.iterrows():
        name = r['bowler_name']
        pid = int(r['bowler_id'])
        arch = r['archetype']
        clutch_score = r['composite_score_a']
        sms_econ = r['sms_econ']
        sms_dots = r['sms_dot_pct']
        sms_surplus = r['sms_surplus_rate']
        death_b = r['death_balls']
        pp_b = r['pp_balls']
        total_b = r['all_balls']

        is_spin = pid in spin_ids or 'Spin' in arch or 'Hunter' in arch
        age_2027 = get_age_2027(pid)
        age_factor = get_bowl_aging_factor(age_2027, is_spin)
        ipl_matches, avail_pct, adf = get_availability_metrics(pid, is_bowler=True)

        projected_clutch_score = clutch_score * age_factor * adf

        norm_sms_econ = np.clip((11.0 - sms_econ) / 5.0 * 10.0, 0.0, 10.0)
        norm_sms_dots = np.clip((sms_dots - 25.0) / 25.0 * 10.0, 0.0, 10.0)
        norm_sms_surplus = np.clip((sms_surplus + 0.15) / 0.50 * 10.0, 0.0, 10.0)
        sms_pitch_fit = norm_sms_econ * 0.40 + norm_sms_dots * 0.35 + norm_sms_surplus * 0.25

        # RR 5 Squad Voids Mapping:
        if pp_b / total_b >= 0.40:
            deficit_category = "Void 2: Powerplay Swing/Seam Partner for Sandeep"
            deficit_multiplier = 1.30
            base_price = 7.5 if projected_clutch_score > 6.8 else 4.0
            tier = "Tier 1: Primary Must-Acquire Target" if projected_clutch_score > 6.8 else "Tier 2: Emerging Domestic Steal"
        elif death_b / total_b >= 0.35:
            deficit_category = "Void 4: Express Death Yorker / High-Pace Enforcer"
            deficit_multiplier = 1.25
            base_price = 7.5 if projected_clutch_score > 7.0 else 4.0
            tier = "Tier 1: Primary Must-Acquire Target" if projected_clutch_score > 7.0 else "Tier 2: Emerging Domestic Steal"
        else:
            deficit_category = "Void 5: Mystery Spin / Middle-Overs Squeeze"
            deficit_multiplier = 1.20
            base_price = 6.0 if projected_clutch_score > 6.5 else 3.5
            tier = "Tier 2: Emerging Domestic Steal"

        is_targetable = name not in untouchables

        # Rajasthan Royals Compatibility Index (RR-TCI)
        rr_tci = (0.55 * projected_clutch_score + 0.30 * sms_pitch_fit + 0.15 * norm_sms_dots) * deficit_multiplier

        bowl_target_records.append({
            'player_name': name,
            'player_id': pid,
            'discipline': 'Bowler',
            'tactical_archetype': arch,
            'batting_order': 11.0,
            'global_clutch_score': round(clutch_score, 2),
            'age_2027': age_2027,
            'age_factor_2027': round(age_factor, 2),
            'ipl_matches_played': ipl_matches,
            'ipl_availability_pct': avail_pct,
            'availability_factor_adf': round(adf, 2),
            'projected_clutch_score_2027': round(projected_clutch_score, 2),
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

    # Combine
    master_targets = pd.DataFrame(bat_target_records + bowl_target_records)
    master_targets = master_targets.sort_values(by='rr_compatibility_index', ascending=False).reset_index(drop=True)

    master_targets.to_parquet("data/rr_personalized_target_board.parquet", index=False)
    master_targets.to_csv("data/rr_personalized_target_board.csv", index=False)

    print(f"SUCCESS: Built master RR Personalized Auction Target Board with 2027 Aging & Availability Discounting!")
    print(f"Total evaluated players: {len(master_targets)}")
    print(f"Targetable candidates: {master_targets['auction_targetable'].sum()}")

    print("\n" + "=" * 90)
    print("RAJASTHAN ROYALS: TIER 1 PRIMARY MUST-ACQUIRE AUCTION TARGET BOARD")
    print("=" * 90)
    t1 = master_targets[(master_targets['auction_targetable']) & (master_targets['auction_priority_tier'].str.contains('Tier 1'))].head(10)
    cols = ['player_name', 'discipline', 'tactical_archetype', 'global_clutch_score', 'age_2027', 'ipl_availability_pct', 'availability_factor_adf', 'projected_clutch_score_2027', 'sms_jaipur_pitch_fit', 'rr_compatibility_index', 'estimated_price_cr', 'roi_value_per_cr']
    print(t1[cols].to_string(index=False))

    print("\n" + "=" * 90)
    print("RAJASTHAN ROYALS: TIER 2 HIGH-VALUE DOMESTIC STEALS BOARD")
    print("=" * 90)
    t2 = master_targets[(master_targets['auction_targetable']) & (master_targets['auction_priority_tier'].str.contains('Tier 2'))].head(10)
    print(t2[cols].to_string(index=False))

if __name__ == '__main__':
    run_rr_tactical_personalization_engine()

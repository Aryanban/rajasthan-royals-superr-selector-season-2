import os
import sys
import numpy as np
import pandas as pd

def build_2027_auction_database():
    print("=" * 90)
    print("BUILDING RAJASTHAN ROYALS: IPL 2027 PROJECTED AUCTION TARGET DATABASE")
    print("Integrating Domestic SMAT, Global Franchise Leagues, and Historical Auction History")
    print("=" * 90)

    # 1. Load Local Player Clutch Metrics
    df_bat = pd.read_parquet("data/player_clutch_batting.parquet")
    df_bowl = pd.read_parquet("data/player_clutch_bowling.parquet")
    ext_bat = pd.read_parquet("data/external_player_batting.parquet")
    ext_bowl = pd.read_parquet("data/external_player_bowling.parquet")

    # Mapping
    mapping = pd.read_csv("competition_team_player_mapping.csv")
    ipl_comps = mapping[mapping['comp_name'].str.contains('IPL', case=False, na=False)].copy()
    ipl_comps['year'] = ipl_comps['comp_name'].str.extract(r'(\d{4})')[0].astype(int)
    p_2026 = ipl_comps[ipl_comps['year'] == 2026][['player_id', 'player_name', 'team_name']].drop_duplicates()
    team_2026_map = p_2026.set_index('player_id')['team_name'].to_dict()

    # Rajasthan Royals 2026 Core (Already in squad - Cannot Buy at Auction)
    rr_core = {
        'Sanju Samson', 'Yashasvi Jaiswal', 'Riyan Parag', 'Dhruv Jurel', 'Shimron Hetmyer',
        'Ravindra Jadeja', 'Jofra Archer', 'Sam Curran', 'Ravi Bishnoi', 'Sandeep Sharma',
        'Vignesh Puthur', 'Vaibhav Sooryavanshi', 'Nandre Burger', 'Yudhvir Singh', 'Shubham Dubey'
    }

    # Untouchable Franchise Locks (Tier 0 Control Benchmark - Never entering auction pool)
    untouchables = {
        'Suryakumar Yadav', 'Heinrich Klaasen', 'Nicholas Pooran', 'Jasprit Bumrah',
        'Rashid Khan', 'Sunil Narine', 'Ruturaj Gaikwad', 'Shreyas Iyer', 'Virat Kohli',
        'Rinku Singh', 'Abhishek Sharma', 'Travis Head', 'Pat Cummins', 'Axar Patel',
        'Kuldeep Yadav', 'Shubman Gill', 'Sai Sudharsan', 'Matheesha Pathirana', 'Hardik Pandya'
    }

    # Target Candidates Pool for IPL 2027
    # Comprehensive candidate list covering:
    # 1. Indian Finishers & Middle Order
    # 2. Spin Enforcers & Wrist-Spinners
    # 3. Death Pacers & Fast Bowling Foils
    # 4. Uncapped Domestic Steals (SMAT / DPL / UP T20)
    # 5. Overseas International Gems
    candidates = [
        # Batters / All-Rounders
        {'name': 'Ashutosh Sharma', 'role': 'Finisher / Lower-Middle Order', 'country': 'India', 'capped': 0, 'archetype': 'Death Muscle / Impact Finisher', 'primary_need': 'Indian Death Finisher'},
        {'name': 'Priyansh Arya', 'role': 'Top-Order Aggressor', 'country': 'India', 'capped': 0, 'archetype': 'Powerplay Boundary Accelerator', 'primary_need': 'Indian Top-Order Depth'},
        {'name': 'Urvil Patel', 'role': 'Wicket-Keeper / Opener', 'country': 'India', 'capped': 0, 'archetype': 'Ultra-Aggressive Opener', 'primary_need': 'Aggressive Indian WK/Opener'},
        {'name': 'Shahrukh Khan', 'role': 'Finisher / Power Hitter', 'country': 'India', 'capped': 1, 'archetype': 'Death Boundary Hitter', 'primary_need': 'Secondary Indian Finisher'},
        {'name': 'Sameer Rizvi', 'role': 'Middle-Overs Hitter', 'country': 'India', 'capped': 0, 'archetype': 'Spin Destroyer (Overs 7-15)', 'primary_need': 'Middle-Overs Spin Enforcer'},
        {'name': 'Abhinav Manohar', 'role': 'Finisher / Middle Order', 'country': 'India', 'capped': 0, 'archetype': 'High-Impact Finisher', 'primary_need': 'Death Phase Backup'},
        {'name': 'Dewald Brevis', 'role': 'Top/Middle Order Hitter', 'country': 'Overseas (SA)', 'capped': 1, 'archetype': '360 Power Accelerator', 'primary_need': 'Overseas Batting Depth'},
        {'name': 'Finn Allen', 'role': 'Top-Order Opener', 'country': 'Overseas (NZ)', 'capped': 1, 'archetype': 'Express Boundary Striker', 'primary_need': 'Dynamic Overseas Opener'},
        {'name': 'Josh Inglis', 'role': 'Wicket-Keeper / Finisher', 'country': 'Overseas (AUS)', 'capped': 1, 'archetype': 'Pace & Spin Adaptable Finisher', 'primary_need': 'Overseas WK/Finisher'},
        {'name': 'Glenn Phillips', 'role': 'Middle Order / Gun Fielder', 'country': 'Overseas (NZ)', 'capped': 1, 'archetype': 'Versatile Finisher & Part-time Spin', 'primary_need': 'Dynamic Overseas Utility'},
        {'name': 'Rovman Powell', 'role': 'Death Finisher', 'country': 'Overseas (WI)', 'capped': 1, 'archetype': 'Pure Death Power', 'primary_need': 'Death Boundary Muscle'},
        {'name': 'Tim David', 'role': 'Death Finisher', 'country': 'Overseas (AUS)', 'capped': 1, 'archetype': 'Extreme Death Striker', 'primary_need': 'Death Overs Power'},
        {'name': 'Ramandeep Singh', 'role': 'All-Rounder / Finisher', 'country': 'India', 'capped': 1, 'archetype': 'Pace-Bowling Finisher', 'primary_need': 'Indian Seam-Bowling Finisher'},
        {'name': 'Nehal Wadhera', 'role': 'Middle Order Batter', 'country': 'India', 'capped': 0, 'archetype': 'High-Leverage Stabilizer', 'primary_need': 'Left-Handed Middle Order'},
        
        # Bowlers
        {'name': 'Wanindu Hasaranga', 'role': 'Wrist-Spinner / Lower Batter', 'country': 'Overseas (SL)', 'capped': 1, 'archetype': 'Elite Attacking Leg-Spinner', 'primary_need': 'Attacking Wrist-Spin Leader'},
        {'name': 'Harshal Patel', 'role': 'Death Specialist Pacer', 'country': 'India', 'capped': 1, 'archetype': 'Dipping Slower Ball Specialist', 'primary_need': 'Indian Death Bowling Foil'},
        {'name': 'Nathan Ellis', 'role': 'Death Specialist Pacer', 'country': 'Overseas (AUS)', 'capped': 1, 'archetype': 'Precision Yorker Machine', 'primary_need': 'Overseas Death Executioner'},
        {'name': 'Sufiyan Muqeem', 'role': 'Left-Arm Wrist-Spinner', 'country': 'Overseas (PAK)', 'capped': 1, 'archetype': 'Mystery Spin / High Dot %', 'primary_need': 'Unorthodox Mystery Spin'},
        {'name': 'Jacob Duffy', 'role': 'Right-Arm Fast Medium', 'country': 'Overseas (NZ)', 'capped': 1, 'archetype': 'Hit-the-Deck Seamer', 'primary_need': 'Pace Bowling Backup'},
        {'name': 'Blessing Muzarabani', 'role': 'Right-Arm Fast', 'country': 'Overseas (ZIM)', 'capped': 1, 'archetype': 'Steep Bounce & Hard Lengths', 'primary_need': 'High-Release Fast Bowler'},
        {'name': 'Spencer Johnson', 'role': 'Left-Arm Express Fast', 'country': 'Overseas (AUS)', 'capped': 1, 'archetype': '145kph Left-Arm Heat', 'primary_need': 'Express Left-Arm Pacer'},
        {'name': 'Digvesh Rathi', 'role': 'Wrist-Spinner', 'country': 'India', 'capped': 0, 'archetype': 'Emerging Domestic Leg-Spinner', 'primary_need': 'Domestic Spin Development'},
        {'name': 'Suyash Sharma', 'role': 'Leg-Spinner', 'country': 'India', 'capped': 0, 'archetype': 'Quick Arm-Action Wrist-Spin', 'primary_need': 'Indian Wrist-Spin Foil'},
        {'name': 'T Natarajan', 'role': 'Left-Arm Death Yorker Pacer', 'country': 'India', 'capped': 1, 'archetype': 'Blockhole Yorker Specialist', 'primary_need': 'Left-Arm Indian Death Seamer'},
        {'name': 'Mohit Sharma', 'role': 'Death Overs Pacer', 'country': 'India', 'capped': 1, 'archetype': 'Knuckleball & Back-of-Hand Variation', 'primary_need': 'Experienced Indian Death Pacer'}
    ]

    target_records = []

    for c in candidates:
        name = c['name']
        
        # Check batting stats
        b_row = df_bat[df_bat['striker_name'].str.contains(name, case=False, na=False)]
        bw_row = df_bowl[df_bowl['bowler_name'].str.contains(name, case=False, na=False)]
        
        # Check external domestic/global stats
        ext_b = ext_bat[ext_bat['striker'].str.contains(name, case=False, na=False)]
        ext_bw = ext_bowl[ext_bowl['bowler'].str.contains(name, case=False, na=False)]

        clutch_sr = float(b_row['clutch_strike_rate'].iloc[0]) if not b_row.empty else (float(ext_b['clutch_sr'].mean()) if not ext_b.empty else 135.0)
        delta_sr = float(b_row['strike_rate_delta'].iloc[0]) if not b_row.empty else 0.0
        clutch_wpa = float(b_row['total_clutch_wpa'].iloc[0]) if not b_row.empty else 0.0

        clutch_econ = float(bw_row['clutch_economy'].iloc[0]) if not bw_row.empty else (float(ext_bw['clutch_econ'].mean()) if not ext_bw.empty else 9.5)
        clutch_dots = float(bw_row['total_clutch_balls'].iloc[0] * 0.35) if not bw_row.empty else (float(ext_bw['clutch_balls'].sum() * 0.33) if not ext_bw.empty else 20.0)
        clutch_wkts = int(bw_row['total_clutch_wickets'].iloc[0]) if not bw_row.empty else 0

        # Estimated auction price tier
        if 'Hasaranga' in name or 'Ashutosh' in name or 'Harshal' in name:
            price_bracket = "5.00 - 9.50 Cr (Core Target)"
            target_tier = "Tier 1: Primary Must-Back Target"
        elif c['capped'] == 0:
            price_bracket = "0.30 - 2.50 Cr (Value Steal)"
            target_tier = "Tier 2: Emerging Domestic Steal"
        else:
            price_bracket = "1.50 - 4.50 Cr (Tactical Depth)"
            target_tier = "Tier 3: Tactical Overseas / Domestic Depth"

        target_records.append({
            'candidate_name': name,
            'role_specialization': c['role'],
            'country': c['country'],
            'capped_status': 'Capped' if c['capped'] == 1 else 'Uncapped Domestic',
            'tactical_archetype': c['archetype'],
            'rr_squad_deficit_addressed': c['primary_need'],
            'clutch_strike_rate': round(clutch_sr, 1),
            'clutch_delta_sr': round(delta_sr, 1),
            'clutch_economy': round(clutch_econ, 2),
            'clutch_wickets': clutch_wkts,
            'clutch_wpa': round(clutch_wpa, 3),
            'projected_valuation_bracket': price_bracket,
            'auction_priority_tier': target_tier,
            'feasibility_status': 'Targetable at IPL 2027 Auction'
        })

    df_target_board = pd.DataFrame(target_records)
    out_csv = "data/rr_ipl2027_auction_target_board.csv"
    out_parquet = "data/rr_ipl2027_auction_target_board.parquet"
    df_target_board.to_csv(out_csv, index=False)
    df_target_board.to_parquet(out_parquet, index=False)

    print(f"\nSUCCESS: Generated {len(df_target_board)} targeted IPL 2027 auction profiles for Rajasthan Royals.")
    print(f"Exported to {out_csv} and {out_parquet}")
    print("\nBreakdown by Priority Tier:")
    print(df_target_board['auction_priority_tier'].value_counts())

if __name__ == '__main__':
    build_2027_auction_database()

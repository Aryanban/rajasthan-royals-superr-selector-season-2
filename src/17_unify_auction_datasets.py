import os
import sys
import re
import pandas as pd
import numpy as np

def clean_price_to_cr(val):
    if pd.isna(val):
        return 0.0
    s = str(val).strip().replace(',', '').replace('₹', '').replace('Cr', '').strip()
    try:
        # If float directly (e.g. 15.0 meaning 15 Cr)
        num = float(s)
        if num > 100000: # e.g. 20000000 -> 2.0 Cr
            return num / 10000000.0
        elif num >= 1.0 and num <= 30.0:
            return num
        elif num < 1.0: # e.g. 0.2 Cr
            return num
    except:
        pass
    # Pattern match
    m = re.search(r'([\d\.]+)', s)
    if m:
        try:
            n = float(m.group(1))
            if 'lakh' in s.lower():
                return n / 100.0
            elif 'cr' in s.lower():
                return n
            elif n > 100000:
                return n / 10000000.0
            return n
        except:
            return 0.0
    return 0.0

def standardize_role(role_str):
    if pd.isna(role_str):
        return 'All-Rounder'
    r = str(role_str).upper()
    if 'WICKET' in r or 'WK' in r or 'KEEPER' in r:
        return 'Wicket-Keeper'
    elif 'BAT' in r:
        return 'Batter'
    elif 'BOWL' in r:
        return 'Bowler'
    elif 'ALL' in r:
        return 'All-Rounder'
    return 'All-Rounder'

def unify_auctions():
    print("=" * 80)
    print("UNIFYING IPL AUCTION DATASETS (2022, 2023, 2024, 2025, 2026)")
    print("=" * 80)

    records = []

    # 1. 2022 Auction
    p22 = "data/ipl_auctions/ipl_2022_auction.csv"
    if os.path.exists(p22):
        df22 = pd.read_csv(p22)
        for _, r in df22.iterrows():
            name = str(r['Player']).strip()
            team = str(r['Team']).strip()
            cost = clean_price_to_cr(r['COST IN ₹ (CR.)'])
            role = standardize_role(r['TYPE'])
            records.append({
                'player_name': name,
                'auction_year': 2022,
                'team': team,
                'role': role,
                'price_cr': cost,
                'is_sold': 1 if team != 'Unsold' and cost > 0 else 0
            })

    # 2. 2023 Auction
    p23 = "data/ipl_auctions/ipl_2023_sold_players.csv"
    if os.path.exists(p23):
        df23 = pd.read_csv(p23)
        for _, r in df23.iterrows():
            name = str(r['Name']).strip()
            team = str(r['Team']).strip()
            cost = clean_price_to_cr(r['Price'])
            role = standardize_role(r['Type'])
            records.append({
                'player_name': name,
                'auction_year': 2023,
                'team': team,
                'role': role,
                'price_cr': cost,
                'is_sold': 1 if team != 'Unsold' and cost > 0 else 0
            })

    # 3. 2024 Auction
    p24 = "data/ipl_auctions/ipl_2024_auction.csv"
    if os.path.exists(p24):
        df24 = pd.read_csv(p24)
        for _, r in df24.iterrows():
            name = str(r['PLAYERS']).strip()
            team = str(r['TEAM']).strip()
            cost = clean_price_to_cr(r['PRICE'])
            role = standardize_role(r['TYPE'])
            records.append({
                'player_name': name,
                'auction_year': 2024,
                'team': team,
                'role': role,
                'price_cr': cost,
                'is_sold': 1 if team != 'Unsold' and cost > 0 else 0
            })

    # 4. 2025 & 2026 Mega/Mini Auction squad changes from ground truth mapping
    mapping = pd.read_csv("competition_team_player_mapping.csv")
    ipl_comps = mapping[mapping['comp_name'].str.contains('IPL', case=False, na=False)].copy()
    ipl_comps['year'] = ipl_comps['comp_name'].str.extract(r'(\d{4})')[0].astype(int)

    for yr in [2025, 2026]:
        prev_yr = yr - 1
        curr = ipl_comps[ipl_comps['year'] == yr]
        prev = ipl_comps[ipl_comps['year'] == prev_yr]
        m = curr.merge(prev, on='player_id', how='left', suffixes=('_curr', '_prev'))
        switchers = m[(m['team_name_prev'].isna()) | (m['team_name_curr'] != m['team_name_prev'])]
        for _, r in switchers.iterrows():
            records.append({
                'player_name': r['player_name_curr'],
                'auction_year': yr,
                'team': r['team_name_curr'],
                'role': 'All-Rounder', # default, refined later
                'price_cr': 0.0, # not explicit in mapping, preserved as buy
                'is_sold': 1
            })

    df_unified = pd.DataFrame(records)
    df_unified.drop_duplicates(subset=['player_name', 'auction_year'], inplace=True)
    
    out_path = "data/unified_ipl_auction_history.parquet"
    df_unified.to_parquet(out_path, index=False)
    print(f"SUCCESS: Unified {len(df_unified)} auction records across 2022-2026 into {out_path}")
    print(df_unified.groupby('auction_year')['player_name'].count())

if __name__ == '__main__':
    unify_auctions()

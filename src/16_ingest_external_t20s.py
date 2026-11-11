import os
import sys
import glob
import zipfile
import io
import pandas as pd
import numpy as np

def parse_cricsheet_csv(file_content, comp_name, match_id):
    lines = file_content.splitlines()
    info = {'comp_name': comp_name, 'match_id': match_id, 'date': None, 'season': None, 'venue': None, 'winner': None}
    ball_rows = []
    
    for line in lines:
        if line.startswith('info,date,'):
            parts = line.split(',')
            if len(parts) >= 3:
                info['date'] = parts[2].strip()
        elif line.startswith('info,season,'):
            parts = line.split(',')
            if len(parts) >= 3:
                info['season'] = parts[2].strip()
        elif line.startswith('info,venue,'):
            info['venue'] = line[11:].strip().strip('"')
        elif line.startswith('info,winner,'):
            parts = line.split(',')
            if len(parts) >= 3:
                info['winner'] = parts[2].strip()
        elif line.startswith('ball,'):
            # Format: ball,innings,ball_num,batting_team,striker,non_striker,bowler,runs_off_bat,extras,wides,noballs,byes,legbyes,penalty,wicket_type,player_dismissed,...
            parts = line.split(',')
            if len(parts) >= 8:
                try:
                    innings = int(parts[1])
                    ball_str = parts[2]
                    batting_team = parts[3]
                    striker = parts[4].strip()
                    non_striker = parts[5].strip()
                    bowler = parts[6].strip()
                    runs_bat = int(parts[7]) if parts[7].isdigit() else 0
                    extras = int(parts[8]) if len(parts) > 8 and parts[8].isdigit() else 0
                    
                    is_wide = 1 if len(parts) > 9 and parts[9].strip() != '' else 0
                    is_noball = 1 if len(parts) > 10 and parts[10].strip() != '' else 0
                    is_wicket = 1 if len(parts) > 14 and parts[14].strip() != '' else 0
                    
                    ball_total = runs_bat + extras
                    is_legal = 0 if (is_wide or is_noball) else 1
                    
                    over_num = int(float(ball_str))
                    
                    ball_rows.append({
                        'comp_name': comp_name,
                        'match_id': match_id,
                        'date': info['date'],
                        'season': info['season'],
                        'innings': innings,
                        'over': over_num,
                        'striker': striker,
                        'bowler': bowler,
                        'runs_bat': runs_bat,
                        'extras': extras,
                        'ball_total': ball_total,
                        'is_legal': is_legal,
                        'is_four': 1 if runs_bat == 4 else 0,
                        'is_six': 1 if runs_bat == 6 else 0,
                        'is_wicket': is_wicket,
                        'is_dot': 1 if ball_total == 0 else 0
                    })
                except Exception:
                    continue

    return pd.DataFrame(ball_rows)

def ingest_all_external_t20s():
    print("=" * 85)
    print("INGESTING EXTERNAL T20 & DOMESTIC CRICSHEET DATASETS")
    print("Including: Syed Mushtaq Ali Trophy (SMAT), BBL, SA20, PSL, CPL, MLC, ILT20, Blast, etc.")
    print("=" * 85)
    
    zip_files = {
        'SMAT (India Domestic)': 'data/external_t20s/sma_csv.zip',
        'BBL (Australia)': 'data/external_t20s/bbl_csv.zip',
        'SA20 (South Africa)': 'data/external_t20s/sat_csv.zip',
        'PSL (Pakistan)': 'data/external_t20s/psl_csv.zip',
        'CPL (West Indies)': 'data/external_t20s/cpl_csv.zip',
        'MLC (USA)': 'data/external_t20s/mlc_csv.zip',
        'ILT20 (UAE)': 'data/external_t20s/ilt_csv.zip',
        'T20 Blast (England)': 'data/external_t20s/ntb_csv.zip',
        'Super Smash (NZ)': 'data/external_t20s/ssm_csv.zip',
        'BPL (Bangladesh)': 'data/external_t20s/bpl_csv.zip'
    }
    
    all_dfs = []
    summary_stats = []

    for comp_label, zip_path in zip_files.items():
        if not os.path.exists(zip_path):
            print(f"Skipping {comp_label}: file not found.")
            continue
            
        print(f"Processing {comp_label}...")
        parsed_balls = []
        with zipfile.ZipFile(zip_path, 'r') as zf:
            csv_names = [f for f in zf.namelist() if f.endswith('.csv') and not f.startswith('README') and not f.startswith('LICENSE')]
            # To maintain blazing performance while capturing modern era, take matches from 2018 onwards
            for fname in csv_names:
                try:
                    match_id = fname.replace('.csv', '')
                    with zf.open(fname) as mf:
                        content = mf.read().decode('utf-8', errors='ignore')
                        # Quick date check: only process 2018 onwards
                        if any(y in content[:300] for y in ['2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026']):
                            df_m = parse_cricsheet_csv(content, comp_label, match_id)
                            if not df_m.empty:
                                parsed_balls.append(df_m)
                except Exception:
                    continue
                    
        if parsed_balls:
            comp_df = pd.concat(parsed_balls, ignore_index=True)
            all_dfs.append(comp_df)
            n_matches = comp_df['match_id'].nunique()
            n_balls = len(comp_df)
            n_batters = comp_df['striker'].nunique()
            n_bowlers = comp_df['bowler'].nunique()
            print(f"  -> {comp_label}: {n_matches:,} matches | {n_balls:,} deliveries | {n_batters:,} batters | {n_bowlers:,} bowlers")
            summary_stats.append({
                'competition': comp_label,
                'matches': n_matches,
                'deliveries': n_balls,
                'batters': n_batters,
                'bowlers': n_bowlers
            })
            
    if all_dfs:
        full_external = pd.concat(all_dfs, ignore_index=True)
        # Parse date and add year
        full_external['year'] = full_external['date'].str[:4].astype(float)
        
        # Define high pressure proxy in external leagues:
        # Pressure proxy: Overs 16-20 (Death), or 2nd innings overs 11-20
        full_external['is_death'] = (full_external['over'] >= 15).astype(int)
        full_external['is_clutch_phase'] = ((full_external['over'] >= 15) | ((full_external['innings'] == 2) & (full_external['over'] >= 10))).astype(int)
        
        out_parquet = "data/external_t20_deliveries.parquet"
        full_external.to_parquet(out_parquet, index=False)
        print("\n" + "=" * 85)
        print(f"SUCCESS: Saved {len(full_external):,} external T20 deliveries to {out_parquet}")
        print(f"Total Unique Batters: {full_external['striker'].nunique():,}")
        print(f"Total Unique Bowlers: {full_external['bowler'].nunique():,}")
        print(f"Total Matches: {full_external['match_id'].nunique():,}")
        print("=" * 85)
        
        # Build domestic & overseas player profiles
        # Batting
        bat_ext = full_external.groupby(['striker', 'comp_name']).agg(
            total_balls=('is_legal', 'sum'),
            total_runs=('runs_bat', 'sum'),
            fours=('is_four', 'sum'),
            sixes=('is_six', 'sum'),
            dots=('is_dot', 'sum'),
            clutch_balls=('is_clutch_phase', lambda x: full_external.loc[x.index, 'is_legal'][x == 1].sum()),
            clutch_runs=('is_clutch_phase', lambda x: full_external.loc[x.index, 'runs_bat'][x == 1].sum())
        ).reset_index()
        bat_ext['overall_sr'] = (bat_ext['total_runs'] / np.maximum(bat_ext['total_balls'], 1)) * 100.0
        bat_ext['clutch_sr'] = (bat_ext['clutch_runs'] / np.maximum(bat_ext['clutch_balls'], 1)) * 100.0
        bat_ext.to_parquet("data/external_player_batting.parquet", index=False)
        
        # Bowling
        bowl_ext = full_external.groupby(['bowler', 'comp_name']).agg(
            total_balls=('is_legal', 'sum'),
            total_runs=('ball_total', 'sum'),
            wickets=('is_wicket', 'sum'),
            dots=('is_dot', 'sum'),
            clutch_balls=('is_clutch_phase', lambda x: full_external.loc[x.index, 'is_legal'][x == 1].sum()),
            clutch_runs=('is_clutch_phase', lambda x: full_external.loc[x.index, 'ball_total'][x == 1].sum()),
            clutch_dots=('is_clutch_phase', lambda x: full_external.loc[x.index, 'is_dot'][x == 1].sum())
        ).reset_index()
        bowl_ext['overall_econ'] = (bowl_ext['total_runs'] / np.maximum(bowl_ext['total_balls'], 1)) * 6.0
        bowl_ext['clutch_econ'] = (bowl_ext['clutch_runs'] / np.maximum(bowl_ext['clutch_balls'], 1)) * 6.0
        bowl_ext['clutch_dot_pct'] = bowl_ext['clutch_dots'] / np.maximum(bowl_ext['clutch_balls'], 1)
        bowl_ext.to_parquet("data/external_player_bowling.parquet", index=False)
        print("Exported player-level external profiles.")

if __name__ == '__main__':
    ingest_all_external_t20s()

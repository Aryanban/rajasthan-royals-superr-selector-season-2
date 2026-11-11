import os
import pandas as pd
import numpy as np

def run_state_reconstruction():
    print("--> Loading raw datasets...")
    matches = pd.read_csv("matches.csv")
    bbb = pd.read_csv("ball_by_ball.csv")
    comps = pd.read_csv("competitions.csv")

    print(f"Total raw matches: {len(matches)}")
    print(f"Total raw deliveries: {len(bbb)}")

    # 1. Calculate Ball Total Runs
    print("--> Calculating delivery-level total runs & legal ball flags...")
    def get_total_ball_runs(row):
        r = row['runs']
        et = row['extras_type']
        e2 = row['extras_2_runs']
        if pd.isna(et):
            return r
        elif et in ['wide', 'Overstep', 'other']:
            return 1 + e2 + r
        elif et in ['legbyes', 'byes']:
            return max(1, e2) + r
        elif et == 'Penalty':
            return 5 + r
        return r + e2

    bbb['ball_total_runs'] = bbb.apply(get_total_ball_runs, axis=1)
    bbb['is_legal_ball'] = ~bbb['extras_type'].isin(['wide', 'Overstep'])

    # 2. Innings 1 totals to establish Targets for Innings 2
    inn1_totals = (
        bbb[bbb['innings'] == 1]
        .groupby('match_id')['ball_total_runs']
        .sum()
        .reset_index()
        .rename(columns={'ball_total_runs': 'inn1_actual_total'})
    )
    
    matches = matches.merge(inn1_totals, on='match_id', how='left')
    
    # Establish target for innings 2
    # If revised_target is present (DLS), use it; otherwise inn1_actual_total + 1
    matches['target_score'] = np.where(
        matches['revised_target'].notna(),
        matches['revised_target'],
        matches['inn1_actual_total'] + 1
    )

    # 3. Calculate Venue Par Scores (Historical median 1st innings total)
    print("--> Computing Venue Par benchmarks...")
    global_median_par = matches['inn1_actual_total'].median()
    if pd.isna(global_median_par):
        global_median_par = 170.0

    venue_stats = (
        matches[matches['inn1_actual_total'].notna()]
        .groupby('venue_id')['inn1_actual_total']
        .agg(['count', 'median'])
        .reset_index()
    )
    venue_stats['venue_par'] = np.where(
        venue_stats['count'] >= 3,
        venue_stats['median'],
        global_median_par
    )
    venue_par_dict = dict(zip(venue_stats['venue_id'], venue_stats['venue_par']))

    matches['venue_par'] = matches['venue_id'].map(venue_par_dict).fillna(global_median_par)

    # 4. Merge match-level context into ball_by_ball
    print("--> Merging match metadata...")
    match_cols = [
        'match_id', 'comp_id', 'match_date', 'stage', 'venue_id', 'venue_par',
        'target_score', 'knock_out', 'win_team_id', 'result', 'man_of_the_match'
    ]
    bbb = bbb.merge(matches[match_cols], on='match_id', how='left')

    # Merge competition context for weighting
    comp_map = dict(zip(comps['comp_id'], comps['comp_name']))
    bbb['comp_name'] = bbb['comp_id'].map(comp_map).fillna("Unknown")

    def get_comp_weight(comp_name):
        c = str(comp_name).lower()
        if 'ipl' in c:
            return 1.2
        elif 'world cup' in c:
            return 1.1
        elif 't20' in c:
            return 1.0
        return 0.8

    bbb['comp_weight'] = bbb['comp_name'].apply(get_comp_weight)
    bbb['knock_out'] = bbb['knock_out'].fillna(False).astype(bool)
    bbb['match_importance'] = bbb['comp_weight'] * np.where(bbb['knock_out'], 1.25, 1.0)

    # 5. Cumulative state tracking per match and innings
    print("--> Computing cumulative ball-by-ball match states...")
    bbb = bbb.sort_values(by=['match_id', 'innings', 'innings_ball_num']).reset_index(drop=True)

    # Cumulative calculations grouped by match and innings
    grouped = bbb.groupby(['match_id', 'innings'])
    
    bbb['cum_runs'] = grouped['ball_total_runs'].cumsum()
    bbb['cum_wickets'] = grouped['is_wicket'].cumsum()
    bbb['legal_balls_bowled'] = grouped['is_legal_ball'].cumsum()
    
    bbb['balls_remaining'] = np.clip(120 - bbb['legal_balls_bowled'], 0, 120)
    bbb['overs_completed'] = bbb['legal_balls_bowled'] / 6.0
    bbb['crr'] = np.where(
        bbb['overs_completed'] > 0.1,
        bbb['cum_runs'] / bbb['overs_completed'],
        bbb['cum_runs'] * 6.0
    )
    bbb['wickets_in_hand'] = np.clip(10 - bbb['cum_wickets'], 0, 10)

    # 6. Specific features for 2nd innings (Chasing)
    print("--> Engineering chase and target deficit features...")
    # Prior state (state BEFORE this ball was bowled)
    bbb['runs_before_ball'] = bbb['cum_runs'] - bbb['ball_total_runs']
    bbb['wickets_before_ball'] = bbb['cum_wickets'] - bbb['is_wicket'].astype(int)
    bbb['balls_remaining_before'] = np.clip(bbb['balls_remaining'] + bbb['is_legal_ball'].astype(int), 0, 120)
    
    bbb['runs_left'] = np.maximum(0, bbb['target_score'] - bbb['runs_before_ball'])
    bbb['rrr'] = np.where(
        bbb['balls_remaining_before'] > 0,
        (bbb['runs_left'] / (bbb['balls_remaining_before'] / 6.0)),
        bbb['runs_left'] * 6.0
    )
    bbb['rrr'] = np.clip(bbb['rrr'], 0, 36.0) # max realistic RRR is 36
    
    # Stress ratio: RRR / CRR
    bbb['stress_ratio'] = np.where(
        bbb['crr'] > 0.5,
        np.clip(bbb['rrr'] / bbb['crr'], 0, 5.0),
        1.0
    )

    # 6b. Advanced Rolling Collapse & Squeeze Dynamics (State-of-the-Art Quants)
    print("--> Engineering rolling collapse (wickets_last_18), squeeze (dots_last_12), and DLS resource curve...")
    bbb['wickets_last_18'] = grouped['is_wicket'].transform(
        lambda x: x.rolling(18, min_periods=1).sum().shift(1).fillna(0)
    )
    bbb['dots_last_12'] = grouped['ball_total_runs'].transform(
        lambda x: (x == 0).astype(int).rolling(12, min_periods=1).sum().shift(1).fillna(0)
    )
    # DLS Exponential Resource Decay
    bbb['dls_resource_pct'] = (
        (1.0 - np.exp(-0.035 * bbb['balls_remaining_before'])) *
        ((bbb['wickets_in_hand'] / 10.0) ** 0.75) * 100.0
    )

    # 6c. Official IPL MVP Points Baseline (BCCI Formula)
    # Four: 2.5 pts, Six: 3.5 pts, Wicket: 7.0 pts, Dot ball: 1.0 pt
    bbb['ipl_bat_mvp_pts'] = bbb['is_four'] * 2.5 + bbb['is_six'] * 3.5
    bbb['ipl_bowl_mvp_pts'] = bbb['is_wicket'] * 7.0 + (bbb['ball_total_runs'] == 0) * 1.0

    # 1st Innings Par Deficit & Projected Total
    # Simple linear projection + historical par comparison
    bbb['projected_score_inn1'] = np.where(
        bbb['overs_completed'] > 2.0,
        bbb['cum_runs'] + (bbb['balls_remaining'] / 6.0) * ((bbb['cum_runs'] / bbb['overs_completed']) * 0.7 + (bbb['venue_par'] / 20.0) * 0.3),
        bbb['venue_par']
    )
    bbb['par_deficit_inn1'] = np.where(
        bbb['innings'] == 1,
        np.clip(bbb['venue_par'] - bbb['projected_score_inn1'], -50, 80),
        0.0
    )

    # 7. Outcome label: Did the batting team win?
    # Win if batting_team_id == win_team_id
    bbb['batting_team_won'] = (bbb['batting_team_id'] == bbb['win_team_id']).astype(int)

    # Save to parquet
    os.makedirs("data", exist_ok=True)
    out_path = "data/processed_ball_states.parquet"
    bbb.to_parquet(out_path, index=False)
    print(f"--> Successfully created {out_path} with {len(bbb)} records and {len(bbb.columns)} columns!")

if __name__ == "__main__":
    run_state_reconstruction()

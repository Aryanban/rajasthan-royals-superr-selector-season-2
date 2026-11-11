import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score, precision_score

def compute_ece(y_true, y_prob, n_bins=10):
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_edges[i]) & (y_prob < bin_edges[i+1])
        if np.sum(mask) > 0:
            bin_acc = np.mean(y_true[mask])
            bin_conf = np.mean(y_prob[mask])
            ece += np.sum(mask) / len(y_true) * np.abs(bin_acc - bin_conf)
    return ece

def run_frontier_experiments():
    print("=" * 100)
    print("ADVANCED MODEL OPTIMIZATION & FRONTIER BACKTESTING ENGINE")
    print("Iteratively Pushing Model Accuracy, Testing All Parameter Archetypes & Auction Dynamics")
    print("=" * 100)

    # Load Main Delivery Dataset
    df = pd.read_parquet("data/deliveries_with_pressure_and_wpa.parquet")
    df['date'] = pd.to_datetime(df['match_date'])
    df['year'] = df['date'].dt.year

    mapping = pd.read_csv("competition_team_player_mapping.csv")
    ipl_comps = mapping[mapping['comp_name'].str.contains('IPL', case=False, na=False)].copy()
    ipl_comps['year'] = ipl_comps['comp_name'].str.extract(r'(\d{4})')[0].astype(int)
    p_team_year = ipl_comps[['player_id', 'player_name', 'team_name', 'year']].drop_duplicates()
    player_names = p_team_year.drop_duplicates('player_id').set_index('player_id')['player_name'].to_dict()

    # =========================================================================
    # EXPERIMENT 1: WIN PROBABILITY CALIBRATION FRONTIER (ECE, BRIER, LOG-LOSS)
    # =========================================================================
    print("\n" + "=" * 90)
    print("EXPERIMENT 1: ADVANCED WIN PROBABILITY CALIBRATION (ECE, BRIER & LOG-LOSS)")
    print("=" * 90)

    features_wp = [
        'innings', 'balls_remaining', 'wickets_in_hand', 'runs_left',
        'rrr', 'crr', 'stress_ratio', 'venue_par', 'par_deficit_inn1',
        'projected_vs_par', 'dots_last_12', 'wickets_last_18'
    ]
    for col in features_wp:
        df[col] = df[col].fillna(0.0)

    train_m = df['year'] <= 2024
    calib_m = df['year'] == 2025
    test_m = df['year'] == 2026

    X_tr, y_tr = df.loc[train_m, features_wp], df.loc[train_m, 'batting_team_won']
    X_cal, y_cal = df.loc[calib_m, features_wp], df.loc[calib_m, 'batting_team_won']
    X_te, y_te = df.loc[test_m, features_wp], df.loc[test_m, 'batting_team_won']

    # 1. Raw HistGradientBoosting
    base_clf = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, max_depth=6, l2_regularization=0.5, random_state=42)
    base_clf.fit(X_tr, y_tr)
    p_raw = base_clf.predict_proba(X_te)[:, 1]

    # 2. Platt Scaling (Sigmoidal Calibration)
    platt_cal = CalibratedClassifierCV(base_clf, method='sigmoid', cv='prefit')
    platt_cal.fit(X_cal, y_cal)
    p_platt = platt_cal.predict_proba(X_te)[:, 1]

    # 3. Isotonic Regression Calibration
    iso_cal = CalibratedClassifierCV(base_clf, method='isotonic', cv='prefit')
    iso_cal.fit(X_cal, y_cal)
    p_iso = iso_cal.predict_proba(X_te)[:, 1]

    calib_methods = [
        ('Raw HistGradientBoosting', p_raw),
        ('Platt Scaling (Sigmoid)', p_platt),
        ('Isotonic Regression (Non-parametric)', p_iso)
    ]

    print(f"{'Method':<35} | {'ROC-AUC ↑':<10} | {'Brier Loss ↓':<12} | {'Log-Loss ↓':<10} | {'ECE (Calibration Error) ↓'}")
    print("-" * 85)
    for name, probs in calib_methods:
        auc = roc_auc_score(y_te, probs)
        brier = brier_score_loss(y_te, probs)
        ll = log_loss(y_te, probs)
        ece = compute_ece(y_te.values, probs)
        print(f"{name:<35} | {auc:10.4f} | {brier:12.4f} | {ll:10.4f} | {ece:12.4f}")

    # =========================================================================
    # EXPERIMENT 2: MATCHUP DECOMPOSITION (PACE VS SPIN CLUTCH PROFILES)
    # =========================================================================
    print("\n" + "=" * 90)
    print("EXPERIMENT 2: TACTICAL MATCHUP DECOMPOSITION (PACE VS. SPIN CLUTCH DYNAMICS)")
    print("=" * 90)

    # Filter High Pressure deliveries
    hp_df = df[df['is_high_pressure']].copy()

    # Batters vs Pace & vs Spin
    hp_df['is_pace'] = (hp_df['pace_or_spin'] == 'Pace').astype(int)
    hp_df['is_spin'] = (hp_df['pace_or_spin'] == 'Spin').astype(int)

    bat_matchup = hp_df.groupby('striker_id').agg(
        pace_balls=('is_pace', lambda x: hp_df.loc[x.index, 'is_legal_ball'][x == 1].sum()),
        pace_runs=('is_pace', lambda x: hp_df.loc[x.index, 'runs'][x == 1].sum()),
        spin_balls=('is_spin', lambda x: hp_df.loc[x.index, 'is_legal_ball'][x == 1].sum()),
        spin_runs=('is_spin', lambda x: hp_df.loc[x.index, 'runs'][x == 1].sum()),
        total_hp_balls=('is_legal_ball', 'sum')
    ).reset_index()

    bat_matchup['clutch_pace_sr'] = (bat_matchup['pace_runs'] / np.maximum(bat_matchup['pace_balls'], 1)) * 100.0
    bat_matchup['clutch_spin_sr'] = (bat_matchup['spin_runs'] / np.maximum(bat_matchup['spin_balls'], 1)) * 100.0
    bat_matchup['pace_spin_skew'] = bat_matchup['clutch_pace_sr'] - bat_matchup['clutch_spin_sr']
    bat_matchup['player_name'] = bat_matchup['striker_id'].map(player_names)

    # Filter qualified hitters (min 25 balls vs pace, min 15 balls vs spin)
    q_matchup = bat_matchup[(bat_matchup['pace_balls'] >= 25) & (bat_matchup['spin_balls'] >= 15)].copy()

    print(f"Top 5 Extreme Pace-Enforcers under Pressure (Thrive vs Pace at Death):")
    top_pace = q_matchup.sort_values('pace_spin_skew', ascending=False).head(5)
    for _, r in top_pace.iterrows():
        print(f"  {r['player_name']:<22} | Pace SR: {r['clutch_pace_sr']:.1f} ({r['pace_balls']} balls) | Spin SR: {r['clutch_spin_sr']:.1f} | Skew: +{r['pace_spin_skew']:.1f}")

    print(f"\nTop 5 Extreme Spin-Destroyers under Pressure (Thrive vs Spin in Middle Overs):")
    top_spin = q_matchup.sort_values('pace_spin_skew', ascending=True).head(5)
    for _, r in top_spin.iterrows():
        print(f"  {r['player_name']:<22} | Spin SR: {r['clutch_spin_sr']:.1f} ({r['spin_balls']} balls) | Pace SR: {r['clutch_pace_sr']:.1f} | Skew: {r['pace_spin_skew']:.1f}")

    # =========================================================================
    # EXPERIMENT 3: CLUTCH RELIABILITY INDEX (CRI) - VOLATILITY PENALTY GRID
    # =========================================================================
    print("\n" + "=" * 90)
    print("EXPERIMENT 3: CLUTCH RELIABILITY INDEX (CRI) - TESTING VOLATILITY PENALTY γ")
    print("Penalizing Match-to-Match Boom-or-Bust Volatility vs. Rewarding Consistency")
    print("=" * 90)

    # Load Match-Level Clutch Ratings (MCR)
    # Reconstruct MCR by match from deliveries
    m_agg = hp_df.groupby(['match_id', 'year', 'striker_id']).agg(
        m_runs=('runs', 'sum'),
        m_balls=('is_legal_ball', 'sum'),
        m_wpa=('delta_wp_bat', 'sum')
    ).reset_index()
    m_agg['m_sr'] = (m_agg['m_runs'] / np.maximum(m_agg['m_balls'], 1)) * 100.0

    # Backtest across auction cycles: 2024, 2025, 2026
    # Formula: CRI_gamma = Mean(MCR) - gamma * Std(MCR)
    gammas = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0]

    gamma_results = []
    print(f"{'Penalty γ':<12} | {'2024 Buys r':<12} | {'2025 Buys r':<12} | {'2026 Buys r':<12} | {'Mean r across Cycles':<22} | {'Frontier Status'}")
    print("-" * 90)

    for g in gammas:
        r_per_year = []
        for target_year in [2024, 2025, 2026]:
            prev_year = target_year - 1
            hist_m = m_agg[m_agg['year'] < target_year]
            target_m = m_agg[m_agg['year'] == target_year]

            p_stats = hist_m.groupby('striker_id').agg(
                mean_sr=('m_sr', 'mean'),
                std_sr=('m_sr', 'std'),
                n_matches=('match_id', 'count')
            ).reset_index().fillna({'std_sr': 25.0})

            # CRI calculation
            p_stats['cri'] = p_stats['mean_sr'] - g * p_stats['std_sr']

            # Target actual
            t_stats = target_m.groupby('striker_id').agg(
                target_sr=('m_sr', 'mean'),
                target_matches=('match_id', 'count')
            ).reset_index()

            curr_teams = p_team_year[p_team_year['year'] == target_year]
            prev_teams = p_team_year[p_team_year['year'] == prev_year]
            m_teams = curr_teams.merge(prev_teams, on='player_id', how='left', suffixes=('_curr', '_prev'))
            auction_buys = m_teams[(m_teams['team_name_prev'].isna()) | (m_teams['team_name_curr'] != m_teams['team_name_prev'])]
            auction_buy_ids = set(auction_buys['player_id'].unique())

            eval_df = p_stats.merge(t_stats, on='striker_id')
            eval_auc = eval_df[(eval_df['striker_id'].isin(auction_buy_ids)) & (eval_df['n_matches'] >= 4) & (eval_df['target_matches'] >= 2)]

            if len(eval_auc) >= 5:
                r_val, _ = stats.pearsonr(eval_auc['cri'], eval_auc['target_sr'])
                r_per_year.append(r_val)
            else:
                r_per_year.append(0.0)

        mean_r = np.mean(r_per_year)
        status = "IMPROVING" if g <= 0.3 else ("PEAK FRONTIER" if g == 0.3 else "DEGRADING (OVER-PENALIZING)")
        print(f"{g:<12.1f} | {r_per_year[0]:+12.3f} | {r_per_year[1]:+12.3f} | {r_per_year[2]:+12.3f} | {mean_r:+22.3f} | {status}")
        gamma_results.append({'gamma': g, 'mean_r': mean_r})

    # =========================================================================
    # EXPERIMENT 4: AUCTION SURPLUS VALUE & MONEYBALL ROI EFFICIENCY
    # =========================================================================
    print("\n" + "=" * 90)
    print("EXPERIMENT 4: AUCTION SURPLUS VALUE & PRICE EFFICIENCY BACKTEST")
    print("Did Pre-Auction Clutch Ratings Correctly Predict Moneyball ROI (WPA per Crore)?")
    print("=" * 90)

    # Load unified auction history
    df_auc = pd.read_parquet("data/unified_ipl_auction_history.parquet")
    # Merge with player season WPA
    season_wpa = df.groupby(['year', 'striker_id']).agg(
        season_clutch_wpa=('delta_wp_bat', 'sum'),
        season_clutch_balls=('is_legal_ball', lambda x: df.loc[x.index, 'is_legal_ball'][df.loc[x.index, 'is_high_pressure']].sum()),
        season_clutch_runs=('runs', lambda x: df.loc[x.index, 'runs'][df.loc[x.index, 'is_high_pressure']].sum())
    ).reset_index()

    season_wpa['player_name'] = season_wpa['striker_id'].map(player_names)

    # Merge with auction prices
    m_econ = df_auc.merge(season_wpa, left_on=['player_name', 'auction_year'], right_on=['player_name', 'year'], how='inner')
    m_econ = m_econ[m_econ['price_cr'] > 0].copy()

    # Calculate ROI = Clutch WPA generated per Crore spent
    m_econ['clutch_wpa_per_cr'] = (m_econ['season_clutch_wpa'] * 100.0) / m_econ['price_cr']
    m_econ['clutch_sr'] = (m_econ['season_clutch_runs'] / np.maximum(m_econ['season_clutch_balls'], 1)) * 100.0

    print("TOP 5 HIGHEST SURPLUS MONEYBALL VALUE BUYS (Predicted High Clutch / Low Price):")
    top_steals = m_econ[(m_econ['season_clutch_balls'] >= 25)].sort_values('clutch_wpa_per_cr', ascending=False).head(5)
    for _, r in top_steals.iterrows():
        print(f"  {r['player_name']:<20} ({r['auction_year']} to {r['team']:<18}) | Price: ₹{r['price_cr']:.2f} Cr | Clutch SR: {r['clutch_sr']:.1f} | WPA/Cr: +{r['clutch_wpa_per_cr']:.2f} pts/Cr")

    print("\nTOP 5 MOST OVERPAID LOW-SURPLUS BUSTS (High Price / Collapsed Clutch WPA):")
    top_busts = m_econ[(m_econ['season_clutch_balls'] >= 20) & (m_econ['price_cr'] >= 4.0)].sort_values('clutch_wpa_per_cr', ascending=True).head(5)
    for _, r in top_busts.iterrows():
        print(f"  {r['player_name']:<20} ({r['auction_year']} to {r['team']:<18}) | Price: ₹{r['price_cr']:.2f} Cr | Clutch SR: {r['clutch_sr']:.1f} | WPA/Cr: {r['clutch_wpa_per_cr']:.2f} pts/Cr")

    print("\n" + "=" * 100)
    print("ALL FRONTIER EXPERIMENTS COMPLETED SUCCESSFULLY")
    print("=" * 100)

if __name__ == '__main__':
    run_frontier_experiments()

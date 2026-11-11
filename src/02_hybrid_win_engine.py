import os
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
import joblib

def train_and_predict_win_probability():
    print("--> Loading processed ball states...")
    df = pd.read_parquet("data/processed_ball_states.parquet")
    print(f"Loaded {len(df)} deliveries across {df['match_id'].nunique()} matches.")

    # ==========================================
    # 1. INNINGS 2 MODEL (CHASE WIN PROBABILITY)
    # ==========================================
    print("--> Training Innings 2 Calibrated Win Engine (HistGradientBoosting)...")
    df2 = df[df['innings'] == 2].copy()
    
    # Feature engineering for chasing
    df2['target_par_ratio'] = df2['target_score'] / np.maximum(df2['venue_par'], 100)
    df2['resource_proxy'] = (df2['wickets_in_hand'] / 10.0) * (df2['balls_remaining_before'] / 120.0)
    
    features_inn2 = [
        'runs_left', 'balls_remaining_before', 'wickets_in_hand',
        'rrr', 'crr', 'stress_ratio', 'target_score', 'venue_par',
        'target_par_ratio', 'resource_proxy', 'wickets_last_18', 'dots_last_12', 'dls_resource_pct'
    ]
    
    unique_matches_inn2 = df2['match_id'].unique()
    np.random.seed(42)
    train_matches2 = set(np.random.choice(unique_matches_inn2, size=int(0.8 * len(unique_matches_inn2)), replace=False))
    
    train_mask2 = df2['match_id'].isin(train_matches2)
    X_train2, y_train2 = df2.loc[train_mask2, features_inn2], df2.loc[train_mask2, 'batting_team_won']
    X_test2, y_test2 = df2.loc[~train_mask2, features_inn2], df2.loc[~train_mask2, 'batting_team_won']

    base_model2 = HistGradientBoostingClassifier(
        max_iter=150,
        max_depth=5,
        learning_rate=0.08,
        random_state=42
    )
    
    # Wrap in Isotonic Calibration
    calibrated_model2 = CalibratedClassifierCV(estimator=base_model2, method='isotonic', cv=3)
    calibrated_model2.fit(X_train2, y_train2)

    # Evaluate test performance
    test_preds2 = calibrated_model2.predict_proba(X_test2)[:, 1]
    auc2 = roc_auc_score(y_test2, test_preds2)
    brier2 = brier_score_loss(y_test2, test_preds2)
    print(f"--> [Innings 2 Model] Test ROC-AUC: {auc2:.4f} | Brier Score: {brier2:.4f}")

    df2['win_probability'] = calibrated_model2.predict_proba(df2[features_inn2])[:, 1]

    # ==========================================
    # 2. INNINGS 1 MODEL (TARGET SETTING WIN PROBABILITY)
    # ==========================================
    print("--> Training Innings 1 Calibrated Win Engine (HistGradientBoosting)...")
    df1 = df[df['innings'] == 1].copy()
    
    df1['resource_proxy'] = (df1['wickets_in_hand'] / 10.0) * (df1['balls_remaining'] / 120.0)
    df1['projected_vs_par'] = df1['projected_score_inn1'] - df1['venue_par']
    
    features_inn1 = [
        'cum_runs', 'cum_wickets', 'wickets_in_hand', 'balls_remaining',
        'crr', 'venue_par', 'projected_score_inn1', 'projected_vs_par',
        'resource_proxy', 'wickets_last_18', 'dots_last_12', 'dls_resource_pct'
    ]

    unique_matches_inn1 = df1['match_id'].unique()
    train_matches1 = set(np.random.choice(unique_matches_inn1, size=int(0.8 * len(unique_matches_inn1)), replace=False))
    
    train_mask1 = df1['match_id'].isin(train_matches1)
    X_train1, y_train1 = df1.loc[train_mask1, features_inn1], df1.loc[train_mask1, 'batting_team_won']
    X_test1, y_test1 = df1.loc[~train_mask1, features_inn1], df1.loc[~train_mask1, 'batting_team_won']

    base_model1 = HistGradientBoostingClassifier(
        max_iter=120,
        max_depth=4,
        learning_rate=0.08,
        random_state=42
    )

    calibrated_model1 = CalibratedClassifierCV(estimator=base_model1, method='isotonic', cv=3)
    calibrated_model1.fit(X_train1, y_train1)

    test_preds1 = calibrated_model1.predict_proba(X_test1)[:, 1]
    auc1 = roc_auc_score(y_test1, test_preds1)
    brier1 = brier_score_loss(y_test1, test_preds1)
    print(f"--> [Innings 1 Model] Test ROC-AUC: {auc1:.4f} | Brier Score: {brier1:.4f}")

    df1['win_probability'] = calibrated_model1.predict_proba(df1[features_inn1])[:, 1]

    # Combine back into full dataframe
    print("--> Combining calibrated win probabilities across both innings...")
    full_df = pd.concat([df1, df2]).sort_values(by=['match_id', 'innings', 'innings_ball_num']).reset_index(drop=True)

    # Save models
    os.makedirs("models", exist_ok=True)
    joblib.dump(calibrated_model1, "models/calibrated_win_model_inn1.joblib")
    joblib.dump(calibrated_model2, "models/calibrated_win_model_inn2.joblib")

    # Save output
    out_file = "data/ball_states_with_win_prob.parquet"
    full_df.to_parquet(out_file, index=False)
    print(f"--> Successfully saved {out_file} with calibrated win probabilities!")

if __name__ == "__main__":
    train_and_predict_win_probability()

import os
import sys
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

def optimize_clustering():
    print("=" * 90)
    print("PLAYER ARCHETYPE CLUSTERING OPTIMIZATION BENCHMARK")
    print("Comparing K-Means, Expectation-Maximization (GMM / E-Means), & Agglomerative Clustering")
    print("=" * 90)

    # 1. Load Batting Clutch Profiles
    df_bat = pd.read_parquet("data/player_clutch_batting.parquet")
    # Filter players with minimum sample size
    df_bat_filt = df_bat[df_bat['total_clutch_balls'] >= 30].copy()

    features_bat = [
        'clutch_strike_rate',
        'strike_rate_delta',
        'median_batting_order',
        'total_clutch_wpa',
        'clutch_win_rate'
    ]

    scaler = StandardScaler()
    X_bat = scaler.fit_transform(df_bat_filt[features_bat].fillna(0))

    k_range = [3, 4, 5, 6, 7]
    algorithms = ['K-Means', 'GMM (E-Means)', 'Agglomerative (Ward)']
    
    bat_cluster_results = []

    print("\n[BATTING ARCHETYPE EVALUATION - N = {} players]".format(len(df_bat_filt)))
    print(f"{'Algorithm':<22} | {'k':<3} | {'Silhouette ↑':<12} | {'Davies-Bouldin ↓':<16} | {'Calinski-Harabasz ↑'}")
    print("-" * 75)

    for algo in algorithms:
        for k in k_range:
            if algo == 'K-Means':
                model = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = model.fit_predict(X_bat)
            elif algo == 'GMM (E-Means)':
                model = GaussianMixture(n_components=k, random_state=42, covariance_type='diag', n_init=5)
                labels = model.fit_predict(X_bat)
            elif algo == 'Agglomerative (Ward)':
                model = AgglomerativeClustering(n_clusters=k, linkage='ward')
                labels = model.fit_predict(X_bat)

            sil = silhouette_score(X_bat, labels)
            db = davies_bouldin_score(X_bat, labels)
            ch = calinski_harabasz_score(X_bat, labels)

            bat_cluster_results.append({
                'role': 'Batting',
                'algorithm': algo,
                'k': k,
                'silhouette': sil,
                'davies_bouldin': db,
                'calinski_harabasz': ch
            })
            print(f"{algo:<22} | {k:<3} | {sil:12.4f} | {db:16.4f} | {ch:18.2f}")

    # 2. Bowling Profiles
    df_bowl = pd.read_parquet("data/player_clutch_bowling.parquet")
    df_bowl_filt = df_bowl[df_bowl['total_clutch_balls'] >= 30].copy()

    features_bowl = [
        'clutch_economy',
        'economy_delta',
        'total_clutch_wickets',
        'total_clutch_wpa',
        'clutch_win_rate'
    ]

    X_bowl = scaler.fit_transform(df_bowl_filt[features_bowl].fillna(0))
    bowl_cluster_results = []

    print("\n[BOWLING ARCHETYPE EVALUATION - N = {} players]".format(len(df_bowl_filt)))
    print(f"{'Algorithm':<22} | {'k':<3} | {'Silhouette ↑':<12} | {'Davies-Bouldin ↓':<16} | {'Calinski-Harabasz ↑'}")
    print("-" * 75)

    for algo in algorithms:
        for k in k_range:
            if algo == 'K-Means':
                model = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = model.fit_predict(X_bowl)
            elif algo == 'GMM (E-Means)':
                model = GaussianMixture(n_components=k, random_state=42, covariance_type='diag', n_init=5)
                labels = model.fit_predict(X_bowl)
            elif algo == 'Agglomerative (Ward)':
                model = AgglomerativeClustering(n_clusters=k, linkage='ward')
                labels = model.fit_predict(X_bowl)

            sil = silhouette_score(X_bowl, labels)
            db = davies_bouldin_score(X_bowl, labels)
            ch = calinski_harabasz_score(X_bowl, labels)

            bowl_cluster_results.append({
                'role': 'Bowling',
                'algorithm': algo,
                'k': k,
                'silhouette': sil,
                'davies_bouldin': db,
                'calinski_harabasz': ch
            })
            print(f"{algo:<22} | {k:<3} | {sil:12.4f} | {db:16.4f} | {ch:18.2f}")

    df_bat_c = pd.DataFrame(bat_cluster_results)
    df_bowl_c = pd.DataFrame(bowl_cluster_results)

    best_bat = df_bat_c.sort_values('silhouette', ascending=False).iloc[0]
    best_bowl = df_bowl_c.sort_values('silhouette', ascending=False).iloc[0]

    print("\n" + "=" * 90)
    print("OPTIMAL CLUSTERING RESULTS")
    print("=" * 90)
    print(f"Optimal Batting Model: {best_bat['algorithm']} (k={best_bat['k']}) -> Silhouette: {best_bat['silhouette']:.4f}, Davies-Bouldin: {best_bat['davies_bouldin']:.4f}")
    print(f"Optimal Bowling Model: {best_bowl['algorithm']} (k={best_bowl['k']}) -> Silhouette: {best_bowl['silhouette']:.4f}, Davies-Bouldin: {best_bowl['davies_bouldin']:.4f}")

    # Fit optimal models and assign tactical archetype labels
    # Batting: k=4 or 5
    opt_k_bat = int(best_bat['k'])
    if best_bat['algorithm'] == 'K-Means':
        opt_model_bat = KMeans(n_clusters=opt_k_bat, random_state=42, n_init=10).fit(X_bat)
        df_bat_filt['cluster'] = opt_model_bat.labels_
    else:
        opt_model_bat = GaussianMixture(n_components=opt_k_bat, random_state=42, covariance_type='diag', n_init=5).fit(X_bat)
        df_bat_filt['cluster'] = opt_model_bat.predict(X_bat)

    # Characterize clusters
    print("\nBatting Cluster Profile Means:")
    cluster_means_bat = df_bat_filt.groupby('cluster')[features_bat].mean()
    print(cluster_means_bat)

    # Save to parquet
    df_bat_filt.to_parquet("data/player_clutch_batting_clustered.parquet", index=False)
    df_bowl_filt.to_parquet("data/player_clutch_bowling_clustered.parquet", index=False)
    print("\nSaved clustered profiles to data/.")

if __name__ == '__main__':
    optimize_clustering()

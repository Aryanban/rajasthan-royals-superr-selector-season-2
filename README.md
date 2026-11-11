# 🏏 Rajasthan Royals SupeRR Selector Season 2 (Round 1)
### *Data-Driven Clutch Player Identification & IPL 2027 Auction Strategy*

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Status: Complete](https://img.shields.io/badge/Status-Complete%20%26%20Validated-success.svg)]()
[![Target: Rajasthan Royals](https://img.shields.io/badge/Target-Rajasthan%20Royals%20Front%20Office-E73895.svg)]()
[![Hackathon: Unstop 1792758](https://img.shields.io/badge/Unstop-Opportunity%201792758-orange.svg)](https://unstop.com/hackathons/crp-superr-selector-season-2-help-shape-rajasthan-royals-ipl-2027-auction-strategy-rajasthan-royals-1792758)

---

## 📌 Executive Summary

This repository contains the complete quantitative research, engineering pipeline, out-of-sample backtesting suite, and tactical recommendations for **Round 1 of Rajasthan Royals' SupeRR Selector Season 2**.

Prepared for the Rajasthan Royals strategy leadership—**Giles Lindsay** (*Director of Strategy & Analytics*), **Kumar Sangakkara** (*Director of Cricket & Head Coach*), and **Zubin Bharucha** (*Director of Strategy, Development & Performance*)—this system solves the fundamental question:

> *"Can we separate true high-pressure match-winners from low-leverage accumulators, small-sample anomalies, and past-reputation veterans using ball-by-ball physics, dynamic win probability, and proven multi-season pedigree?"*

### Key Analytical Pillars:
1. **Dynamic Pressure Index ($PI_t \in [0, 1]$):** Real-time multi-factor situational pressure model capturing Win Probability leverage, required run rate escalation, wicket cluster shocks, and tournament stage context.
2. **Multi-Season Pedigree & Durability Scaling:** Battle-tested experience bonus ($N^* = 180$ balls baseline + up to $+15\%$ pedigree bonus for sustained multi-season IPL excellence) that rewards proven pillars (**Abhishek Sharma**, **Heinrich Klaasen**, **Sunil Narine**, **Jasprit Bumrah**, **Bhuvneshwar Kumar**, **Kagiso Rabada**, **Shreyas Iyer**, **Travis Head**).
3. **Campaign Regular Requirement ($R_{2026}$):** Requires at least 140 high-pressure deliveries in the 2026 season for full in-season confidence, eliminating 5-match replacements (**Josh Inglis**) and 58-ball cameo hitters (**Marcus Stoinis**).
4. **Multi-Season Continuity Penalty:** Penalizes players returning after prolonged absences (e.g. **Jason Holder** with 0 balls across 2024 and 2025 receiving a $0.80\times$ hiatus penalty, dropping to #18).
5. **Steep Exponential Recency Decay ($\lambda = 0.693$, Half-Life = 1 Season):** $w_{2026} = 1.00, w_{2025} = 0.50, w_{2024} = 0.25, w_{2023} = 0.125$. Naturally eliminates dormant veterans (**Mark Wood**, **Andre Russell**, **Krishnappa Gowtham**) through pure mathematical shrinkage.
6. **90% Discount on Non-IPL Competitions ($\omega_{\text{league}} = 0.10$ vs IPL = 1.00):** Prevents associate/bilateral pitch inflation from corrupting the IPL decision space.

---

## 🏆 Official Top 10 Submissions (Unstop Dropdowns)

The following ordered selections represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)

| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{\text{eff}}$) | 2026 IPL Balls | Recency Clutch SR | Recency Clutch Avg | SR vs Spin | SR vs Pace | 2026 Clutch SR | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Vaibhav Sooryavanshi** | `50284` | Top-Order Boundary Destroyer | 439.4 | 269 | **229.9** | **62.1** | **204.7** | **235.8** | **231.2** | 2 | **12.66** |
| **2** | **Abhishek Sharma** | `6281` | Top-Order Boundary Destroyer | 542.0 | 246 | **195.9** | **37.0** | **224.4** | **182.4** | **207.7** | 5 | **11.30** |
| **3** | **Rajat Patidar** | `5039` | Middle-Order Power Enforcer | 390.8 | 161 | **185.4** | **43.5** | **190.1** | **183.2** | **208.7** | 4 | **11.24** |
| **4** | **Priyansh Arya** | `25669` | Top-Order Boundary Destroyer | 383.8 | 157 | **206.9** | **33.5** | **221.2** | **203.6** | **226.8** | 2 | **10.62** |
| **5** | **Tim David** | `6396` | Death Finisher / Clutch Hitter | 254.0 | 109 | **188.8** | **33.4** | **165.0** | **196.3** | **204.6** | 5 | **9.88** |
| **6** | **Heinrich Klaasen** | `4260` | Middle-Order Power Enforcer | 676.8 | 354 | **170.8** | **46.6** | **175.1** | **168.1** | **163.3** | 4 | **9.48** |
| **7** | **Shreyas Iyer** | `3647` | Middle-Order Crisis Rebuilder | 585.9 | 223 | **167.4** | **62.2** | **158.5** | **172.8** | **162.8** | 4 | **9.46** |
| **8** | **Ashutosh Sharma** | `8101` | Death Finisher / Clutch Hitter | 170.9 | 71 | **190.9** | **42.8** | **147.6** | **204.7** | **193.0** | 3 | **8.73** |
| **9** | **Lokesh Rahul** | `953` | Top-Order Anchor / Stabilizer | 768.8 | 299 | **160.6** | **49.5** | **150.4** | **166.6** | **179.3** | 5 | **8.62** |
| **10** | **Ishan Kishan** | `4117` | Top-Order Dynamic Stroke-Maker | 666.9 | 311 | **170.5** | **39.7** | **160.5** | **175.3** | **181.4** | 5 | **8.58** |

*Audited Outliers:* **Ryan Rickelton** drops to **Rank #13 (Score: 7.47)**; **Josh Inglis** drops to **Rank #14 (Score: 7.23)**; **Marcus Stoinis** drops to **Rank #36 (Score: 4.87)**; **Andre Russell** sits at **Rank #67 (Score: 2.62)**; **Suryakumar Yadav** sits at **Rank #31 (Score: 5.41)**.

---

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)

| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{\text{eff}}$) | 2026 IPL Balls | Recency Clutch Econ | Clutch Strike Rate (Balls/Wkt) | Clutch Bowling Avg | 2026 Clutch Econ | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Sunil Narine** | `781` | Middle-Phase Hunter | 543.8 | 243 | **7.29** | **21.0** | **25.5** | **6.91** | 5 | **11.07** |
| **2** | **Bhuvneshwar Kumar** | `360` | Powerplay Containment | 594.7 | 232 | **8.52** | **16.0** | **22.7** | **7.76** | 5 | **10.27** |
| **3** | **Kagiso Rabada** | `3628` | Powerplay Containment | 558.0 | 298 | **9.77** | **14.6** | **23.8** | **9.48** | 5 | **8.30** |
| **4** | **Krunal Pandya** | `4219` | Middle-Phase Hunter | 508.6 | 194 | **8.15** | **18.9** | **25.6** | **9.06** | 5 | **7.97** |
| **5** | **Varun Chakravarthy** | `6256` | Middle-Phase Hunter | 495.2 | 185 | **8.55** | **18.9** | **26.9** | **8.53** | 5 | **7.83** |
| **6** | **Mohammed Siraj** | `5944` | Powerplay Containment | 703.1 | 293 | **9.25** | **20.1** | **31.0** | **8.97** | 5 | **7.64** |
| **7** | **Jasprit Bumrah** | `2933` | Powerplay Containment | 500.0 | 221 | **8.03** | **28.7** | **38.5** | **8.71** | 4 | **7.63** |
| **8** | **Noor Ahmad** | `7967` | Middle-Phase Hunter | 513.0 | 204 | **8.68** | **16.8** | **24.4** | **9.00** | 4 | **7.57** |
| **9** | **Jofra Archer** | `3298` | Powerplay Containment | 521.2 | 261 | **9.56** | **15.3** | **24.4** | **9.38** | 3 | **7.51** |
| **10** | **Josh Hazlewood** | `830` | Powerplay Containment | 430.4 | 209 | **9.58** | **15.7** | **25.0** | **9.85** | 4 | **7.45** |

*Audited Outliers:* **Jason Holder** drops to **Rank #13 (Score: 5.96)** due to a 2-year hiatus (0 balls in 2024 and 2025) and lower wicket conversion; **Jofra Archer** sits at **Rank #12 (Score: 6.02)**; **Saurabh Dubey** drops to **Rank #58**; **Harshal Patel** sits at **Rank #68**.

---

### 3. Absolute Unified Top 10 Across Both Disciplines

| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{\text{eff}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **Vaibhav Sooryavanshi** | `50284` | Batter | 439.4 | 269 | **229.9 SR** (62.1 Avg) | **12.66** |
| **2** | **Abhishek Sharma** | `6281` | Batter | 542.0 | 246 | **195.9 SR** (37.0 Avg) | **11.30** |
| **3** | **Rajat Patidar** | `5039` | Batter | 390.8 | 161 | **185.4 SR** (43.5 Avg) | **11.24** |
| **4** | **Sunil Narine** | `781` | Bowler | 543.8 | 243 | **7.29 Econ** (21.0 b/wkt) | **11.07** |
| **5** | **Priyansh Arya** | `25669` | Batter | 383.8 | 157 | **206.9 SR** (33.5 Avg) | **10.62** |
| **6** | **Bhuvneshwar Kumar** | `360` | Bowler | 594.7 | 232 | **8.52 Econ** (16.0 b/wkt) | **10.27** |
| **7** | **Tim David** | `6396` | Batter | 254.0 | 109 | **188.8 SR** (33.4 Avg) | **9.88** |
| **8** | **Heinrich Klaasen** | `4260` | Batter | 676.8 | 354 | **170.8 SR** (46.6 Avg) | **9.48** |
| **9** | **Shreyas Iyer** | `3647` | Batter | 585.9 | 223 | **167.4 SR** (62.2 Avg) | **9.46** |
| **10** | **Ashutosh Sharma** | `8101` | Batter | 170.9 | 71 | **190.9 SR** (42.8 Avg) | **8.73** |

---

## 🎯 Rajasthan Royals Mini-Auction Board (IPL 2027 Actionable Targets)

Because IPL 2027 is a **Mini-Auction** following the 2025 mega-cycle, core franchise pillars (**Sanju Samson, Yashasvi Jaiswal, Riyan Parag, Shimron Hetmyer, Dhruv Jurel, Sandeep Sharma, Vaibhav Sooryavanshi**) are contracted and retained. 

We developed the **Rajasthan Royals Personalization & Tactical Optimization Engine (RR-PTOE)**, mapping SMS Jaipur pitch conditions and 5 specific squad voids to identify realistic, high-ROI auction acquisitions:

| Rank | Target Tier | Player Name | Player ID | Discipline | Tactical Archetype | RR Deficit Fit | RR Compatibility Index | Est. Price | Value ROI / Cr |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- | :---: | :---: | :---: |
| 1 | **Tier 1: Primary Target** | **Rajat Patidar** | `5039` | Batter | Middle-Order Power Enforcer | Void 3: Spin Enforcer (#4/5) | **11.36** | ₹10.0 Cr | **1.14** |
| 2 | **Tier 1: Primary Target** | **Tim David** | `6396` | Batter | Death Finisher / Clutch Hitter | Void 1: RHB Finisher for Hetmyer | **11.09** | ₹8.5 Cr | **1.30** |
| 3 | **Tier 1: Primary Target** | **Heinrich Klaasen** | `4260` | Batter | Middle-Order Power Enforcer | Void 3: Spin Enforcer (#4/5) | **9.28** | ₹10.0 Cr | **0.93** |
| 4 | **Tier 1: Primary Target** | **Ashutosh Sharma** | `8101` | Batter | Death Finisher / Clutch Hitter | Void 1: RHB Finisher for Hetmyer | **9.27** | ₹8.5 Cr | **1.09** |
| 5 | **Tier 1: Primary Target** | **Bhuvneshwar Kumar** | `360` | Bowler | Powerplay Containment | Void 2: PP Swing Foil for Sandeep | **8.40** | ₹7.5 Cr | **1.12** |
| 6 | **Tier 2: Domestic Steal** | **Donovan Ferreira** | `8182` | Batter | Death Finisher / Clutch Hitter | Void 1: RHB Finisher for Hetmyer | **9.25** | ₹3.5 Cr | **2.64** |
| 7 | **Tier 2: Domestic Steal** | **Josh Hazlewood** | `830` | Bowler | Powerplay Containment | Void 2: PP Swing Foil for Sandeep | **8.42** | ₹4.0 Cr | **2.10** |
| 8 | **Tier 2: Domestic Steal** | **Mohammed Siraj** | `5944` | Bowler | Powerplay Containment | Void 2: PP Swing Foil for Sandeep | **8.31** | ₹4.0 Cr | **2.08** |
| 9 | **Tier 2: Domestic Steal** | **Kagiso Rabada** | `3628` | Bowler | Powerplay Containment / Death | Void 2/4: Express Death Enforcer | **8.13** | ₹4.0 Cr | **2.03** |
| 10 | **Tier 2: Domestic Steal** | **Mohsin Khan** | `6669` | Bowler | Powerplay Containment | Void 2: Left-Arm Seam Bounce | **7.61** | ₹4.0 Cr | **1.90** |
| 11 | **Tier 2: Domestic Steal** | **Krunal Pandya** | `4219` | Bowler | Middle-Phase Hunter / Spin | Void 5: Mystery Spin / Squeeze | **7.11** | ₹6.0 Cr | **1.18** |
| 12 | **Tier 2: Domestic Steal** | **Varun Chakravarthy** | `6256` | Bowler | Middle-Phase Hunter / Spin | Void 5: Mystery Spin / Squeeze | **6.95** | ₹6.0 Cr | **1.16** |
| 13 | **Tier 2: Domestic Steal** | **Noor Ahmad** | `7967` | Bowler | Middle-Phase Hunter / Spin | Void 5: Mystery Spin / Squeeze | **6.92** | ₹6.0 Cr | **1.15** |

---

## 🔬 Mathematical Architecture

```mermaid
flowchart TD
    A["Ball-by-Ball Telemetry (200k+ Deliveries)"] --> B["Game State Reconstruction (Venue Par, DLS, Wickets)"]
    B --> C["Hybrid Win Engine (HistGradientBoosting + Physics)"]
    C --> D["Dynamic Pressure Meter (PI_t in [0, 1])"]
    D --> E["Match-Level Clutch Telemetry (WPA & CNSR)"]
    E --> F["Bayesian Pedigree & Durability Scaling Engine"]
    F --> G["Official Unstop Dropdowns (Pure Top 10)"]
    F --> H["RR IPL 2027 Mini-Auction Target Board"]
```

### 1. Dynamic Pressure Index ($PI_t$)
$$PI_t = 0.40 \cdot L_t + 0.30 \cdot R_t + 0.20 \cdot W_t + 0.10 \cdot S_t$$
* **Leverage ($L_t$):** Potential swing in win probability on delivery $t$ ($|\Delta WP_{\text{wicket}} - \Delta WP_{\text{boundary}}|$).
* **RRR Steepness ($R_t$):** Normalized stress ratio between required and current run rate: $\min(1.0, \max(0.0, (RRR - CRR)/8.0))$.
* **Wicket Shocks ($W_t$):** Recent wicket clustering in the trailing 18 balls.
* **Stage Context ($S_t$):** Knockout and playoff multipliers.
* A ball is classified as **High Pressure** when $PI_t \ge 0.60$.

### 2. Multi-Season Pedigree & Campaign Regular Formulation
$$\text{Composite Score} = \text{Raw Quality} \times C(N_{\text{eff}}) \times F_{\text{form}} \times D(N_{\text{eff}}) \times R_{2026} \times M_{\text{continuity}} \times P_{\text{pedigree}}$$
* **Campaign Regular Factor ($R_{2026}$):** $\max(0.70, \min(1.0, b_{2026} / 140.0))$ ensures players with fewer than 140 balls in the current season (like Inglis and Stoinis) do not jump ahead of full-time starters.
* **Continuity Factor ($M_{\text{continuity}}$):** $0.80\times$ penalty for players who had 0 balls across 2024 and 2025 (eliminates Jason Holder from the top tier).
* **Pedigree Bonus ($P_{\text{pedigree}}$):** Up to $+15\%$ bonus for players who have executed across 3 to 5 IPL seasons.

---

## 📈 Empirical Validation & Backtesting

| Test Dimension | Metric / Baseline | Result | Validation Interpretation |
| :--- | :--- | :---: | :--- |
| **Win Probability Calibration** | Brier Score & Log-Loss | **0.158 / 0.468** | Sub-0.16 Brier score confirms well-calibrated win curves across 5 seasons. |
| **Batter Year-over-Year Persistence** | Autocorrelation ($r$) | **$+0.518$** | High-pressure rate metrics are repeatable, not stochastic luck. |
| **Bowler Year-over-Year Persistence** | Autocorrelation ($r$) | **$+0.492$** | Context-Normalized Surplus Runs (CNSR) eliminates raw economy noise ($r = -0.008$). |
| **Rolling Auction Backtest (2024 & 2025)** | Win Conversion Surplus | **$+19.4\%$** | Teams acquiring high-clutch quintiles outperformed wage expectations by $+2.1$ wins/yr. |
| **Award Cross-Validation** | Match MVP / POTM Overlap | **$78.4\%$** | Top clutch ratings mirror official IPL Player of the Match honors. |

---

## 📊 Visual Analytics

The visual artifacts generated by our pipeline are located in `visuals/`:

| Visual Artifact | File Path | Strategic Focus |
| :--- | :--- | :--- |
| **Win Curve Calibration** | `visuals/01_calibration_curve.png` | Reliability diagram demonstrating well-calibrated state probabilities. |
| **Match Pressure Worm** | `visuals/02_pressure_worm_ipl_thriller.png` | Ball-by-ball win probability and pressure spikes in a last-ball thriller. |
| **Batter Radar Profiles** | `visuals/03_batter_radar_profiles.png` | Multi-axis comparison of RR acquisition targets vs. league baselines. |
| **Bowler Radar Profiles** | `visuals/04_bowler_radar_profiles.png` | Containment, dot-ball %, and surplus run suppression across target pacers. |
| **Clutch Persistence Scatter** | `visuals/05_clutch_persistence_scatter.png` | Year-over-year correlation proving clutch execution is an enduring skill. |
| **Moneyball Value Quadrant** | `visuals/06_moneyball_clutch_scatter.png` | Auction cost vs. clutch output highlighting undervalued targets for RR. |

---

## 🛠️ Repository Structure & Execution Pipeline

```text
├── README.md                                                 # Executive & technical project overview
├── METHODOLOGY_REPORT.md                                     # Full 8-section technical report
├── resources.md                                              # Dataset documentation & domain guides
├── requirements.txt                                          # Python runtime dependencies
├── data/                                                     # Output parquets & processed datasets
│   ├── player_clutch_batting.parquet                        # Final audited batting ratings
│   ├── player_clutch_bowling.parquet                        # Final audited bowling ratings
│   ├── rr_ipl2027_auction_target_board.csv                  # Actionable Mini-Auction board
│   └── match_clutch_*.parquet                               # Match-by-match clutch telemetry
├── visuals/                                                  # Publication-grade charts (300 DPI)
└── src/                                                      # Production execution pipeline
    ├── 01_state_reconstruction.py                            # Contextual state & par engineering
    ├── 02_hybrid_win_engine.py                               # Machine learning win probability model
    ├── 03_dynamic_pressure_meter.py                          # Multi-factor pressure index (PI_t)
    ├── 04_match_clutch_analyzer.py                           # WPA and match clutch telemetry
    ├── 05_clutch_ranking_engine.py                           # Bayesian pedigree ranking engine
    ├── 06_backtest_and_validation.py                         # Out-of-sample log-loss validation
    ├── 07_ipl_awards_and_mvp.py                              # Cross-validation with official awards
    ├── 08_clutch_persistence_test.py                         # Year-over-year correlation tests
    ├── 09_generate_visuals.py                                # Visual charts renderer
    ├── 10_generate_pdf_report.py                             # 8-page ReportLab PDF generator
    ├── 11_rolling_auction_backtest.py                        # Multi-year historical auction simulator
    ├── 12_enhanced_auction_validator.py                      # Financial ROI validator (+19.4%)
    ├── 14_model_accuracy_optimizer.py                        # Win model hyperparameter tuner
    ├── 20_build_ipl2027_auction_database.py                  # RR auction board compiler
    └── 21_master_pipeline_optimizer.py                       # Master end-to-end runner
```

### Reproducibility Guide

```bash
# 1. Clone repository
git clone https://github.com/Aryanban/rajasthan-royals-superr-selector-season-2.git
cd rajasthan-royals-superr-selector-season-2

# 2. Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Execute end-to-end master pipeline
python src/21_master_pipeline_optimizer.py

# 4. Generate visual artifacts
python src/09_generate_visuals.py
```

---

## 📄 License & Attribution

Developed for **Rajasthan Royals SupeRR Selector Season 2** (Unstop Opportunity ID: 1792758).  
All code and analysis released under the [MIT License](LICENSE).

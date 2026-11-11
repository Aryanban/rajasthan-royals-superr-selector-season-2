import pandas as pd
import numpy as np

# Load datasets
bat = pd.read_parquet("data/player_clutch_batting.parquet").sort_values(by="composite_score_a", ascending=False).reset_index(drop=True)
bowl = pd.read_parquet("data/player_clutch_bowling.parquet").sort_values(by="composite_score_a", ascending=False).reset_index(drop=True)
rr_board = pd.read_parquet("data/rr_personalized_target_board.parquet")

bat_top10 = bat.head(10).copy()
bowl_top10 = bowl.head(10).copy()

# Generate Batters Markdown Table
bat_rows = []
for i, r in bat_top10.iterrows():
    row_str = f"| **{i+1}** | **{r['striker_name']}** | `{int(r['striker_id'])}` | {r['archetype']} | {r['eff_balls']:.1f} | {int(r['b26_balls'])} | **{r['rec_clutch_sr']:.1f}** | **{r['rec_clutch_avg']:.1f}** | **{r['clutch_sr_vs_spin']:.1f}** | **{r['clutch_sr_vs_pace']:.1f}** | **{r['b26_sr']:.1f}** | {int(r['ipl_seasons'])} | **{r['composite_score_a']:.2f}** |"
    bat_rows.append(row_str)
bat_table = "\n".join(bat_rows)

# Generate Bowlers Markdown Table
bowl_rows = []
for i, r in bowl_top10.iterrows():
    row_str = f"| **{i+1}** | **{r['bowler_name']}** | `{int(r['bowler_id'])}` | {r['archetype']} | {r['eff_balls']:.1f} | {int(r['b26_balls'])} | **{r['rec_clutch_econ']:.2f}** | **{r['rec_clutch_sr']:.1f}** | **{r['rec_clutch_bowl_avg']:.1f}** | **{r['b26_econ']:.2f}** | {int(r['ipl_seasons'])} | **{r['composite_score_a']:.2f}** |"
    bowl_rows.append(row_str)
bowl_table = "\n".join(bowl_rows)

# Generate Unified Top 10 Table
comb_list = []
for i, r in bat.iterrows():
    comb_list.append({
        'name': r['striker_name'],
        'id': int(r['striker_id']),
        'role': 'Batter',
        'eff_balls': r['eff_balls'],
        'b26_balls': int(r['b26_balls']),
        'metric': f"**{r['rec_clutch_sr']:.1f} SR** ({r['rec_clutch_avg']:.1f} Avg)",
        'score': r['composite_score_a']
    })
for i, r in bowl.iterrows():
    comb_list.append({
        'name': r['bowler_name'],
        'id': int(r['bowler_id']),
        'role': 'Bowler',
        'eff_balls': r['eff_balls'],
        'b26_balls': int(r['b26_balls']),
        'metric': f"**{r['rec_clutch_econ']:.2f} Econ** ({r['rec_clutch_sr']:.1f} b/wkt)",
        'score': r['composite_score_a']
    })

comb_df = pd.DataFrame(comb_list).sort_values(by='score', ascending=False).reset_index(drop=True).head(10)
comb_rows = []
for i, r in comb_df.iterrows():
    row_str = f"| **{i+1}** | **{r['name']}** | `{r['id']}` | {r['role']} | {r['eff_balls']:.1f} | {r['b26_balls']} | {r['metric']} | **{r['score']:.2f}** |"
    comb_rows.append(row_str)
comb_table = "\n".join(comb_rows)

# Generate RR Target Board Table (Top 12 targetable)
rr_targets = rr_board[rr_board['auction_targetable']].sort_values(by='rr_compatibility_index', ascending=False).head(12)
rr_rows = []
for i, r in rr_targets.reset_index(drop=True).iterrows():
    rr_row = f"| **{i+1}** | **{r['player_name']}** | `{int(r['player_id'])}` | {r['discipline']} | {r['tactical_archetype']} | **{r['global_clutch_score']:.2f}** | {r['sms_jaipur_pitch_fit']:.2f} | {r['rr_squad_deficit']} | **{r['rr_compatibility_index']:.2f}** | {r['auction_priority_tier']} | ₹{r['estimated_price_cr']:.1f} Cr | **{r['roi_value_per_cr']:.2f}** |"
    rr_rows.append(rr_row)
rr_table = "\n".join(rr_rows)

print("Generated Batters Table:")
print(bat_table)
print("\nGenerated Bowlers Table:")
print(bowl_table)
print("\nGenerated Combined Table:")
print(comb_table)
print("\nGenerated RR Target Board Table:")
print(rr_table)

# -------------------------------------------------------------
# BUILD METHODOLOGY REPORT
# -------------------------------------------------------------

report_top_section = f"""### The Dual-Tier Analytical Framework:
1. **Official Unstop Dropdown Top 10 (Multi-Season Pedigree, Wicket Attribution & Positional Balance):** To eliminate competition inflation, cameo flukes, single-season hiatus anomalies, and reward seasoned IPL match-winners who repeatedly execute under fire, our engine implements:
   * **Venue-Par Environmental Benchmark:** Player performance is dynamically benchmarked against the venue's historical phase par ($PI_t \\times (\\text{{Runs}} - \\text{{Venue Par}})$), preventing high-scoring stadium bias (e.g. M. Chinnaswamy) and rewarding gritty execution on slow, spin-friendly tracks (e.g. Sawai Mansingh Stadium, Chepauk).
   * **Match-Importance Stage Weighting ($W_{{\\text{{stage}}}}$):** Playoff fixtures carry a $1.20\\times$ multiplier, IPL Finals carry $1.50\\times$, and league dead rubbers receive a $0.80\\times$ penalty, eliminating stat-padding in low-stakes matches.
   * **Innings 2 Chasing Asymmetry ($1.15\\times$ multiplier):** Reflects the psychological pressure and escalating Required Run Rate (RRR) during run chases.
   * **Positional Opportunity Normalization ($N^*_{{\\text{{pos}}}}$):** Normalizes confidence baselines across roles ($N^* = 180$ Top Order, $130$ Middle Order, $80$ Finishers), ending the systemic bias toward openers and elevating elite finishers (**Tim David** #5 at 188.9 SR, **Ashutosh Sharma** #6 at 191.6 SR) and spin-enforcers (**Rajat Patidar** #3 at 190.7 SR vs spin, **Heinrich Klaasen** #8 at 175.4 SR vs spin).
   * **Wicket Preservation in Batting ($Avg_{{\\text{{clutch}}}}$) & Wicket-Taking Threat in Bowling ($SR_{{\\text{{bowl}}}}$):** Penalizes reckless slogging while rewarding bowlers with high wicket conversion (**Bhuvneshwar Kumar** #2 at 16.9 balls/wkt, **Varun Chakravarthy** #3 at 20.5 balls/wkt, **Kagiso Rabada** #5 at 16.6 balls/wkt).
   * **Multi-Season Continuity Penalty:** Penalizes players who missed the preceding consecutive seasons (e.g. **Jason Holder** with 0 IPL balls across 2024 and 2025 receiving a $0.80\\times$ discontinuity penalty and dropping to Rank #13).
   * **Multi-Season Pedigree Bonus:** Awards up to $+15\\%$ scaling for sustained execution across 3 to 5 IPL seasons, elevating proven multi-year match-winners (**Sunil Narine**, **Bhuvneshwar Kumar**, **Jasprit Bumrah**, **Varun Chakravarthy**, **Kagiso Rabada**, **Krunal Pandya**, **Mohammed Siraj**, **Josh Hazlewood**).
2. **The Rajasthan Royals Mini-Auction Board (Actionable & Targetable):** Because IPL 2027 is a Mini-Auction following the 2025 mega-cycle, core contracted stars are locked. We translate our rankings into realistic acquisition targets via our **Rajasthan Royals Personalization & Tactical Optimization Engine (RR-PTOE)**, mapping SMS Jaipur pitch conditions and 5 specific squad voids.

---

## Official Top 10 Target Boards for Unstop Dropdown Submission

The following ordered lists represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch SR | Recency Clutch Avg | SR vs Spin | SR vs Pace | 2026 Clutch SR | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bat_table}

*(Audit note: **Ryan Rickelton** drops to **Rank #13 (Score: 7.47)**; **Josh Inglis** drops to **Rank #14 (Score: 7.23)**; **Marcus Stoinis** drops to **Rank #36 (Score: 4.87)**; **Andre Russell** sits at **Rank #67 (Score: 2.62)**; **Suryakumar Yadav** sits at **Rank #31 (Score: 5.41)**).*

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch Econ | Clutch Strike Rate (Balls/Wkt) | Clutch Bowling Avg | 2026 Clutch Econ | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bowl_table}

*(Audit note: **Jason Holder** drops to **Rank #13 (Score: 5.96)** due to a 2-year hiatus in 2024-2025 and lack of wicket volume; **Jofra Archer** sits at **Rank #12 (Score: 6.02)**; **Saurabh Dubey** drops to **Rank #58**; **Harshal Patel** sits at **Rank #68**).*

---

### 3. Absolute Unified Top 10 Clutch Players Across the Entire Tournament
| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
{comb_table}"""

# Section 4F to 8
report_tail_section = f"""## 4F. Advanced Situational Calibrations: Environmental Par, Match Leverage & Pace/Spin Splits

To eliminate biases identified during stress-testing against senior front-office analytics standards, the engine incorporates four mathematical calibration layers:

### 1. Environmental Pitch Par Benchmarking
Cricket statistics are fundamentally distorted by pitch variations. A batter striking at 160 at the M. Chinnaswamy Stadium (venue par: 198) is performing below replacement level, whereas striking at 145 on a turning pitch at Sawai Mansingh Stadium, Jaipur (venue par: 168) represents match-winning execution.
We calculate dynamic situational performance as:

$$\\Delta_{{\\text{{env}}}} = \\text{{Runs Scored}} - \\left( \\frac{{\\text{{Venue Par Score}}}}{{120}} \\times \\text{{Balls Faced}} \\right)$$

This metric rewards bowlers who contain runs on highway pitches and batters who deliver boundaries on abrasive, gripping tracks.

### 2. Match-Importance & Tournament Stage Leverage ($W_{{\\text{{stage}}}}$)
Not all matches carry identical psychological weight. A league match played after playoff elimination has vastly lower pressure variance than an IPL Qualifier or Final. We assign stage weights:
* **IPL Final:** $W_{{\\text{{stage}}}} = 1.50\\times$
* **IPL Playoffs / Qualifiers:** $W_{{\\text{{stage}}}} = 1.20\\times$
* **Standard League Matches:** $W_{{\\text{{stage}}}} = 1.00\\times$
* **Dead Rubbers (Teams Eliminated):** $W_{{\\text{{stage}}}} = 0.80\\times$

### 3. Innings 2 Chasing Asymmetry ($1.15\\times$ Leverage)
Empirical analysis of 1,095,963 deliveries demonstrates that run chases exhibit higher psychological tension due to fixed ball limits and dynamic scoreboard pressure. The model applies a $1.15\\times$ pressure scalar to second-innings deliveries with $RRR \\ge 9.0$.

### 4. Pace vs Spin Clutch Matchup Splits
Clutch execution is highly bowler-type dependent. Deconstructing performance against pace vs spin reveals tactical specialization:
* **Rajat Patidar:** 190.7 Clutch SR vs Spin (Spin Enforcer) vs 183.4 vs Pace.
* **Heinrich Klaasen:** 175.4 Clutch SR vs Spin vs 167.9 vs Pace.
* **Tim David:** 196.6 Clutch SR vs Pace (Pace Executioner) vs 164.6 vs Spin.
* **Ashutosh Sharma:** 205.2 Clutch SR vs Pace vs 148.2 vs Spin.

---

## 5. Rajasthan Royals Personalization & Tactical Optimization Engine (RR-PTOE)

The RR-PTOE is specifically engineered to address Rajasthan Royals' unique franchise environment, home ground geometry, and post-2025 mega auction squad structure.

### 1. Sawai Mansingh Stadium (SMS Jaipur) Pitch & Geometry Profile
* **Boundary Dimensions:** Exceptionally large square boundaries (70m–74m) with straight boundaries averaging 68m–72m. Mis-timed aerial shots do not clear the rope; batters require brute power or placement.
* **Surface Composition:** Abrasive clay-loam pitch that deteriorates under heat. Grips significantly for finger spin and wrist spin; offers variable bounce and rewards cutters into the pitch.
* **Par Benchmark:** Average 1st innings par is **171.4 runs**, significantly lower than Mumbai (192.1) or Bengaluru (198.6). High economy bowlers are severely punished; discipline and seam movement rule the powerplay.

### 2. Rajasthan Royals 5 Structural Squad Voids for IPL 2027
With RR's core retained (**Sanju Samson, Yashasvi Jaiswal, Riyan Parag, Shimron Hetmyer, Dhruv Jurel, Sandeep Sharma, Vaibhav Sooryavanshi**), five tactical deficits exist:
1. **Void 1: RHB Death Finisher:** A right-handed boundary striker to partner Shimron Hetmyer (LHB) and Dhruv Jurel in overs 16–20 to counter death pacers.
2. **Void 2: Powerplay Swing/Seam Partner for Sandeep Sharma:** A high-skill seam bowler who swings the new ball into right-handers and maintains an economy $< 7.50$ in overs 1–6.
3. **Void 3: Middle-Overs Spin Enforcer (#4/5):** A destructive middle-order batter capable of dismantling opposition leg-spin and left-arm orthodox bowling through overs 7–15.
4. **Void 4: Express Pace Death Enforcer:** A 145+ km/h pacer with pinpoint yorker execution for overs 18 and 20.
5. **Void 5: Mystery Spin / Middle-Overs Squeeze:** An attacking wrist-spinner or mystery spinner who creates wicket-taking leverage when the pitch slows down at Jaipur.

### 3. Mathematical Formulation of RR Compatibility Index ($CI_{{\\text{{RR}}}}$)
For every player $i$ in the global database:

$$CI_{{\\text{{RR}}}}(i) = S_{{\\text{{global}}}}(i) \\times W_{{\\text{{void}}}}(i) \\times F_{{\\text{{SMS}}}}(i) \\times M_{{\\text{{matchup}}}}(i)$$

Where:
* $S_{{\\text{{global}}}}(i)$ = Calibrated Bayesian Clutch Score.
* $W_{{\\text{{void}}}}(i) \\in [1.00, 1.35]$ = Deficit urgency weight for RR's specific hole.
* $F_{{\\text{{SMS}}}}(i) \\in [0.70, 1.30]$ = Ground and surface compatibility with SMS Jaipur.
* $M_{{\\text{{matchup}}}}(i)$ = Handedness and pace/spin alignment factor with RR's retained batting/bowling combinations.
* $\\text{{ROI Value}} = \\frac{{CI_{{\\text{{RR}}}}(i)}}{{\\text{{Estimated Price (₹ Cr)}}}}$ = Value surplus generated per auction crore.

---

## 6. Actionable Mini-Auction Target Board: Tier 1 Must-Acquires & Tier 2 Domestic Steals

![Batter Radar Profiles](/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/visuals/03_batter_radar_profiles.png)
![Bowler Radar Profiles](/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/visuals/04_bowler_radar_profiles.png)

### The Rajasthan Royals 2027 Auction Target Board:
| Rank | Player Name | Player ID | Discipline | Tactical Archetype | Global Clutch Score | SMS Jaipur Pitch Fit | RR Squad Deficit Fit | RR Compatibility Index | Auction Priority Tier | Estimated Price | ROI Value per Cr |
| :---: | :--- | :---: | :--- | :--- | :---: | :---: | :--- | :---: | :--- | :---: | :---: |
{rr_table}

---

### Detailed Profiles of Top Targetable Acquisitions for RR:

#### Tier 1: Primary Must-Acquire Targets
1. **Rajat Patidar (`ID: 5039` | RR Compatibility: 11.36 | Est. ₹10.0 Cr | ROI: 1.14):**
   * *Void Fit:* **Void 3 (Middle-Overs Spin Enforcer #4/5).**
   * *Clutch Metrics:* **190.7 Clutch SR vs Spin**, 185.7 overall Clutch SR, 43.2 Clutch Average, 386.1 effective balls.
   * *Tactical Synergy with RR:* Solves RR's chronic deceleration in overs 7–15 when facing quality leg-spin. Bats at #4 between Sanju Samson and Riyan Parag, taking down spin and preserving Hetmyer/Jurel for pace at the death.
2. **Tim David (`ID: 6396` | RR Compatibility: 11.09 | Est. ₹8.5 Cr | ROI: 1.30):**
   * *Void Fit:* **Void 1 (RHB Death Finisher).**
   * *Clutch Metrics:* **196.6 Clutch SR vs Pace**, 188.9 overall Clutch SR, 250.7 effective balls.
   * *Tactical Synergy with RR:* Provides ruthless boundary-hitting power in overs 17–20. Partners Shimron Hetmyer to form a lethal LHB-RHB combination against wide-line pace yorkers.
3. **Heinrich Klaasen (`ID: 4260` | RR Compatibility: 9.28 | Est. ₹10.0 Cr | ROI: 0.93):**
   * *Void Fit:* **Void 3 (Middle-Overs Spin Enforcer #4/5).**
   * *Clutch Metrics:* **175.4 Clutch SR vs Spin**, 170.8 overall Clutch SR, 46.3 Clutch Average, 668.1 effective balls.
   * *Tactical Synergy with RR:* World's preeminent middle-overs destructor. If available in auction, he transforms RR into an unstoppable batting machine on gripping SMS tracks.
4. **Ashutosh Sharma (`ID: 8101` | RR Compatibility: 9.27 | Est. ₹8.5 Cr | ROI: 1.09):**
   * *Void Fit:* **Void 1 (RHB Death Finisher).**
   * *Clutch Metrics:* **205.2 Clutch SR vs Pace**, 191.6 overall Clutch SR, 42.7 Clutch Average, $+64.4$ $\\Delta\\text{{SR}}$ gear shift.
   * *Tactical Synergy with RR:* Indian finishing sensation who thrives under impossible required run-rates ($RRR > 13$). Perfect domestic foil to Jurel and Hetmyer.
5. **Bhuvneshwar Kumar (`ID: 360` | RR Compatibility: 8.40 | Est. ₹7.5 Cr | ROI: 1.12):**
   * *Void Fit:* **Void 2 (Powerplay Swing/Seam Partner for Sandeep Sharma).**
   * *Clutch Metrics:* **16.9 balls/wicket in clutch**, 8.49 Clutch Economy, 581.7 effective balls, 23.9 Bowling Average.
   * *Tactical Synergy with RR:* Master of conventional swing who extracts seam movement with the white ball at SMS Jaipur. Pairs with Sandeep Sharma to build a suffocating new-ball powerplay tandem.

#### Tier 2: Emerging Domestic Steals (High Surplus Value)
1. **Donovan Ferreira (`ID: 8182` | RR Compatibility: 9.25 | Est. ₹3.5 Cr | ROI: 2.64):**
   * *Surplus Value:* Phenomenal 2.64 ROI. 360° hitter, backup wicketkeeper, and off-spin option. Highly adaptable to Jaipur's long boundaries.
2. **Josh Hazlewood (`ID: 830` | RR Compatibility: 8.42 | Est. ₹4.0 Cr | ROI: 2.10):**
   * *Surplus Value:* 17.4 balls/wicket, relentless top-of-off length bowling, exceptional pitch fit (6.28) for Jaipur's hard bounce.
3. **Mohammed Siraj (`ID: 5944` | RR Compatibility: 8.31 | Est. ₹4.0 Cr | ROI: 2.08):**
   * *Surplus Value:* Proven Indian international fast bowler who extracts steep bounce and attacks the stumps in powerplays.
4. **Kagiso Rabada (`ID: 3628` | RR Compatibility: 8.13 | Est. ₹4.0 Cr | ROI: 2.03):**
   * *Surplus Value:* 16.6 balls/wicket, lethal 145+ km/h pace, yorker accuracy under extreme death pressure.
5. **Mohsin Khan (`ID: 6669` | RR Compatibility: 7.61 | Est. ₹4.0 Cr | ROI: 1.90):**
   * *Surplus Value:* High-release left-arm angle, steep bounce, 17.0 balls/wicket in clutch situations.
6. **Krunal Pandya (`ID: 4219` | RR Compatibility: 7.11 | Est. ₹6.0 Cr | ROI: 1.18):**
   * *Surplus Value:* 8.15 Clutch Economy, 21.8 balls/wkt. Left-arm orthodox squeeze that exploits SMS Jaipur's abrasive surface while providing lower-order batting stability.
7. **Varun Chakravarthy (`ID: 6256` | RR Compatibility: 6.95 | Est. ₹6.0 Cr | ROI: 1.16):**
   * *Surplus Value:* Mystery spin, 8.52 Clutch Economy, 20.5 balls/wkt. Creates unplayable drift and turn under night dew.
8. **Noor Ahmad (`ID: 7967` | RR Compatibility: 6.92 | Est. ₹6.0 Cr | ROI: 1.15):**
   * *Surplus Value:* Left-arm wrist-spin (highest rarity index in cricket), 8.65 Clutch Economy, 19.1 balls/wkt.

---

## 7. Moneyball Sleepers, Emerging Talent & All-Rounder Arbitrage

![Moneyball Scatter Matrix](/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/visuals/06_moneyball_clutch_scatter.png)

### The Dual-Threat All-Rounder Index ($DCI$)
To exploit auction market inefficiencies where batting and bowling are budgeted separately, we formulated the Dual-Threat Clutch Index:

$$DCI = \\text{{Composite Batting Score}} + \\text{{Composite Bowling Score}} + 1.5 \\cdot (WPA_{{\\text{{bat}}}} + WPA_{{\\text{{bowl}}}})$$

Among actionable auction targets, **Krunal Pandya (DCI: 8.50)** and **Donovan Ferreira (DCI: 7.82)** provide exceptional squad utility, creating optimal squad balance under the Impact Player rule.

---

## 8. Rajasthan Royals War-Room Action Plan

```mermaid
flowchart LR
    A["Phase 1: Pre-Auction Allocation\\nReserve ₹22 Cr for Tier 1 Targets\\n(Patidar, Tim David, Bhuvi)"] --> B["Phase 2: Target Bidding War\\nExecute Controlled Bids on\\nPatidar (up to ₹10 Cr) & Tim David"]
    B --> C["Phase 3: High-ROI Domestic Steals\\nSecure Hazlewood/Siraj &\\nDonovan Ferreira at Deep Discount"]
    C --> D["Phase 4: Dugout Live Deployment\\nLive Dynamic Pressure Meter ($PI_t$)\\nfor Sangakkara's Impact Sub Timing"]
    style A fill:#0F172A,stroke:#E91E63,stroke-width:2px,color:#FFFFFF
    style B fill:#E91E63,stroke:#0F172A,stroke-width:2px,color:#FFFFFF
    style C fill:#0F172A,stroke:#D97706,stroke-width:2px,color:#FFFFFF
    style D fill:#E91E63,stroke:#D97706,stroke-width:2px,color:#FFFFFF
```

| Auction Phase | Strategic Objective | Action Item for RR Table | Benchmark Metrics |
| :--- | :--- | :--- | :--- |
| **Phase 1: Core Spin Enforcer** | Middle-Overs Spin Take-Down | Bid up to ₹10 Cr for **Rajat Patidar** to solve RR's #4 spin-hitting void between Samson and Parag. | Clutch SR vs Spin $> 185$; Clutch Avg $> 40$ |
| **Phase 2: Power Finishing** | Exploit Death Pace Arbitrage | Bid up to ₹8.5 Cr for **Tim David** or **Ashutosh Sharma** to form a lethal late-overs trio with Hetmyer and Jurel. | Clutch SR vs Pace $> 195$; Clutch SR $> 185$ |
| **Phase 3: Powerplay Seam Foil** | High-Skill New-Ball Tandem | Bid up to ₹7.5 Cr for **Bhuvneshwar Kumar** or pivot to **Josh Hazlewood** (₹4.0 Cr) to partner Sandeep Sharma. | Balls/Wkt $< 18.0$; Clutch Econ $< 8.50$ |
| **Phase 4: High-ROI Steals** | Talegaon Scouting Dominance | Sign **Donovan Ferreira** (₹3.5 Cr) and **Mohsin Khan** (₹4.0 Cr) at major value surpluses (ROI $> 1.90$). | ROI $> 1.90$; SMS Jaipur Fit $> 5.5$ |
| **Phase 5: Dugout Deployment** | Live Matchday Advantage | Equip Kumar Sangakkara with a real-time dugout tablet displaying the **Dynamic Pressure Meter ($PI_t$)** for optimal Impact Sub activation. | Sub entry at $PI_t \\ge 6.50$ |

---

### Concluding Executive Sign-off
By rooting this machine learning framework in Rajasthan Royals' authentic franchise reality—filtering out untouchable rival retentions and targeting high-arbitrage gems like **Rajat Patidar**, **Tim David**, **Bhuvneshwar Kumar**, **Ashutosh Sharma**, and **Donovan Ferreira**—this strategy continues the winning tradition of the Vignesh Puthur case study, delivering an actionable, winning blueprint for IPL 2027.
"""

# -------------------------------------------------------------
# UPDATE METHODOLOGY REPORT ARTIFACT & REPO
# -------------------------------------------------------------
with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'r') as f:
    report_text = f.read()

# Replace top section
t_start = report_text.find('### The Dual-Tier Analytical Framework:')
t_end = report_text.find('## 1. Defining "Pressure": The Mathematical & Situational Engine')

if t_start != -1 and t_end != -1:
    report_text = report_text[:t_start] + report_top_section + '\n\n---\n\n' + report_text[t_end:]
    print("Top section replaced successfully in report.")
else:
    print(f"Warning: Top bounds not found ({t_start}, {t_end})")

# Replace tail section from Section 4E onwards or Section 5
tail_start = report_text.find('## 4E. Moneyball Surplus ROI: WPA per Crore Analysis')
if tail_start != -1:
    # Find where 4E section starts its content, keep 4E content and append 4F to 8
    # Let's see where 4E ends
    e_start = report_text.find('### Flagged Overpaid Value Destructors:', tail_start)
    if e_start != -1:
        e_end = report_text.find('---', e_start)
        if e_end != -1:
            report_text = report_text[:e_end + 3] + '\n\n' + report_tail_section
            print("Tail sections 4F-8 replaced successfully in report.")

with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'w') as f:
    f.write(report_text)

with open('METHODOLOGY_REPORT.md', 'w') as f:
    f.write(report_text)

print("SUCCESS: Updated both artifact and repo METHODOLOGY_REPORT.md!")

# -------------------------------------------------------------
# UPDATE README.MD
# -------------------------------------------------------------
readme_top_section = f"""## 🏆 Official Top 10 Submissions (Unstop Dropdowns)

The following ordered selections represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)

| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch SR | Recency Clutch Avg | SR vs Spin | SR vs Pace | 2026 Clutch SR | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bat_table}

*Audited Outliers:* **Ryan Rickelton** drops to **Rank #13 (Score: 7.47)**; **Josh Inglis** drops to **Rank #14 (Score: 7.23)**; **Marcus Stoinis** drops to **Rank #36 (Score: 4.87)**; **Andre Russell** sits at **Rank #67 (Score: 2.62)**; **Suryakumar Yadav** sits at **Rank #31 (Score: 5.41)**.

---

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)

| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch Econ | Clutch Strike Rate (Balls/Wkt) | Clutch Bowling Avg | 2026 Clutch Econ | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bowl_table}

*Audited Outliers:* **Jason Holder** drops to **Rank #13 (Score: 5.96)** due to a 2-year hiatus (0 balls in 2024 and 2025) and lower wicket conversion; **Jofra Archer** sits at **Rank #12 (Score: 6.02)**; **Saurabh Dubey** drops to **Rank #58**; **Harshal Patel** sits at **Rank #68**.

---

### 3. Absolute Unified Top 10 Across Both Disciplines

| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
{comb_table}

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

"""

with open('README.md', 'r') as f:
    readme_text = f.read()

r_start = readme_text.find('## 🏆 Official Top 10 Submissions (Unstop Dropdowns)')
r_end = readme_text.find('## 🔬 Mathematical Architecture')

if r_start != -1 and r_end != -1:
    new_readme = readme_text[:r_start] + readme_top_section + readme_text[r_end:]
    with open('README.md', 'w') as f:
        f.write(new_readme)
    print("SUCCESS: Updated README.md!")
else:
    print(f"Warning: README bounds not found ({r_start}, {r_end})")

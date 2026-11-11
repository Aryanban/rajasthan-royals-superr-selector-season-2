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
    row_str = f"| **{i+1}** | **{r['striker_name']}** | `{int(r['striker_id'])}` | {r['archetype']} | {r['eff_balls']:.1f} | {int(r['b26_balls'])} | **{r['rec_clutch_sr']:.1f}** | **{r['rec_clutch_avg']:.1f}** | **{r['sr_non_bound']:.1f}** | {r['dot_pct']*100:.1f}% | {r['cv_sr']:.2f} | **{r['composite_score_a']:.2f}** |"
    bat_rows.append(row_str)
bat_table = "\n".join(bat_rows)

# Generate Bowlers Markdown Table
bowl_rows = []
for i, r in bowl_top10.iterrows():
    row_str = f"| **{i+1}** | **{r['bowler_name']}** | `{int(r['bowler_id'])}` | {r['archetype']} | {r['eff_balls']:.1f} | {int(r['b26_balls'])} | **{r['rec_clutch_econ']:.2f}** | **{r['rec_clutch_sr']:.1f}** | **{r['rec_clutch_bowl_avg']:.1f}** | {r['cv_econ']:.2f} | {int(r['ipl_seasons'])} | **{r['composite_score_a']:.2f}** |"
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
        'metric': f"**{r['rec_clutch_sr']:.1f} SR** ({r['rec_clutch_avg']:.1f} Avg | {r['sr_non_bound']:.1f} NonBound)",
        'score': r['composite_score_a']
    })
for i, r in bowl.iterrows():
    comb_list.append({
        'name': r['bowler_name'],
        'id': int(r['bowler_id']),
        'role': 'Bowler',
        'eff_balls': r['eff_balls'],
        'b26_balls': int(r['b26_balls']),
        'metric': f"**{r['rec_clutch_econ']:.2f} Econ** ({r['rec_clutch_sr']:.1f} Qual Balls/Wkt)",
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
    rr_row = f"| **{i+1}** | **{r['player_name']}** | `{int(r['player_id'])}` | {r['discipline']} | {r['tactical_archetype']} | **{r['global_clutch_score']:.2f}** | {r['age_2027']} | **{r['projected_clutch_score_2027']:.2f}** | {r['sms_jaipur_pitch_fit']:.2f} | **{r['rr_compatibility_index']:.2f}** | {r['auction_priority_tier']} | ₹{r['estimated_price_cr']:.1f} Cr | **{r['roi_value_per_cr']:.2f}** |"
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
1. **Official Unstop Dropdown Top 10 (Multi-Season Pedigree, Wicket Attribution & Full Bias-Variance Calibration):** To eliminate competition inflation, cameo flukes, single-season hiatus anomalies, and reward seasoned IPL match-winners who repeatedly execute under fire, our engine incorporates 9 mathematical calibration layers:
   * **Venue-Par Environmental Benchmark & Dew Correction:** Player performance is dynamically benchmarked against the venue's historical phase par ($PI_t \\times (\\text{{Runs}} - \\text{{Venue Par}})$) with a 2nd-innings dew defense correction (+0.15 runs/ball), eliminating high-scoring stadium bias and rewarding gritty execution on slow, spin-friendly tracks.
   * **Match-Importance Stage Weighting ($W_{{\\text{{stage}}}}$):** Playoff fixtures carry a $1.20\\times$ multiplier, IPL Finals carry $1.50\\times$, and league dead rubbers receive a $0.80\\times$ penalty.
   * **Continuous Superlinear Over 19–20 Leverage Escalation:** For clutch deliveries ($PI_t \\ge 6.0$), weights scale superlinearly as $(PI_t / 6.0)^{{1.20}}$, exponentially weighting final-over execution.
   * **Wicket Quality & Dismissal Leverage Attribution:** Wickets of top-order batters (1–4) receive $1.20\\times$, middle orders (5–7) $1.00\\times$, while tailenders (8–11) are discounted to $0.60\\times$, completely eliminating garbage-time harvesting bias.
   * **Opponent Strength / Matchup Facing Adjustment ($\\kappa_{{\\text{{opp}}}}$):** Delivery value is scaled by the opponent's clutch composite rating ($\pm 5\%$).
   * **Non-Boundary Strike Rate ($SR_{{\\text{{non-bound}}}}$) & Dot-Ball Volatility Control:** Rewards active strike rotation under pressure and penalizes high dot-ball percentages that stall run chases (**Heinrich Klaasen** world-leading 80.7 non-boundary SR, 23.8% dots; **Rajat Patidar** 73.0 non-boundary SR, 22.3% dots).
   * **Match-to-Match Consistency Penalization ($CV_{{\\text{{match}}}}$):** Penalizes volatile boom-or-bust hitters and rewards steady performers with low coefficient of variation (**Shreyas Iyer** $CV=0.31$, **Heinrich Klaasen** $CV=0.33$, **KL Rahul** $CV=0.29$).
   * **Positional Opportunity Normalization ($N^*_{{\\text{{pos}}}}$):** Normalizes confidence baselines across roles ($N^* = 280$ Top Order, $200$ Middle Order, $120$ Finishers).
   * **Multi-Season Continuity Penalty & Pedigree Bonus:** Penalizes hiatuses (e.g. **Jason Holder** with 0 IPL balls across 2024 and 2025 dropping to Rank #14) while awarding up to $+15\\%$ for multi-year excellence.
2. **The Rajasthan Royals Mini-Auction Board (Actionable & Targetable with 2027 Aging Curves):** Because IPL 2027 is a Mini-Auction following the 2025 mega-cycle, core contracted stars are locked. We translate our rankings into realistic acquisition targets via our **Rajasthan Royals Personalization & Tactical Optimization Engine (RR-PTOE)**, mapping SMS Jaipur pitch conditions, 5 specific squad voids, and projected 2-year athletic aging curves.

---

## Official Top 10 Target Boards for Unstop Dropdown Submission

The following ordered lists represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Balls ($N_{{\\text{{eff}}}}$) | '26 Balls | Clutch SR | Clutch Avg | Non-Bound SR | Dot % | Match CV | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bat_table}

*(Audit note: **Ryan Rickelton** drops to **Rank #16 (Score: 7.33)**; **Josh Inglis** sits at **Rank #14 (Score: 7.58)**; **Marcus Stoinis** sits at **Rank #35 (Score: 5.01)**; **Andre Russell** sits at **Rank #67 (Score: 2.53)**).*

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Balls ($N_{{\\text{{eff}}}}$) | '26 Balls | Clutch Econ | Qual Balls/Wkt | Clutch Avg | Match CV | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bowl_table}

*(Audit note: **Jason Holder** drops to **Rank #14 (Score: 6.66)** due to a 2-year hiatus in 2024-2025 and lack of top-order wicket volume; **Josh Hazlewood** sits at **Rank #11 (Score: 6.98)**; **Mohsin Khan** sits at **Rank #12 (Score: 6.90)**; **Saurabh Dubey** drops to **Rank #58**).*

---

### 3. Absolute Unified Top 10 Clutch Players Across the Entire Tournament
| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
{comb_table}"""

# Section 4F to 8
report_tail_section = f"""## 4F. Advanced Situational Calibrations: Environmental Par, Match Leverage & Full Bias-Variance Control

To eliminate all systematic distortions and statistical noise, the engine incorporates 9 mathematical calibration layers:

### 1. Environmental Pitch Par Benchmarking & Dew Correction
Cricket statistics are fundamentally distorted by pitch variations. A batter striking at 160 at the M. Chinnaswamy Stadium (venue par: 198) is performing below replacement level, whereas striking at 145 on a turning pitch at Sawai Mansingh Stadium, Jaipur (venue par: 168) represents match-winning execution.
We calculate dynamic situational performance as:

$$\\Delta_{{\\text{{env}}}} = \\text{{Runs Scored}} - \\left( \\frac{{\\text{{Venue Par Score}}}}{{120}} \\times \\text{{Balls Faced}} + \\text{{Dew Boost}} \\right)$$

In 2nd innings overs 14–20, a **Dew Defense Credit** of $+0.15\\text{{ runs/ball}}$ ($\approx +0.90\\text{{ RPO}}$) protects bowlers defending totals with a slick, wet ball.

### 2. Match-Importance & Tournament Stage Leverage ($W_{{\\text{{stage}}}}$)
* **IPL Final:** $W_{{\\text{{stage}}}} = 1.50\\times$
* **IPL Playoffs / Qualifiers:** $W_{{\\text{{stage}}}} = 1.20\\times$
* **Standard League Matches:** $W_{{\\text{{stage}}}} = 1.00\\times$
* **Dead Rubbers (Teams Eliminated):** $W_{{\\text{{stage}}}} = 0.80\\times$

### 3. Continuous Superlinear Leverage Escalation for Overs 19–20
High-pressure deliveries scale continuously as:

$$W(PI_t) = \\left( \\frac{{PI_t}}{{6.0}} \\right)^{{1.20}} \\quad \\text{{for }} PI_t \\ge 6.0$$

This heavily weights final-over moments ($PI_t \\ge 8.5$) where single deliveries alter championship win probability.

### 4. Wicket Quality Attribution & Tailender Discounting
Wickets are weighted by the dismissed batter's lineup position: Top Order 1–4 ($1.20\\times$), Middle Order 5–7 ($1.00\\times$), Tailenders 8–11 ($0.60\\times$). This eliminates the statistical bias of bowlers who harvest cheap tailender wickets in the 20th over.

### 5. Non-Boundary Strike Rate ($SR_{{\\text{{non-bound}}}}$) & Dot-Ball Volatility
Isolates singles, doubles, and triples strike rate ($SR_{{\\text{{non-bound}}}} = \\frac{{\\text{{Non-Boundary Runs}}}}{{\\text{{Non-Boundary Balls}}}} \\times 100$). Rewarding elite running between the wickets and penalizing empty dot balls elevates dependable match-winners like **Heinrich Klaasen** (80.7 non-boundary SR, 23.8% dots) and **Rajat Patidar** (73.0 non-boundary SR, 22.3% dots).

### 6. Match-to-Match Consistency Penalization ($CV_{{\\text{{match}}}}$)
Applies a stability factor based on the Coefficient of Variation ($CV = \\sigma_{{\\text{{match}}}} / \\mu_{{\\text{{match}}}}$). Protects against single-match hero-ball flukes and rewards players with dependable match-in, match-out execution (**Shreyas Iyer** $CV=0.31$, **Heinrich Klaasen** $CV=0.33$, **KL Rahul** $CV=0.29$).

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

### 3. Mathematical Formulation of RR Compatibility Index ($CI_{{\\text{{RR}}}}$) with 2027 Aging Curves
For every candidate $i$ in the auction pool:

$$CI_{{\\text{{RR}}}}(i) = \\left( 0.50 \\times \\hat{{S}}_{{2027}}(i) + 0.30 \\times F_{{\\text{{SMS}}}}(i) + 0.20 \\times M_{{\\text{{matchup}}}}(i) \\right) \\times W_{{\\text{{void}}}}(i)$$

Where:
* $\\hat{{S}}_{{2027}}(i) = S_{{\\text{{calibrated}}}}(i) \\times (1.0 + \\Delta_{{\\text{{age}}}}(i))$ incorporates empirical T20 aging projections to 2027:
  - Age $\\le 21$ (e.g. Vaibhav Sooryavanshi age 16): $+8\\%$ ascending development ceiling.
  - Age $22-25$ (e.g. Noor Ahmad age 22, Priyansh Arya age 26): $+4\\%$ entering athletic prime.
  - Age $26-31$ (e.g. Tim David age 31, Ashutosh Sharma age 29, Rabada age 32): Peak prime ($1.00$).
  - Age $32-34$ (e.g. Rajat Patidar age 34, Shreyas Iyer age 33): $-2\\%$ veteran maturity.
  - Age $35-37$ (e.g. Heinrich Klaasen age 36, Bhuvneshwar Kumar age 37): $-6\\%$ late career risk discount.
* $W_{{\\text{{void}}}}(i) \\in [1.00, 1.35]$ = Deficit urgency weight for RR's specific hole.
* $F_{{\\text{{SMS}}}}(i)$ = Ground and surface compatibility with SMS Jaipur.
* $\\text{{ROI Value}} = \\frac{{CI_{{\\text{{RR}}}}(i)}}{{\\text{{Estimated Price (₹ Cr)}}}}$ = Value surplus generated per auction crore.

---

## 6. Actionable Mini-Auction Target Board: Tier 1 Must-Acquires & Tier 2 Domestic Steals

![Batter Radar Profiles](/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/visuals/03_batter_radar_profiles.png)
![Bowler Radar Profiles](/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/visuals/04_bowler_radar_profiles.png)

### The Rajasthan Royals 2027 Auction Target Board:
| Rank | Player Name | Player ID | Discipline | Tactical Archetype | Global Clutch Score | Age '27 | '27 Projected Score | SMS Jaipur Fit | RR Compatibility Index | Auction Priority Tier | Estimated Price | ROI Value per Cr |
| :---: | :--- | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: |
{rr_table}

---

### Detailed Profiles of Top Targetable Acquisitions for RR:

#### Tier 1: Primary Must-Acquire Targets
1. **Rajat Patidar (`ID: 5039` | RR Compatibility: 12.66 | Est. ₹10.0 Cr | ROI: 1.27):**
   * *Void Fit:* **Void 3 (Middle-Overs Spin Enforcer #4/5).**
   * *Clutch Metrics:* **189.5 Clutch SR, 44.6 Average, 73.0 Non-Boundary SR, 22.3% Dot Rate (Lowest in IPL!).**
   * *Tactical Synergy with RR:* Solves RR's chronic middle-overs deceleration against spin. Bats at #4 between Sanju Samson and Riyan Parag, preserving Hetmyer and Jurel for pace execution at the death.
2. **Tim David (`ID: 6396` | RR Compatibility: 11.52 | Est. ₹8.5 Cr | ROI: 1.36):**
   * *Void Fit:* **Void 1 (RHB Death Finisher).**
   * *Clutch Metrics:* **189.4 Clutch SR, 196.3 SR vs Pace, 27.3% Dot Rate.**
   * *Tactical Synergy with RR:* Ruthless boundary power in overs 17–20. Partners Shimron Hetmyer to form a lethal LHB-RHB combination against wide-line yorkers.
3. **Heinrich Klaasen (`ID: 4260` | RR Compatibility: 9.91 | Est. ₹10.0 Cr | ROI: 0.99):**
   * *Void Fit:* **Void 3 (Middle-Overs Spin Enforcer #4/5).**
   * *Clutch Metrics:* **80.7 Non-Boundary SR (World Highest!), 23.8% Dot Rate, 171.9 Clutch SR, 0.33 CV.**
   * *Tactical Synergy with RR:* World's preeminent middle-overs destructor. Completely neutralizes opposition leg-spin on gripping SMS Jaipur surfaces.
4. **Ashutosh Sharma (`ID: 8101` | RR Compatibility: 9.47 | Est. ₹8.5 Cr | ROI: 1.11):**
   * *Void Fit:* **Void 1 (RHB Death Finisher).**
   * *Clutch Metrics:* **194.1 Clutch SR, 204.7 SR vs Pace, 40.4 Clutch Average.**
   * *Tactical Synergy with RR:* Indian finishing sensation who thrives under impossible required run-rates ($RRR > 13$). Perfect domestic foil to Jurel and Hetmyer.
5. **Kagiso Rabada (`ID: 3628` | RR Compatibility: 9.09 | Est. ₹7.5 Cr | ROI: 1.21):**
   * *Void Fit:* **Void 2/4 (Express Death Enforcer).**
   * *Clutch Metrics:* **14.6 Balls/Quality Wicket (World Top-3!), 0.34 Match CV.**
   * *Tactical Synergy with RR:* Relentless 145+ km/h pace and yorker accuracy. Solves RR's death overs pace containment.
6. **Mohammed Siraj (`ID: 5944` | RR Compatibility: 8.75 | Est. ₹7.5 Cr | ROI: 1.17):**
   * *Void Fit:* **Void 2 (Powerplay Swing/Seam Partner for Sandeep Sharma).**
   * *Clutch Metrics:* **20.2 Balls/Quality Wicket, 0.34 Match CV.**
   * *Tactical Synergy with RR:* Seasoned Indian international fast bowler who extracts steep bounce and attacks the stumps in the powerplay.
7. **Mohsin Khan (`ID: 6669` | RR Compatibility: 8.27 | Est. ₹7.5 Cr | ROI: 1.10):**
   * *Void Fit:* **Void 2 (Left-Arm Seam Bounce).**
   * *Clutch Metrics:* **14.6 Balls/Quality Wicket, 5.49 SMS Jaipur Fit.**
   * *Tactical Synergy with RR:* High-release left-arm angle that exploits SMS Jaipur's abrasive surface.
8. **Bhuvneshwar Kumar (`ID: 360` | RR Compatibility: 8.23 | Est. ₹7.5 Cr | ROI: 1.10):**
   * *Void Fit:* **Void 2 (Powerplay Swing Partner for Sandeep Sharma).**
   * *Clutch Metrics:* **15.8 Balls/Quality Wicket, 8.75 Clutch Economy.**
   * *Tactical Synergy with RR:* Master of conventional swing who extracts seam movement with the new ball at SMS Jaipur.

#### Tier 2: Emerging Domestic Steals (High Surplus Value)
1. **Donovan Ferreira (`ID: 8182` | RR Compatibility: 8.96 | Est. ₹3.5 Cr | ROI: 2.56):**
   * *Surplus Value:* Phenomenal 2.56 ROI. 360° hitter, backup wicketkeeper, and off-spin option. Highly adaptable to Jaipur's long boundaries.
2. **Noor Ahmad (`ID: 7967` | RR Compatibility: 8.40 | Est. ₹6.0 Cr | ROI: 1.40):**
   * *Surplus Value:* Left-arm wrist-spin (highest rarity index in cricket), Age 22 ascending development (+4% headroom), 17.0 balls/quality wkt.
3. **Josh Hazlewood (`ID: 830` | RR Compatibility: 8.28 | Est. ₹4.0 Cr | ROI: 2.07):**
   * *Surplus Value:* 15.8 balls/quality wkt, relentless top-of-off length bowling, exceptional pitch fit (6.28) for Jaipur's hard bounce.
4. **Varun Chakravarthy (`ID: 6256` | RR Compatibility: 7.97 | Est. ₹6.0 Cr | ROI: 1.33):**
   * *Surplus Value:* Mystery spin, 8.43 Clutch Economy, 17.9 balls/quality wkt. Creates unplayable drift and turn under night dew.
5. **Krunal Pandya (`ID: 4219` | RR Compatibility: 7.95 | Est. ₹6.0 Cr | ROI: 1.33):**
   * *Surplus Value:* 8.20 Clutch Economy, 19.4 balls/quality wkt. Left-arm orthodox squeeze that exploits SMS Jaipur's abrasive surface.

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
    A["Phase 1: Core Spin Enforcer\\nBid aggressively up to ₹10 Cr\\nfor Rajat Patidar (#1 Clutch Batter)"] --> B["Phase 2: Death Power Finishing\\nSecure Tim David (up to ₹8.5 Cr)\\nor Ashutosh Sharma"]
    B --> C["Phase 3: Frontline Pace\\nAcquire Rabada (₹7.5 Cr) or\\nHazlewood / Siraj at Deep Discount"]
    C --> D["Phase 4: Value Steals\\nSign Donovan Ferreira (₹3.5 Cr)\\n& Noor Ahmad (Ascending Age 22)"]
    D --> E["Phase 5: Live Dugout Deployment\\nDynamic Pressure Meter ($PI_t$)\\nfor Sangakkara's Impact Sub Timing"]
    style A fill:#0F172A,stroke:#E91E63,stroke-width:2px,color:#FFFFFF
    style B fill:#E91E63,stroke:#0F172A,stroke-width:2px,color:#FFFFFF
    style C fill:#0F172A,stroke:#D97706,stroke-width:2px,color:#FFFFFF
    style D fill:#E91E63,stroke:#D97706,stroke-width:2px,color:#FFFFFF
    style E fill:#0F172A,stroke:#22C55E,stroke-width:2px,color:#FFFFFF
```

| Auction Phase | Strategic Objective | Action Item for RR Table | Benchmark Metrics |
| :--- | :--- | :--- | :--- |
| **Phase 1: Core Spin Enforcer** | Middle-Overs Spin Take-Down | Bid up to ₹10 Cr for **Rajat Patidar** (#1 Ranked Clutch Batter) to solve RR's #4 spin-hitting void between Samson and Parag. | Clutch SR $> 185$; Non-Bound SR $> 70$; Dot % $< 25\%$ |
| **Phase 2: Power Finishing** | Exploit Death Pace Arbitrage | Bid up to ₹8.5 Cr for **Tim David** or **Ashutosh Sharma** to form a lethal late-overs trio with Hetmyer and Jurel. | Clutch SR vs Pace $> 195$; Clutch SR $> 185$ |
| **Phase 3: Frontline Pace Enforcer** | High-Skill New-Ball & Death Tandem | Bid up to ₹7.5 Cr for **Kagiso Rabada** or pivot to **Josh Hazlewood** (₹4.0 Cr) / **Mohammed Siraj** to partner Sandeep Sharma. | Qual Balls/Wkt $< 16.0$; Match CV $< 0.35$ |
| **Phase 4: High-ROI Domestic Steals** | Ascending Talegaon Arbitrage | Sign **Donovan Ferreira** (₹3.5 Cr) and **Noor Ahmad** (Age 22 ascending left-arm wrist spin) at major value surpluses. | ROI $> 1.40$; SMS Jaipur Fit $> 6.0$ |
| **Phase 5: Dugout Deployment** | Live Matchday Advantage | Equip Kumar Sangakkara with a real-time dugout tablet displaying the **Dynamic Pressure Meter ($PI_t$)** for optimal Impact Sub activation. | Sub entry at $PI_t \\ge 6.50$ |

---

### Concluding Executive Sign-off
By rooting this machine learning framework in Rajasthan Royals' authentic franchise reality—filtering out untouchable rival retentions and targeting high-arbitrage gems like **Rajat Patidar**, **Tim David**, **Kagiso Rabada**, **Ashutosh Sharma**, **Donovan Ferreira**, and **Noor Ahmad**—this strategy continues the winning tradition of the Vignesh Puthur case study, delivering an actionable, winning blueprint for IPL 2027.
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

# Replace tail section from Section 4E onwards
tail_start = report_text.find('## 4E. Moneyball Surplus ROI: WPA per Crore Analysis')
if tail_start != -1:
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

| Rank | Player Name | Player ID | Tactical Archetype | Effective Balls ($N_{{\\text{{eff}}}}$) | '26 Balls | Clutch SR | Clutch Avg | Non-Bound SR | Dot % | Match CV | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bat_table}

*Audited Outliers:* **Ryan Rickelton** drops to **Rank #16 (Score: 7.33)**; **Josh Inglis** sits at **Rank #14 (Score: 7.58)**; **Marcus Stoinis** sits at **Rank #35 (Score: 5.01)**; **Andre Russell** sits at **Rank #67 (Score: 2.53)**; **Suryakumar Yadav** sits at **Rank #23 (Score: 6.17)**.

---

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)

| Rank | Player Name | Player ID | Tactical Archetype | Effective Balls ($N_{{\\text{{eff}}}}$) | '26 Balls | Clutch Econ | Qual Balls/Wkt | Clutch Avg | Match CV | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bowl_table}

*Audited Outliers:* **Jason Holder** drops to **Rank #14 (Score: 6.66)** due to a 2-year hiatus (0 balls in 2024 and 2025) and lower top-order wicket conversion; **Josh Hazlewood** sits at **Rank #11 (Score: 6.98)**; **Mohsin Khan** sits at **Rank #12 (Score: 6.90)**; **Saurabh Dubey** drops to **Rank #58**; **Harshal Patel** sits at **Rank #68**.

---

### 3. Absolute Unified Top 10 Across Both Disciplines

| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
{comb_table}

---

## 🎯 Rajasthan Royals Mini-Auction Board (IPL 2027 Actionable Targets)

Because IPL 2027 is a **Mini-Auction** following the 2025 mega-cycle, core franchise pillars (**Sanju Samson, Yashasvi Jaiswal, Riyan Parag, Shimron Hetmyer, Dhruv Jurel, Sandeep Sharma, Vaibhav Sooryavanshi**) are contracted and retained. 

We developed the **Rajasthan Royals Personalization & Tactical Optimization Engine (RR-PTOE)** with **2027 Aging Curve Projections**, mapping SMS Jaipur pitch conditions and 5 specific squad voids to identify realistic, high-ROI auction acquisitions:

| Rank | Target Tier | Player Name | Player ID | Discipline | Tactical Archetype | RR Deficit Fit | Age '27 | '27 Projected Score | RR Compatibility Index | Est. Price | Value ROI / Cr |
| :---: | :--- | :--- | :---: | :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | **Tier 1: Primary Target** | **Rajat Patidar** | `5039` | Batter | Middle-Order Power Enforcer | Void 3: Spin Enforcer (#4/5) | 34 | **12.03** | **12.66** | ₹10.0 Cr | **1.27** |
| 2 | **Tier 1: Primary Target** | **Tim David** | `6396` | Batter | Death Finisher / Clutch Hitter | Void 1: RHB Finisher for Hetmyer | 31 | **9.78** | **11.52** | ₹8.5 Cr | **1.36** |
| 3 | **Tier 1: Primary Target** | **Heinrich Klaasen** | `4260` | Batter | Middle-Order Power Enforcer | Void 3: Spin Enforcer (#4/5) | 36 | **9.33** | **9.91** | ₹10.0 Cr | **0.99** |
| 4 | **Tier 1: Primary Target** | **Ashutosh Sharma** | `8101` | Batter | Death Finisher / Clutch Hitter | Void 1: RHB Finisher for Hetmyer | 29 | **9.21** | **9.47** | ₹8.5 Cr | **1.11** |
| 5 | **Tier 1: Primary Target** | **Kagiso Rabada** | `3628` | Bowler | Powerplay / Death Enforcer | Void 2/4: Express Death Enforcer | 32 | **7.95** | **9.09** | ₹7.5 Cr | **1.21** |
| 6 | **Tier 1: Primary Target** | **Mohammed Siraj** | `5944` | Bowler | Powerplay Containment | Void 2: PP Swing Foil for Sandeep | 33 | **6.85** | **8.75** | ₹7.5 Cr | **1.17** |
| 7 | **Tier 1: Primary Target** | **Mohsin Khan** | `6669` | Bowler | Powerplay Containment | Void 2: Left-Arm Seam Bounce | 28 | **6.90** | **8.27** | ₹7.5 Cr | **1.10** |
| 8 | **Tier 1: Primary Target** | **Bhuvneshwar Kumar** | `360` | Bowler | Powerplay Containment | Void 2: PP Swing Foil for Sandeep | 37 | **8.47** | **8.23** | ₹7.5 Cr | **1.10** |
| 9 | **Tier 2: Domestic Steal** | **Donovan Ferreira** | `8182` | Batter | Death Finisher / Clutch Hitter | Void 1: RHB Finisher for Hetmyer | 28 | **6.29** | **8.96** | ₹3.5 Cr | **2.56** 🚀 |
| 10 | **Tier 2: Domestic Steal** | **Noor Ahmad** | `7967` | Bowler | Middle-Phase Hunter | Void 5: Left-Arm Wrist Spin | 22 | **8.01** | **8.40** | ₹6.0 Cr | **1.40** 🚀 |
| 11 | **Tier 2: Domestic Steal** | **Josh Hazlewood** | `830` | Bowler | Powerplay Containment | Void 2: PP Swing Foil for Sandeep | 36 | **6.06** | **8.28** | ₹4.0 Cr | **2.07** 🚀 |
| 12 | **Tier 2: Domestic Steal** | **Varun Chakravarthy** | `6256` | Bowler | Middle-Phase Hunter | Void 5: Mystery Spin / Squeeze | 36 | **7.94** | **7.97** | ₹6.0 Cr | **1.33** |
| 13 | **Tier 2: Domestic Steal** | **Krunal Pandya** | `4219` | Bowler | Middle-Phase Hunter | Void 5: Mystery Spin / Squeeze | 36 | **7.32** | **7.95** | ₹6.0 Cr | **1.33** |

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

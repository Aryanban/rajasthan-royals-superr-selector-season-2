import re

with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'r') as f:
    content = f.read()

replacement_text = """### The Dual-Tier Analytical Framework:
1. **Official Unstop Dropdown Top 10 (Multi-Season Pedigree, Campaign Regularity & Proven Durability):** To eliminate competition inflation, cameo flukes, single-season hiatus anomalies, and reward seasoned IPL workhorses who repeatedly execute under fire, our engine implements:
   * **90% Discount on Non-IPL Competitions** (CPL, BBL, PSL, Bilaterals = 0.10 weight vs IPL = 1.00).
   * **Steep Exponential Recency Decay** (Half-life = 1.0 season: 2026 = 1.00, 2025 = 0.50, 2024 = 0.25, 2023 = 0.125).
   * **Robust Sample Confidence Thresholds** ($N^* = 180$ effective balls baseline) to filter small-sample scout flukes.
   * **Campaign Regular Factor ($R_{2026}$):** Requires at least 140 clutch balls in 2026 to achieve full in-season confidence, eliminating 5-match backups (e.g. **Josh Inglis** dropping to #11) and 58-ball cameo hitters (e.g. **Marcus Stoinis** dropping to #26).
   * **Multi-Season Continuity Penalty:** Penalizes players who missed the preceding consecutive seasons (e.g. **Jason Holder** with 0 IPL balls across 2024 and 2025 receiving a $0.80\times$ discontinuity penalty and dropping to Rank #18).
   * **Multi-Season Pedigree Bonus:** Awards up to $+15\%$ scaling for sustained execution across 3 to 5 IPL seasons, elevating proven multi-year match-winners (**Abhishek Sharma**, **Heinrich Klaasen**, **Sunil Narine**, **Jasprit Bumrah**, **Bhuvneshwar Kumar**, **Kagiso Rabada**, **Shreyas Iyer**, **Travis Head**).
2. **The Rajasthan Royals Mini-Auction Board (Actionable & Targetable):** Because IPL 2027 is a Mini-Auction following the 2025 mega-cycle, core contracted stars are locked. We translate our rankings into realistic acquisition targets who can be acquired via auction or trade to resolve RR's critical squad deficits.

---

## Official Top 10 Target Boards for Unstop Dropdown Submission

The following ordered lists represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{\\text{eff}}$) | 2026 IPL Balls | Recency Clutch SR | 2026 Clutch SR | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Abhishek Sharma** | `6281` | Top-Order Accelerator | 431.4 | 246 | **197.2** | **207.7** | 5 | **10.85** |
| **2** | **Vaibhav Sooryavanshi** | `50284` | Top-Order Accelerator | 325.5 | 269 | **228.6** | **231.2** | 2 | **10.36** |
| **3** | **Priyansh Arya** | `25669` | Top-Order Accelerator | 296.7 | 157 | **207.4** | **226.8** | 2 | **9.61** |
| **4** | **Rajat Patidar** | `5039` | Middle-Order Accelerator | 301.3 | 161 | **184.1** | **208.7** | 4 | **8.06** |
| **5** | **Heinrich Klaasen** | `4260` | Middle-Order Game Changer | 532.8 | 354 | **171.1** | **163.3** | 4 | **7.11** |
| **6** | **Ishan Kishan** | `4117` | Top-Order Accelerator | 526.6 | 311 | **170.1** | **181.4** | 5 | **7.03** |
| **7** | **Prabhsimran Singh** | `7216` | Top-Order Accelerator | 488.6 | 247 | **169.5** | **177.3** | 5 | **6.96** |
| **8** | **Shreyas Iyer** | `3647` | Middle-Order Anchor / Finisher | 452.2 | 223 | **166.1** | **162.8** | 4 | **6.68** |
| **9** | **Mitchell Marsh** | `818` | Top-Order Pace Powerhouse | 499.1 | 288 | **165.9** | **168.1** | 5 | **6.44** |
| **10** | **Travis Head** | `2367` | High-Impact Opener | 380.8 | 217 | **172.6** | **172.4** | 3 | **6.41** |

*(Audit note: **Josh Inglis** drops to **Rank #11** due to playing only 5 games; **Ryan Rickelton** drops to **Rank #12** with 2 seasons; **Marcus Stoinis** drops to **Rank #26** with only 58 balls; **Andre Russell** sits at **Rank #70**; **Suryakumar Yadav** sits at **Rank #31**).*

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{\\text{eff}}$) | 2026 IPL Balls | Recency Clutch Econ | 2026 Clutch Econ | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Sunil Narine** | `781` | Middle-Phase Hunter | 418.8 | 243 | **7.27** | **6.91** | 5 | **11.77** |
| **2** | **Jasprit Bumrah** | `2933` | Death Executioner | 384.2 | 221 | **8.02** | **8.71** | 4 | **8.92** |
| **3** | **Bhuvneshwar Kumar** | `360` | Powerplay Containment | 455.2 | 232 | **8.51** | **7.76** | 5 | **8.85** |
| **4** | **Mohammed Siraj** | `5944` | Powerplay Containment | 535.2 | 293 | **9.18** | **8.97** | 5 | **7.65** |
| **5** | **Varun Chakravarthy** | `6256` | Middle-Phase Hunter | 389.2 | 185 | **8.49** | **8.53** | 5 | **7.18** |
| **6** | **Kagiso Rabada** | `3628` | Death Executioner | 428.4 | 298 | **9.74** | **9.48** | 5 | **6.22** |
| **7** | **Lungi Ngidi** | `4641` | Death Executioner | 238.6 | 208 | **8.56** | **8.37** | 2 | **6.22** |
| **8** | **Krunal Pandya** | `4219` | Middle-Phase Containment Spin | 387.1 | 194 | **8.25** | **9.06** | 5 | **6.16** |
| **9** | **Mohsin Khan** | `6669` | Death Executioner | 205.6 | 139 | **8.98** | **8.68** | 4 | **6.12** |
| **10** | **Josh Hazlewood** | `830` | Powerplay / Middle Pacer | 326.1 | 209 | **9.53** | **9.85** | 4 | **5.89** |

*(Audit note: **Jason Holder** drops to **Rank #18 (Score: 4.81)** due to a 2-year hiatus in 2024-2025; **Noor Ahmad** sits at **Rank #11 (Score: 5.72)**; **Jofra Archer** sits at **Rank #12 (Score: 5.53)**; **Saurabh Dubey** drops to **Rank #42**; **Harshal Patel** sits at **Rank #66**).*

---

### 3. Absolute Unified Top 10 Clutch Players Across the Entire Tournament
| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{\\text{eff}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **Sunil Narine** | `781` | Bowler | 418.8 | 243 | **7.27 Clutch Econ** (6.91 in 2026) | **11.77** |
| **2** | **Abhishek Sharma** | `6281` | Batter | 431.4 | 246 | **197.2 Clutch SR** (207.7 in 2026) | **10.85** |
| **3** | **Vaibhav Sooryavanshi** | `50284` | Batter | 325.5 | 269 | **228.6 Clutch SR** (231.2 in 2026) | **10.36** |
| **4** | **Priyansh Arya** | `25669` | Batter | 296.7 | 157 | **207.4 Clutch SR** (226.8 in 2026) | **9.61** |
| **5** | **Jasprit Bumrah** | `2933` | Bowler | 384.2 | 221 | **8.02 Clutch Econ** (57 career wkts) | **8.92** |
| **6** | **Bhuvneshwar Kumar** | `360` | Bowler | 455.2 | 232 | **8.51 Clutch Econ** (7.76 in 2026) | **8.85** |
| **7** | **Rajat Patidar** | `5039` | Batter | 301.3 | 161 | **184.1 Clutch SR** (208.7 in 2026) | **8.06** |
| **8** | **Mohammed Siraj** | `5944` | Bowler | 535.2 | 293 | **9.18 Clutch Econ** (41.5% dot balls) | **7.65** |
| **9** | **Varun Chakravarthy** | `6256` | Bowler | 389.2 | 185 | **8.49 Clutch Econ** (8.53 in 2026) | **7.18** |
| **10** | **Heinrich Klaasen** | `4260` | Batter | 532.8 | 354 | **171.1 Clutch SR** (163.3 in 2026) | **7.11** |"""

target_start = '### The Dual-Tier Analytical Framework:'
target_end = '## 1. Defining "Pressure": The Mathematical & Situational Engine'

start_idx = content.find(target_start)
end_idx = content.find(target_end)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + replacement_text + '\n\n---\n\n' + content[end_idx:]
    with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'w') as f:
        f.write(new_content)
    print("SUCCESS: Updated artifact markdown with fully calibrated pedigree rankings!")
else:
    print(f"FAILED: Bounds not found ({start_idx}, {end_idx})")

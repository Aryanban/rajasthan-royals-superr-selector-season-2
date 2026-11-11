import re

with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'r') as f:
    content = f.read()

replacement_text = """### The Dual-Tier Analytical Framework:
1. **Official Unstop Dropdown Top 10 (Proven Durability, High-Volume Recency & In-Season Multipliers):** To eliminate competition inflation, small-sample anomalies, and reward seasoned workhorses who repeatedly execute under fire, our engine implements:
   * **90% Discount on Non-IPL Competitions** (CPL, BBL, PSL, Bilaterals = 0.10 weight vs IPL = 1.00).
   * **Steep Exponential Recency Decay** (Half-life = 1.0 season: 2026 = 1.00, 2025 = 0.50, 2024 = 0.25, 2023 = 0.125).
   * **Robust Sample Confidence Thresholds** ($N^* = 180$ effective balls baseline) to filter small-sample scout flukes.
   * **Proven Clutch Durability / Experience Bonus** (Up to $+20\%$ scaling for battle-tested workhorses facing/bowling 180 to 480+ clutch balls, elevating proven masters like **Heinrich Klaasen**, **Sunil Narine**, **Jasprit Bumrah**, and **Bhuvneshwar Kumar**).
   * **2026 In-Season Form & Activity Multiplier** to penalize severe collapses (e.g. **Harshal Patel** conceding 12.56 rpo in 2026 dropping to Rank #66) and inactive players (e.g. **Andre Russell** with 0 balls in 2026 dropping to Rank #70, **Mustafizur Rahman** dropping to Rank #58, **Jake Fraser-McGurk** dropping to Rank #92).
2. **The Rajasthan Royals Mini-Auction Board (Actionable & Targetable):** Because IPL 2027 is a Mini-Auction following the 2025 mega-cycle, core contracted stars are locked. We translate our rankings into realistic acquisition targets who can be acquired via auction or trade to resolve RR's critical squad deficits (death-overs hitting and specialist pace/spin foils).

---

## Official Top 10 Target Boards for Unstop Dropdown Submission

The following ordered lists represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{\\text{eff}}$) | 2026 IPL Balls | Recency Clutch SR | 2026 Clutch SR | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | **Vaibhav Sooryavanshi** | `50284` | Top-Order Accelerator | 325.5 | 269 | **228.6** | **231.2** | **9.86** |
| **2** | **Abhishek Sharma** | `6281` | Top-Order Accelerator | 431.4 | 246 | **197.2** | **207.7** | **9.43** |
| **3** | **Priyansh Arya** | `25669` | Top-Order Accelerator | 296.7 | 157 | **207.4** | **226.8** | **9.15** |
| **4** | **Rajat Patidar** | `5039` | Middle-Order Accelerator | 301.3 | 161 | **184.1** | **208.7** | **7.01** |
| **5** | **Tim David** | `6396` | Death Finisher | 203.0 | 109 | **189.7** | **204.6** | **6.95** |
| **6** | **Josh Inglis** | `4736` | Middle-Order Finisher | 207.2 | 129 | **187.6** | **197.7** | **6.36** |
| **7** | **Heinrich Klaasen** | `4260` | Middle-Order Game Changer | 532.8 | 354 | **171.1** | **163.3** | **6.19** |
| **8** | **Ishan Kishan** | `4117` | Top-Order Accelerator | 526.6 | 311 | **170.1** | **181.4** | **6.11** |
| **9** | **Marcus Stoinis** | `2639` | High-Impact Pace All-Rounder | 180.3 | 58 | **179.4** | **208.6** | **6.10** |
| **10** | **Prabhsimran Singh** | `7216` | Top-Order Accelerator | 488.6 | 247 | **169.5** | **177.3** | **6.05** |

*(Audit note: **Heinrich Klaasen** enters at **Rank #7** with 532.8 proven clutch balls; single-season low-volume bats like Finn Allen (114 balls) and Ashutosh Sharma (131 balls) drop to #22-#23; **Andre Russell** drops to **Rank #70 (Score: 1.63)** due to 0 balls in IPL 2026; **Jake Fraser-McGurk** drops to **Rank #92 (Score: 0.81)**; **Suryakumar Yadav** sits at **Rank #31 (Score: 3.96)**).*

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{\\text{eff}}$) | 2026 IPL Balls | Recency Clutch Econ | 2026 Clutch Econ | Dot Ball % | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Sunil Narine** | `781` | Middle-Phase Hunter | 418.8 | 243 | **7.27** | **6.91** | **37.6%** | **10.23** |
| **2** | **Jasprit Bumrah** | `2933` | Death Executioner | 384.2 | 221 | **8.02** | **8.71** | **36.0%** | **7.76** |
| **3** | **Bhuvneshwar Kumar** | `360` | Powerplay Containment | 455.2 | 232 | **8.51** | **7.76** | **36.1%** | **7.70** |
| **4** | **Mohammed Siraj** | `5944` | Powerplay Containment | 535.2 | 293 | **9.18** | **8.97** | **41.5%** | **6.65** |
| **5** | **Varun Chakravarthy** | `6256` | Middle-Phase Hunter | 389.2 | 185 | **8.49** | **8.53** | **35.1%** | **6.24** |
| **6** | **Jason Holder** | `2633` | Death Executioner | 191.5 | 139 | **8.32** | **7.99** | **33.6%** | **6.05** |
| **7** | **Lungi Ngidi** | `4641` | Death Executioner | 238.6 | 208 | **8.56** | **8.37** | **36.1%** | **5.92** |
| **8** | **Khaleel Ahmed** | `4816` | Powerplay Containment | 259.8 | 67 | **9.42** | **8.78** | **41.5%** | **5.61** |
| **9** | **Kagiso Rabada** | `3628` | Death Executioner | 428.4 | 298 | **9.74** | **9.48** | **39.2%** | **5.41** |
| **10** | **Mohsin Khan** | `6669` | Death Executioner | 205.6 | 139 | **8.98** | **8.68** | **37.8%** | **5.36** |

*(Audit note: High-volume proven workhorse **Kagiso Rabada** (428.4 balls) enters at **Rank #9**; small-sample bowler **Saurabh Dubey** drops to **Rank #42 (Score: 2.33)** on 63 balls; **Mustafizur Rahman** drops to **Rank #58 (Score: 1.80)**; **Harshal Patel** drops to **Rank #66 (Score: 1.38)** after conceding 12.56 rpo in 2026; **Mark Wood** drops to **Rank #172 (Score: 0.18)**).*

---

### 3. Absolute Unified Top 10 Clutch Players Across the Entire Tournament
| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{\\text{eff}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Sunil Narine** | `781` | Bowler | 418.8 | 243 | **7.27 Clutch Econ** (6.91 in 2026) | **10.23** |
| **2** | **Vaibhav Sooryavanshi** | `50284` | Batter | 325.5 | 269 | **228.6 Clutch SR** (231.2 in 2026) | **9.86** |
| **3** | **Abhishek Sharma** | `6281` | Batter | 431.4 | 246 | **197.2 Clutch SR** (207.7 in 2026) | **9.43** |
| **4** | **Priyansh Arya** | `25669` | Batter | 296.7 | 157 | **207.4 Clutch SR** (226.8 in 2026) | **9.15** |
| **5** | **Jasprit Bumrah** | `2933` | Bowler | 384.2 | 221 | **8.02 Clutch Econ** (57 career wkts) | **7.76** |
| **6** | **Bhuvneshwar Kumar** | `360` | Bowler | 455.2 | 232 | **8.51 Clutch Econ** (7.76 in 2026) | **7.70** |
| **7** | **Rajat Patidar** | `5039` | Batter | 301.3 | 161 | **184.1 Clutch SR** (208.7 in 2026) | **7.01** |
| **8** | **Tim David** | `6396` | Batter | 203.0 | 109 | **189.7 Clutch SR** (204.6 in 2026) | **6.95** |
| **9** | **Mohammed Siraj** | `5944` | Bowler | 535.2 | 293 | **9.18 Clutch Econ** (41.5% dot balls) | **6.65** |
| **10** | **Josh Inglis** | `4736` | Batter | 207.2 | 129 | **187.6 Clutch SR** (197.7 in 2026) | **6.36** |"""

target_start = '### The Dual-Tier Analytical Framework:'
target_end = '## 1. Defining "Pressure": The Mathematical & Situational Engine'

start_idx = content.find(target_start)
end_idx = content.find(target_end)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + replacement_text + '\n\n---\n\n' + content[end_idx:]
    with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'w') as f:
        f.write(new_content)
    print("SUCCESS: Updated artifact markdown with proven durability rankings!")
else:
    print(f"FAILED: Bounds not found ({start_idx}, {end_idx})")

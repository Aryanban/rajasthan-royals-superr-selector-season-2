import pandas as pd
import numpy as np

# Load parquets
bat = pd.read_parquet("data/player_clutch_batting.parquet").sort_values(by="composite_score_a", ascending=False).reset_index(drop=True)
bowl = pd.read_parquet("data/player_clutch_bowling.parquet").sort_values(by="composite_score_a", ascending=False).reset_index(drop=True)

bat_top10 = bat.head(10).copy()
bowl_top10 = bowl.head(10).copy()

# Generate Batters Markdown Table
bat_rows = []
for i, r in bat_top10.iterrows():
    row_str = f"| **{i+1}** | **{r['striker_name']}** | `{int(r['striker_id'])}` | {r['archetype']} | {r['eff_balls']:.1f} | {int(r['b26_balls'])} | **{r['rec_clutch_sr']:.1f}** | **{r['rec_clutch_avg']:.1f}** | **{r['b26_sr']:.1f}** | {int(r['ipl_seasons'])} | **{r['composite_score_a']:.2f}** |"
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

print("Generated Batters Table:")
print(bat_table)
print("\nGenerated Bowlers Table:")
print(bowl_table)
print("\nGenerated Combined Table:")
print(comb_table)

# Replacement section for Methodology Report
report_section = f"""### The Dual-Tier Analytical Framework:
1. **Official Unstop Dropdown Top 10 (Multi-Season Pedigree, Wicket Attribution & Campaign Regularity):** To eliminate competition inflation, cameo flukes, single-season hiatus anomalies, and reward seasoned IPL workhorses who repeatedly execute under fire, our engine implements:
   * **Wicket Preservation in Batting:** Incorporates Clutch Batting Average ($Avg_{{\\text{{clutch}}}} = \\frac{{\\text{{Runs}}}}{{\\text{{Dismissals}}}}$) to penalize reckless slogging and reward resilient finishers (**Heinrich Klaasen** #3 at 46.6 avg, **Shreyas Iyer** #6 at 59.2 avg, **KL Rahul** #9 at 50.3 avg).
   * **Wicket-Taking Threat in Bowling:** Incorporates Bowling Strike Rate ($SR_{{\\text{{bowl}}}} = \\frac{{\\text{{Balls}}}}{{\\text{{Wicket}}}}$) and Bowling Average to ensure defensive containment alone is not over-rewarded, promoting lethal strike bowlers (**Bhuvneshwar Kumar** #2 at 17.0 balls/wkt, **Varun Chakravarthy** #3 at 20.5 balls/wkt, **Kagiso Rabada** #5 at 16.6 balls/wkt, **Mohsin Khan** #8 at 17.0 balls/wkt).
   * **90% Discount on Non-IPL Competitions** (CPL, BBL, PSL, Bilaterals = 0.10 weight vs IPL = 1.00).
   * **Steep Exponential Recency Decay** (Half-life = 1.0 season: 2026 = 1.00, 2025 = 0.50, 2024 = 0.25, 2023 = 0.125).
   * **Robust Sample Confidence Thresholds** ($N^* = 180$ effective balls baseline) to filter small-sample scout flukes (e.g. **Saurabh Dubey** #58).
   * **Campaign Regular Factor ($R_{{2026}}$):** Requires at least 140 clutch balls in 2026 for bowlers and 120 for batters, eliminating 5-match backups (e.g. **Josh Inglis** dropping to #14) and 58-ball cameo hitters (e.g. **Marcus Stoinis** dropping to #28).
   * **Multi-Season Continuity Penalty:** Penalizes players who missed the preceding consecutive seasons (e.g. **Jason Holder** with 0 IPL balls across 2024 and 2025 receiving a $0.80\\times$ discontinuity penalty and dropping to Rank #13).
   * **Multi-Season Pedigree Bonus:** Awards up to $+15\\%$ scaling for sustained execution across 3 to 5 IPL seasons, elevating proven multi-year match-winners (**Sunil Narine**, **Bhuvneshwar Kumar**, **Heinrich Klaasen**, **Jasprit Bumrah**, **Mohammed Siraj**, **Kagiso Rabada**, **Shreyas Iyer**, **KL Rahul**).
2. **The Rajasthan Royals Mini-Auction Board (Actionable & Targetable):** Because IPL 2027 is a Mini-Auction following the 2025 mega-cycle, core contracted stars are locked. We translate our rankings into realistic acquisition targets who can be acquired via auction or trade to resolve RR's critical squad deficits.

---

## Official Top 10 Target Boards for Unstop Dropdown Submission

The following ordered lists represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch SR | Recency Clutch Avg | 2026 Clutch SR | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bat_table}

*(Audit note: **Ryan Rickelton** drops to **Rank #13**; **Josh Inglis** drops to **Rank #14**; **Marcus Stoinis** drops to **Rank #28**; **Andre Russell** sits at **Rank #70**; **Suryakumar Yadav** sits at **Rank #31**).*

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)
| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch Econ | Clutch Strike Rate (Balls/Wkt) | Clutch Bowling Avg | 2026 Clutch Econ | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bowl_table}

*(Audit note: **Jason Holder** drops to **Rank #13 (Score: 5.36)** due to a 2-year hiatus in 2024-2025 and lack of wicket volume; **Jofra Archer** sits at **Rank #12 (Score: 5.56)**; **Krunal Pandya** sits at **Rank #11 (Score: 5.57)**; **Saurabh Dubey** drops to **Rank #58**; **Harshal Patel** sits at **Rank #68**).*

---

### 3. Absolute Unified Top 10 Clutch Players Across the Entire Tournament
| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
{comb_table}"""

# Update artifact
with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'r') as f:
    content = f.read()

target_start = '### The Dual-Tier Analytical Framework:'
target_end = '## 1. Defining "Pressure": The Mathematical & Situational Engine'

start_idx = content.find(target_start)
end_idx = content.find(target_end)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + report_section + '\n\n---\n\n' + content[end_idx:]
    with open('/Users/aryanbansal/.gemini/antigravity/brain/d040610f-e02f-41b3-84a7-460159ecd824/rajasthan_royals_ipl2027_methodology_report.md', 'w') as f:
        f.write(new_content)
    with open('METHODOLOGY_REPORT.md', 'w') as f:
        f.write(new_content)
    print("SUCCESS: Updated both artifact and repo METHODOLOGY_REPORT.md!")
else:
    print(f"FAILED: Bounds not found ({start_idx}, {end_idx})")

# Update README.md
with open('README.md', 'r') as f:
    readme_content = f.read()

readme_target_start = '## 🏆 Official Top 10 Submissions (Unstop Dropdowns)'
readme_target_end = '## 🎯 Rajasthan Royals Mini-Auction Board (IPL 2027 Actionable Targets)'

r_start = readme_content.find(readme_target_start)
r_end = readme_content.find(readme_target_end)

readme_replacement = f"""## 🏆 Official Top 10 Submissions (Unstop Dropdowns)

The following ordered selections represent the mathematically verified Top 10 batters and bowlers under pressure from the dataset of 1,082 players:

### 1. Top 10 Batters Under Pressure (Dropdown Selections)

| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch SR | Recency Clutch Avg | 2026 Clutch SR | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bat_table}

*Audited Outliers:* **Ryan Rickelton** drops to **Rank #13**; **Josh Inglis** drops to **Rank #14**; **Marcus Stoinis** drops to **Rank #28**; **Andre Russell** sits at **Rank #70**; **Suryakumar Yadav** sits at **Rank #31**.

---

### 2. Top 10 Bowlers Under Pressure (Dropdown Selections)

| Rank | Player Name | Player ID | Tactical Archetype | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Recency Clutch Econ | Clutch Strike Rate (Balls/Wkt) | Clutch Bowling Avg | 2026 Clutch Econ | IPL Seasons | Composite Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
{bowl_table}

*Audited Outliers:* **Jason Holder** drops to **Rank #13 (Score: 5.36)** due to a 2-year hiatus (0 balls in 2024 and 2025) and lower wicket conversion; **Jofra Archer** sits at **Rank #12 (Score: 5.56)**; **Krunal Pandya** sits at **Rank #11 (Score: 5.57)**; **Saurabh Dubey** drops to **Rank #58**; **Harshal Patel** sits at **Rank #68**.

---

### 3. Absolute Unified Top 10 Across Both Disciplines

| Overall Rank | Player Name | Player ID | Primary Discipline | Effective Recency Balls ($N_{{\\text{{eff}}}}$) | 2026 IPL Balls | Key Clutch Metric | Composite Clutch Score |
| :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
{comb_table}

---

"""

if r_start != -1 and r_end != -1:
    new_readme = readme_content[:r_start] + readme_replacement + readme_content[r_end:]
    with open('README.md', 'w') as f:
        f.write(new_readme)
    print("SUCCESS: Updated README.md!")
else:
    print(f"FAILED README: Bounds not found ({r_start}, {r_end})")

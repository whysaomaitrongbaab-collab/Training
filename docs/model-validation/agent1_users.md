# Agent 1 — User/Customer Number Validity Audit
Model: Constistant_Financial_Model.xlsx · Lens: customer-count chain → revenue/cost impact
Sources checked: model_dump.txt (full), researchA.md, researchE.md (exists, not fully re-read), 2026-09-02-market-sizing-assumptions-summary.md (found at `C:\Users\taddy\OneDrive\work\Stecon\constistant\Constistant\docs\research\market\`)

## (a) VERDICT: **NOT DEFENSIBLE for investor use in its current Base/Best form** — the arithmetic is internally correct and churn IS applied, but the Base-case customer count is 99.5% driven by a single admitted goal-seeked guess (self-serve leads), the Best case exceeds the model's own market ceiling in Year 1, and the "active scenario" wired into the Business Model / Profit sheets is **Best, not Base**. Fixable: the GTM-bottom-up structure is good; replace 3 inputs and re-anchor the base case (the current *Worst* case is roughly what a defensible Base looks like).

---

## (b) Numbered findings

### 1. CRITICAL — Base Year-1 customer count is 99.5% a goal-seeked guess
- Cells: `Assumptions!C140` (3,000 self-serve leads/mo), `Assumptions!C141` (3%), `GTM — Bottom-Up!C38` (=3000×12×0.03 = 1,080), `GTM — Bottom-Up!B19` (=1×8×12×0.06 + 1,080 = 1,085.76 → 1,086).
- Sales Channel 1 contributes **5.76 customers** in Base Year 1; self-serve contributes **1,080**. The note on `Assumptions!E140` and `Investor Dashboard!A34` openly says the 3,000 leads/mo was "กำหนดเป้าเพื่อให้ Base Year1 > 1,000 ราย" (set to force Year 1 > 1,000). The research summary (§5, quoted in `Assumptions!A95`) explicitly forbids inventing conversion/churn/lead numbers without pilot data.
- Fix: never present 1,086 as "bottom-up". Replace C140 with a ramped, budget-linked figure (see §c) or present it as an upside scenario contingent on a funded marketing pilot with stated CPL.

### 2. CRITICAL — Lead volume exceeds the entire addressable universe
- Cells: `Assumptions!C140` vs `Market — TopDown!B9` (reachable pool Y1-3 = **4,797 firms**) and `Market — TopDown!B8` (nationwide digital-ready = **15,989 firms**).
- Base requires 3,000×12 = **36,000 leads/yr = 7.5× the whole regional reachable universe** in Year 1 (Best: 96,000/yr = 20×). Even nationwide, 36,000 > 2.25× the digital-ready population. Any investor who divides two cells sees this immediately.
- Fix: cap annual leads at a fraction of the pool (e.g. ≤25%/yr of 4,797 ≈ 100/mo regional; more only with nationwide scope and evidence).

### 3. CRITICAL — Best case breaches the SOM ceiling every single year
- Cells: `GTM — Bottom-Up!B32/C32/D32` (5,789 / 11,143 / 16,098) vs `Market — TopDown!B9` (4,797) and `B8` (15,989); `Market — TopDown!D26` (Y4 = 32,196), `Cost Structure!F8` (Y5 = 64,392).
- Y1 Best = **120.7% of the regional reachable pool**; Y3 Best = **100.7% of the entire nationwide digital-ready pool**; Y5 Best = 64,392 = **4× the digital-ready pool and 80.5% of all 80,000 registered contractors** (digital-ready or not). The GTM funnel has no MIN(…, pool) cap anywhere.
- Fix: add `=MIN(calc, 'Market — TopDown'!$B$9)` (Y1-3) / `$B$23` (Y4-5) to `GTM — Bottom-Up!B12/B22/B32` etc., or delete the Best column from investor-facing tabs.

### 4. CRITICAL — Investor-facing "active scenario" is Best, not Base
- Cells: `Assumptions!B16` = 'Best' (label claims it is retired, "ไม่ขับเคลื่อนสูตรไหนแล้ว" — false), but `Business Model — Revenue!B5:D5` still IF() on it and show 5,789/11,143/16,098; `Business Model — Profit!B5:D8` therefore shows Y3 revenue ฿1,265M at 97.6% margin as "Scenario ที่ใช้งานอยู่ … ดึงเลขนี้ไปใช้ในสไลด์ Financial ได้เลย"; `Cost — Sustainability!B5:D5` and `Win-Win Summary!B14:D15` (Y3 = 16,098 customers, ฿1,265M) inherit the same.
- Presenting these sheets pitches an impossible Best case as the plan.
- Fix: set B16='Base' (or hard-wire Business Model sheets to the Base column) and re-check every downstream cached value.

### 5. HIGH — Churn: applied, but the level (15% annual Base) is far below SMB-SaaS reality and contradicts the model's own warnings
- Cells: `Assumptions!B126:D126` (25/15/8% **annual**); applied at `GTM — Bottom-Up!C10/C20/C30` (=prior cumulative × (1−churn)); no in-year churn on new cohorts.
- Verification: churn IS wired in and arithmetic checks (e.g. Base Y2 = 1086×0.85 + 1,091.52 = 2,014.6 → 2,015 ✓; Y3 = 2015×0.85 + 1,097.28 = 2,810 ✓).
- Plausibility: self-serve micro-SMB SaaS typically churns **3-7%/month (≈30-58%/yr)**; 15%/yr is enterprise-grade retention. The model itself flags Small ROI ≈ 1.00x (`Pricing Strategy!A18`, `Investor Dashboard!A30`) and Small = **90% of the Year-1 mix** (`Assumptions!B133`), and BUILK's churn is described as "steep" (`Assumptions!A93`). 8% (Best) is not credible for this segment at all.
- Fix: Base 30-40%/yr while Small-heavy, improving with mix shift; Worst 50%; Best 20%. Also apply ~half-year churn to in-year adds.

### 6. HIGH — CAC is charged on *net* adds, not gross new customers, and no marketing budget backs the lead guess
- Cells: `Cost Structure!C21` `=$B$16+(C7-B7)*Assumptions!$B$68` — charges CAC on 929 net adds in Y2 while the funnel acquires 1,091.5 gross new (churn replacement is free). Understates Base cost ~฿0.49M (Y2) / ~฿0.9M (Y3); the distortion grows with churn.
- Consistency: ฿3,000 CAC × 1,080 self-serve customers = ฿3.24M/yr ⇒ implied **฿90/lead** at 3% conversion. Thai B2B construction-niche paid CPL is realistically ฿300-1,000+, so either leads or CAC is off 3-10×. Nothing in `Cost Structure` or `Business Model — Cost` contains a marketing-spend line generating 36,000 leads/yr.
- Fix: CAC × gross new (`new/yr` row B19/C19/D19 of GTM sheet), and model marketing spend = leads × CPL as its own line; back-solve which lead volume the budget actually buys.

### 7. HIGH — Year-4/5 "×2 per year" is circular and pushes Base to near-monopoly of the segment
- Cells: `Assumptions!B117` = 2.0, justified in `E117` by "Market—TopDown!B34/D26 = 6361/3181 ≈ 2.0×" — but B34/D26 are themselves the **goal-seeked** ฿600M/฿300M targets (600/300 = 2 by construction). The growth rate is laundered goal-seek arithmetic, then applied to *all* scenarios.
- Result: Base Y5 = 11,240 (`Cost Structure!F7`) = **70.3% of the nationwide digital-ready pool** — a near-monopoly presented as base case; and the GTM engine (reps, leads) that produced Y1-3 cannot mechanically produce a doubling (Y3 Base engine adds only ~1,100/yr gross).
- Fix: extend the actual GTM engine into Y4-5 (reps ramp + self-serve ramp − churn), cap at ≤30% of the relevant pool; treat ×2 as Best-only.

### 8. HIGH — Explicit goal-seek cells for ฿300M/600M/1,200M remain in the model
- Cells: `Assumptions!B77` `=300000000/('Market — TopDown'!$B$23*'Client — Summary'!$E$17)` → 19.9% capture; `B82` (600M → 39.8%); `B83` (1,200M → **79.6% of the digital-ready pool ≈ "เกือบ monopoly"**, per its own note). All flagged 🔴 in-model, and `Business Model — Revenue!B22-B29` still builds Y5/Y6 revenue from them (599,969,520 ≈ target −30,480 — reverse-engineered to the baht).
- Fix: delete or quarantine to a clearly-labelled "aspirational" tab; never let them feed Business Model rows that slides read.

### 9. MEDIUM — Broken cells in Business Model sheets corrupt cost/profit
- `Business Model — Revenue!E5` `='Market — TopDown'!B29` → **0** (empty cell), making `E6` = −16,098 "new customers".
- `Business Model — Cost!B19` (Y5 CAC) `=('Business Model — Revenue'!B22−'Market — TopDown'!D26)×3000` = (6,361−32,196)×3,000 = **−฿77.5M**, driving Y5 total cost **negative** (`B20` = −65.3M) and Y5 margin **110.9%** (`Business Model — Profit!B31`). Mixes the goal-seek customer track (6,361) with the GTM ×2 track (32,196) — two inconsistent Y4-5 customer series coexist in the workbook.
- Fix: pick one Y4-5 customer series; repair E5/B19; a margin >100% in any printed sheet is an instant credibility kill.

### 10. MEDIUM — Self-serve channel is flat (no ramp) and identical for 3 years
- Cells: `GTM — Bottom-Up!B9/C9/D9,B19…` all add the same `$B$38/$C$38/$D$38` — 3,000 leads/mo from month 1 of Year 1, no ramp-up, no growth to Y3. Real funnels start near zero. This inflates Y1 most (exactly the number the founder is worried about) and understates Y3 relative to Y1.
- Fix: per-year lead ramp (see §c).

### 11. LOW — Driver plausibility of Channel 1 (the defensible part)
- `Assumptions!B121:D125`: 1-6 reps, 5/8/12 leads/rep/mo, 3/6/10% lead→close. These are actually *conservative-to-normal* for high-touch SMB SaaS (typical outbound SDR: 10-30 qualified leads/mo; lead→close 5-10%). BUILK precedent justifies the low close rate. Keep; consider 5% Base close given trust barrier. Note this channel yields only ~6-17 customers/yr — the honest scale of the business in Y1.

### 12. LOW — LTV:CAC 78.6x internally inconsistent
- `5-Year Projection!B26` uses fixed 3-yr lifetime with CAC ฿3,000, while churn 15% implies 6.7-yr lifetime and 25% implies 4-yr. Already flagged on the dashboard; recompute lifetime = 1/churn from the chosen churn set and use realistic blended CAC → expect LTV:CAC ~3-8x, which is the *believable* range investors want.

### 13. Source spot-check (positive finding)
- `Assumptions!B11` (80,000 contractors), `B12` (99.93% SME), `B13` (20% digital-ready) all match the found sources verbatim (market-sizing-assumptions-summary.md §1; researchA.md TCA 2023 20/60/20 survey). The market-funnel inputs are genuinely sourced. But the same summary (§5) states churn/conversion/SOM for Thai ConTech are **UNVERIFIED — "must be sensitivity-tested assumptions, not sourced facts"** — the model violates this in its headline Base numbers.

---

## Sensitivity quantification (Task 3)

| Lever moved to conservative | Y1 / Y2 / Y3 customers (Base engine) | vs model Base 1,086/2,015/2,810 |
|---|---|---|
| Model Base (as-is) | 1,086 / 2,015 / 2,810 | — |
| Self-serve leads 3,000→1,000/mo only | 366 / 683 / 957 | **−66% every year** |
| Conversion 3%→1% only | 366 / 683 / 957 | −66% (symmetric with leads) |
| Churn 15%→30% only | 1,086 / 1,852 / 2,393 | 0 / −8% / −15% |
| All three (500-1,000-2,000 leads ramp, 2% conv, 30% churn, close 5%) | **~125 / ~337 / ~730** | −88% / −83% / −74% |

Revenue impact (× blended ARPU `Client — Summary!B69:D69` = 40,692 / 50,910 / 78,600): conservative case Y1 ≈ ฿5.1M (vs ฿44.2M), Y3 ≈ ฿57M (vs ฿220.9M). Cost impact is smaller in absolute terms (AI COGS and CAC scale down with customers; fixed ฿3.1M team cost dominates), so the published 81-91% net margins collapse to roughly **30-45%** in Y1-2 — i.e. the founder's instinct is right: user count is the single dominant driver of both revenue and margin optics. Note the model's own **Worst** case (122/213/282) almost equals this conservative Base — strong evidence Worst should be renamed Base.

Self-serve leads is the highest-impact single assumption in the entire workbook: ±1 unit of leads/mo moves Y1 revenue by ~฿14,650 (12 × 3% × ฿40,692).

## SOM ceiling check per year (Task 4)
Pool: regional Y1-3 = 4,797 (`Market — TopDown!B9`); nationwide digital-ready Y4-5 = 15,989 (`B8`/`B23`).

| Year | Worst | Base | Best |
|---|---|---|---|
| Y1 | 122 (2.5%) OK | 1,086 (**22.6%** of pool in yr 1 — implausible) | 5,789 (**120.7% — impossible**) |
| Y2 | 213 (4.4%) OK | 2,015 (42.0%) implausible | 11,143 (232% — impossible) |
| Y3 | 282 (5.9%) OK | 2,810 (**58.6%** of regional pool) implausible | 16,098 (**100.7% of nationwide pool — impossible**) |
| Y4 | 564 (3.5% ntl) OK | 5,620 (35.2% ntl) aggressive | 32,196 (201% — impossible) |
| Y5 | 1,128 (7.1%) OK | 11,240 (**70.3% ntl**) not defensible | 64,392 (403%; 80.5% of ALL 80k firms) |

Only the Worst column stays inside the ceiling in all years. Base breaches plausibility (not the raw cap) from Y1; Best breaches the hard mathematical cap from Y1.

---

## (c) Recommended defensible base-case user-number set

| Driver | Cell | Current Base | Recommended | Rationale |
|---|---|---|---|---|
| Sales reps Y1/2/3 | Assumptions!C121:C123 | 1/2/3 | keep 1/2/3 | funded hiring plan, fine |
| Leads/rep/mo | C124 | 8 | keep 8 | conservative for SDR norms |
| Close rate | C125 | 6% | 5% | BUILK trust-barrier; still in SaaS 5-10% norm |
| Self-serve leads/mo | C140 | 3,000 flat | **ramp 250 / 750 / 1,500** (Y1/Y2/Y3) | ≤ ~25-35%/yr of the 4,797-firm reachable pool; must be tied to an explicit marketing budget line (leads × CPL ฿400-600) and validated by a pilot campaign before the pitch |
| Self-serve conversion | C141 | 3% | 2% (raise only with pilot data) | SME-Thai self-serve unfamiliarity, model's own note |
| Churn | C126 | 15%/yr | **30%/yr** Y1-2 → 20% Y3+ (mix shifts off Small) | SMB-SaaS norm 30-58%/yr; Small ROI ≈ 1.0x; BUILK "steep" precedent; also churn half the in-year cohort |
| Y4-5 growth | B117 | ×2.0 all scenarios | extend GTM engine (~×1.5-1.7), cap cumulative at 30% of digital-ready pool | ×2 is laundered from the ฿300M→600M goal-seek |
| Active scenario | B16 | 'Best' | 'Base' | Business Model/Profit/Win-Win sheets still read it |

**Resulting defensible Base:** Y1 ≈ **65-125** customers, Y2 ≈ **250-350**, Y3 ≈ **550-750**, Y4 ≈ 900-1,200, Y5 ≈ 1,400-2,000 (max 12.5% of nationwide digital-ready pool — leaves room for an upside story). Revenue: Y1 ~฿3-5M, Y3 ~฿45-60M, Y5 ~฿120-175M. Smaller, but every number survives the two questions an investor will ask first: "where do 3,000 leads/month come from on day one?" and "your Year-3 Best case is bigger than your own market — which one is wrong?" Present today's Base (1,086/2,810) as the *upside* scenario conditional on a validated ฿15-20M/yr marketing engine, and delete or cap the current Best column.

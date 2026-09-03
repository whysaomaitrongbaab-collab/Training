# Agent 3 — Formula Integrity & Internal Consistency Audit
Constistant_Financial_Model.xlsx · audited 2026-09-03 · 751 formula cells traced, key chains recomputed independently in Python.

## (a) Verdict: **UNSOUND** (as a coherent whole)

The **5-Year Projection chain** (GTM — Bottom-Up → Market — TopDown → Cost Structure → 5-Year Projection → Investor Dashboard) is arithmetically correct: every cached value I recomputed matched exactly (customers, ARR ฿44.19M→฿991.37M, margins 81.3–91.4%). The file is not stale.

But the workbook contains a **second, contradictory P&L** (Business Model — Revenue/Cost/Profit) that is still driven by the "retired" scenario dropdown, is silently locked to **Best case**, references an empty cell, and produces a **negative annual cost of −฿65.3M and a 110.9% margin**. Anyone pulling numbers from those sheets (which the sheet itself invites: "ดึงเลขนี้ไปใช้ในสไลด์ Financial ได้เลย") gets numbers 5.7× larger than the Base case shown on the Investor Dashboard. Several blended metrics (ROI 2.65x, LTV:CAC 78.6x) are also mathematically mis-constructed or built on mix assumptions that contradict the year-phased mix used for revenue.

---

## (b) Findings

### CRITICAL

**C1. "Retired" dropdown Assumptions!B16 still drives the entire 3-year P&L — and it is set to "Best".**
- Assumptions!A16/E16 claim the dropdown "ไม่ขับเคลื่อนสูตรไหนแล้ว" (drives no formula). False. `'Business Model — Revenue'!B5:D5` and `B17` are `=IF(Assumptions!$B$16="Worst",…,IF(…="Best",…))`, and B16 = **"Best"**.
- Consequence: Business Model — Revenue/Profit, Cost — Sustainability (B5:D5), and Win-Win Summary (B14:D14 via BM—Revenue!D5) all silently report **Best case**: Y1 revenue ฿235.57M, Y3 ฿1,265.3M, margin 89.5–97.6% — while the Investor Dashboard and 5-Year Projection headline Base (Y1 ฿44.19M, margin 81.3%).
- Fix: either delete the dropdown and hardwire these sheets to Base (`'Market — TopDown'!C13:C15`), or restore the dropdown as live and label the sheets with the active scenario. At minimum set B16="Base" before any presentation.

**C2. Business Model — Revenue!E5 references an empty cell → Year-4 row is garbage.**
- `E5 ='Market — TopDown'!B29` → B29 is **empty** → 0 customers. `E6 =E5-D5` → **−16,098** "new customers"; `E8 = 0` Year-4 revenue. Year-4 customers actually live at Market — TopDown!B26/C26/D26. This is a stale pointer left from a deleted layout.
- Fix: `E5` should reference the appropriate scenario cell in B26:D26 (row moved during the Y4-rework); or delete columns E of rows 5–8 since rows 15–18 already handle Y4.

**C3. Business Model — Cost!B19 Year-5 CAC is −฿77,505,000 (negative cost) → total Y5 cost −฿65.3M → Profit sheet shows margin 110.9% (>100%).**
- `B19 =('Business Model — Revenue'!B22 - 'Market — TopDown'!D26)*Assumptions!$B$68` = (6,361 − 32,196)×3,000. It subtracts customers from **two incompatible Best-case tracks**: B22 = back-solved-from-฿600M-target track (Market—TopDown!B34 = 6,361) minus D26 = GTM-engine track (32,196).
- Downstream: `B20 = SUM(B15:B19)` = **−65,318,250**; 'Business Model — Profit'!B29:B31 → Y5 profit ฿665.3M on revenue ฿600.0M, margin **1.1089**. A margin above 100% is an impossible figure sitting in a pitch-ready sheet.
- Fix: pick one Y5 customer basis. If using the ฿600M-target track, prior-year customers are B33 (3,181): CAC = (6,361−3,181)×3,000 = ฿9.54M, total Y5 cost ≈ ฿21.73M, margin ≈ 96.4%.

**C4. Two P&Ls disagree on every overlapping year — same company, same file.**
| Year | 5-Year Projection (Base) | Business Model — Profit ("active scenario") |
|---|---|---|
| Y1 revenue | ฿44,191,512 | ฿235,565,988 |
| Y3 revenue | ฿220,866,000 | ฿1,265,302,800 |
| Y3 cost | ฿18,969,000 | ฿30,034,500 |
| Y3 margin | 91.4% | 97.6% |
- Even holding scenario constant (Best), the cost models differ (see H2/H3): 5-Year Y3 Best cost ฿95.23M vs Business Model ฿30.03M — a 3.2× gap for identical customers.
- Fix: retire the Business Model trio or rebuild it as a strict view over Cost Structure / 5-Year Projection.

### HIGH

**H1. Blended ROI 2.65x (Client — Summary!E9, echoed on Dashboard B7:E7) is a weighted average of ratios — mathematically wrong construction.**
- `E9 =B9*0.6+C9*0.25+D9*0.15` = 2.6516. The correct blended ROI = blended value ÷ blended price = E7/E8 = 255,242.89/78,600 = **3.247x**. Averaging ratios weights by customer count, not by baht; the two only coincide when all prices are equal.
- Fix: `E9 =E7/E8`. (Understates here, but it's still the wrong operator.)

**H2. Business Model — Cost!B8:E8 AI cost uses a hardcoded Small-only workload for every customer — 6.4× below the model's own COGS engine.**
- `B8 =customers × Assumptions!B67(50 pages) × B66(฿15)` — ignores Medium (250 pages, B98), Large (666.7 pages, B99) and projects/year (B43/B48/B53). Per-customer/yr it charges ฿750 vs the AI Infra — Unit Cost figures ฿1,125/฿7,500/฿15,000.
- Y3 (Best, 16,098 cust): BM—Cost D8 = ฿12,073,500 vs Cost Structure!D14 = **฿77,270,400** for the same customers. Same duplication in B18/C18 (Y5/Y6) and in 'Business Model — Profit'!B13:D13.
- Fix: reuse Cost Structure's blended formula `customers × Σ(mix% × 'AI Infra — Unit Cost'!B16:D16)`.

**H3. Year-4/5 team-size assumptions (12/20/35 people, Assumptions!B79/B84/B85) are NOT what the headline projection uses.**
- Cost Structure Y4-5 scales fixed cost by customer ratio: `E21 =$B$16*(E7/D7)+…` → Base Y4 fixed = ฿6.192M ≈ **16 people-equivalent** (vs stated 12); Y5 = ฿12.384M ≈ 32 people (vs stated 20). B79/B84/B85 are only consumed by the Best-case-locked Business Model — Cost (E5/B15/C15). So the "team of 12/20/35" narrative and the P&L cost line are two different models.
- Fix: drive Cost Structure Y4-5 team cost from B79/B84 directly (`Assumptions!$B$79*$B$64*12+…`), or delete B79/B84/B85 and state the ratio-scaling rule as the assumption.

**H4. Year-4/5 revenue mix contradicts Year-4 ARPU-with-upsell; the two revenue sheets use different ARPU for the same year.**
- 5-Year Projection Y4-5 uses `'Client — Summary'!E69/F69` (phased-mix ARPU ฿84,000/฿88,200, **no upsell**), while its own G10 note claims it uses E17. Business Model — Revenue Y4-6 uses `'Client — Summary'!E17` = ฿94,320 (static 60/25/15 mix × 1.2 upsell, Assumptions!B78).
- Y4 Best revenue: 32,196×84,000 = ฿2.704bn (5-Year!E12) vs 32,196×94,320 = ฿3.037bn (BM—Revenue!D18). ฿332M discrepancy from mix/upsell inconsistency. Assumptions!B78 (20% upsell) is effectively dead in the headline projection.
- Fix: define one Y4 ARPU (phased mix ± upsell) and reference it from both; correct the G10 note.

**H5. Static mix 60/25/15 vs phased mix (Assumptions!B133:F135 — Y1 90/10/0 … Y5 45/30/25): both are live, feeding different metrics.**
- Static mix drives: blended price ฿6,550 (Client — Summary!E12, Dashboard B6:E6), blended ROI E9, ARPU ฿78,600 (E8), Y4 ARPU E17, **LTV:CAC 78.6x**, Sustainability blended CO2 (Sustainability Impact!B30), and Best-case capture-rate back-solves (Assumptions!B77/B82/B83 via E17).
- Phased mix drives: revenue (Client — Summary!B68:F69) and AI COGS (Cost Structure rows 12–14).
- The dashboard's "blended 6,550" therefore describes a mix (60/25/15) that the revenue model says will not exist until Year 3. In Y1 the true blended price is ฿3,391/mo. Not double-counted anywhere fatal, but the same label ("blended") means two different portfolios depending on the sheet.
- Fix: label static-mix figures "steady-state (Y3) mix" and compute year-specific versions where investor-facing.

**H6. LTV:CAC = 78.6x (5-Year Projection!B26) is triply inconsistent with the model's own inputs.**
- `=('Client — Summary'!$E$8*3)/Assumptions!$B$68` = 78,600×3/3,000.
  1) Uses steady-state ARPU ฿78,600 though Y1-2 ARPU is ฿40,692–50,910 (launch pricing).
  2) Hardcodes 3-year lifetime while the model's own churn inputs imply 1/0.15 = 6.7 yrs (Base) — the two churn assumptions never reconcile (already flagged in-sheet, but the formula also contradicts B126).
  3) LTV uses revenue, not gross profit (standard LTV uses GM%; even at the model's own 89% GM it would change), and CAC ฿3,000 excludes all sales-rep salary (reps exist in GTM but their cost appears nowhere in any cost sheet).
- Fix: LTV = year-phased ARPU × GM% × (1/churn); CAC = (marketing + sales comp)/gross new customers. Expect the ratio to fall an order of magnitude and still be presentable.

**H7. Net Margin 81–91% is arithmetically correct but the P&L omits entire cost categories — it is not a "Net" margin.**
- What IS included (Cost Structure, Base): AI COGS (phased mix), team 8×฿30k×12 = ฿2.88M flat for Y1-3, hosting ฿96k/yr, overhead ฿120k/yr, CAC ฿3,000×new customers. What is NOT anywhere in the Base P&L: sales-rep compensation (GTM assumes 1-3 reps closing 100% of Channel-1 revenue), the self-serve marketing budget behind 3,000 leads/mo (Assumptions!C140 — CAC ฿3,000/customer × 1,080 self-serve customers = ฿3.24M/yr must cover a paid-ads engine generating 36,000 leads/yr), payroll burden/tax, any tax line, and team growth in Y1-3 (8 people fixed while customers go 1,086→2,810).
- ฿30k/mo average salary for an 8-person AI-SaaS dev+ops team is itself the load-bearing assumption: total fixed cost ฿3.096M/yr against ฿44M Y1 revenue mechanically forces 81%+ margins. The label "Net Margin" (5-Year!A24, Dashboard A14) should be "Operating margin under placeholder costs".
- Fix: rename the line; add sales comp + marketing budget lines tied to GTM headcount/lead targets; sanity-benchmark against 70–80% *gross* margin SaaS norms (the model's own Assumptions!B71 target is 70% GM, i.e. the model outperforms its own sustainability target's *gross* margin at the *net* line — internally incoherent).

### MEDIUM

**M1. Hardcoded numbers inside formulas — the "no numbers embedded outside Assumptions" claim (Assumptions!A2, README!A3) is false.**
- `'Business Model — Revenue'!D19 =300000000-D18`, `B24 =600000000-B23`, `B29 =1200000000-B28` — revenue targets hardcoded, duplicating the same literals inside Assumptions!B77/B82/B83 formulas (4 copies of each target; change one, the others silently diverge).
- `'AI Infra — Unit Cost'!B27 =B26*24*30*35` — FX rate 35 THB/USD and 720 hrs/mo hardcoded (FX documented only in a comment).
- `'5-Year Projection'!B26` — lifetime `*3` hardcoded (see H6).
- `'Sustainability Impact'!B33 =B31/21` — EPA 21 kg/tree hardcoded (documented in E33, but the rule says it belongs in Assumptions).
- Assumptions!B133:F134 phasing percentages (0.9/0.75/0.5/0.45; 0.1/0.2/0.3/0.3) are typed constants — inside Assumptions, so technically compliant, but D133:D135 are formulas referencing B59:B61 while their neighbors are literals: fragile mixed pattern (editing B59 changes only Year 3).
- `'Business Model — Profit'!B13:D13` re-derives Y3 cost with a long inline formula instead of referencing Cost Structure — duplicated logic that has already drifted (see C4/H2).

**M2. CAC is charged on NET adds, not gross adds — churn replacement acquisition is free.**
- Cost Structure `C21 =$B$16+(C7-B7)*B68` charges CAC on 929 net new Base customers in Y2, but GTM says gross new = 1,091.52 (plus 162.9 churned to replace). Understates CAC every year Y2-5; same pattern in Business Model — Cost C9/D9/E9. Fix: `(cumulative_t − cumulative_{t−1}×(1−churn))×CAC` or reference GTM row 19 directly.

**M3. Self-serve customers (Channel 2) are Small-tier by definition but receive the blended Medium/Large mix in revenue and COGS.**
- Assumptions!A138 says Channel 2 is "Small-tier, low-touch"; GTM adds 1,080/yr (Base) into the same pool to which the 60/25/15 (or phased) mix is applied. In Y1, self-serve is 99.5% of all Base customers (1,080 of 1,086) yet 10% of them are priced as ฿7,000/mo Medium. Revenue is overstated whenever mix% × non-self-serve pool < actual Medium/Large count implied. Fix: apply mix only to Channel-1 customers, price Channel-2 at Small launch price.

**M4. Small ROI ≈ 1.0x is computed at the ฿5,000 post-Y3 price while Y1-2 revenue uses the ฿2,990 launch price.**
- Client — Small!B27 = Assumptions!B55 (5,000), never B129 (2,990). At launch price the ROI is 60,119/35,880 = **1.68x** — materially better and never shown; conversely, the flagged 1.0x is the price customers will only face in Y3+. Both the warning (Pricing Strategy!A18, Dashboard A30) and the revenue model are right individually but describe different years. Fix: add a launch-price ROI row (Y1-2) next to B29.

**M5. Win-Win Summary!B18 vs C18 cross-check differs by ฿97,200 (1,265,400,000 vs 1,265,302,800).**
- Cause: B14:D14 round customers per size before multiplying (9,659+4,025+2,415=16,099 ≠ 16,098). The in-sheet note anticipates a "1-2 customer" rounding gap; here it is 1 customer × mix arithmetic = ฿97,200. Acceptable, but the "must be equal" label (D18) is currently false. Also inherits C1 (Best-case lock).

**M6. Dashboard price row (B6:E6 = 5,000/7,000/12,000, blended 6,550) does not reflect launch pricing.**
- Nothing on the Investor Dashboard reveals that Y1-2 Small revenue is booked at ฿2,990. An investor reconciling ARR Y1 (฿44.19M) against 1,086 customers × ฿6,550×12 = ฿85.4M will find a 48% gap with no explanation on the page. Fix: add the phased ARPU row (Client — Summary!B69:F69) to the dashboard.

### LOW

**L1. Orphan value Assumptions!D58 = 0.12** — a bare number sitting in the color/type column under the header row "สัดส่วนลูกค้าแต่ละไซส์". No formula in the workbook references D58. Likely a leftover from an old 12% figure. Delete.

**L2. Documentation/label errors:** 5-Year Projection!G10 claims Y4-5 uses E17 (actually E69/F69 — see H4). Cost Structure!A4 says "Y4-5 จาก nationwide expansion" (actually Y4-5 = Y3×2 growth engine). Dashboard!A26 "(ต้น)" should be "(ตัน)" for tCO2e. Business Model — Revenue!A2 still advertises the dropdown as live.

**L3. Percent-unit cosmetics:** unit column says "%" for values stored as fractions (B12=0.9993, B13=0.2, …). Usage is consistent (no double-division found), so display-only.

**L4. Best-case capture rates knowingly exceed SAM** (Assumptions!B82 = 49.8%, B83 = 99.7% of the digital-ready population) — flagged in-model as 🔴, but these cells still feed Market — TopDown!B33:B35 → Business Model — Revenue/Cost Y5-6 → the sheets in C1/C3. Aspirational cells should be quarantined from any P&L.

**L5. AVERAGE() usage (Assumptions!B43/B48/B53, Market — TopDown!B5/B6) is legitimate** (midpoints of 2-value ranges) — no misuse found there; the weighted-average defect is H1.

**L6. Sustainability math verified:** steel-saved kg → ×1.99 kgCO2e/kg → ×projects → blended (60/25/15) 9,475.78 kg/customer/yr → ×Y3 customers → /1000 t → /21 trees. All arithmetic reproduces exactly (Base 26,626.9 tCO2e; 1,267,950 trees). Caveats: metrics 2-3 are team guesses (flagged in-model), and the blend uses the static mix (H5) — with the Y3 mix identical, no numeric impact at Y3.

**L7. Churn IS applied to revenue** — via the customer count (GTM rows 10/20/30), not as a revenue line. Simplifications: churn skips in-year adds, and every customer books a full year of ARR from day one (no mid-year proration) — overstates Y1 ARR for a base acquired throughout the year (real Y1 recognized revenue would be roughly half of ฿44.19M).

**L8. Staleness check: PASS.** Every recomputed value matched the cached value bit-for-bit (see table). The workbook was saved fully recalculated; the wrong numbers are wrong by construction, not by stale cache.

---

## (c) Independently recomputed metrics vs model

| Metric | Model (cached) | Recomputed | Match |
|---|---|---|---|
| Customers Base Y1/Y2/Y3 | 1,086 / 2,015 / 2,810 | 1,086 / 2,015 / 2,810 | ✔ |
| Customers Worst Y1-3 | 122 / 213 / 282 | 122 / 213 / 282 | ✔ |
| Customers Best Y1-3 | 5,789 / 11,143 / 16,098 | 5,789 / 11,143 / 16,098 | ✔ |
| Customers Base Y4/Y5 | 5,620 / 11,240 | 5,620 / 11,240 | ✔ |
| Blended ARPU/yr Y1…Y5 | 40,692 / 50,910 / 78,600 / 84,000 / 88,200 | identical | ✔ |
| ARR Base Y1 | ฿44,191,512 | ฿44,191,512 | ✔ |
| ARR Base Y5 | ฿991,368,000 | ฿991,368,000 | ✔ |
| Total cost Base Y1…Y5 | 8.268 / 12.117 / 18.969 / 47.288 / 102.374 M฿ | identical | ✔ |
| Net margin Base Y1…Y5 | 81.29 / 88.19 / 91.41 / 89.98 / 89.67 % | identical | ✔ (label misleading — H7) |
| AI COGS per cust/yr S/M/L | 1,125 / 7,500 / 15,000 | identical | ✔ |
| ROI S/M/L | 1.002 / 5.073 / 5.215 | identical | ✔ |
| Blended ROI | **2.652** | **3.247** (blended value ÷ blended price) | ✘ wrong construction (H1) |
| LTV:CAC | 78.6x | 78.6x arithmetic, but construction invalid (H6) | ✘ |
| BM — Cost Y5 CAC | **−฿77,505,000** | should be ≈ +฿9.54M on a consistent track | ✘ (C3) |
| BM — Profit Y5 margin | **110.9%** | ≈96% after C3 fix | ✘ |
| BM — Revenue Y4 (active) | ฿0 (empty-cell ref) | broken | ✘ (C2) |
| Y3 AI cost, Best: BM—Cost vs Cost Structure | 12.07M vs 77.27M | Cost Structure is the correct engine | ✘ (H2) |
| Sustainability tCO2e Y3 W/B/B | 2,672 / 26,627 / 152,541 | identical | ✔ |
| Tree equivalents Y3 Base | 1,267,950 | 1,267,950 | ✔ |

**Bottom line for the pitch:** the 5-Year Projection numbers are reproducible and internally consistent, but (1) do not present anything from the Business Model — Revenue/Cost/Profit trio until C1–C4 are fixed, (2) restate "Net Margin" as placeholder-cost operating margin and rebuild LTV:CAC and blended ROI (H1/H6/H7) — these are the three numbers an investor will attack first, and two of them are currently computed incorrectly even on the model's own terms.

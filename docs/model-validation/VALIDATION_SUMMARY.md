# Constistant Financial Model — Triple-Agent Validation Summary
Date: 2026-09-03 · File audited: `Constistant_Financial_Model.xlsx` (20 sheets, 751 formula cells)
Method: 3 independent agent runs — Agent 1 (user/customer numbers), Agent 2 (structure vs VC template), Agent 3 (formula forensics). Full reports in this folder: `agent1_users.md`, `agent2_structure.md`, `agent3_formulas.md`.

## Overall verdict: NOT investor-ready yet — but fixable, and the foundation is genuinely good

- Agent 1 (user numbers): **NOT DEFENSIBLE** as-is (arithmetic correct, inputs not)
- Agent 2 (structure): **DOES NOT MATCH** VC-standard template (survives demo-day glance, fails associate-level screen)
- Agent 3 (formulas): **UNSOUND** as a whole workbook (headline 5-Year chain reproduces bit-for-bit; the Business Model trio is broken)

What IS good (all 3 agents agreed): single Assumptions sheet with 🟩/🟨/🟥 source tags citing research files by section, everything formula-linked, self-check rows, honest Key Flags block on the Dashboard, and a genuinely sourced market funnel (80,000 contractors / 99.93% SME / 20% digital-ready all verified against market-sizing-assumptions-summary.md and researchA.md). The appendix goal ("everything explainable with linked formulas and notes") is very reachable.

## Cross-confirmed CRITICAL defects (found independently by 2–3 agents)

1. **The "retired" scenario switch still runs 4 sheets and is set to Best.** `Assumptions!B16='Best'` drives `Business Model — Revenue/Profit`, `Cost — Sustainability`, `Win-Win Summary` → the sheets labeled "pull these numbers into slides" show Best case (Y3 revenue ฿1,265M, 16,098 customers) while the Investor Dashboard shows Base (฿220.9M, 2,810). Two different companies in one file. → Set B16='Base' or hardwire.
2. **Live formula errors in pitch-facing sheets.** `Business Model — Revenue!E5` points at empty `Market — TopDown!B29` → −16,098 "new customers", ฿0 Y4 revenue. `Business Model — Cost!B19` mixes two incompatible customer tracks → CAC = **−฿77.5M**, Y5 total cost **negative**, `Business Model — Profit` margin **110.9%**. Any of these ends diligence.
3. **Base Year-1 customers (1,086) are 99.5% a goal-seeked guess.** Sales channel contributes 5.76 customers; 1,080 come from `Assumptions!C140` = 3,000 self-serve leads/mo, which the model admits was set to force Y1 > 1,000 — and which equals **7.5× the entire reachable universe** (4,797 firms, `Market — TopDown!B9`). The research summary §5 explicitly forbids inventing this number.
4. **Best case breaches the model's own SOM ceiling every year** (Y1 = 120.7% of regional pool; Y3 = 100.7% of nationwide digital-ready pool; Y5 = 4×). No MIN(pool) cap exists. Goal-seek cells for ฿300M/600M/1,200M remain live (`Assumptions!B77/B82/B83`) and feed P&L rows.
5. **Two parallel, disagreeing P&L chains** (Cost Structure→5-Year Projection vs Business Model trio): Y3 cost ฿95.2M vs ฿30.0M for identical customers. Keep one.
6. **No cash flow, burn, runway, funding ask, or monthly granularity anywhere.** Every scenario is profitable from Year 1 → the model cannot answer "how much do you need and how long does it last", which is STECX's first question.

## The user-number problem (your concern #1) — answer

Your instinct is right: user count is the dominant driver. Sensitivity (Agent 1): moving self-serve leads/conversion/churn to conservative values gives **Y1 ≈ 125, Y2 ≈ 337, Y3 ≈ 730** customers (−88%/−74% vs model) and Y1 revenue ~฿5M vs ฿44M; published 81–91% margins collapse to ~30–45%. Notably, the model's own **Worst case (122/213/282) is approximately what a defensible Base looks like**.

Recommended defensible Base set:
| Driver | Cell | Now | Recommended |
|---|---|---|---|
| Self-serve leads/mo | Assumptions!C140 | 3,000 flat | ramp 250 / 750 / 1,500 (tie to a marketing-budget line, leads × CPL ฿400–600) |
| Self-serve conversion | C141 | 3% | 2% until pilot data |
| Churn | C126 | 15%/yr | 30%/yr Y1–2 → 20% Y3+ (SMB norm 30–58%; Small ROI≈1.0x; BUILK precedent) |
| Close rate | C125 | 6% | 5% |
| Y4–5 growth | B117 | ×2 (laundered goal-seek) | extend GTM engine ~×1.5–1.7, cap at 30% of pool |
| Active scenario | B16 | Best | Base |

Result: Y1 ≈ 65–125 → Y5 ≈ 1,400–2,000 customers, revenue Y1 ~฿3–5M → Y5 ~฿120–175M. Present today's Base (1,086→11,240) as the **upside scenario conditional on a validated marketing engine**; cap or delete the current Best. This is the scale story you CAN defend to STECX: every number survives "where do the leads come from?" and "is this bigger than your own market?"

## Structure vs industry template (your concern #2) — answer

Current file is a well-documented unit-economics + market-sizing workbook, not yet a fundraising model. To match the standard early-stage SaaS VC template, add 5 sheets and merge 5:
**Add:** Funding Ask & Use of Funds · Headcount & Opex plan · Cash Flow & Runway (monthly Y1–2) · KPI sheet (ARR growth, layered GM→EBITDA, CAC payback, NRR, burn multiple) · Assumption Register (appendix).
**Merge:** 3 Business Model sheets → one P&L · 4 Client sheets → one Unit Economics tab · Cost Structure + BM—Cost → one Cost Build. Rename `Cost — Sustainability` (it's an affordability back-solve, not environmental). Color-code tabs inputs/calcs/outputs. Target: 18 sheets. Full layout in `agent2_structure.md` §c; appendix-grade checklist (assumption IDs, register, tag legend, named ranges, checks block) in §d.

## Headline metrics to repair before any pitch

- "Net Margin 81–91%" → arithmetically right but omits sales comp, the marketing engine behind 36,000 leads/yr, payroll burden, tax, and any Y1–3 team growth (8 people flat even at 16,098 customers). Relabel + rebuild costs; expect real SaaS-normal numbers.
- LTV:CAC 78.6x → triply invalid (3-yr lifetime contradicts own churn; revenue not gross profit; CAC excludes rep salaries). Use CAC payback months instead.
- Blended ROI 2.65x → wrong construction (average of ratios); correct value-weighted = **3.25x** (a better number).
- Blended price ฿6,550 on Dashboard uses the Y3 steady-state mix while Y1 reality is ฿3,391 with launch pricing — add the phased ARPU row so ARR reconciles.

## Fix order (highest leverage first)

1. Repair broken cells (BM—Revenue!E5, BM—Cost!B19) — margin >100% is an instant credibility kill
2. Kill/repoint the B16 scenario switch → one consistent scenario everywhere
3. Collapse to a single P&L chain
4. Make costs scale (headcount plan, sales comp, marketing = leads × CPL, hosting scaling)
5. Re-anchor Base on defensible user numbers (table above); cap Best at SOM
6. Add Cash Flow/Runway + Funding Ask + monthly Y1–2
7. Reorg sheets + Assumption Register + KPI sheet (mechanical, do last)

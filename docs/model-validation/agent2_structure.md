# Agent 2 — Workbook Organization & VC-Template Conformance Audit
Constistant_Financial_Model.xlsx · 20 sheets · audited 2026-09-03 against standard early-stage SaaS VC model conventions.

---

## (a) VERDICT: **DOES NOT MATCH the VC-standard template** (strong in provenance discipline, structurally incomplete as a fundraising model)

- **Survives:** a demo-day / pitch-competition glance, and a friendly first meeting. The assumption hygiene (single Assumptions sheet, everything formula-linked, 🟩/🟨/🟥 source tags, self-check rows) is genuinely above average and will earn credibility points.
- **Does NOT survive:** an associate-level screen at a corporate VC like STECX. Three template-defining artifacts are absent entirely — **cash flow / burn / runway, a funding-ask & use-of-funds sheet, and monthly granularity** — and the workbook currently shows 81–97% net margins with profitability from Year 1 in every scenario, which reads as "does not need money" and simultaneously "has never modeled real costs." It also contains live formula errors (negative costs, >100% margin) and two contradictory P&L chains. Any analyst who opens `Business Model — Profit` will find them within minutes.
- **Bottom line:** this is a well-documented *unit-economics and market-sizing workbook*, not yet a *financial model for a raise*. The reorganization in section (c) converts it with mostly-additive work; the assumption/tagging system in place makes the appendix goal very reachable.

---

## (b) Numbered Findings

### CRITICAL

**C1. No cash flow, no burn, no runway — anywhere.**
The workbook has no cash view at all: no monthly cash balance, no cumulative burn, no runway months. Every scenario is profitable from Year 1 (`5-Year Projection!B20` Worst Y1 profit = +1,287,399 ฿; `Business Model — Profit!B7` = +210.8M ฿). A VC's first question — "how much do you need and how long does it last" — cannot be answered from this file. `Cost — Sustainability!A20` even acknowledges the runway concept in a note ("ยอมรับว่าปีแรกๆ ขาดทุน... แล้วมีทุนมารองรับ (runway)") but no sheet models it.

**C2. No funding ask / use of funds sheet.**
Nothing states the raise amount, instrument, pre/post valuation context, use-of-funds breakdown, or milestones the money buys. For a pitch to STECX Venture this is the single most important output sheet and it does not exist. (Cap table is optional at this stage but a placeholder helps.)

**C3. Annual-only granularity; no monthly build for Years 1–2.**
Every sheet is ปี 1…ปี 5 columns. VC-standard is monthly for months 1–24 (at minimum quarterly), because burn, hiring timing, and runway only exist at monthly resolution. The GTM funnel (`GTM — Bottom-Up`) is already parameterized per-month (leads/rep/**เดือน**) so a monthly build is a mechanical extension, not new thinking.

**C4. Retired scenario switch still drives four sheets → workbook contradicts itself.**
`Assumptions!B16` = "Best" is documented as retired (`Assumptions!A16`: "❌ เลิกใช้แล้ว... เหลือไว้เป็น label เฉยๆ — ไม่ขับเคลื่อนสูตรไหนแล้ว") — but it still drives `Business Model — Revenue!B5:D5` (IF on B16 → shows **Best**: 5,789 / 11,143 / 16,098 customers, Y1 revenue 235.6M ฿), and through it `Business Model — Profit`, `Cost — Sustainability!B5:D5`, and `Win-Win Summary!B14:D14` (Y3 = 9,659 Small customers). Meanwhile `Investor Dashboard` and `5-Year Projection` present **Base** (1,086 / 2,015 / 2,810). Two different companies live in one workbook. Either wire B16 back up or hard-retire it and re-point the four sheets to Base.

**C5. Live formula errors: negative costs and >100% margin.**
- `Business Model — Revenue!E5` = `'Market — TopDown'!B29` → **0** (empty cell reference), making `E6` (new customers Y4) = **−16,098** and `E8` (Y4 revenue) = 0.
- `Business Model — Cost!B19` (Y5 CAC) = **−77,505,000 ฿** (subtracts a larger Y4 Best base from a Y5 target series that lives on a different growth track), so `B20` total Y5 cost = **−65,318,250 ฿** and `Business Model — Profit!B31` shows **Margin 110.9%**. A negative total cost line is an instant credibility kill in diligence.

**C6. Two parallel, disagreeing P&L chains.**
Chain A: `Cost Structure` → `5-Year Projection` (Base Y3 cost 18.97M, margin 91.4%). Chain B: `Business Model — Revenue/Cost/Profit` (Y3 cost 30.03M on the Best customer base, margin 97.6%; its own Y3 Worst/Base/Best block at `Business Model — Profit!B13:D13` computes cost a third way). Same question, three answers. Standard template rule: **one revenue build, one cost build, one P&L output** — everything else references them.

### HIGH

**H1. Cost lines do not scale credibly → implausible 81–97% net margins on the face of the model.**
- Team is flat at 8 people × 30,000 ฿/mo for Y1–3 **in all scenarios** (`Business Model — Cost!B5:D5`; `Cost Structure!B16` note "flat ทุก Scenario ก่อน Y4-5") — including Best case serving 16,098 customers.
- Hosting flat 96,000 ฿/yr through Year 6 (`Business Model — Cost!C16`) regardless of 64,392 customers.
- Salary has no employer on-costs (SSO, bonus, equipment), no salary inflation, no engineering-vs-sales split.
- **Sales reps in `GTM — Bottom-Up` (up to 6 reps in Best) are never costed anywhere** — revenue is driven by headcount that doesn't appear in any cost line; CAC is a separate flat 3,000 ฿ (`Assumptions!B68`) unlinked to rep salaries or the Channel-2 ad spend that `Assumptions!B140` says requires "paid ads/viral campaign".
- No tax, no D&A/capex, no working capital / receivables (construction clients pay slowly — a known sector trait), no FX line despite USD AI costs.
Result: `5-Year Projection!B24:F24` Net Margin 81–91% and `Business Model — Profit!D8` 97.6%. Best-in-class public SaaS runs 70–80% *gross*, ~0–20% net. This must be fixed before showing any investor, or the honesty of the rest of the model is discounted.

**H2. No headcount plan sheet.**
Headcount exists only as scattered scalars (`Assumptions!B63` = 8, `B79` = 12, `B84` = 20, `B85` = 35) with no role/timing/salary-band breakdown, and Y1–3 hiring is implicitly zero. Standard template has a Headcount tab (role × start month × salary) feeding Opex; it is also the natural backbone of the use-of-funds story.

**H3. No KPI sheet; several dashboard metrics are the wrong ones (see (e)).**
MRR/ARR by month, gross vs net margin properly layered, CAC by channel, CAC payback months, NRR/GRR, logo churn monthly, burn multiple, magic number — none exist as a computed sheet. `5-Year Projection!B26` LTV:CAC = **78.6x** (self-flagged as unreliable at `Investor Dashboard!A33`) is the only efficiency metric, and it's one you don't want on the page.

**H4. Churn/cohort logic is a single annual survival factor, not a cohort build.**
`GTM — Bottom-Up` applies one blanket churn (`(1-churn)` on prior-year stock, e.g. `!C10`). No cohort retention by segment (the model itself warns Small ROI ≈ 1.0x → high churn risk, `Pricing Strategy!A18`), no expansion revenue, no NRR. Monthly cohort rows (even simplified) are the credible version.

### MEDIUM

**M1. Sheet count and naming don't follow inputs→calcs→outputs convention.**
20 sheets, no tab color coding described, mixed Thai/English names, and order interleaves outputs (`Investor Dashboard` first — fine) with calc and appendix sheets. Three `Business Model — *` sheets and two sustainability-named sheets fragment what should be single tabs. See target structure in (c).

**M2. `Cost — Sustainability` is misnamed.**
It is an *affordability back-solve* (what team size can revenue support at 70% GM target) — nothing to do with environmental sustainability, yet it sits next to `Sustainability Impact`. Rename (e.g. "งบที่จ่ายไหว — Affordability Check") or absorb into the cost build as a sanity block.

**M3. Best-case is reverse-engineered from revenue targets and flagged as exceeding SAM.**
`Assumptions!B77/B82/B83` back into capture rates from 300M/600M/1,200M ฿ targets, tagged 🔴 "เกินจำกัด SAM" (B83 requires 99.7% of the digital-ready market). Honest — but presenting a scenario the model itself proves impossible is non-standard. Move to a clearly-labeled "Aspirational / target math" appendix block or drop from the main scenario set.

**M4. Stray/orphan cells.**
`Assumptions!D58` = 0.12 sits in the ประเภท (tag) column of a header row — orphan value, likely a paste error; it will make an auditor question the tag column's integrity. `Business Model — Revenue!E5/E6` (see C5). `AI Infra — Unit Cost!E28` is a formula that evaluates to its own label text (formula-as-note hack).

**M5. Blended ROI is customer-count-weighted, not value-weighted.**
`Client — Summary!E9` blends the three segment ROIs by mix % (2.65x). ROI of a blend should be blended value ÷ blended price (255,243/78,600 = 3.25x). Minor, but a numerate investor will recompute it.

**M6. Channel-2 self-serve volume is constant across years.**
`GTM — Bottom-Up!B38/C38/D38` add the same self-serve customer count to every year (no ramp of leads or conversion), while Channel 1 ramps reps. Also self-flagged (`Assumptions!C140` 🔥) as requiring an unvalidated 3,000 leads/month from day one to hit the "Year 1 > 1,000 customers" target — this is target-seeking, same pattern as M3.

### LOW

**L1. Thai text has scattered typos/mojibake** (e.g. `Assumptions!E55` "รางอิง", `A16` "เลิกเลิก", `Sustainability Impact!A6` "เสdียก") — cosmetic, but an appendix meant to be read closely should be proofed.

**L2. README sheet order list is stale.** `README!A11-A18` lists 12 sheets; the workbook has 20 (GTM — Bottom-Up, AI Infra, Cost Structure, Pricing Strategy, 5-Year Projection, Sustainability Impact, Investor Dashboard not listed). Update alongside the reorg.

**L3. Hard-coded cross-sheet cell addresses in note columns** ("Client — Summary!B12:E12", "Assumptions!A92-95") will silently rot when rows shift. Named ranges / assumption IDs (see (d)) fix this.

**L4. Competitors price row mixes currencies/periods as text** (`Competitors!D10` "$299/user/เดือน" vs `D13` "฿1,050/ปี") — fine for an appendix, but add a normalized ฿/month column so the positioning claim in `Pricing Strategy!A22` is checkable.

---

## (c) Proposed Target Sheet Structure

Tab color convention (industry standard): **เหลือง = Inputs · ฟ้า = Calculations · เขียว = Outputs · เทา = Appendix/Reference**. Keep Thai names where they exist; suggested names below preserve current conventions.

| # | Tab (color) | Name | Purpose / provenance |
|---|---|---|---|
| 1 | เขียว | **Investor Dashboard** | Keep first. Rebuilt per (e): ARR + growth, layered GM%, burn, runway, ask. |
| 2 | เขียว | **Funding Ask & Use of Funds** *(NEW)* | Raise amount, use-of-funds by category tied to Headcount/Opex, milestones, runway delivered. Optional mini cap-table block. |
| 3 | เทา | **README** | Updated legend (add 🟥/🔴/⚪ which are used but not in the current legend at `README!A7-A8`), updated sheet map, changelog. |
| 4 | เหลือง | **Assumptions** | Keep as the single input sheet. Add ID column (see (d)). Remove retired B16 switch or re-wire it. Move GTM rows (B119-141) intact — they already live here, good. |
| 5 | ฟ้า | **Market — TopDown** | Keep. TAM→SAM→reachable→digital-ready. |
| 6 | ฟ้า | **GTM — Bottom-Up (รายเดือน)** | Extend to monthly for M1–24 + annual Y3–5; cost the sales reps and Channel-2 marketing spend here so CAC is derived, not assumed. |
| 7 | ฟ้า | **Client — Unit Economics** | **Merge** `Client — Small` + `Medium` + `Large` + `Summary` into one sheet (the three size sheets are identical row templates — perfect as Small/Medium/ใหญ่/Blended columns; Summary's blended-ARPU-by-year block moves here too). |
| 8 | ฟ้า | **AI Infra — Unit Cost** | Keep (good sheet). GPU-breakeven block stays as its forward-looking section. |
| 9 | ฟ้า | **Headcount & Opex** *(NEW)* | Role × start-month × salary(+on-costs) plan per scenario; hosting/overhead scaling rules. Feeds Cost Build. Absorb the affordability back-solve from `Cost — Sustainability` as a sanity block ("ทีมสูงสุดที่จ่ายไหว"). |
| 10 | ฟ้า | **Cost Build** | **Merge** `Cost Structure` + `Business Model — Cost` into ONE cost chain (fix C5/C6). AI COGS as COGS; S&M (reps+ads), R&D, G&A as opex lines. |
| 11 | เขียว | **P&L 5 ปี (Worst/Base/Best)** | **Merge** `5-Year Projection` + `Business Model — Revenue` + `Business Model — Profit` into one output P&L: Revenue → COGS → Gross Profit/GM% → Opex by function → EBITDA → Net. Monthly Y1–2 columns + annual Y1–5. |
| 12 | เขียว | **Cash Flow & Runway** *(NEW)* | Monthly: EBITDA ± working capital (receivable days for construction clients) − capex → net cash flow → cash balance given the raise; burn, runway months, burn multiple. |
| 13 | เขียว | **KPI Sheet** *(NEW)* | MRR/ARR, ARR growth %, GM% (full), logo & revenue churn, NRR, CAC by channel, CAC payback, LTV:CAC (with defensible lifetime), Rule of 40. |
| 14 | เทา | **Pricing Strategy** | Keep as appendix (cost-plus / value-based / competitive checks). |
| 15 | เทา | **Competitors** | Keep; add normalized ฿/เดือน column (L4). |
| 16 | เทา | **Sustainability Impact** | Keep single sustainability sheet (Metric 2–3 clearly kept 🟥). Do NOT merge `Cost — Sustainability` into it — that content moves to sheet 9 (M2). |
| 17 | เทา | **Win-Win Summary** | Keep (it is presentation-layer; point it at Base, not the retired switch — C4). |
| 18 | เทา | **Assumption Register (ภาคผนวก)** *(NEW)* | The appendix-grade register per (d). |

Net effect: 20 sheets → 18, with 5 merges, 5 new sheets, 1 rename, and one deletion class (the three Business Model tabs and two redundant client tabs disappear into merges).

---

## (d) Checklist to reach "appendix-grade" explainability

Current state, credit where due: the 🟩/🟨/🟥 system + ที่มา columns citing research files *by section* (`Assumptions!E6` "Krungsri Research 2024 — researchE.md §2") is already better than most seed models, and self-check rows exist (`Client — Summary!B25:E25` = 0 checks, `Win-Win Summary!B18` vs `C18` cross-check). What's missing to make it a formal appendix:

- [ ] **Assumption IDs.** Add an ID column in `Assumptions` (e.g. `MKT-01` TAM-low, `EFF-03` engineer hourly rate, `GTM-07` close rate, `SUS-04`). Every downstream ที่มา note cites IDs, not cell addresses (kills L3 rot).
- [ ] **Assumption Register sheet** (target sheet 18): one row per ID — ค่า, หน่วย, tag (🟩/🟨/🟥/🔴/⚪), source document + section, date last verified, owner, "what evidence would upgrade this tag" (pilot data, survey, invoice), and which sheets consume it. Mostly a re-projection of the existing Assumptions columns — cheap to build.
- [ ] **Complete the tag legend.** README defines only 🟩/🟨 (`README!A7-A8`) but the workbook uses 🟥 (team guess), 🔴 (exceeds SAM), ⚪ (formula), 🔥 and ⚠️. Define all, and state the escalation rule (🟥 must never appear upstream of a headline number without a flag on the output sheet — the Dashboard's Key Flags section already does this well).
- [ ] **Tag census on the register:** counts of 🟩 vs 🟨 vs 🟥 driving each headline output (e.g. "Y3 Base ARR depends on 9 🟩, 6 🟨, 5 🟥") — this is exactly the transparency a corporate VC rewards.
- [ ] **Formula map** (one page, can live on README): the dependency spine `Assumptions → GTM/Market → Client Unit Econ + AI Unit Cost → Cost Build/Headcount → P&L → Cash Flow → Dashboard`, so a reader can trace any dashboard number in ≤3 hops. The `F`/`G`/`E` "ที่มา/สูตร" columns already on most sheets do the per-row job; keep them.
- [ ] **One number, one home.** After the C6 merge, verify no metric is computed in two places (add a checks block: Dashboard ARR = P&L ARR, etc., in the style of `Client — Summary!A25`).
- [ ] **Fix the broken/orphan cells first** (C5, M4) — an appendix that documents wrong numbers is worse than none.
- [ ] **Changelog block** on README (the 2026-09-02 note at `README!A28` is the right instinct — make it a running dated list).
- [ ] **Named ranges** for the ~20 most-referenced assumptions (`ChurnBase`, `CAC`, `ARPU_Blended_Y3`...) so formulas self-document.
- [ ] **Data-validation / protection:** lock calc & output sheets, leave only Assumptions editable; mark input cells with the standard blue-font convention.
- [ ] **Print/PDF areas** per output sheet so the appendix exports cleanly for the STECX deck; consider a one-page English summary of Assumptions for the corporate VC's investment committee (body can stay Thai).

---

## (e) Investor Dashboard — presentation-layer check

**Already there (keep):** ARR by year (`!B13:F13`), customer counts, per-segment pricing & customer ROI, AI-COGS gross margin, 3-scenario Y3 compare, sustainability headline, and — its best feature — the **Key Flags candor block** (`!A30-A34`) that self-discloses weak assumptions. Keep that block; VCs rarely see it and it builds trust.

**Missing (add):**
1. **ARR growth %** YoY (and MoM once monthly exists) — growth rate is the first VC metric and it's absent.
2. **Layered margin**: Gross Margin (all COGS incl. hosting/support) → EBITDA margin. Today only "AI COGS GM" 98.1% (`!B8`) and "Net Margin" 81–91% (`!B14:F14`) are shown — both misleading per H1; the 98% figure invites the exact "what about everything else" question.
3. **Burn & runway**: monthly net burn, cash-out date, runway months at the proposed raise (needs sheet 12).
4. **CAC payback (months)** by channel — with 78,600 ฿ blended ARPU and 3,000 ฿ CAC it's <1 month, which itself signals the CAC assumption is broken (H1); deriving CAC from real S&M spend fixes both the number and the optics.
5. **NRR / churn line** — even as "🟥 assumed until pilot," show the assumption explicitly.
6. **Burn multiple / Rule of 40** once cash flow exists.
7. **The ask**: one row — raising X ฿, gets Y months runway, to milestones Z (links to sheet 2).

**Remove / repair:**
- **LTV:CAC 78.6x** (`5-Year Projection!B26`, flagged at `!A33`) — replace with churn-derived LTV (Base 15%/yr → ~6.7-yr lifetime is *worse* optics; use payback months instead, which VCs trust more at pre-traction stage).
- **Net Margin 81–91% row** — repair via H1 before any investor sees it; as-is it undermines the whole dashboard.
- **Blended customer ROI 2.65x** (`!E7`) — recompute value-weighted (M5) → 3.25x, which is also a better number.
- Scenario Y3 strip (`!B17:D17`): fine, but Best (16,098 customers / 1.27B ฿) inherits the 🔴 exceeds-SAM math (M3) — either cap Best at SAM or footnote it on the dashboard itself.

---

*Cross-reference note for the merger of the three audit runs: the highest-leverage fixes in priority order are C5 (broken formulas) → C4 (retired switch) → C6 (single P&L) → H1 (credible costs) → C1/C2/C3 (cash, ask, monthly) → then the reorg and register, which are largely mechanical.*

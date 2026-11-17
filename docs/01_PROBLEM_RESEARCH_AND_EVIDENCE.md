# 01 — Problem Research, Root-Cause Analysis & Evidence Ledger

**Project:** ServiceYield AI  
**Theme:** AI & Automation (Theme 1, Tek-Qubit 2026)  
**Authoritative Reference:** Technical, Financial & Regulatory Report (Sections 2, 11, 12) & Product Blueprint (Section 2)  
**Evidence Standard:** All figures and assertions are tagged with strict evidentiary classifications.

---

## 1. Industry Context: The Fixed Operations Powerhouse

Dealership after-sales service and parts ("Fixed Operations") represent the economic core of automotive retail franchises in the United States:

| Metric | Industry Figure | Source / Classification | Operational Relevance |
| :--- | :--- | :--- | :--- |
| **US Franchised Dealerships** | ~16,950 rooftops | `[PUBLIC]` NADA Data 2025 | Total addressable physical footprint. |
| **Annual Service & Parts Sales** | > $164 Billion | `[PUBLIC]` NADA 2025 | Massive recurring revenue stream. |
| **Share of Dealership Revenue** | ~13.2% – 13.6% | `[PUBLIC]` Presidio-NCM Q4 2025 | Modest percentage of gross dealership top-line turnover. |
| **Share of Dealership Gross Profit** | **48% – 59%** | `[PUBLIC]` Presidio-NCM Q4 2025 | Fixed ops funds dealership fixed overhead and drives net margin. |
| **Average Rooftop Annual ROs** | ~16,300 – 16,500 ROs | `[PUBLIC]` NADA 2025 (276M ROs / 16,950 dealers) | Baseline transaction volume (~55–65 ROs/day). |
| **Average Service Sales per Rooftop** | ~$9.7 Million | `[PUBLIC]` NADA 2025 | Average scale of a mid-size franchised store. |
| **Average Customer-Pay RO Value** | ~$494 | `[PUBLIC]` NADA 2025 | Labour + parts blend on typical repair. |
| **Average Fixed Absorption Rate** | ~64% (Range: 54%–66%) | `[PUBLIC]` McKinsey 2024; NADA 2025 | Percentage of total dealership overhead covered by fixed ops profit. |
| **Absorption Point Economic Value** | **$20M – $40M / point** | `[PUBLIC]` McKinsey Automotive Practice | Financial value of a 1.0-point absorption gain for large dealer groups. |
| **Customer Retention Decline** | 72% (2023) $\to$ 54% (2025) | `[PUBLIC]` Cox Automotive Service Industry Study | Sharp erosion in customer loyalty back to selling dealer. |
| **Customer Lateness NPS Impact** | NPS falls from **+72 to +29** | `[PUBLIC]` CDK Global Service Experience Report | A 43-point collapse in Net Promoter Score when promises slip. |

---

## 2. The Operational Leak: The Parts-Delay Paradox

### 2.1 The Traditional Disconnect
In traditional dealership software suites (including standard legacy DMS and appointment schedulers), work scheduling and parts procurement operate in disconnected functional silos:
1. **The Scheduler** slots jobs into technician calendars based on generic flat-rate labor estimates and appointment times, assuming parts will be present.
2. **The Parts Department** receives electronic pick-tickets or purchase orders and optimizes for vendor discounts, manufacturer purchasing incentives, or unit invoice costs.
3. **The Workshop** discovers mid-repair that a required gasket, sensor, or fastener is backordered, delayed in transit, or damaged in shipping.

### 2.2 The Physics of a Mid-Repair Bay Stall
When a repair is interrupted after teardown:
- **Vehicle Immobilization:** The vehicle has its engine disassembled, wheels off, or subframe dropped. It is physically trapped on a hydraulic two-post lift (`IMMOBILIZED_ON_LIFT`).
- **Resource Blockage:** The lift cannot be used for any other vehicle. If pushed outside, it requires a tow or 2–3 technicians to manually push, risking lot damage and violating safety protocols.
- **Cascading Capacity Destruction:** The blocked bay consumes 4 to 8 hours of productive shop time while waiting for a $30 bracket. Downstream jobs requiring that specialist lift (e.g., heavy duty, alignment, EV isolation) are bumped, triggering customer promise delays across multiple unrelated repair orders.
- **Flat-Rate Technician Friction:** In the US, flat-rate technicians are paid strictly for "flagged" flat-rate production hours. When a vehicle stalls on their assigned lift, they face unpaid downtime, uneven earnings, and morale degradation.

---

## 3. Fishbone (Ishikawa) Root-Cause Analysis

To understand why parts delays cause outsized economic damage, ServiceYield models the complete workshop ecosystem through a systematic Ishikawa root-cause decomposition:

```
                       PEOPLE                                 PARTS
              Technician Absence                   Stock Level Discrepancy
                      \                                       \
          Flat-Rate Skill Mismatch                 Supplier ETA Volatility
                        \                                       \
             Incomplete Shift Handoff              Incompatible Supersession
                          \                                       \
   ────────────────────────┴───────────────────────────────────────┴───────────────►
                          /                                       /                │
             Specialist Bay Scarcity                Manual Parts Phone Calls       │
                        /                                       /                  ├──► WORKSHOP
         Immobilized Vehicle on Lift                Stale Schedule Board           │    CAPACITY
                      /                                       /                    │    LEAK
              Missing EV Insulation Bay            Delayed Manager Escalation      │
                     /                                       /                     │
                   BAYS                                    PROCESS                 │
                                                                                   │
   ────────────────────────┬───────────────────────────────────────┬───────────────►
                          /                                       /
             Fragmented DMS / Parts Data           Local Unit-Cost Optimization
                        /                                       /
            Stale Telemetry & Promises             Ignoring Bay-Hour Opportunity Cost
                      /                                       /
               No Unified Snapshot                 Lateness Penalties Unmonetized
                     /                                       /
                   DATA                                   ECONOMICS
```

### Detailed Factor Breakdown:
1. **People:** Technicians possess heterogeneous skill certifications (Engine Overhaul, High-Voltage EV, Transmission, Suspension). Assigning a complex teardown to a technician who cannot complete reassembly creates severe bottlenecking.
2. **Parts:** Real-world delivery ETAs exhibit fat tails. Local stock counts are frequently inaccurate due to unrecorded damage, misplacement, or prior reservations.
3. **Bays:** Bays are capital-intensive physical fixtures. Dealerships have fixed counts of specialized bays (e.g., 2 alignment racks, 1 EV isolation bay, 4 heavy-duty lifts, 6 generic service bays). Bay substitution is constrained by physical lifting limits and ceiling heights.
4. **Process:** When a delay occurs, communication happens via phone calls, sticky notes, or walk-ins to the parts counter. Escalation to the Service Manager happens hours after the delay began.
5. **Data:** Schedulers operate on static assumptions; parts catalogs operate on inventory batches; dispatchers operate on local whiteboards. No single system maintains a synchronized, version-controlled state snapshot.
6. **Economics:** Traditional parts procurement minimizes purchase price (e.g., choosing Sister Store S2 at $120 over Hotshot S1 at $157). The procurement system does not factor that saving $37 on freight destroys $220 in service bay capacity.

---

## 4. Evidence Classification Ledger

ServiceYield AI enforces complete transparency. Every metric used in the product design, economic models, and pitch is indexed below:

```
EVIDENTIARY CLASSIFICATIONS:
[PUBLIC]    — Sourced from verified public filings, regulatory reports, or vendor documentation.
[MODEL]     — Calculated output of the ServiceYield mathematical and financial models.
[ASSUMPTION]— Empirical operational parameter requiring shadow-mode validation.
[INFERENCE] — Strategic product and competitive positioning analysis.
[VALIDATE]  — Open hypothesis requiring direct dealer or Tekion confirmation.
```

### Master Evidence Table
| Code | Tag | Assertion / Metric | Value / Range | Evidentiary Basis & Source | Validation Plan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **EV-01** | `[PUBLIC]` | US franchised dealership rooftops | 16,950 rooftops | NADA Data 2025 Annual Financial Profile | DMS market census. |
| **EV-02** | `[PUBLIC]` | Total annual US dealership ROs | ~276 Million | NADA Data 2025 | Dealer DMS aggregation. |
| **EV-03** | `[PUBLIC]` | Fixed ops share of dealership gross profit | 48% – 59% | Presidio-NCM Q4 2025; NADA 2025 | Dealer group annual 10-K filings. |
| **EV-04** | `[PUBLIC]` | Average fixed absorption rate | 64% | McKinsey Automotive Report 2024; NADA 2025 | Benchmark against rooftop P&L. |
| **EV-05** | `[PUBLIC]` | Economic value of 1.0 absorption point | $20M – $40M / yr | McKinsey Automotive Practice (large groups) | Group financial statements. |
| **EV-06** | `[PUBLIC]` | Tekion live rooftop base | 3,000+ rooftops | Tekion NADA 2026 Recap (March 2026) | Verified press disclosure. |
| **EV-07** | `[PUBLIC]` | Tekion platform users | ~120,000 users | Tekion NADA 2026 Recap | Corporate public report. |
| **EV-08** | `[PUBLIC]` | Tekion total app installs | 6,125+ installs | Tekion APC Marketplace Homepage (Nov 2026) | Partner cloud ecosystem metric. |
| **EV-09** | `[PUBLIC]` | Customer NPS loss on service delays | NPS +72 $\to$ +29 | CDK Global Service Experience Study | Customer satisfaction telemetry. |
| **EV-10** | `[ASSUMPTION]` | Share of ROs experiencing parts delay beyond promise | **5.0%** (3%–6.5%) | Baseline engineering planning assumption | **Day 1 Shadow Mode Metric #1**. |
| **EV-11** | `[ASSUMPTION]` | Share of delayed ROs that stall a bay mid-repair | **30.0%** (20%–40%) | Operational workshop survey assumption | **Day 1 Shadow Mode Metric #2**. |
| **EV-12** | `[ASSUMPTION]` | Contribution per incremental sold hour | **$120** ($100–$130) | $175 effective labor rate × 72% gross margin | Rooftop labor cost ledger. |
| **EV-13** | `[ASSUMPTION]` | Share of delay events avoided by Predict | **12.0%** (8%–14%) | Early risk escalation and parts staging | Pilot A/B comparison. |
| **EV-14** | `[ASSUMPTION]` | Technician idle hours per avoided delay | **1.5 hours** | Tech reallocation and staging efficiency | Timecard audit in pilot. |
| **EV-15** | `[ASSUMPTION]` | Extra sold hours generated from CP-SAT sequencing | **1.5%** (0.8%–2.0%) | Reduction in micro-gaps and idle bay slots | Solver benchmark vs T1. |
| **EV-16** | `[ASSUMPTION]` | Commercial sell-through of recovered bay hours | **70.0%** (55%–80%) | Capacity-constrained service market demand | Service appointment waitlist. |
| **EV-17** | `[ASSUMPTION]` | Recover improvement rate on stalled ROs | **70.0%** (55%–75%) | Sourcing alternatives and re-planning | Solver optimization rate. |
| **EV-18** | `[ASSUMPTION]` | Average bay-hours saved per recovered stall | **1.8 hours** | Faster bay release via expedited sourcing | Bay telemetry logs. |
| **EV-19** | `[ASSUMPTION]` | Inter-lever overlap discount | **20.0%** | Anti-double-counting statistical barrier | Empirical pilot attribution. |
| **EV-20** | `[ASSUMPTION]` | Realization factor (manager adoption & compliance) | **75.0%** (60%–80%) | Manager acceptance rate of recommendations | UI audit logs. |
| **EV-21** | `[MODEL]` | Base-case net economic value per rooftop | **$50.3K / year** | ServiceYield Financial Model (16,300 RO base) | Comprehensive rooftop P&L audit. |
| **EV-22** | `[MODEL]` | Net fixed absorption gain per average rooftop | **~0.7 points** | $50.3K net value / $7.2M average overhead | Financial absorption model. |
| **EV-23** | `[INFERENCE]` | Tekion product gap hypothesis | Joint Economic Loop | Tekion publicly offers scheduling and AI workflows; joint optimization is unaddressed | Product validation interviews. |
| **EV-24** | `[VALIDATE]` | Tekion Automotive Partner Cloud (APC) API access | Read/Write webhook | API permissions, webhook latency, SLAs | Tekion Partner Program review. |
| **EV-25** | `[VALIDATE]` | Legal compliance of flat-rate fairness constraints | Fair Labor Standards | 29 U.S.C. §207(i); California Labor Code §226.2 | Dealership labor counsel review. |

---

## 5. The Root Operational Decision: Why "Cheapest Part" Fails

The defining insight of ServiceYield AI is that **minimizing parts acquisition cost in isolation destroys dealership profit**.

### Mathematical Illustration:
Consider an immobilized vehicle in Bay 4 undergoing a transmission repair:
- **Baseline Delay:** Original supplier cannot deliver the replacement seal until tomorrow afternoon. The vehicle will block Bay 4 for an additional 110 minutes of shop operating hours today.
- **Supplier Option A (Sister Store S2):** Unit cost = $120. Delivered in 2 days. Freight = $0.
- **Supplier Option B (Hotshot Courier S1):** Unit cost = $120. Courier freight surcharge = $37. Delivery time = 25 minutes (usable-ready in 40 minutes, saving 110 minutes of bay blockage).
- **Workshop Value:** Bay 4 is a heavy lift generating $\nu = \$2.00/\text{minute}$ ($\$120/\text{hour}$) of contribution when active. Customer promise lateness penalty $\lambda_{\text{late}} = \$0.50/\text{minute}$.

$$\begin{aligned}
\text{Incremental Freight Expense} &= -\$37.00 \\
\text{Freed Bay Capacity Value} &= 110 \text{ min} \times \$2.00/\text{min} = +\$220.00 \\
\text{Avoided Promise Lateness Penalty} &= 110 \text{ min} \times \$0.50/\text{min} = +\$55.00 \\
\hline
\mathbf{\text{Net Dealership Economic Value}} &= +\$220.00 + \$55.00 - \$37.00 = \mathbf{+\$238.00}
\end{aligned}$$

A traditional parts buyer or purchasing module looking only at supplier invoices chooses Option A to save $37.00. **The dealership loses $238.00 in real economic contribution.**

ServiceYield AI solves the holistic problem: it gives the Service Manager the exact, transparent economic trade-off to approve Option B with complete confidence.

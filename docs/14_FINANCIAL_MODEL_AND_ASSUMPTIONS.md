# 14 — Financial Model, Assumptions Register & Commercial Sizing

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 11, 12) & Product Blueprint (Sections 13, 14)  
**Classification:** Financial & Commercial Model Specification  
**Standard:** Strict Evidentiary Classification (`[PUBLIC]`, `[MODEL]`, `[ASSUMPTION]`)

---

## 1. The Three Lenses on "$200 Million" (Strict Separation Rule)

To prevent commercial overreach, misleading investor claims, and credibility loss during executive pitches, ServiceYield AI enforces an absolute rule regarding financial sizing:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        THE THREE DISTINCT FINANCIAL LENSES                             │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ ❌ CRITICAL RULE: NEVER CONFLATE OR MIX THESE THREE MEASURES ON A SLIDE.               │
│                                                                                        │
│ 1. LENS 1 — ANNUAL ECONOMIC VALUE CREATED FOR DEALERSHIPS [MODEL]:                     │
│    The aggregate operational and financial profit delivered across all adopting       │
│    dealerships (~$50.3K/rooftop/year). Reaching $200M requires ~4,000 rooftops (~24%   │
│    of US franchised dealers).                                                          │
│                                                                                        │
│ 2. LENS 2 — ANNUAL TEKION PRODUCT REVENUE [MODEL]:                                     │
│    The direct SaaS software subscription fees collected by Tekion from selling        │
│    ServiceYield at $900/month ($10.8K/year). Year 5 base-case revenue is $21.6M.       │
│    Claiming "$200M in product revenue" is factually false under the model.             │
│                                                                                        │
│ 3. LENS 3 — CAPITALIZED EQUITY VALUE FOR TEKION [MODEL / INFERENCE]:                   │
│    The enterprise valuation created for Tekion by capitalizing high-margin, sticky    │
│    fixed-ops SaaS revenue at software multiples (e.g., $21.6M ARR × 10× = ~$216M).     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Complete Assumptions Register (Model Inputs)

Every input variable in the financial model is indexed below with its operational basis and sensitivity range:

| # | Parameter / Assumption Name | Base Value | Range Tested | Classification | Evidentiary Basis & Source | Validation Method |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A1** | Repair Orders per Average Rooftop / Year | **16,300** | Fixed | `[PUBLIC]` | 276M ROs across ~16,950 US dealers | NADA Data 2025 |
| **A2** | Technicians per Rooftop; Clock Hours Each | **11; 2,000**| Fixed | `[ASSUMPTION]` | Typical mid-size franchised dealership | Rooftop payroll records |
| **A3** | Contribution per Incremental Sold Hour | **$120.00** | $100–$130 | `[ASSUMPTION]` | $175 labor rate × ~72% labor gross | Rooftop P&L statements |
| **A4** | Share of ROs Hit by Parts Delay Beyond Promise | **5.0%** | 3.0%–6.5% | `[ASSUMPTION]` | **No public benchmark found!** | **Day 1 Shadow Mode** |
| **A5** | Share of Delayed ROs that Block Bay Mid-Repair | **30.0%** | 20%–40% | `[ASSUMPTION]` | Workshop operational survey | Shadow mode telemetry |
| **A6** | Delay Events Avoided by Predict Early Staging | **12.0%** | 8%–14% | `[ASSUMPTION]` | Risk escalation prior to teardown | Stepped-wedge pilot |
| **A7** | Tech Idle Hours Avoided / Delay; Comp Cost | **1.5 h; $40**| Fixed | `[ASSUMPTION]` | Reallocation efficiency + loaner fees | Pilot timecard audit |
| **A8** | Extra Sold Hours from CP-SAT Sequencing | **1.5%** | 0.8%–2.0% | `[ASSUMPTION]` | Elimination of micro-gaps on lifts | Solver benchmark vs T1 |
| **A9** | Commercial Sell-Through of Recovered Hours | **70.0%** | 55%–80% | `[ASSUMPTION]` | Capacity-constrained service market | Appointment backlog logs |
| **A10**| Recover: Stalls Improved; Bay-Hours Saved; Slips| **70%; 1.8h; 0.6**| 55%–75% | `[ASSUMPTION]` | StallBreaker 2 sourcing efficiency | Pilot telemetry |
| **A11**| Inter-Lever Overlap Discount | **20.0%** | 15%–25% | `[ASSUMPTION]` | Prevents double-counting benefits | Attribution modeling |
| **A12**| Operational Realization Factor | **75.0%** | 60%–80% | `[ASSUMPTION]` | Manager compliance & override rate | UI audit clickstream |
| **A13**| Blended Subscription Price / Rooftop / Month | **$900.00** | $800–$1,000| `[ASSUMPTION]` | Core ($600) vs Pro ($1,100) blend | Tekion pricing team |
| **A14**| Tekion Total Live Rooftops (2027 to 2033) | **3,400 $\to$ 6,800**| 3,300–8,500| `[MODEL]` | 3,000+ live (PUBLIC) + 15–20% CAGR | Tekion management |
| **A15**| Product Attach Rate to Tekion Base (Yr 1 to 7) | **2.0% $\to$ 47.0%**| 1.0%–62.0%| `[MODEL]` | Enterprise fixed-ops SaaS adoption | Partner sales metrics |

---

## 3. Value Created per Paying Rooftop (Base Case: $50.3K Net)

For an average franchised rooftop generating 16,300 annual ROs with 11 technicians (~22,000 clocked hours) and ~$7.2M in annual fixed dealership overhead:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        BASE-CASE ROOFTOP VALUE DECOMPOSITION                           │
├──────────────────────────────────────────────────────────────────────┬─────────────────┤
│ VALUE LEVER & DERIVATION                                             │ GROSS VALUE     │
├──────────────────────────────────────────────────────────────────────┼─────────────────┤
│ **LEVER 1: PREDICT (Avoided Parts Delays & Technician Staging)**     │                 │
│ • 16,300 ROs × 5.0% parts delay rate = 815 delayed ROs               │                 │
│ • 815 delayed ROs × 12.0% avoided by Predict = 98 avoided delays     │                 │
│ • 98 events × [(1.5 h tech idle × $120/h) + $40 loaner/comp cost]    │ **$21,560.00**  │
├──────────────────────────────────────────────────────────────────────┼─────────────────┤
│ **LEVER 2: OPTIMISE (CP-SAT Sequencing & Capacity Fill)**            │                 │
│ • 22,000 technician clock hours × 1.5% sequencing productivity gain  │                 │
│ • 330 recovered hours × 70.0% commercial sell-through × $120/h       │ **$27,720.00**  │
├──────────────────────────────────────────────────────────────────────┼─────────────────┤
│ **LEVER 3: RECOVER (StallBreaker 2 Bay Release & Sourcing)**         │                 │
│ • 815 delayed ROs × 30.0% bay-blocking rate = 244 bay-blocking stalls│                 │
│ • 244 stalls × 70% improved × [(1.8 h freed × 70% × $120) +          │                 │
│   (0.6 promise slips avoided × $60) + $15 freight savings]           │ **$34,570.00**  │
├──────────────────────────────────────────────────────────────────────┼─────────────────┤
│ **TOTAL GROSS OPERATIONAL BENEFIT**                                  │ **$83,850.00**  │
│ Less: 20.0% Inter-Lever Overlap Discount                             │ -$16,770.00     │
│ Subtotal: Non-Overlapping Economic Value                             │ $67,080.00      │
│ Multiplied by: 75.0% Operational Realization Factor                  │ × 0.75          │
├──────────────────────────────────────────────────────────────────────┼─────────────────┤
│ **NET ANNUAL REALIZED ECONOMIC VALUE PER ROOFTOP**                   │ **$50,310.00**  │
└──────────────────────────────────────────────────────────────────────┴─────────────────┘
```

### Scenario Sensitivity Analysis:
- **Low Case ($13.1K Net / Rooftop):** 3.0% parts delay rate, 0.8% sequencing gain, 60% realization. Generates **~0.2 points of fixed absorption**.
- **Base Case ($50.3K Net / Rooftop):** 5.0% parts delay rate, 1.5% sequencing gain, 75% realization. Generates **~0.7 points of fixed absorption**.
- **High Case ($90.1K Net / Rooftop):** 6.5% parts delay rate, 2.0% sequencing gain, 80% realization. Generates **~1.3 points of fixed absorption**.

---

## 4. Dealer Economics, Pricing & Payback

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        DEALER RETURN ON INVESTMENT (ROI)                               │
├────────────────────────────────────────┬───────────────────────────────────────────────┤
│ METRIC                                 │ VALUE / DERIVATION                            │
├────────────────────────────────────────┼───────────────────────────────────────────────┤
│ Blended Annual SaaS Subscription Price │ **$10,800.00 / year** ($900.00 / month)       │
│ One-Time Dealer Onboarding & Training  │ $4,000.00 (Implementation cost)               │
│ Year 1 Net Dealer Profit (Base Case)   │ $50,310 - $10,800 - $4,000 = **$35,510.00**   │
│ **Dealer Value-to-Price Multiple**     │ **4.7× Return on Price** ($50.3k / $10.8k)    │
│ Share of Created Value Retained by Dealer│ **78.5% retained by dealership**             │
│ **Payback Period**                     │ **1.2 Months** (~37 operating days)           │
│ Renewal Retention Threshold            │ Clears 2.0× threshold ($21.6k minimum value)  │
└────────────────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 5. Seven-Year Financial Projections (Base Case)

Modeled trajectory assuming launch in early 2027 within the Tekion ecosystem:

| Year | Live Tekion Rooftops | Attach Rate | Paying Rooftops | Tekion ARR ($M) | Direct Costs ($M) | S&M + CS ($M) | Fixed Costs ($M) | Product EBIT ($M) | Dealer Value ($M) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2027** | 3,400 | 2.0% | **68** | **$0.37M** | $2.21M | $0.10M | $0.80M | **-$2.74M** | **$3.4M** |
| **2028** | 3,950 | 10.0%| **395** | **$2.50M** | $4.13M | $0.67M | $1.00M | **-$3.29M** | **$19.9M** |
| **2029** | 4,550 | 22.0%| **1,001** | **$7.54M** | $5.91M | $1.81M | $1.10M | **-$1.28M** | **$50.4M** |
| **2030** | 5,200 | 32.7%| **1,700** | **$14.59M** | $7.43M | $3.49M | $1.10M | **+$2.57M** | **$85.5M** |
| **2031** | 5,900 | 39.0%| **2,300** | **$21.60M** | $8.67M | $5.16M | $1.10M | **+$6.67M** | **$115.7M** |
| **2032** | 6,400 | 43.3%| **2,772** | **$27.10M** | $9.47M | $6.54M | $1.10M | **+$10.00M**| **$139.5M** |
| **2033** | 6,800 | 47.0%| **3,196** | **$32.20M** | $10.15M| $7.81M | $1.10M | **+$13.14M**| **$160.8M** |

**Capital at Risk:** Cumulative cash low point is **-$7.31M** reached in mid-2029 before turning sustainably cash-flow positive.

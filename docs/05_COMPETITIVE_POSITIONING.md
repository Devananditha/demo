# 05 — Competitive Positioning & Product Discipline

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 2.2, 2.3, 3, 12.8, 13) & Product Blueprint (Sections 1, 2, Appendix)  
**Host Ecosystem:** Tekion Automotive Retail Cloud (ARC) / Automotive Partner Cloud (APC)

---

## 1. What Tekion Publicly Offers Today

To maintain technical credibility before Tekion executives, engineers, and hackathon judges, ServiceYield AI acknowledges Tekion's existing, publicly described market capabilities in detail:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TEKION PUBLIC PRODUCT FOOTPRINT                                 │
├─────────────────────────────────────────────────┬──────────────────────────────────────┤
│ CAPABILITY / MODULE                             │ PUBLICLY DESCRIBED FUNCTIONALITY     │
├─────────────────────────────────────────────────┼──────────────────────────────────────┤
│ **Tekion Service AI / Service Scheduler AI**     │ AI-driven service appointment booking│
│ [PUBLIC: Tekion Blog, Product Portfolio]        │ based on dealership availability,    │
│                                                 │ customer preferences, and shop load. │
├─────────────────────────────────────────────────┼──────────────────────────────────────┤
│ **Technician AI & Mobile Workflows**            │ Mobile technician interface for RO   │
│ [PUBLIC: Tekion NADA Announcements]             │ clocking, multi-point inspection     │
│                                                 │ (MPI), video capture, and flags.     │
├─────────────────────────────────────────────────┼──────────────────────────────────────┤
│ **Automotive Partner Cloud (APC)**              │ Open API and partner integration hub │
│ [PUBLIC: Tekion APC Marketplace]                │ supporting 6,125+ partner app        │
│                                                 │ installs across 3,000+ live dealers. │
├─────────────────────────────────────────────────┼──────────────────────────────────────┤
│ **Parts & Inventory Integrations**              │ Electronic parts catalogs, vendor PO │
│ [PUBLIC: Tekion Fixed Ops Solutions]            │ dispatch, and inventory tracking.    │
├─────────────────────────────────────────────────┼──────────────────────────────────────┤
│ **T1 Orchestration**                            │ Internal dealership workflow routing │
│ [PUBLIC: Tekion Platform Updates]               │ and process automation.              │
└─────────────────────────────────────────────────┴──────────────────────────────────────┘
```

**Discipline Rule:** Never present these existing capabilities as "problems nobody has solved" or claim that Tekion lacks workflow automation or technician tools.

---

## 2. The Product Gap Hypothesis

While Tekion provides a modern, cloud-native dealership platform, public documentation and fixed-ops industry workflows reveal a clear structural white space:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              THE STRUCTURAL WORKFLOW GAP                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   TRADITIONAL SILO 1: APPOINTMENT SCHEDULING                                           │
│   • Focus: Customer intake & booking slots                                             │
│   • Limitation: Schedules appointments without real-time parts supply chain guarantees │
│                                                                                        │
│   TRADITIONAL SILO 2: PARTS PROCUREMENT                                                │
│   • Focus: Lowest invoice purchase cost & OEM catalog ordering                         │
│   • Limitation: Blind to lift/bay bottlenecks and customer promise lateness penalties  │
│                                                                                        │
│   TRADITIONAL SILO 3: WORKSHOP DISPATCH                                                │
│   • Focus: Assigning tickets to available technicians                                  │
│   • Limitation: Scrambles reactively when an immobilized vehicle stalls on a lift      │
│                                                                                        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│   ★ THE SERVICEYIELD AI SOLUTION: THE JOINT ECONOMIC DECISION LOOP                     │
│   Couples all three silos in real time:                                                │
│   [Predict Readiness] ──> [Optimise Allocation] ──> [Disruption Recovery]             │
│   Linked by the shared Bay-Hour Shadow Price ($\nu_b(t)$) and Hard Constraints (C1–C7) │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Exact Differentiator Hypothesis:
- Schedulers book based on expected capacity;
- Parts systems buy based on unit price;
- Dispatchers allocate based on available bodies.
- **ServiceYield AI is the joint economic decision engine** that unifies all three: it calculates whether an expedited parts surcharge ($+\$37$) is economically superior because it avoids stalling a critical bay ($+\$220$) and protects a customer delivery promise ($+\$55$).

---

## 3. Product Positioning: Advisory Extension, Not DMS Replacement

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   TEKION ARC / APC                                     │
│       System of Record: RO Accounting, Customer CRM, Payroll, Invoicing & Parts        │
└───────────────────────────────────────────▲────────────────────────────────────────────┘
                                            │
                        Advisory Bidirectional Telemetry (API / Webhooks)
                                            │
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                                   SERVICEYIELD AI                                      │
│                 Advisory Economic Decision & Optimization Co-Pilot                     │
│      [Predict Readiness]  ──  [CP-SAT Optimiser]  ──  [StallBreaker 2 Recovery]        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

ServiceYield AI is engineered explicitly to complement Tekion:
1. **Advisory Decision Support:** ServiceYield generates verified, explainable recommendations. It leaves final execution authority with the dealership Service Manager.
2. **Host Fail-Open Resilience:** If ServiceYield is offline or unreachable, Tekion ARC continues its native dispatch and scheduling without interruption. Dealership operations never halt.
3. **Ecosystem Value Creation:** Positioned as an elite high-margin add-on module for Tekion ARC or a premium partner application on the Automotive Partner Cloud (APC).

---

## 4. Boundary Discipline & Prohibited Claims

Every team member, slide deck, demo script, and documentation file must strictly adhere to the following claim boundaries:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              PROHIBITED CLAIMS CHECKLIST                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ ❌ DO NOT CLAIM: "No dealership software has scheduling."                              │
│    FACT: Schedulers exist across CDK, Reynolds & Reynolds, and Tekion.                 │
│                                                                                        │
│ ❌ DO NOT CLAIM: "Tekion has no technician intelligence or AI."                         │
│    FACT: Tekion has publicized significant AI capabilities and technician mobile tools.│
│                                                                                        │
│ ❌ DO NOT CLAIM: "ServiceYield is the first-ever dealership optimizer."                │
│    FACT: Linear programming and heuristics have historical academic precedents.        │
│                                                                                        │
│ ❌ DO NOT CLAIM: "Every dealership loses a fixed 20% of bay capacity."                 │
│    FACT: Parts delay rates and bay blockage vary and must be measured in shadow mode.  │
│                                                                                        │
│ ❌ DO NOT CLAIM: "Our financial model represents measured dealership ROI."             │
│    FACT: All ROI figures are model projections based on stated industry assumptions.   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. How to Pitch to a Dealership Service Manager

A Service Manager does not care about constraint programming, mixed-integer programming, or dual shadow variables. They care about **cars, customers, bays, and gross profit**.

### The Jargon-Free Manager Pitch:
> *"Marcus, when a car is torn down on your heavy diagnostic lift and the part doesn't show up, you lose two things: that customer's trust and that bay's earning power.*  
>  
> *Today, your parts guy orders the cheapest part to save $30 on an invoice, while your lift sits dead for four hours, costing you $400 in lost labor and blowing your 4:30 PM delivery promise.*  
>  
> *ServiceYield AI fixes that. It watches your parts orders, flags delays before the car ever gets torn down, and when a delay does happen, it shows you the exact trade-off: 'Pay $37 for hotshot delivery, free your diagnostic bay two hours earlier, save RO #104, and get RO #106 out on time.'*  
>  
> *You review the plan, click Approve, and your shop stays on track."*

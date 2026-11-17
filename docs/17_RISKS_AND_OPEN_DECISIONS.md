# 17 — Risk Management, Legal Concerns & Open Decisions Register

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 14, 16) & Product Blueprint (Sections 14, 15)  
**Standard:** Enterprise Risk Register & Governance Log (Phase 0)

---

## 1. Comprehensive Risk Matrix & Mitigation Controls

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM RISK MATRIX & CONTROLS                             │
├───────────────┬───────────────────────────┬──────┬─────────────────────────────────────┤
│ RISK DOMAIN   │ OPERATIONAL HAZARD        │ SEV  │ ARCHITECTURAL CONTROL / MITIGATION  │
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **Stale State**│ Committing plan after real│ HIGH │ Optimistic Concurrency Control (OCC)│
│               │ world shop state changed. │      │ on SHA-256 snapshot hash. Rejects.  │
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **Infeasible**│ Solver generates plan that│ CRIT │ L4 Independent Sweep-Line Verifier; │
│ **Plan**      │ violates real-world lift. │      │ mutation testing with 100% kill rate│
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **Missing**   │ Unknown part ETA leads to │ MED  │ Strict `UNKNOWN` readiness state;   │
│ **Data**      │ false start on vehicle.   │      │ system fails closed; never guesses. │
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **Solver**    │ CP-SAT runtime exceeds    │ MED  │ Discrete 2.5s timeout; immediate    │
│ **Tails**     │ live API budget.          │      │ fallback to T1 Earliest-Fit (<2ms). │
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **AI Hallu-** │ LLM invents constraint or │ HIGH │ LLM strictly isolated to narrative; │
│ **cination**  │ approves purchase order.  │      │ zero authority over math or commit. │
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **Labor &**   │ Flat-rate dispatch bias   │ HIGH │ Rolling 2-week ±15% fairness band;  │
│ **Wage Law**  │ triggers dealer lawsuit.  │      │ lunch break checks; no public ranks.│
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **Antitrust** │ Sharing dealer parts data │ HIGH │ Regional aggregation; zero price    │
│ **Data Risk** │ creates price-fixing risk.│      │ features shared across rooftop orgs.│
├───────────────┼───────────────────────────┼──────┼─────────────────────────────────────┤
│ **Host Outage**| ServiceYield crash halts │ CRIT │ Advisory overlay only; host fail-   │
│               │ dealership operations.    │      │ open allows native DMS to continue. │
└───────────────┴───────────────────────────┴──────┴─────────────────────────────────────┘
```

---

## 2. Regulatory, Legal & Employment Compliance

Dealership operations are governed by dense statutory frameworks. ServiceYield AI incorporates **Compliance-by-Design**:

### 2.1 Employment & Wage Law (FLSA & State Labor Codes)
- **The Issue:** Many dealership technicians are compensated on a "flat-rate" piece-rate system under 29 U.S.C. §207(i). If an automated algorithm systematically routes high-flagged warranty jobs to favored technicians while assigning difficult, low-paying diagnostic tickets to others, the dealership faces severe collective wage discrimination lawsuits (e.g., under California Labor Code §226.2).
- **The Built-In Control:** The optimiser enforces a **rolling two-week flat-rate fairness band** (default: within $\pm 15\%$ of peer group median). Mandatory meal windows are non-negotiable hard constraints ($C6$). The system generates **zero public technician performance rankings**.

### 2.2 Consumer Protection & Repair Authorisations
- **The Issue:** State motor vehicle repair acts require written customer authorizations before work commences and prohibit exceeding estimate limits without customer consent.
- **The Built-In Control:** ServiceYield leaves the DMS as the sole system of record for customer authorizations ($C7$). A delivery promise change is annotated as "provisional" until the service advisor logs customer reconfirmation.

### 2.3 Product Liability & Safety Lines
- **The Issue:** High-voltage EV disconnects, brake system bleeds, and ADAS calibrations are safety-critical. Rushing or reordering them creates catastrophic physical liability.
- **The Built-In Control:** Safety lines are non-negotiable. Operation DAG constraints ($C3$) cannot be relaxed or reordered by the solver. Vehicle lift movements require explicit physical verification ($C5$).

---

## 3. Product Kill Criteria & Go / No-Go Thresholds

The project establishes explicit, unemotional **kill criteria** to prevent sunk-cost fallacy during development:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FORMAL PROJECT KILL CRITERIA                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Zero Feasibility Breach Tolerance:                                                  │
│    If the L4 Independent Verifier fails to catch 100% of injected mutation faults,     │
│    the engine cannot be approved for live pilot staging.                               │
│                                                                                        │
│ 2. S-MATH-01 Reproduction Gate:                                                        │
│    If the Phase 1 greenfield solver fails to reproduce the 99 vs 33 weighted tick      │
│    reduction and the +$238 net economic gain within ±$0.50, the optimization model is  │
│    halted for mathematical re-formulation.                                             │
│                                                                                        │
│ 3. Benchmark Superiority Gate:                                                         │
│    If empirical testing across Families F1 and F3 reveals that P3 does not beat A2+    │
│    with statistically significant confidence intervals, the project immediately drops │
│    the "algorithmic superiority" claim and pivots to "execution safety and audit".     │
│                                                                                        │
│ 4. Tekion Host Compatibility Gate:                                                     │
│    If testing shows that an advisory crash ever disrupts native Tekion dispatch, the   │
│    system fails the "Host Fail-Open" requirement and cannot be submitted.              │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Open Decisions Register (Requiring Human Approval)

The following items are documented as open decisions and flagged for human sign-off:

| Decision ID | Topic / Scope | Option A | Option B | Recommended Decision | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEC-01** | Canonical Shadow Price Internal Unit | Store as USD per Bay-Minute ($\$2.00/\text{min}$) | Store as USD per Bay-Hour ($\$120.00/\text{hr}$) | **Option B (USD per Bay-Hour)** as canonical storage; convert to ticks at runtime. | `[FLAGGED FOR APPROVAL]` |
| **DEC-02** | Initial Hackathon UI Presentation Focus | Deep CP-SAT parameter tuning panel | Frictionless Service Manager operational replay | **Option B (Frictionless Manager Replay)**; hide CP-SAT math in technical drawer. | `[APPROVED]` |
| **DEC-03** | Machine Learning Scope for MVP | Build complex LightGBM & Conformal models | Deterministic Layer 1 Empirical Bayes Baseline | **Option B (Layer 1 Baseline first)**; defer LightGBM to Tier B roadmap. | `[APPROVED]` |
| **DEC-04** | Pilot Rooftop Selection | Partner directly with large multi-franchise group | Partner with single mid-size metro dealership | **Option B (Single mid-size store first)** to validate 5% parts delay rate in shadow mode. | `[OPEN / PENDING]` |
| **DEC-05** | Production APC Webhook vs Polling | Real-time bidirectional webhooks | Polling API every 60 seconds | **Option A (Webhooks)** with exponential backoff polling fallback. | `[PENDING TEKION APC]` |

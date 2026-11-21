# ServiceYield AI — Limitations & Reality Check

**Document Reference:** `docs/24_LIMITATIONS_AND_REALITY_CHECK.md`  
**Review Perspective:** Skeptical University Project Evaluator, Industrial Operations Auditor  
**Purpose:** Honest, rigorous appraisal of theoretical vs operational real-world boundaries  

---

## 1. Clear Demarcation: Synthetic Research Model vs Dealership Realities

ServiceYield AI is an academic and algorithmic prototype built upon the canonical **S-MATH-01** specification. To maintain intellectual integrity, the following boundaries must be clearly understood:

```
+----------------------------------------------------------------------------------------------------+
| SYNTHETIC SIMULATION MODEL (IN SCOPE)       | REAL DEALERSHIP OPERATIONS (OUT OF SCOPE / FUTURE)   |
+---------------------------------------------+------------------------------------------------------+
| Discrete 5-minute ticks [0, 288]            | Continuous, asynchronous task progress & interrupts  |
| Deterministic flat-rate durations           | Stochastic labor variance, rusted bolts, comebacks   |
| Synchronous supplier quotes & fixed freight | Unreliable supplier APIs, courier routing delays     |
| Certified static technician skill sets      | Apprentice mentoring, split labor, fatigue curves    |
| Single-rooftop localized scope              | Multi-store inventory pooling, warranty approvals    |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Technical and Operational Limitations

### 2.1 Discrete Time Tick Quantization (5-Minute Intervals)
- **Model Assumption:** The day is divided into discrete ticks $t \in [0, 288]$ where each tick equals 5 minutes.
- **Operational Reality:** Real mechanical repairs do not start or stop on exact 5-minute boundaries. Liquid spills, tool changeovers, and parts unpacking happen continuously.
- **Impact:** Sub-5-minute scheduling precision is not modeled; however, 5-minute discretization is industry standard for CP-SAT tractability.

### 2.2 OEM Flat-Rate vs Actual Clock Hours
- **Model Assumption:** Task durations are assumed to follow deterministic flat-rate tick estimates ($d_i$).
- **Operational Reality:** Technician proficiency varies significantly. A 2.0-hour flat rate job may take a Master Tech 1.2 hours and a junior tech 2.8 hours. Unforeseen mechanical complications (e.g., seized fasteners, stripped threads) introduce right-tail duration overruns.
- **Mitigation in ServiceYield AI:** Layer 1 Predict models lead-time risk quantiles, but live in-bay wrench-time telemetry remains future work.

### 2.3 Supplier Quote Availability and Delivery Reliability
- **Model Assumption:** Hotshot courier deliveries arrive precisely at quoted ETA ticks ($U_p = \text{ETA} + \text{Inspection}$).
- **Operational Reality:** Traffic congestion, wrong parts received in box, or damaged packaging during transit can invalidate expedited delivery promises.
- **Mitigation in ServiceYield AI:** Receiving inspection time (10–20 min) is explicitly modeled as a mandatory buffer, and courier transit risk is flagged as an `unresolved_risk` in the Replay explainability payload.

### 2.4 Human Manager Overrides & Institutional Dynamics
- **Model Assumption:** Service Managers approve the mathematically optimal recovery plan based solely on net economic yield ($Z$).
- **Operational Reality:** Dealership service managers often prioritize long-term customer relationships (VIP customers, fleet accounts) over immediate marginal dollar contribution.
- **Mitigation in ServiceYield AI:** StallBreaker is designed as an advisory decision workbench that presents transparent trade-offs without performing autonomous non-consensual dispatch. Manager authorization is strictly required.

---

## 3. Academic Integrity Certifications

1. **Zero Manufactured Advantage:** In null-control benchmarks where no disruption occurred, StallBreaker demonstrated $\Delta Z = \$0.00$ with 0 plan churn. No synthetic lift is claimed where none exists.
2. **Hard Constraint Inviolability:** Hard constraints C1–C7 are never relaxed to achieve higher financial objectives. A plan that violates a physical lift weight limit or shifts boundary is declared infeasible.
3. **Traceability:** Every claimed metric in the evaluation dashboard is backed by live, reproducible backend Python tests and JSON audit records.

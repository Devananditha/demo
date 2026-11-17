# 03 — Product Functional & Non-Functional Requirements

**Project:** ServiceYield AI  
**Authoritative Reference:** Product Blueprint (Sections 5, 6, 7, 8) & Technical Report (Sections 5, 6, 7, 8)  
**Status:** Frozen Requirements Baseline (Phase 0)

---

## 1. System Functional Decomposition

ServiceYield AI consists of four primary functional engines (Predict, Optimise, Recover, Verifier) orchestrated through an immutable, versioned state pipeline:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 CANONICAL DATA ADAPTER (L0)                            │
│           Ingests ROs, Parts Telemetry, Technician Shifts, Bay Telemetry & Events      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              VERSIONED SHOP STATE STORE (L1)                           │
│               Immutable Snapshots (snapshot_hash), Read-Sets & Change Log              │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              ELIGIBILITY & COMPATIBILITY GATEWAY (L2)                  │
│       Part Fitment (ACES/PIES), Supersession, ATP Expiry, Vehicle Physical State       │
└───────┬───────────────────────────────────┼────────────────────────────────────┬───────┘
        │                                   │                                    │
        ▼                                   ▼                                    ▼
┌───────────────────────┐   ┌───────────────────────┐    ┌───────────────────────┐
│     PREDICT (L3.1)    │   │     OPTIMISE (L3.2)   │    │     RECOVER (L3.3)    │
│  Predictive Readiness │   │ Economic Allocation   │    │ Disruption Recovery   │
│  4 States & Intervals │   │ CP-SAT + $\nu_b(t)$   │    │ Multi-source Search   │
└───────┬───────────────┘   └───────┬───────────────┘    └───────┬───────────────┘
        │                           │                            │
        └───────────────────────────┼────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              INDEPENDENT VERIFIER (L4)                                 │
│        Sweep-Line Occupancy Oracle: Validates C1–C7; Sole Feasibility Certifier        │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              AUTHORITY & COMMIT GATE (L5)                              │
│         Manager Approval UI, OCC State Revalidation, Outbox & Audit Logging            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Module 1: Predict (Predictive Service Readiness)

### 2.1 Functional Objective
Determine whether every active Repair Order (RO) can realistically proceed within its planned window without causing a workshop blockage.

### 2.2 Four Mandatory Readiness States
Predict classifies each RO into exactly one non-overlapping operational state:

| State | Operational Definition | Actionable Engine Behavior |
| :--- | :--- | :--- |
| **`READY`** | All hard requirements (parts in stock/inspected, technician scheduled, bay open, vehicle rollable) are verified satisfied. | Eligible for immediate allocation and dispatch. |
| **`AT_RISK`** | A soft constraint, supplier lead-time variance, or tight slack threatens the latest feasible start ($P(\text{delay}) > \tau_{\text{raise}}$). | Triggers proactive manager risk alert and expedited parts tracking; remains eligible with warning. |
| **`BLOCKED`** | A known hard operational constraint cannot be satisfied (part backordered, required skill unavailable, vehicle immobilized). | Solver strictly prohibited from scheduling mechanical work until gate clears. |
| **`UNKNOWN`** | Telemetry is missing, stale, or incomplete (e.g. unentered teardown diagnosis). | Fails closed: marked unready; prompts manual advisor/manager review; never assumes ready. |

### 2.3 Layered Estimation Architecture
To balance immediate hackathon executability with long-term MLOps rigor, Predict implements three distinct layers:
1. **Layer 1 (Deterministic Empirical Baseline — Mandatory MVP):**
   - Empirical-Bayes quantiles computed from historical supplier and operation performance.
   - P² quantile estimators or t-digest sketches for streaming quantiles ($p_{10}, p_{50}, p_{90}$).
   - Rule-based slack analysis: $\text{Slack} = \text{Latest Feasible Start} - \text{Usable-Ready Time}$. If $\text{Slack} < 0 \implies \text{BLOCKED}$; if $\text{Slack} < 30\text{ min} \implies \text{AT\_RISK}$.
   - Guarantees 100% availability even on cold starts.
2. **Layer 2 (Covariate-Aware Regression — Tier B Enhancement):**
   - LightGBM quantile regression (quantiles $\alpha \in \{0.05, 0.50, 0.95\}$) conditioned on supplier ID, distance band, weekday, part category, and recent residual CUSUM.
   - Features strictly exclude post-outcome leakage. Monotone rearrangement applied to prevent quantile crossing.
3. **Layer 3 (Conformal Calibration — Tier B Enhancement):**
   - Conformalized quantile regression with adaptive online updates:
     $$\alpha_{t+1} = \alpha_t + \gamma (\alpha - \text{err}_t)$$
   - Produces mathematically valid coverage intervals regardless of distribution drift.
   - If coverage drifts beyond 5 percentage points, triggers the `DEGRADED` calibration flag and automatically widens intervals to Layer 1 bounds.

### 2.4 Required Output Schema
Every prediction record must contain:
```json
{
  "ro_id": "RO-104",
  "snapshot_hash": "a8f3b9c1d...",
  "state": "AT_RISK",
  "reasons": ["SUPPLIER_ETA_TIGHT_SLACK", "SPECIALIST_BAY_REQUIRED"],
  "p_delay": 0.38,
  "usable_ready_ticks": {
    "p10": 164,
    "p50": 172,
    "p90": 188
  },
  "calibration_status": "CALIBRATED_LIGHT",
  "data_freshness_seconds": 45,
  "computed_at": "2026-11-18T13:15:00Z"
}
```

---

## 3. Module 2: Optimise (Economic Service Yield Optimiser)

### 3.1 Functional Objective
Generate the globally optimal or best-feasible assignment of ROs to technicians, bays, parts, and discrete time slots to maximize dealership economic contribution while honoring all customer delivery commitments and hard operational rules.

### 3.2 Solving Pipeline & Multi-Tier Fallback

```
   [T0: Eligibility Pre-Checks]
   Validates schema, certifications, fitment, and physical gates. Fails impossible ROs immediately.
                 │
                 ▼
   [T1: Constructive Priority-Rule Scheduler]
   Deterministic earliest-fit bitset dispatcher (< 2 ms). Instant preview & infallible fallback.
                 │
                 ▼
   [T2: OR-Tools CP-SAT Exact Engine]
   Warm-started by T1. Discrete 5-min ticks ($H=288$). 2.5s time budget, 4 workers, deterministic seed.
                 │
                 ▼
   [T3: Large Neighbourhood Search (LNS)]
   Destroy-and-repair heuristic over conflict graph. (Tier C enhancement for large rooftops).
                 │
                 ▼
   [T4: CVaR Scenario Stress Evaluator]
   Evaluates tail-risk over correlated supplier delay scenarios. Shortlists resilient plans.
                 │
                 ▼
   [L4: Independent Verifier Check]
   MANDATORY GATE: Independent occupancy sweep-line audit. Only verifier can tag "FEASIBLE".
```

### 3.3 Solver Status Categorisation
The engine must explicitly distinguish between solver outcomes. An unproven solution must never be mislabeled:
- `OPTIMAL`: Proven mathematical global optimum within CP-SAT optimality tolerance ($\text{gap} = 0.0\%$).
- `FEASIBLE`: Valid, constraint-satisfying plan found, but solve stopped by time limit ($\text{gap} > 0.0\%$). Must display remaining gap percentage.
- `INFEASIBLE`: No solution exists satisfying constraints C1–C7. Triggers constraint relaxation advisor.
- `UNKNOWN`: Solver failed or timed out without finding an initial feasible incumbent. System automatically reverts to the verified T1 constructive schedule.

---

## 4. Module 3: Recover (ServiceYield Recovery Engine)

### 4.1 Functional Objective
When an operational disruption strikes an active schedule, automatically identify affected dependencies, search multi-echelon sourcing alternatives, re-optimize the global schedule, and present a mathematically verified recovery plan to the Service Manager.

### 4.2 Recovery Workflow Execution Sequence
1. **Disruption Ingestion:** Ingests trigger event (parts delivery delay, supplier cancellation, technician illness, bay hydraulic failure, duration overrun).
2. **Blast-Radius Identification:** Traces direct and downstream dependencies across the active schedule DAG.
3. **Physical State Inspection:** Queries vehicle physical state ($C5$). If vehicle is `IMMOBILIZED_ON_LIFT`, it cannot be displaced to a parking stall.
4. **Sourcing Candidate Search:** Evaluates multi-source tree (OEM distributor, sister stores, aftermarket suppliers, hotshot couriers).
   - Implements two-layer admissible branch-and-bound pruning: Jackson’s Preemptive Schedule on parallel bays + infinite-capacity critical path bound.
5. **Full Shop Rescheduling:** Recalculates the complete workshop schedule for each surviving candidate using the unified economic objective.
6. **Shadow Price Evaluation:** Uses $\nu_b(t)$ to quantify the dollar value of earlier bay release versus incremental courier expense.
7. **Pareto Candidate Ranking:** Ranks options along the Pareto frontier (Weighted Lateness, Sourcing Cost, Bay-Blocked Hours, Schedule Churn).
8. **Independent Verification:** Submits shortlisted proposal to L4 Verifier.
9. **Manager Approval Gate:** Displays side-by-side trade-off with clear reason codes.
10. **Fresh-State Revalidation:** Re-verifies state hash before any simulated commit.

---

## 5. Module 4: Independent Verifier (L4)

### 5.1 Architecture & Separation
- **Code Path Isolation:** The Verifier is an entirely independent module written in pure Python. It imports **no** constraint-builder code, variables, or solver abstractions from OR-Tools CP-SAT or the T1 dispatcher.
- **Verification Algorithm:** Implements an $O(N \log N)$ sweep-line interval occupancy oracle:
  - Sweeps discrete event intervals across each bay to prove $\sum \text{Occupancy}_b(t) \le 1$.
  - Sweeps technician time to prove $\sum \text{Work}_k(t) \le 1$ and verifies mandatory lunch breaks.
  - Verifies precedence: $S_{o2} \ge C_{o1}$ for all $(o1, o2) \in \text{Precedences}$.
  - Verifies parts availability: $S_o \ge \text{usable\_ready}(p)$ for all required parts.
  - Verifies vehicle state: vehicle in lift cannot be relocated without rollable confirmation.
- **Sole Feasibility Authority:** A plan is marked `FEASIBLE` if and only if the L4 Verifier returns a passing verdict.

---

## 6. Non-Functional Requirements (NFRs)

| NFR Domain | Requirement / Metric | Target Value | Verification Method |
| :--- | :--- | :--- | :--- |
| **Solving Latency** | End-to-end plan generation (T2 CP-SAT) | **p95 < 2.5s; p99 < 5.0s** | Automated benchmark load test. |
| **T1 Heuristic Latency** | Priority-rule preview & fallback | **< 10 milliseconds** | High-resolution CPU timer. |
| **Advisory Availability** | Prediction and scheduling API uptime | **99.9% availability** | Health check monitoring. |
| **Commit Availability** | State commit and outbox pipeline | **99.95% availability** | Multi-AZ database heartbeat. |
| **Concurrency Control** | Optimistic Concurrency Control (OCC) | Read-set SHA-256 validation | Concurrent modification unit tests. |
| **Determinism** | Solver and heuristic reproducibility | **100% bit-exact plans** given identical seed and snapshot | Paired execution unit tests. |
| **Host Fail-Open** | Host DMS business continuity | **Zero interruption** to host dispatch on engine crash | Chaos engineering network partition test. |
| **LLM-Disabled Parity**| Core engine functionality without LLM | **100% mathematical parity** with LLM offline | Pytest suite running with `LLM_DISABLED=true`. |
| **Data Privacy** | Regulatory PII and dealer security | **Zero real PII or VINs**; synthetic-only demo | Automated regex compliance linting. |

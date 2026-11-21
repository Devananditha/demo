# ServiceYield AI — StallBreaker & Benchmark Architecture

**Document Reference:** `docs/21_STALLBREAKER_AND_BENCHMARK_ARCHITECTURE.md`  
**System Layer:** Event-Driven Recovery Engine & Multi-Tier Optimization Architecture  
**Author:** Principal AI Systems Architect & Senior Optimization Engineer  

---

## 1. System Architecture Overview

ServiceYield AI integrates an event-driven telemetry pipeline with an exact mathematical constraint solver to deliver autonomous shop-floor disruption detection, economic re-optimization, and explainable decision playback.

```
                           +----------------------------------+
                           |   DMS / IoT Telemetry Events     |
                           |   (PARTS_ETA_CHANGED, RO_OPENED) |
                           +-----------------+----------------+
                                             |
                                             v
                           +----------------------------------+
                           |    HMAC-SHA256 Security Gate     |
                           |   & Append-Only Event Store      |
                           +-----------------+----------------+
                                             |
                                             v
                           +----------------------------------+
                           |  StallBreaker Disruption Engine  |
                           |  - Graph Dependency Analysis     |
                           |  - Blast Radius & Lift Contention|
                           +-----------------+----------------+
                                             |
                                             v
        +------------------------------------+------------------------------------+
        |                                                                         |
        v                                                                         v
+-------------------------------+                                 +-------------------------------+
|   Two-Layer Sourcing Search   |                                 |   Unmitigated Baseline Solve  |
|   - Multi-supplier evaluation |                                 |   - Discrete CP-SAT Solver    |
|   - Branch-and-bound pruning  |                                 |   - Objective Z*(Baseline)    |
+---------------+---------------+                                 +---------------+---------------+
                |                                                                 |
                +--------------------------------+--------------------------------+
                                                 |
                                                 v
                               +----------------------------------+
                               | Full-Shop Candidate Re-optimise  |
                               | - Bay-hour shadow price nu_b(t)  |
                               | - Delta Z = Z(Cand) - Z(Base)    |
                               +-----------------+----------------+
                                                 |
                                                 v
                               +----------------------------------+
                               |     Inviolable L4 Dual Gate      |
                               | - Sweep-Line Oracle O(N log N)   |
                               | - Supplemental Audit Oracle      |
                               +-----------------+----------------+
                                                 |
                                                 v
                               +----------------------------------+
                               |  OCC Manager Approval Gateway   |
                               | - Cryptographic Hash Recheck     |
                               | - Transactional Outbox Dispatch  |
                               +-----------------+----------------+
                                                 |
                                                 v
                               +----------------------------------+
                               |     Decision Replay & Diffs      |
                               | - Objective Decomposition ($)    |
                               | - Rejection Reason Audit Trails  |
                               +----------------------------------+
```

---

## 2. Core Modules & Responsibilities

### 2.1 Append-Only Event Store & Security (`app/stallbreaker/event_store.py`, `security.py`)
- **HMAC-SHA256 Signature Verification:** Ingested event payloads can be validated against configured secrets using constant-time comparisons (`hmac.compare_digest`) to prevent timing side-channel attacks.
- **Idempotency & Duplicate Rejection:** Events with identical IDs and identical payloads return `is_duplicate: True` without mutating state. Tampered payloads re-submitted under existing event IDs raise hard concurrency conflicts.
- **Thread-Safe Memory & Persistence:** Synchronized via reentrant mutex locks ensuring thread safety under concurrent high-throughput ingestion.

### 2.2 Disruption Detection & Dependency Graph (`app/stallbreaker/engine.py`)
- Ingests events including `PARTS_ETA_CHANGED`, `PART_UNAVAILABLE`, `TECHNICIAN_UNAVAILABLE`, `BAY_RESERVATION_CHANGED`, `OPERATION_COMPLETED`.
- Evaluates whether active schedules are invalidated by checking task start ticks against new part usable times ($S_i < U_p$) or technician shifts.
- Traces the vehicle dependency graph to compute the **Blast Radius**:
  - Identifies immobilized vehicles stalled on specialized lifts (e.g. RO-104 on BAY-01).
  - Identifies downstream queued vehicles blocked from entering the lift (e.g. RO-106).

### 2.3 Sourcing Search & Branch-and-Bound (`app/recover/search.py`)
- Evaluates available supplier offers across lead time, freight cost, and fitment compatibility.
- Applies **Two-Layer Branch-and-Bound**:
  - **Upper Bound Pruning:** If a candidate's maximum possible gross contribution minus freight surcharge cannot exceed the baseline objective ($UB_c \le Z_{\text{baseline}}$), the candidate is pruned before invoking the solver.
  - **Dominance Pruning:** Offers arriving strictly after a faster, cheaper alternative are pruned.

### 2.4 Discrete Optimization & Shadow Pricing (`app/optimise/cpsat_solver.py`, `shadow_price.py`)
- **OR-Tools CP-SAT Solver:** Solves discrete interval scheduling across horizon $[0, 288]$ (5-minute ticks).
- **Objective Maximization:**
  $$\max Z = \sum_i M_i \cdot z_i - \sum_r w_r \cdot \max(0, C_r - D_r) \cdot \lambda_{\text{late}} - \sum_{\text{occ}} \text{IdleTicks} \cdot \lambda_{\text{block}} - \text{Freight} - \text{ChurnCost}$$
- **Bay-Hour Shadow Price $\nu_b(t)$:**
  Computes the marginal economic value of releasing a service bay over interval $\Delta t$:
  $$\nu_b(t) = \frac{Z^*(C \cup \{(b, t)\}) - Z^*(C \setminus \{(b, t)\})}{\Delta t} \quad [\$/\text{bay-hour}]$$

### 2.5 Dual Verification Gate (`app/verifier/sweep_oracle.py`, `app/optimise/supplemental_audit.py`)
- **L4 Sweep-Line Oracle:** Independent $O(N \log N)$ event sweep certifying interval non-overlap (technicians, bays, vehicle exclusivity), precedence topological order, technician breaks, and shift limits. Shares zero solver or heuristic code.
- **Supplemental Audit Oracle:** Audits vehicle physical movements, staging buffer delays, parts fitment, and customer authorizations.

### 2.6 OCC Approval Gateway & Outbox Dispatch (`app/stallbreaker/approval.py`)
- **Optimistic Concurrency Control (OCC):** Prevents stale manager approvals. Validates that `expected_snapshot_hash == current_snapshot_hash`. If state mutated between recommendation and approval, returns `ABORTED_STALE_STATE` with `OCC_VERSION_MISMATCH`.
- **Transactional Outbox:** Stages domain events (`DISRUPTION_DETECTED`, `RECOVERY_APPROVED`, `OUTBOX_ORDER_DISPATCHED`) for asynchronous transmission to DMS and parts ordering systems.

### 2.7 Decision Replay Engine (`app/replay/engine.py`)
- Computes mathematical deltas between baseline and recovered plans:
  - $\Delta \text{Gross Contribution}$, $\Delta \text{Net Objective}$, $\Delta \text{Lateness}$, $\Delta \text{Bay Utilisation}$, $\Delta \text{Avoidable Idle Minutes}$.
- Generates natural-language explainability and itemizes exact technical reasons for rejecting alternative supplier offers.

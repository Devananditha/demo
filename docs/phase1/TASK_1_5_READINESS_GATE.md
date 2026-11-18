# TASK 1.5 READINESS CERTIFICATION GATE
## Formal Engineering Readiness Audit for Phase 1 — Task 1.5 (Recover Engine)

**Project:** ServiceYield AI — Fixed Operations Decision Intelligence  
**Evaluator:** Principal Software Architect, Operations Research Engineer & Auditor  
**Date:** November 19, 2026  
**Active Branch:** `phase1/task-1-4-audit-fix-2`  
**Base Commit:** `044b5100155b36f4af04d781b8c61b6570db0589`  
**Test Suite Status:** 156 / 156 PASSED (100%)  
**Mutation Kill Rate:** 7 / 7 MUT-01..07 KILLED (100%)  
**Test Coverage:** 89% overall (>80% across all modules, 100% models, 99% evidence)  
**Execution Latency:** T1 Scheduler p50 $= 0.229\text{ ms}$ (limit: $< 10\text{ ms}$); T2 CP-SAT p50 $= 15.868\text{ ms}$  

---

## 1. Formal Readiness Declaration

```markdown
READY_FOR_TASK_1_5 = false
```

### Executive Justification:
The software engineering and mathematical implementation of **Task 1.4 (Optimise Engine & Dual Verification)** is fully complete, hardened, verified, and certified:
- Replaced boolean lists with true arbitrary-precision integer bitmasks.
- Implemented dual-certification architecture (interval physics via L4 Sweep Line Oracle + domain evidence via Supplemental Audit Oracle).
- Eliminated all synthetic fallback fabrications (failing closed to unverified customer authorization, unverified parts fitment, missing technician fairness history, and missing WIP progress).
- Pre-allocated active WIP technician and bay intervals.
- Enforced vehicle physical movement delays ($\Delta t_{\text{move}} = 2\text{ ticks}$) and locked immobilized vehicles to their assigned bay.
- Certified signed discrete marginal shadow prices with multi-bay valuation surface support.

**HOWEVER**, the underlying canonical benchmark specification **S-MATH-01 contains unresolved physical and mathematical contradictions** between narrative documentation and constraint-enforced execution (as detailed in `docs/phase1/S_MATH_01_MATHEMATICAL_AUDIT.md`):
1. In the unmitigated baseline, RO-104 finishes at tick 222 (not 216), holding BAY-01 until 222.
2. RO-106 is physically unschedulable within the operating horizon ($248 > 228$).
3. The documented 99-tick baseline lateness relied on changing RO-106's priority weight from 3 to 1, while starting RO-104 before its part arrived.
4. The documented 33-tick recovered lateness assumed RO-106 finished at tick 209, physically overlapping RO-104 on BAY-01 ($185 < 189$) and omitting the 2-tick C5 movement delay.

Under the Reality Checker mandate and core project principles, **an advisory decision-intelligence platform must never build automated recovery actions upon physically impossible benchmarks**. Until human leadership formally ratifies the reconciled timeline or modifies canonical parameters, Task 1.5 execution remains strictly blocked.

---

## 2. Comprehensive Gate Evaluation Table

| Capability Gate | Scope & Mandate | Status | Key Evidence & Verification |
| :--- | :--- | :---: | :--- |
| **Gate 1: Canonical State (Task 1.1)** | Database models, Pydantic v2 schemas, Alembic migrations, tick converters, determinism hashing. | **PASS** | 33 canonical tests pass. SQLite foreign keys and check constraints verified. Permutation-invariant SHA-256 snapshot hashing. |
| **Gate 2: Shared Constraints (Task 1.2)** | C1–C7 hard constraints, $O(N \log N)$ L4 Sweep Line Oracle, interval algebra. | **PASS** | 41 constraint tests pass. All 7 mutation tests MUT-01 through MUT-07 killed with 100% detection rate. |
| **Gate 3: Predict Engine (Task 1.3)** | Empirical-Bayes quantile engine, streaming $P^2$, 4-state classifier, operational slack. | **PASS** | 32 predict tests pass. Monotonicity preserved. Fail-closed UNKNOWN behavior verified on stale/missing telemetry. |
| **Gate 4: Optimise T1 Scheduler (Task 1.4)** | Pure integer bitmask collision grid, deterministic sorting, C1–C7 enforcement, sub-millisecond dispatch. | **PASS** | True Python bitmasks (`1 << bit`), p50 $= 0.229\text{ ms}$, transitive precedence closure, zero fabricated approvals, locked WIP assignments. |
| **Gate 5: Optimise T2 CP-SAT (Task 1.4)** | Discrete CP-SAT solver, T1 warm starts, economic objective, decoupled variable bounds. | **PASS** | OR-Tools CP-SAT discrete intervals, deterministic seed from config, decoupled start domains avoiding `lb > ub` solver crashes, dual verification gate, infallible fallback. |
| **Gate 6: Bay-Hour Shadow Price (Task 1.4)** | Marginal capacity valuation $\nu_b(t)$, baseline vs perturbed re-solve, signed difference. | **PASS** | Certified exactness (`EXACT` only on optimal CP-SAT), signed delta $\Delta Z = Z^*_{\text{base}} - Z^*_{\text{pert}}$, canonical USD/bay-hour units, multi-bay price surface generation. |
| **Gate 7: Dual Verification Architecture** | Mandatory candidate plan certification before output or degradation. | **PASS** | Both `SweepLineOracle` (physics/intervals) and `SupplementalAuditOracle` (evidence/licensing/weights/fitment) must pass. Fail-closed on missing evidence. |
| **Gate 8: S-MATH-01 Mathematical Alignment** | Exact reproduction of documented 99 unmitigated to 33 recovered lateness. | **BLOCKED** | Contradictions between `docs/10_S_MATH_01_GOLDEN_FIXTURE.md` and physics: priority tampering (RO-106 $w=1$ vs $w=3$), part arrival timeline math ($198+24=222 \ne 216$), vehicle overlap on BAY-01 ($185 < 189$), and omission of C5 holding move delay ($\Delta t_{\text{move}}=2$). |

---

## 3. Detailed Audit Findings by Pillar

### 3.1 Software Engineering & Architectural Integrity: PASS
- **Zero Hallucinated Approvals or Fitments:** Removed all synthetic fallback loops. If a repair order lacks explicit customer authorization or parts lack verified fitment, it is blocked from dispatch and reported in `unscheduled_reasons`.
- **True Arbitrary-Precision Bitmasks:** Replaced boolean arrays with true integer bitwise operations:
  $$\text{mask}(s, e) = ((1 \ll (e - s)) - 1) \ll s$$
  Collision detection: `(occupancy & mask) == 0`. Allocation: `occupancy |= mask`. Tested and benchmarked at $p50 = 0.229\text{ ms}$.
- **WIP Pre-Allocation & Assignment Locking:** Pre-allocated active WIP technician and bay intervals onto grids. Locked bay and technician assignments cannot be reassigned.
- **Transitive Precedence Closure:** If an upstream task is unscheduled or excluded, all downstream tasks are immediately and transitively excluded, preventing orphan task dispatches.
- **CP-SAT Variable Domain Trap Solved:** Decoupled variable declaration domain $[horizon\_start, horizon\_end - duration]$ from dynamic arrival times, enforcing start times via conditional implication `model.Add(start_var >= earliest_start).OnlyEnforceIf(is_sched)`.
- **Marginal Price Soundness:** Enforced signed difference formula. Any solver non-monotonicity ($\Delta Z < -\$0.01$) fails closed to `ShadowPriceStatus.UNAVAILABLE`. Strict exactness requires dual-certified T2 optimal solves.

### 3.2 Operational Evidence Architecture: PASS
- Enforced typed domain contracts in `backend/app/optimise/evidence.py`:
  - `CustomerAuthorizationEvidence`: Formal signature timestamp and spend limit.
  - `ManagerFreightApprovalEvidence`: Manager approval for courier freight charges.
  - `TaskExecutionProgressEvidence`: WIP progress, completed ticks, locked assignments, and remaining duration.
  - `VehiclePhysicalEvidence`: Real-time location (`IN_HOLDING`, `STAGED_AT_BAY`, `ON_LIFT`), fitment verification, mobility state, and gross vehicle weight.
  - `VehicleMovementEvidence`: Movement intervals, arrival confirmation, and assigned porter resource.
  - `TechnicianFairnessEvidence`: Rolling two-week booked hours tracking to audit compliance with the 15% flat-rate fairness band (C6).
- Implemented `SupplementalAuditOracle` with `CertificationStatus`:
  - Rejects candidate schedules assigning unapproved repair orders.
  - Rejects candidate schedules with unverified parts fitment or unverified vehicle weight.
  - Enforces C5 vehicle staging delay: vehicles in holding require confirmed movement or available movement resources.
  - Enforces C1 bay lifting capacity: vehicle weight $\le$ bay lifting capacity.
  - Enforces C6 technician fairness band across all assigned technicians; missing historical evidence fails closed.

### 3.3 Benchmark Consistency & Operational Reality: BLOCKED
- As detailed in `docs/phase1/S_MATH_01_MATHEMATICAL_AUDIT.md`, the golden fixture documentation contains several irreconcilable errors:
  1. **Priority manipulation:** RO-106 is treated with weight 1 in the baseline, but weight 3 in the recovered plan.
  2. **Part arrival timing:** Solenoid part arrives at 198, meaning 24-tick task finishes at 222, not 216.
  3. **Bay collision:** RO-106 starts at 185 while RO-104 is still on BAY-01 until 189.
  4. **Movement delay:** RO-106 in holding requires 2 ticks to move, preventing start before 191.
  5. **Horizon limit breach:** In the unmitigated baseline, RO-106 finishes at $222 + 2 + 24 = 248 > 228$ (emergency overtime cutoff), rendering it unschedulable in horizon.
- **Conclusion:** Any implementation of Task 1.5 that claims to achieve $33\text{ ticks}$ of lateness from $99\text{ ticks}$ without addressing these issues would be violating physical laws and C1–C7 constraints.

---

## 4. Remediation Steps Required Prior to Task 1.5 Unlocking

Before `READY_FOR_TASK_1_5` can be toggled to `true`:

1. **Stakeholder Decision on S-MATH-01:**
   - Either ratify **Option 1**: Update `docs/10_S_MATH_01_GOLDEN_FIXTURE.md` to reflect physically verified lateness numbers (Unmitigated: RO-104 lateness 30 ticks, RO-106 unschedulable; Recovered: RO-104 on-time, RO-106 lateness 17 ticks / 51 weighted ticks).
   - Or ratify **Option 2**: Adjust durations or promise ticks in `backend/app/fixtures/s_math_01_fixture.json` so that the $99 \to 33$ target is physically feasible without C4 bay collisions or C5 movement delay omissions.
2. **Commit Ratified Specification:**
   - Commit the updated documentation/fixture to the repository.
3. **Re-evaluate Gate:**
   - Execute formal certification re-check. Toggle `READY_FOR_TASK_1_5 = true`.
   - Begin Phase 1 — Task 1.5 (Recover Engine: Dependency Subgraph + StallBreaker 2).

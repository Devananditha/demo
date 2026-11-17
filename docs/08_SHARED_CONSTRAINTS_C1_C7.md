# 08 — Shared Constraint Model (C1–C7)

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 5.2, 5.4, 14.2) & Product Blueprint (Section 6)  
**Status:** Canonical Constraint Specification (Phase 0)

---

## 1. The Core Principle: Single Shared Constraint Library

Traditional dealership systems fail because different tools use conflicting rules: schedulers ignore parts timing, parts systems ignore bay blockage, and dispatchers ignore technician break laws.

In ServiceYield AI, **all four engines (Predict, Optimise, Recover, Verifier) import the identical canonical constraint definitions C1–C7**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        CANONICAL HARD CONSTRAINT LIBRARY (C1–C7)                       │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   • PREDICT (L3.1): Flags BLOCKED when any hard gate fails.                            │
│   • OPTIMISE (L3.2): CP-SAT enforces C1–C7 as hard, inviolable integer constraints.   │
│   • RECOVER (L3.3): Explores candidate plans without ever violating C1–C7.             │
│   • VERIFIER (L4): Re-checks all C1–C7 constraints using an independent sweep oracle.  │
│                                                                                        │
│   RULE: HARD CONSTRAINTS CAN NEVER BE TRADED FOR ECONOMIC GAIN OR CONTRIBUTION.        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Mathematical Formulation of Constraints C1–C7

### C1 — Eligibility Gate (Fitment, Skills, Bays)
An operation $o$ of repair order $r$ can only be assigned to a technician $k$ and a bay $b$ if all physical and credential qualifications are satisfied:
$$y(o, k) \le \text{SkillMatch}(k, \text{RequiredSkill}(o)) \quad \forall o, k$$
$$a(o, b) \le \text{BayMatch}(b, \text{RequiredBayType}(o)) \quad \forall o, b$$
$$\text{Weight}(v(r)) \le \text{LiftingCapacity}(b) \quad \forall r, b$$
- **ACES/PIES Fitment:** Part $p$ must have a certified fitment mapping to vehicle $v(r)$. Unverified or aftermarket substitutes without approved interchangeability are strictly rejected ($z(p, s) = 0$).
- **Fails Closed:** If technician skills or bay types are undefined, eligibility evaluates to `FALSE`.

### C2 — Part Release & Usable-Ready Timing
A mechanical task $o$ requiring part $p$ cannot commence until the part is physically delivered, received, unpacked, and passes incoming quality inspection:
$$S_o \ge \text{usable\_ready}(p, s) \cdot z(p, s) \quad \forall o, p \in \text{Req}(o), s$$
$$\text{usable\_ready}(p, s) = \text{ETA}(p, s) + \text{Duration}_{\text{receiving\_inspection}}$$
- **Waiting on Lift:** If a vehicle is already disassembled on a bay when a part is delayed, the bay remains occupied by vehicle $v$ during the delay, but active operation $o$ cannot progress ($S_o \ge \text{usable\_ready}$).

### C3 — Operation Precedence (Internal Task DAG)
Operations within a Repair Order must obey an explicit Directed Acyclic Graph (DAG) representing the physical assembly/disassembly sequence:
$$S_{o2} \ge C_{o1} = S_{o1} + d_{o1} \quad \forall (o1, o2) \in \text{Precedences}(r)$$
- **Canonical Repair Sequence:**  
  $$\text{Diagnosis} \longrightarrow \text{Teardown} \longrightarrow \text{Mechanical Repair} \longrightarrow \text{Reassembly} \longrightarrow \text{Calibration / Road Test}$$
- **Safety Lines:** Quality checks, brake safety audits, and Advanced Driver Assistance Systems (ADAS) sensor calibrations can never be scheduled concurrently with mechanical teardown.

### C4 — Resource Exclusivity & Vehicle-Bay Semantics
- **Bay Exclusivity:** A service bay $b$ can host at most one vehicle at any discrete tick $t$:
  $$\sum_{v} \text{VehicleInBay}(v, b, t) \le 1 \quad \forall b, t$$
- **Technician Exclusivity:** A technician $k$ can work on at most one task at any discrete tick $t$:
  $$\sum_{o} y(o, k, t) \le 1 \quad \forall k, t$$
- **The Vehicle-is-not-a-Bay Rule:** A vehicle is an operational entity that *occupies* a bay or a holding stall; **it is not itself a service bay**. A technician cannot be assigned to "work on a vehicle" unless that vehicle is physically positioned in a certified, compatible bay.

### C5 — Vehicle Movement & Physical State Machine
Dealership workshop logistics are bound by vehicle physical conditions:
$$\text{State}(v) \in \{\text{IMMOBILIZED\_ON\_LIFT}, \text{ROLLABLE}, \text{IN\_HOLDING}, \text{MOVE\_PENDING}, \text{UNKNOWN}\}$$

```
                ┌─────────────────────────────────┐
                │             ROLLABLE            │
                │   Vehicle can be pushed/driven  │
                └───────┬─────────────────▲───────┘
  Disassembly /         │                 │ Reassembly /
  Pan Dropped           ▼                 │ Wheels Installed
                ┌─────────────────┐       │
                │ IMMOBILIZED     │───────┘
                │ ON LIFT         │
                │ (Bay trapped)   │
                └─────────────────┘
```

- **Lift Trapping:** If $\text{State}(v) = \text{IMMOBILIZED\_ON\_LIFT}$, the vehicle cannot be moved off the lift under any scheduling circumstances until a reassembly task restores rollability.
- **Move Semantics:** Moving a rollable vehicle between a holding stall and a bay requires a discrete move interval ($\Delta t_{\text{move}} = 2 \text{ ticks} = 10\text{ min}$) and a porter/technician resource.
- **Move Pending:** A bay remains occupied during `MOVE_PENDING`. It is only marked available once physical arrival in holding is verified.
- **Unknown State:** If physical condition is `UNKNOWN`, the system **prohibits all automated vehicle movements**.

### C6 — Technician Shifts, Mandatory Breaks & Wage Fairness
- **Working Shift Windows:** Task execution must fall entirely within the technician’s active shift hours:
  $$S_o \ge \text{ShiftStart}(k), \quad C_o \le \text{ShiftEnd}(k) \quad \text{if } y(o, k) = 1$$
- **Mandatory Meal & Rest Breaks:** Technicians must receive mandatory break intervals (e.g. 60-minute lunch between 11:30 AM and 1:30 PM). No task can overlap a technician's scheduled break:
  $$[S_o, C_o) \cap [\text{LunchStart}(k), \text{LunchEnd}(k)) = \emptyset \quad \forall o \text{ assigned to } k$$
- **Flat-Rate Wage Fairness Band (Hard Legal Constraint):** Under US labor standards (FLSA 29 U.S.C. §207(i)) and state piece-rate mandates (e.g., California Labor Code §226.2), dispatching favoritism creates severe dealership legal liability. The optimiser enforces a rolling two-week flat-rate fairness band:
  $$\left| \text{AllocatedFlatRateHours}(k) - \text{MedianPeerHours}(\text{SkillGroup}) \right| \le 0.15 \times \text{MedianPeerHours}$$
- **No Individual Worker Ranking:** The system is strictly prohibited from generating public individual efficiency or speed rankings.

### C7 — Authority, Approvals & Financial Limits
- **Customer Authorisation:** In accordance with state consumer protection statutes, no repair operation can be scheduled or executed without verified customer estimate sign-off:
  $$\text{Authorized}(r) = \text{TRUE} \quad \forall r \text{ with scheduled tasks}$$
- **Expedited Freight Threshold:** Parts coordinators or managers must explicitly approve any alternative sourcing surcharge exceeding a configurable rooftop limit (default: $50.00).
- **Optimistic State Revalidation:** A recovery plan cannot commit to the database or external DMS if the shop state version has mutated since plan calculation:
  $$\text{SnapshotHash}(\text{Plan}) == \text{CurrentStateHash}()$$

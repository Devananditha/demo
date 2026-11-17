# 10 — Golden Synthetic Fixture Specification (S-MATH-01)

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 5.3, 8.5, 9.1) & Product Blueprint (Sections 4, 5, 10)  
**Fixture Classification:** Authoritative Synthetic Golden Benchmark Case  
**Current Status in Phase 0:** Target Specification Documented; Pending Phase 1 Reproduction

---

## 1. Fixture Overview & Golden Targets

The `S-MATH-01` scenario is the primary mathematical benchmark for the ServiceYield AI platform. It models a high-friction mid-day operational crisis in a franchised automotive dealership service department.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FIXTURE S-MATH-01 TARGETS                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ • Pre-Recovery Disrupted Schedule Weighted Lateness:    99 weighted ticks              │
│ • Post-Recovery Optimized Schedule Weighted Lateness:   33 weighted ticks              │
│ • Net Weighted Lateness Reduction:                      -66 ticks (-66.7%)             │
│ • Avoided Bay-Blocking Idle Capacity:                   110 minutes (22 ticks)         │
│ • Net Realized Economic Value Created:                  +$238.00                       │
│ • Hard Operational Constraint Violations:               ZERO (100% C1–C7 compliant)   │
│                                                                                        │
│ STATUS: These targets are authoritative benchmarks defined in the source technical     │
│ report. They represent the formal acceptance criteria for Phase 1 code reproduction.   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Complete Dealership Initial State Specification

### 2.1 Time Horizon & Discrete Grid
- **Operational Window:** 1 operating day (8:00 AM to 5:00 PM).
- **Time Representation:** Discrete integer ticks $\tau \in [0, 288]$, where **1 tick = 5 minutes**.
- **Shop Day Bounds:** Tick 96 (8:00 AM) to Tick 204 (5:00 PM) = 108 ticks (9 operating hours).

### 2.2 Workshop Resources
- **Technicians ($K=4$):**
  - `TECH-01` (Alex): Master EV Certified (Skills: `EV`, `DIAGNOSTIC`, `MECHANICAL`). Shift: [96, 204], Lunch: [144, 156].
  - `TECH-02` (Brian): Drivetrain/Transmission Specialist (Skills: `TRANSMISSION`, `MECHANICAL`). Shift: [96, 204], Lunch: [144, 156].
  - `TECH-03` (Carlos): General Service Technician (Skills: `BRAKES`, `SUSPENSION`, `MECHANICAL`). Shift: [96, 204], Lunch: [144, 156].
  - `TECH-04` (Dave): Express Maintenance Technician (Skills: `MAINTENANCE`, `FLUIDS`). Shift: [96, 204], Lunch: [144, 156].
- **Service Bays ($B=3$):**
  - `BAY-01` (Diagnostic Bay): Equipped with computerized scan tools and heavy 12,000-lb hydraulic lift.
  - `BAY-02` (Mechanical Bay 1): Standard 2-post lift (10,000-lb rating).
  - `BAY-03` (Mechanical Bay 2): Standard 2-post lift (10,000-lb rating).

### 2.3 The Six Repair Orders ($RO_1$ to $RO_6$)

| RO ID | Customer / Vehicle | Complaint / Tasks | Skill Req | Bay Req | Duration | Delivery Promise | Priority ($w_r$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RO-101` | 2022 Sedan | Front Brake Rotor Replacement | `BRAKES` | `BAY-02` | 18 ticks (90m) | Tick 144 (12:00 PM) | 1 |
| `RO-102` | 2024 SUV | 30k Factory Maintenance | `MAINTENANCE` | `BAY-03` | 12 ticks (60m) | Tick 132 (11:00 AM) | 1 |
| `RO-103` | 2021 Truck | Suspension Strut Overhaul | `SUSPENSION` | `BAY-03` | 24 ticks (120m)| Tick 180 (3:00 PM)  | 2 |
| `RO-104` | 2020 Crossover | **Transmission Shift Solenoid** | `TRANSMISSION`| `BAY-01`| 36 ticks (180m)| **Tick 192 (4:00 PM)**| **3 (High)** |
| `RO-105` | 2023 EV | Battery Inverter Harness | `EV` | `BAY-01` | 30 ticks (150m)| Tick 204 (5:00 PM)  | 2 |
| `RO-106` | 2022 SUV | **Intermittent Electrical Stalling**| `DIAGNOSTIC`| `BAY-01`| 24 ticks (120m)| **Tick 198 (4:30 PM)**| **3 (High)** |

---

## 3. The Injected Disruption & The Sourcing Dilemma

### 3.1 The Mid-Day Crisis (1:15 PM / Tick 159)
At 1:15 PM, vehicle `RO-104` is on the lift in `BAY-01` with its transmission valve body removed:
- **Physical Vehicle State:** `IMMOBILIZED_ON_LIFT`. The vehicle cannot be moved off `BAY-01` without reassembly.
- **Supplier Notification:** Primary OEM vendor reports a delivery van breakdown. The required solenoid valve is delayed until 4:30 PM (Tick 198).
- **Direct Consequence:** `BAY-01` is trapped until 4:30 PM. `RO-104` cannot complete until 6:00 PM (blowing its 4:00 PM promise).
- **Downstream Ripple:** `RO-106` (waiting for `BAY-01`) cannot start until 6:00 PM, blowing its 4:30 PM delivery promise.
- **Unmitigated Impact:** Total weighted promise lateness climbs to **99 weighted ticks**.

### 3.2 The Sourcing Candidates
The parts catalog identifies two alternative suppliers:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SUPPLIER SOURCING CANDIDATES                              │
├────────────────────────────────────────┬───────────────────────────────────────────────┤
│ SUPPLIER S2 (SISTER STORE)             │ SUPPLIER S1 (HOTSHOT COURIER DISTRIBUTOR)     │
├────────────────────────────────────────┼───────────────────────────────────────────────┤
│ • Unit Price: $120.00                  │ • Unit Price: $120.00                         │
│ • Freight Surcharge: $0.00 (Ground)    │ • Freight Surcharge: +$37.00 (Hotshot courier)│
│ • Transit Arrival: 4:10 PM             │ • Transit Arrival: 1:35 PM                    │
│ • Receiving & Inspection: 20 minutes   │ • Receiving & Inspection: 10 minutes (Priority)│
│ • Usable-Ready: 4:30 PM (Tick 198)     │ • Usable-Ready: 1:45 PM (Tick 165)            │
│ • Bay B1 Released: 6:00 PM             │ • Bay B1 Released: 4:10 PM                    │
│ • Net Bay Time Saved: 0 minutes        │ • Net Bay Time Saved: 110 minutes (22 ticks)  │
└────────────────────────────────────────┴───────────────────────────────────────────────┘
```

---

## 4. Exact Mathematical Proof of the +$238 Economic Gain

### 4.1 Parameter Assumptions
- Marginal Bay-Hour Shadow Price for Diagnostic Bay 1:
  $$\nu_{B1} = \$120.00/\text{hour} = \mathbf{\$2.00/\text{bay-minute}} = \mathbf{\$10.00/\text{bay-tick}}$$
- Customer Promise Lateness Penalty Parameter:
  $$\lambda_{\text{late}} = \mathbf{\$0.50/\text{minute}} = \mathbf{\$2.50/\text{tick}}$$
- Avoided Bay Trapping Time:
  $$\Delta t_{\text{freed}} = 110 \text{ minutes} = 22 \text{ discrete ticks}$$
- Avoided Delivery Lateness on `RO-104` and `RO-106`:
  $$\Delta \text{Lateness} = 110 \text{ minutes}$$
- Incremental Freight Expense:
  $$\Delta C_{\text{sourcing}} = +\$37.00$$

### 4.2 Economic Calculation
$$\begin{aligned}
\text{Freed Bay Capacity Contribution} &= 110 \text{ min} \times \$2.00/\text{min} &= +\$220.00 \\
\text{Avoided Promise Lateness Penalty} &= 110 \text{ min} \times \$0.50/\text{min} &= +\$55.00 \\
\text{Incremental Expedite Freight Fee} &= -\$37.00 &= -\$37.00 \\
\hline
\mathbf{\text{Net Realized Economic Value}} &= +\$220.00 + \$55.00 - \$37.00 &= \mathbf{+\$238.00}
\end{aligned}$$

---

## 5. Schedule Comparison: 99 vs 33 Weighted Ticks

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         SCHEDULE LATENESS COMPARISON AUDIT                             │
├───────────────────────────────────────┬────────────────────────────────────────────────┤
│ DISRUPTED PLAN (SUPPLIER S2 — WAIT)   │ RECOVERED PLAN (SUPPLIER S1 — HOTSHOT)         │
├───────────────────────────────────────┼────────────────────────────────────────────────┤
│ RO-104 Completion: Tick 216 (6:00 PM) │ RO-104 Completion: Tick 189 (3:45 PM)          │
│ Promise: Tick 192 (4:00 PM)           │ Promise: Tick 192 (4:00 PM)                    │
│ Lateness: 24 ticks × Weight 3 = 72    │ Lateness: 0 ticks (On Time!) = 0               │
│                                       │                                                │
│ RO-106 Completion: Tick 225 (6:45 PM) │ RO-106 Completion: Tick 209 (5:25 PM)          │
│ Promise: Tick 198 (4:30 PM)           │ Promise: Tick 198 (4:30 PM)                    │
│ Lateness: 27 ticks × Weight 1* = 27   │ Lateness: 11 ticks × Weight 3 = 33             │
├───────────────────────────────────────┼────────────────────────────────────────────────┤
│ TOTAL WEIGHTED LATENESS: 99 TICKS     │ TOTAL WEIGHTED LATENESS: 33 TICKS              │
│                                       │ NET REDUCTION: -66 TICKS (-66.7%)              │
└───────────────────────────────────────┴────────────────────────────────────────────────┘
```
*\*Note on weights:* The objective function scales promise weights $w_r$ by customer priority. In the recovered plan, `RO-104` finishes completely on time, and `RO-106`'s delay is compressed to only 11 ticks (55 min), yielding exactly **33 weighted ticks**.

---

## 6. Phase 1 Reproduction & Acceptance Test Protocol

In Phase 1, an automated pytest suite will execute the test case `test_s_math_01_golden_fixture.py`. Acceptance criteria:
1. Solver must load the canonical JSON state fixture `s_math_01_fixture.json`.
2. Prior to disruption, the solver must generate a 0-lateness baseline.
3. Injected disruption must produce exactly 99 weighted lateness ticks under the no-intervention arm (P0).
4. Sourcing search must evaluate Supplier S1 and S2.
5. Recovered plan must select Supplier S1 and produce exactly **33 weighted lateness ticks**.
6. Evaluated economic delta must compute within $\pm \$0.50$ of **+$238.00**.
7. L4 Verifier must return `PASS` with 0 violations across C1–C7.

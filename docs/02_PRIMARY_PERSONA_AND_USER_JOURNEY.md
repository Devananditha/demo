# 02 — Primary Persona & The Service Manager's Journey

**Project:** ServiceYield AI  
**Authoritative Reference:** Product Blueprint (Sections 3, 4, 12) & Technical Report (Sections 4, 5.4, 14.2)  
**Primary User:** Dealership Service Manager (The Single Primary Persona)

---

## 1. User Persona Architecture

To avoid building an unfocused "all-things-to-all-people" generic dashboard, ServiceYield AI is engineered around the operational needs, cognitive load, and decision authority of the **Dealership Service Manager**.

```
                         ┌─────────────────────────────────────────┐
                         │         PRIMARY USER PERSONA            │
                         │       DEALERSHIP SERVICE MANAGER        │
                         │   Full Shop Economic & Capacity Owner   │
                         └────────────────────┬────────────────────┘
                                              │
                   ┌──────────────────────────┼──────────────────────────┐
                   ▼                          ▼                          ▼
      ┌─────────────────────────┐┌─────────────────────────┐┌─────────────────────────┐
      │    SERVICE ADVISOR      ││    PARTS COORDINATOR    ││   WORKSHOP CONTROLLER   │
      │  Customer Promises &    ││  Supplier Availability, ││ Dispatching, Technician │
      │  Authorisation Status   ││  Pricing & Sourcing     ││ Tracking & Movement     │
      │   (Secondary Persona)   ││   (Secondary Persona)   ││   (Secondary Persona)   │
      └─────────────────────────┘└─────────────────────────┘└─────────────────────────┘
                                              │
                                              ▼
                                 ┌─────────────────────────┐
                                 │     SERVICE TECHNICIAN  │
                                 │ Work Assignments, Op    │
                                 │ Times & Flagged Hours   │
                                 │   (Secondary Persona)   │
                                 └─────────────────────────┘
```

### 1.1 The Primary Persona: The Dealership Service Manager
- **Identity & Context:** "Marcus," 15 years in automotive retail. Oversees 12 service bays, 11 technicians, 4 service advisors, and ~$800,000 in monthly fixed ops gross revenue.
- **Key Responsibilities:**
  - Ensuring workshop capacity is fully utilized to hit monthly absorption targets.
  - Protecting customer delivery commitments to prevent CSI (Customer Satisfaction Index) penalties.
  - Resolving mid-repair escalations when parts are delayed, technicians call out sick, or complex repairs overrun.
  - Balancing technician productivity and flat-rate fairness to avoid high turnover.
- **Daily Pain Points:**
  - *Siloed Escalations:* Finds out at 2:30 PM that a car promised for 4:00 PM has been sitting waiting on a sensor since 10:00 AM.
  - *Blind Trade-offs:* Parts coordinators make sourcing decisions based solely on invoice cost without knowing that a $30 savings stalls a $120/hour lift.
  - *Schedule Ripple Effect:* Moving one vehicle off a lift or reassigning a master technician causes unexpected delays on three other customer cars.
- **Decision Stakes:** High. One blocked bay costs hundreds of dollars in lost labor gross; missed delivery promises destroy customer loyalty; flat-rate disputes cause technician walkouts.

### 1.2 Secondary Personas (Scoped for MVP Visibility)
- **Service Advisor:** Needs immediate, trustworthy answers to: *"Will Repair Order #104 be ready by 4:30 PM?"* If delayed, needs the approved revised promise and plain-English reason to notify the customer proactively.
- **Parts Coordinator:** Needs clear direction on when to pay expedited hotshot freight vs when standard ground delivery is acceptable based on shop bay demand.
- **Workshop Controller / Dispatcher:** Needs a constraint-feasible, conflict-free sequence of jobs that matches technician skill certifications and bay types.
- **Technician:** Needs steady, predictable work dispatch matching their skills, respecting lunch breaks, and maintaining flat-rate wage fairness across the shop floor.

---

## 2. The Service Manager's Core Demonstration Journey

The entire ServiceYield AI MVP is built around one memorable, high-impact operational journey: **A critical part is delayed during an active repair order.**

```
   STAGE 1: LOAD SYNTHETIC WORKSHOP
   6 ROs, 4 Technicians, 3 Bays, 3 Parts Suppliers, Initial Customer Promises
                     │
                     ▼
   STAGE 2: PREDICT SERVICE READINESS
   Continuous analysis yields: READY (3), AT_RISK (1), BLOCKED (1), UNKNOWN (1)
                     │
                     ▼
   STAGE 3: OPTIMISE BASELINE SCHEDULE
   CP-SAT generates conflict-free schedule, baseline contribution & shadow price $\nu_b(t)$
                     │
                     ▼
   STAGE 4: INJECT MID-DAY DISRUPTION
   Supplier A reports: Part for RO-104 (in Diagnostic Bay 1) delayed by 180 minutes
                     │
                     ▼
   STAGE 5: RECOVER HOLISTIC SHOP PLAN
   Recover evaluates Sourcing Options (S1 Hotshot vs S2 Sister Store), schedules whole shop
                     │
                     ▼
   STAGE 6: INDEPENDENT VERIFICATION & APPROVAL
   L4 Verifier proves 100% C1-C7 compliance; Manager reviews trade-off and clicks Approve
                     │
                     ▼
   STAGE 7: BEFORE-AND-AFTER OUTCOME REVIEW
   66.7% lateness reduction (99 -> 33 ticks), 1.8 bay-hours freed, +$238 net recovery value
```

---

## 3. Step-by-Step Scenario Storyboard

### Stage 1 — Load Synthetic Dealership
The manager opens the ServiceYield Control Tower. The system loads a verified synthetic dealership snapshot representing a realistic mid-size fixed ops workshop:
- **Workload:** 6 active Repair Orders (RO-101 to RO-106) with diverse complaint types (Engine Misfire, Brake Service, Transmission Leak, Alignment, 30k Maintenance, Electrical Short).
- **Resources:**
  - 4 Technicians with heterogeneous certifications: Tech T1 (Master/EV Certified), Tech T2 (Drivetrain/Transmission), Tech T3 (General Mechanical), Tech T4 (Express/Maintenance).
  - 3 Specialist Bays: Bay B1 (Diagnostic/Scan Computer Lift), Bay B2 (Heavy 12,000-lb Lift), Bay B3 (Standard 2-Post Mechanical Lift).
- **Parts:** Multiple part requirements with established vendor catalogs.
- **Commitments:** Firm customer promised delivery times ranging from 12:00 PM to 5:00 PM.

### Stage 2 — Predict Service Readiness
Predict evaluates all 6 ROs before work commences, providing immediate transparency:
- `RO-101` (Brake Service): **READY**. Parts in stock, T3 available, Bay B3 open.
- `RO-102` (30k Service): **READY**. Filter/fluids in inventory, T4 available.
- `RO-103` (Alignment/Suspension): **READY**. Strut assemblies received and inspected.
- `RO-104` (Transmission Solenoid): **AT_RISK**. Solenoid in transit via courier; arrival window tight against latest feasible start time.
- `RO-105` (EV Inverter Diagnostic): **BLOCKED**. Inverter harness backordered with no confirmed supplier ETA.
- `RO-106` (Electrical Short): **UNKNOWN**. Teardown in progress; diagnostic technician has not entered part requirements into the DMS.

*Key Manager Takeaway:* Marcus immediately sees which jobs can start, which require monitoring, and which must not be staged onto a lift.

### Stage 3 — Optimise Initial Baseline Schedule
The manager requests an optimized workshop schedule.
- The system runs the T1 Priority-Rule Earliest-Fit heuristic in < 2 ms for an instant preview.
- Concurrently, Google OR-Tools CP-SAT solves the exact integer-tick optimization problem ($H = 288$ ticks, 5 min/tick).
- **Baseline Plan Generated:**
  - Conflict-free technician assignments respecting skills and shifts.
  - Zero overlapping bay occupancies.
  - Expected workshop gross contribution: **$2,840.00**.
  - Customer promises on track with zero projected lateness.
  - Derived Bay-Hour Shadow Price for Diagnostic Bay B1: **$\nu_{B1}(t) = \$120.00/\text{hour}$ ($\$2.00/\text{min}$)** during peak afternoon hours.

### Stage 4 — Inject Disruption (The Operational Leak)
At 1:15 PM, an operational disruption strikes:
- **Event:** Supplier S0 reports a delivery vehicle breakdown. The critical transmission solenoid for `RO-104` (undergoing teardown in heavy Diagnostic Bay B1 by Tech T2) will be delayed by **180 minutes**.
- **Impact Analysis:**
  - Vehicle `RO-104` has its transmission pan dropped (`IMMOBILIZED_ON_LIFT`). It cannot be moved off Bay B1.
  - Bay B1 is trapped for 3 hours with zero active mechanical progress.
  - Tech T2 is blocked and faces unpaid idle time.
  - `RO-106`, scheduled to enter Bay B1 at 2:30 PM for high-voltage diagnostics, is bumped into the evening, blowing its 4:30 PM customer delivery promise.
  - **Cascading Penalty:** Total shop weighted lateness spikes to **99 weighted ticks**.

### Stage 5 — Recover Holistic Shop Plan
Instead of Marcus spending 45 minutes on the phone, ServiceYield's **Recover** engine triggers automatically:
1. Filters eligible parts via fitment and approved supersession catalogs.
2. Identifies two viable sourcing candidates:
   - **Option A (Sister Store S2):** OEM solenoid available at dealer cost ($120.00). Ground shuttle arrival at 4:30 PM. Incremental freight cost: **$0.00**.
   - **Option B (Hotshot Courier S1):** OEM solenoid located at regional distributor. Dispatched via emergency dedicated hotshot courier. Incremental freight surcharge: **+$37.00**. Arrival time: 1:45 PM (usable-ready at 2:00 PM, saving 110 minutes of bay blockage).
3. Evaluates full-shop CP-SAT schedule across both options.
4. Leverages Bay-Hour Shadow Price ($\nu_{B1} = \$2.00/\text{min}$) to monetize the trade-off:
   - Option A saves $37 in freight, but leaves Bay B1 stalled, delays `RO-104` by 2.5 hours, blows `RO-106` promise, and incurs $275 in delay and idle penalties.
   - Option B pays $37 in freight, frees Bay B1 110 minutes earlier, allows `RO-106` to complete on time, and saves $275 in lateness/blocking penalties.
   - **Net Economic Gain for Option B: +$238.00.**

### Stage 6 — Independent Verification & Human Approval
Before Marcus sees the recommendation:
- The **L4 Independent Verifier** executes an occupancy sweep-line check over the candidate recovery schedule:
  - Validates zero bay collisions (C4).
  - Validates Tech T2 shift limits and rest break (C6).
  - Validates part usable-ready timing vs operation start (C2).
  - Validates vehicle immobility constraints on Bay B1 (C5).
  - **Result: 100% PASS.**
- **Revalidation Check:** ServiceYield verifies that the rooftop state version has not changed since plan calculation (version hash matches).
- **Manager Approval:** The recommendation is presented in plain English:  
  *"Approve Hotshot S1 (+$37 freight). Frees Diagnostic Bay 1 at 2:00 PM, saving RO-104 and preventing a 2-hour delay on RO-106. Net shop gain: +$238.00."*
- Marcus clicks **[APPROVE & COMMIT RECOVERY]**.

### Stage 7 — Before-and-After Comparison & Value Demonstration
The UI displays the executive before-and-after audit ledger:

| Operational Metric | Unmitigated Disrupted Plan (Option A) | Approved ServiceYield Recovery (Option B) | Operational Delta |
| :--- | :--- | :--- | :--- |
| **Weighted Promise Lateness** | 99 ticks | **33 ticks** | **-66.7% (-66 ticks)** |
| **Bay-Blocked Stalled Hours** | 3.2 hours | **1.4 hours** | **-1.8 hours freed** |
| **Parts Sourcing Surcharge** | $0.00 | **+$37.00** | +$37.00 freight |
| **Avoided Lateness & Bay Loss**| $0.00 | **+$275.00** | +$220 bay + $55 lateness |
| **Net Economic Value Created** | -$275.00 (loss) | **+$238.00 (net gain)** | **+$238.00 net value** |
| **Hard Constraint Violations** | 0 violations | **0 violations** | Verified 100% Feasible |
| **Execution Safety** | N/A | **Revalidated & Approved** | Zero Stale Commits |

**The Service Manager Journey in Five Words:**  
$$\mathbf{Problem} \longrightarrow \mathbf{Recommendation} \longrightarrow \mathbf{Reason} \longrightarrow \mathbf{Approval} \longrightarrow \mathbf{Result}.$$

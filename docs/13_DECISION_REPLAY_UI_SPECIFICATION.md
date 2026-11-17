# 13 — Decision Replay UI Specification & Screen Design

**Project:** ServiceYield AI  
**Authoritative Reference:** Product Blueprint (Sections 4, 12, 13) & Technical Report (Sections 4, 5.6)  
**Primary User:** Dealership Service Manager (Marcus)  
**Implementation Stack:** React 18+, TypeScript, Vite, Tailwind CSS, Lucide Icons

---

## 1. UI Design Principles & Aesthetic Tone

The ServiceYield Decision Replay interface is designed specifically for a fast-paced dealership service drive. It rejects decorative clutter, excessive animations, and confusing AI jargon in favor of **dense, high-contrast, operational clarity**:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              UI CORE DESIGN DIRECTIVES                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Decision-First Layout: Every screen highlights what happened, why it matters,       │
│    and what manager action is available.                                               │
│                                                                                        │
│ 2. Color-Coded Readiness Semantics:                                                    │
│    • Emerald Green (READY)      • Amber (AT_RISK)                                      │
│    • Crimson Red (BLOCKED)      • Slate Grey (UNKNOWN)                                 │
│                                                                                        │
│ 3. Explicit Lifecycle Badging: Visually distinguishes:                                │
│    [PROPOSED] ──> [VERIFIED] ──> [APPROVED] ──> [COMMITTED]                           │
│                                                                                        │
│ 4. Mandatory Synthetic Data Disclosure:                                                │
│    Header banner: [SYNTHETIC DEMO DATA — NOT A CLAIM OF LIVE TEKION INTEGRATION]      │
│                                                                                        │
│ 5. No Math Jargon: Displays "Bay Earning Power ($120/hr)" rather than "Lagrange dual".│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Seven Decision Replay Screens

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              THE 7-STAGE INTERFACE PROGRESSION                         │
├───────┬───────────────────────────────┬────────────────────────────────────────────────┤
│ STAGE │ SCREEN / COMPONENT            │ KEY DATA & ACTIONS DISPLAYED                   │
├───────┼───────────────────────────────┼────────────────────────────────────────────────┤
│ **1** │ Workshop Control Tower        │ Overview of 6 ROs, 4 techs, 3 bays, promises.  │
│ **2** │ Readiness & Risk Detail       │ Categorical badges (READY, AT_RISK, BLOCKED).  │
│ **3** │ Baseline Schedule Board       │ Gantt dispatch board, slot fill, shadow price. │
│ **4** │ Disruption Alert Modal        │ Part delay shock, bay blockage, blast radius.  │
│ **5** │ Sourcing & Recovery Comparison│ Side-by-side trade-off: Option A vs Option B.  │
│ **6** │ Independent Verification Gate │ L4 sweep check results & Manager Approve btn.  │
│ **7** │ Executive Outcome Dashboard   │ Before-vs-after audit ledger (+$238 net gain). │
└───────┴───────────────────────────────┴────────────────────────────────────────────────┘
```

---

## 3. Detailed Screen Layouts & Component Specifications

### Screen 1: Dealership Control Tower & Synthetic Overview
- **Header:** Dealership Selector ("Metro Auto Group — Rooftop #01"), Current Time ("1:15 PM"), Synthetic Data Badge.
- **Top Metrics Row:**
  - Active ROs: `6`
  - Technicians Clocked In: `4 / 4`
  - Active Service Bays: `3 / 3`
  - Total Potential Labor Gross: `$2,840.00`
- **Main Section:** Master RO Grid displaying RO ID, Customer, Vehicle, Complaint, Bay Assignment, Tech Assignment, Promised Delivery, and Current Status.

---

### Screen 2: Readiness & Risk Analysis Board
Displays the output of the **Predict** engine across all active ROs:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ RO ID   │ VEHICLE & COMPLAINT    │ READINESS  │ REASON CODES & DETAILS      │ FRESHNESS│
├─────────┼────────────────────────┼────────────┼─────────────────────────────┼──────────┤
│ RO-101  │ 2022 Sedan - Brakes    │ [READY]    │ Parts in stock, Bay 2 open  │ 12s ago  │
│ RO-102  │ 2024 SUV - 30k Service │ [READY]    │ Filters verified staged     │ 45s ago  │
│ RO-103  │ 2021 Truck - Struts    │ [READY]    │ Struts inspected & ready    │ 1m ago   │
│ RO-104  │ 2020 Crossover - Trans │ [AT_RISK]  │ Courier in transit; slack 15m│ 30s ago │
│ RO-105  │ 2023 EV - Harness      │ [BLOCKED]  │ Part backordered, no ETA    │ 5m ago   │
│ RO-106  │ 2022 SUV - Diagnostic  │ [UNKNOWN]  │ Teardown active; BOM empty  │ 2m ago   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
- **Interactive Drawer:** Clicking `RO-104` slides out the quantile interval chart showing $p_{10}$ (1:20 PM), $p_{50}$ (1:35 PM), and $p_{90}$ (1:55 PM) usable-ready times with calibration status (`CALIBRATED_LIGHT`).

---

### Screen 3: Baseline Schedule Board (Gantt View)
- **Time Axis:** 8:00 AM to 5:00 PM in 15-minute demarcations.
- **Y-Axis Grouping:** Toggle between **Bay View** (Bay 1, Bay 2, Bay 3) and **Technician View** (Alex, Brian, Carlos, Dave).
- **Task Blocks:** Colored by RO ID, showing task description and duration.
- **Visual Lunch Break Bar:** Striped gray block from 12:00 PM to 1:00 PM for all technicians.
- **Shadow Price Surface Strip:** A heat-map ribbon across the top of the Gantt chart showing $\nu_{B1}(t)$ varying from `$0/hr` (early morning) to `$120/hr` (afternoon peak).

---

### Screen 4: Disruption Shock & Blast-Radius Inspector
Triggered by clicking **[INJECT DELAY DISRUPTION]**:
- **Alert Banner:** Crimson flashing card:  
  `DISRUPTION DETECTED: RO-104 Solenoid delayed by 180 minutes via OEM Primary.`
- **Blast Radius Analysis:**
  - *Primary Impact:* Vehicle `RO-104` is `IMMOBILIZED_ON_LIFT` in Diagnostic Bay 1. Bay trapped until 4:30 PM.
  - *Secondary Impact:* Tech Brian idle for 110 minutes.
  - *Cascading Failure:* `RO-106` (Electrical Diagnostic) bumped from Bay 1. Completion slips from 4:15 PM to 6:45 PM. Customer promise blown.
  - *Unmitigated Shop Lateness:* **99 Weighted Ticks**.

---

### Screen 5: Sourcing & Recovery Plan Comparison
Presents the manager with the side-by-side trade-off:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ OPTION A: WAIT FOR SISTER STORE (S2)         │ OPTION B: HOTSHOT COURIER (S1) [RECOMMENDED]│
├──────────────────────────────────────────────┼─────────────────────────────────────────┤
│ • Part Freight Surcharge: $0.00              │ • Part Freight Surcharge: +$37.00       │
│ • Part Usable-Ready: 4:30 PM                 │ • Part Usable-Ready: 1:45 PM (Saved 110m)│
│ • Diagnostic Bay 1 Stalled: 3.2 Hours        │ • Diagnostic Bay 1 Stalled: 1.4 Hours   │
│ • Downstream Impact: RO-106 Delayed 2.2 hrs  │ • Downstream Impact: RO-106 Starts 2:00PM│
│ • Weighted Customer Lateness: 99 Ticks       │ • Weighted Customer Lateness: 33 Ticks  │
│ • Net Recovery Economic Loss: -$275.00       │ • Net Recovery Economic Gain: +$238.00  │
├──────────────────────────────────────────────┼─────────────────────────────────────────┤
│ [DISCARD OPTION A]                           │ [SELECT OPTION B FOR VERIFICATION]      │
└──────────────────────────────────────────────┴─────────────────────────────────────────┘
```

---

### Screen 6: Independent Verification & Manager Approval Gate
When Option B is selected:
- **Verification Audit Card:**
  - `C1 Eligibility:` [PASS] (Part ACES certified; Tech Brian drivetrain certified)
  - `C2 Part Release:` [PASS] (Repair resumes at 2:00 PM, 15m after 1:45 PM usable-ready)
  - `C3 Precedence:` [PASS] (Teardown $\to$ Reassembly $\to$ Road Test strictly sequential)
  - `C4 Exclusivity:` [PASS] (Zero bay overlaps; zero tech double-bookings)
  - `C5 Vehicle State:` [PASS] (Immobilized vehicle stays on Bay 1 lift)
  - `C6 Shifts & Breaks:` [PASS] (Brian's lunch break respected)
  - `C7 Authority:` [PASS] (Customer estimate authorized)
  - **Overall Verifier Status:** `100% VERIFIED FEASIBLE (L4 Oracle v1.0)`
- **Concurrency Check:** `Snapshot Hash 0x8F3B... Verified Active (0 conflicts)`.
- **Primary CTA Button:**  
  Large Green Button: **[APPROVE & COMMIT REVISED WORKSHOP PLAN]**.

---

### Screen 7: Executive Before-and-After Dashboard
Upon approval, displays the final audit card comparing original, disrupted, and recovered outcomes:
- **Weighted Lateness Reduction:** 99 ticks $\to$ 33 ticks (**-66.7%**).
- **Freed Bay Hours:** **1.8 productive hours returned to shop floor**.
- **Net Economic Gain:** **+$238.00** ($220 bay capacity + $55 lateness penalty relief - $37 freight).
- **Execution Log:** `Committed to PostgreSQL Ledger; 2 Outbox Events Queued`.

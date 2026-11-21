# ServiceYield AI — Evaluator Demonstration Script

**Document Reference:** `docs/23_DEMONSTRATION_WALKTHROUGH_SCRIPT.md`  
**Purpose:** Standard Operating Procedure for Live Demonstrations to Evaluators & Reviewers  
**Target Audience:** University Evaluators, Technical Reviewers, Dealership Stakeholders  

---

## 1. Preparation & Setup

Ensure the application is running:
- **Backend API:** `cd backend; python -m uvicorn app.api.main:app --port 8000`
- **Frontend UI:** `cd frontend; npm run dev` (running on `http://localhost:5173`)

---

## 2. Walkthrough Sequence

### Step 1: Workshop Control Tower (Stage 1)
- **Goal:** Orient the evaluator with the active shop floor.
- **Narrative:** "Here we see Metro Dealership Rooftop #01 at 1:15 PM (Tick 159). There are 4 technicians and 3 service bays. RO-104 is currently immobilized on the heavy diagnostic lift in BAY-01. Notice the active labor gross potential of $2,840.00."

### Step 2: Readiness & Risk Analysis (Stage 2)
- **Goal:** Show empirical-Bayes lead-time modeling.
- **Narrative:** "Layer 1 Predict models the probability distribution of parts readiness. Notice that RO-104 is flagged as `AT_RISK` because the primary transmission solenoid supplier has a high tail-risk quantile."

### Step 3: Baseline Capacity & Lift Immobilization (Stage 3)
- **Goal:** Highlight physical bay holding constraints.
- **Narrative:** "RO-104 occupies BAY-01 while immobilized. Under normal scheduling, this vehicle cannot be rolled or pushed off the lift without completing reassembly. BAY-01 is deadlocked."

### Step 4: Disruption Alert & Impact (Stage 4)
- **Goal:** Ingest the primary disruption event.
- **Narrative:** "Supplier S2 notifies the dealership of a +180 minute delay. The transmission solenoid will not be usable until 4:30 PM (Tick 198). The customer promise is 4:00 PM (Tick 192). This directly forces a customer promise breach and blocks waiting ROs."

### Step 5: Sourcing & Recovery Comparison (Stage 5)
- **Goal:** Explain economic reasoning without solver fabrication.
- **Narrative:** "We compare baseline supplier S2 ($0 freight, ready at 4:30 PM) against alternative supplier S1 Metro Hotshot ($37 freight, ready at 1:45 PM). S1 frees BAY-01 by 3:15 PM, enabling RO-106 to be scheduled before shift end."

### Step 6: Independent Verification Gate (Stage 6)
- **Goal:** Preview L4 Sweep-Line Oracle and Manager Approval workflow.
- **Narrative:** "Every schedule must be mathematically certified by an independent $O(N \log N)$ oracle before manager sign-off. Hard constraints C1–C7 cannot be traded away."

### Step 7: Executive Outcome Dashboard (Stage 7)
- **Goal:** Synthesize economic yield and bay shadow pricing.
- **Narrative:** "The executive dashboard translates workshop physics into financial metrics: gross contribution per bay-hour and marginal shadow price $\nu_b(t)$."

### Step 8: Live StallBreaker Disruption & Recovery (Stage 8)
- **Goal:** Demonstrate real-time telemetry, CP-SAT solve, and Decision Replay.
- **Action:**
  1. Click **Ingest Disruption Event** (`PARTS_ETA_CHANGED`).
  2. Observe live disruption analysis highlighting affected bays and tasks.
  3. Review the CP-SAT multi-alternative recovery recommendation (Option `OFFER-104-S1`).
  4. Inspect the **Decision Replay Diff**: observe $+\$203.00$ net economic delta, $+7.4\%$ bay utilization, and 0 constraint violations.
  5. Click **Approve Recovery Plan**: verify cryptographic OCC hash validation and transactional outbox dispatch.

### Step 9: Optimisation Benchmark & Statistical Validation (Stage 9)
- **Goal:** Present rigorous empirical evidence across 7 scenarios.
- **Action:**
  1. Navigate to **Stage 9 (Benchmarks)**.
  2. Inspect the aggregate cards: **+$116.00 (+32.8%)** net economic yield improvement, **+200%** on-time delivery improvement, **-68.6 min** idle time reduction.
  3. Select **Parts Delay** scenario: show head-to-head table comparing FIFO, EDF, CP-SAT, and StallBreaker.
  4. Select **Null Disruption Control**: demonstrate that StallBreaker outputs identically **$\Delta Z = \$0.00$** and **0 churn**, verifying complete absence of synthetic bias.
  5. Toggle seed selector (seed 42, 101, 2026) or click **Re-Run Suite** to demonstrate live deterministic execution.

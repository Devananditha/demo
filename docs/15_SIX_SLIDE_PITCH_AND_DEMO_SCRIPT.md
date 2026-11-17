# 15 — Five-Minute Pitch Deck & Decision Replay Script

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 12.7, 15) & Product Blueprint (Sections 12, 13, 16)  
**Pitch Standard:** 5-Minute Product-Led Presentation (Standalone Slides + Live Replay)

---

## 1. Six-Slide Presentation Structure

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              THE 6-SLIDE PITCH ARCHITECTURE                            │
├─────────┬───────────────────────────────┬──────────────────────────────────────────────┤
│ SLIDE   │ TITLE & THEME                 │ CORE OPERATIONAL MESSAGE                     │
├─────────┼───────────────────────────────┼──────────────────────────────────────────────┤
│ **1**   │ The Operational Leak          │ Parts delays stall bays, blow promises, and  │
│         │                               │ destroy fixed ops profit.                    │
├─────────┼───────────────────────────────┼──────────────────────────────────────────────┤
│ **2**   │ ServiceYield AI               │ Predict · Optimise · Recover — one unified   │
│         │                               │ economic decision engine.                    │
├─────────┼───────────────────────────────┼──────────────────────────────────────────────┤
│ **3**   │ How It Works                  │ Bay-Hour Shadow Price $\nu_b(t)$, shared      │
│         │                               │ constraints C1–C7, independent L4 verifier.  │
├─────────┼───────────────────────────────┼──────────────────────────────────────────────┤
│ **4**   │ Working Decision Replay       │ Fixture S-MATH-01: +$238 net gain and 66.7%  │
│         │                               │ lateness cut via hotshot courier trade-off.  │
├─────────┼───────────────────────────────┼──────────────────────────────────────────────┤
│ **5**   │ Business Impact & Economics   │ Base: $50.3K net/rooftop (0.7 abs points).   │
│         │                               │ Strict 3-lens separation of $200M.           │
├─────────┼───────────────────────────────┼──────────────────────────────────────────────┤
│ **6**   │ Tekion Fit & Execution        │ Advisory ARC/APC overlay, host fail-open,    │
│         │                               │ phased roadmap, clear validation path.       │
└─────────┴───────────────────────────────┴──────────────────────────────────────────────┘
```

**Presentation Rule:** The slide deck must stand completely on its own. A judge reading the PDF slides without clicking the demo link must fully understand the problem, architecture, mathematics, and commercial ROI.

---

## 2. Slide Content Specifications

### Slide 1 — The Operational Leak: The Fixed Operations Paradox
- **Headline:** Fixed Ops Drives Dealership Profit — But Uncoordinated Parts Delays Paralyze the Workshop.
- **Visuals:** Split graphic showing high gross profit contribution (48–59% of dealership profit [PUBLIC: NADA]) vs an immobilized vehicle trapping a heavy hydraulic lift.
- **Three Core Pain Points:**
  1. *Bay Immobilization:* Disassembled vehicles physically trap specialist lifts waiting for delayed parts.
  2. *Cascading Promise Slips:* Customer NPS plunges from +72 to +29 when delivery slips [PUBLIC: CDK].
  3. *The Sourcing Siphon:* Parts departments buy from the cheapest supplier to save $30 on an invoice, unwittingly idling a $120/hour bay and destroying hundreds in shop labor.

---

### Slide 2 — ServiceYield AI: Predict · Optimise · Recover
- **Headline:** An Economic Decision Engine for Automotive Dealership Fixed Operations.
- **Visuals:** The 3-module loop connected by the canonical state store.
- **The Three Connected Modules:**
  - **PREDICT:** Anticipates readiness risks before vehicles are torn down. Four clean states: `READY`, `AT_RISK`, `BLOCKED`, `UNKNOWN`.
  - **OPTIMISE:** Allocates technicians, bays, and discrete time slots via OR-Tools CP-SAT to maximize economic contribution.
  - **RECOVER:** Instantly rebuilds a global schedule when a disruption hits, evaluating alternative multi-echelon sourcing.
- **Tagline:** *"Not a replacement DMS — an intelligent economic co-pilot for the Dealership Service Manager."*

---

### Slide 3 — How It Works: The Bay-Hour Shadow Price & Independent Verifier
- **Headline:** Grounded in Rigorous Mathematics, Operational Physics, and Execution Safety.
- **Key Concepts:**
  - **Bay-Hour Shadow Price ($\nu_b(t)$):** The marginal economic value of an available bay hour ($120/hr = $2.00/min). Acts as the shared economic language across Predict, Optimise, and Recover.
  - **Shared Constraints (C1–C7):** Identical physical rules across all modules: ACES fitment, part release, operation DAG, vehicle-lift immobility, flat-rate wage fairness, and customer authorization.
  - **L4 Independent Verifier:** An isolated sweep-line occupancy oracle that audits every plan before presentation. Only L4 can tag a plan "FEASIBLE".
  - **Human Authority & Fail-Open:** Service Manager approves all actions; if ServiceYield is offline, Tekion native dispatch continues seamlessly.

---

### Slide 4 — The Working Decision Replay: Fixture S-MATH-01
- **Headline:** Transforming a 3-Hour Stall Into a +$238 Net Dealership Win.
- **Visuals:** Side-by-side screenshot of the Decision Replay interface showing Option A (Wait) vs Option B (Hotshot Courier).
- **The Numbers (Clearly Labeled Synthetic Scenario):**
  - *Supplier S1 (Hotshot):* Costs +$37.00 extra freight, but delivers the solenoid 110 minutes earlier.
  - *Freed Bay Value:* 110 minutes × $2.00/min = **+$220.00**.
  - *Avoided Lateness Penalty:* 110 minutes × $0.50/min = **+$55.00**.
  - *Net Gain:* $+\$220.00 + \$55.00 - \$37.00 = \mathbf{+\$238.00}$.
  - *Lateness Impact:* Customer weighted lateness drops from **99 ticks to 33 ticks (-66.7%)**.
  - *Execution:* 100% verified against C1–C7; approved by Service Manager Marcus.

---

### Slide 5 — Business Impact & Transparent Commercial Economics
- **Headline:** $50.3K Net Economic Value per Rooftop — With Strict Evidentiary Discipline.
- **Visuals:** Three-tier financial scenario table (Low: $13.1K | Base: $50.3K | High: $90.1K).
- **The Three Distinct Financial Lenses:**
  1. *Dealer Value Created:* **$116M/year** across 2,300 rooftops by Year 5 ($50.3K/rooftop, ~0.7 absorption points).
  2. *Tekion Software ARR:* **$21.6M/year** in Year 5 (2,300 rooftops × $900/mo SaaS subscription).
  3. *Capitalized Equity Value:* **~$216M** enterprise valuation created for Tekion (at 10× software ARR).
- **Dealer ROI:** 4.7× return on software spend; payback achieved in **1.2 months**.

---

### Slide 6 — Tekion Fit, Team & Phased Execution
- **Headline:** The Natural Complement to Tekion ARC — Implementation-Ready.
- **Key Takeaways:**
  - *Why Tekion Wins:* Extends ARC/APC beyond scheduling into closed-loop economic dispatch. High-margin SaaS add-on driving platform retention.
  - *Phase 1 Roadmap:* Tier A MVP delivering deterministic Decision Replay, CP-SAT solver, verifier, and golden benchmark reproduction.
  - *Immediate Next Step:* Day 1 Shadow Mode to empirically validate the 5% parts delay rate across 3–5 pilot rooftops.

---

## 3. Five-Minute Spoken Narration Script

### [0:00 – 0:45] Slide 1: The Operational Leak
*"Good morning. In automotive retail, fixed operations is the engine that keeps the lights on. While car sales drive top-line volume, parts and service generate up to 59% of total dealership gross profit. Yet every single day, millions of dollars in fixed ops margin leak onto the shop floor.*  
*Here is how it happens: A customer brings in an SUV with a transmission shudder. The technician tears down the valve body on a heavy lift, only to discover a damaged solenoid. The parts coordinator orders a replacement from a sister store to save thirty dollars on freight. But that part won't arrive until tomorrow.*  
*Now, that vehicle is immobilized on the lift. The bay is trapped for four hours. Other customer appointments scheduled for that lift are bumped into the evening. Customer NPS collapses, the flat-rate technician sits idle with no pay, and the dealership loses hundreds in labor gross. This is the parts-delay paradox."*

### [0:45 – 1:30] Slide 2: ServiceYield AI
*"To solve this, we built ServiceYield AI. ServiceYield is not another chatbot, and it is not a replacement DMS. It is an economic decision engine built as an advisory overlay for Tekion ARC.*  
*ServiceYield connects three capabilities that have traditionally operated in disconnected silos: Predict, Optimise, and Recover.*  
*Predict monitors parts delivery telemetry and technician availability to flag readiness risks before vehicles are torn down.*  
*Optimise uses Google OR-Tools CP-SAT to generate a globally optimal, conflict-free workshop schedule.*  
*And Recover automatically calculates the best full-shop recovery plan when disruptions occur.*  
*Together, they answer one central question: How do we maximize the economic contribution of every service bay hour while rigorously protecting customer delivery promises?"*

### [1:30 – 2:15] Slide 3: How It Works
*"The core innovation linking these three modules is what we call the Bay-Hour Shadow Price—nu.*  
*Nu is the marginal economic value of an available service bay hour across space and time. During quiet morning hours, an extra open bay may have an economic value near zero. But on a Friday afternoon with six cars waiting, that heavy diagnostic lift is worth $120 an hour.*  
*By sharing nu across modules, Predict prioritizes parts checks for high-value bays, and Recover instantly knows whether spending extra money on expedited parts is justified.*  
*Crucially, ServiceYield is governed by seven hard operational constraints, C1 through C7—covering parts fitment, technician skills, mandatory lunch breaks, and vehicle physical state. To guarantee safety, every plan is audited by an independent L4 sweep-line verifier that shares zero constraint code with the solver. Furthermore, final authority remains with the Service Manager, and our architecture is fail-open: if ServiceYield is offline, Tekion's native dispatch continues without missing a beat."*

### [2:15 – 3:30] Slide 4: The Decision Replay
*"Let's look at this in action with our golden synthetic fixture, S-MATH-01.*  
*In this scenario, a dealership has six active repair orders, four technicians, and three bays. At 1:15 PM, a delivery van breaks down: a critical solenoid for RO-104 in Diagnostic Bay 1 is delayed by three hours. The vehicle is immobilized on the lift. In an unmitigated shop, this blows customer promises on both RO-104 and downstream RO-106, producing 99 weighted ticks of delay.*  
*ServiceYield's Recover engine triggers instantly. It identifies two viable sources:*  
*Option A is the sister store: zero freight cost, but the part arrives late, stalling the bay for 3.2 hours and resulting in a net economic loss of $275.*  
*Option B is an emergency hotshot courier: it costs an extra $37 in freight, but it delivers the part 110 minutes earlier.*  
*Because ServiceYield understands that Bay 1 generates $2.00 a minute, it calculates that freeing the bay is worth $220, and avoiding the customer delay is worth $55. Paying $37 for freight creates a net economic gain of +$238.*  
*The L4 verifier certifies the plan, Manager Marcus clicks Approve, and total customer lateness is slashed by 66.7%—from 99 ticks down to 33 ticks. Problem, recommendation, reason, approval, result."*

### [3:30 – 4:15] Slide 5: Business Impact & Economics
*"The financial upside for dealerships is substantial. In our base-case model—built on an average rooftop doing 16,300 annual ROs with 11 technicians—ServiceYield creates $50,300 in net annual economic value per rooftop. That represents an improvement of 0.7 points of fixed absorption, which translates to tens of millions in operating profit for large dealer groups.*  
*We maintain strict evidentiary discipline: we never conflate dealer value with product revenue.*  
*At a blended SaaS price of $900 a month, the dealership achieves payback in just 1.2 months with a 4.7× return on software spend.*  
*For Tekion, scaling this to 2,300 rooftops by Year 5 generates $21.6 million in high-margin annual software revenue—creating over $200 million in capitalized enterprise equity value."*

### [4:15 – 5:00] Slide 6: Tekion Fit & Execution
*"ServiceYield AI is the missing intelligence layer in automotive retail. It respects Tekion's existing platform, leverages Automotive Partner Cloud APIs, and ensures dealerships extract maximum gross margin from every square foot of their workshop.*  
*Our architecture is complete, our constraints are locked, and our Phase 1 development roadmap is ready for execution.*  
*Thank you, and we welcome your questions."*

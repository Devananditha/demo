# 16 — Team Responsibilities Framework & Executive Q&A Preparation

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 2.3, 3, 9.3, 14) & Product Blueprint (Section 15, Appendix)  
**Standard:** Role Governance & Defensive Judge Q&A Playbook (Phase 0)

---

## 1. Team Responsibility Framework

To maintain professional discipline and avoid inventing fictional team members, bios, or prior achievements, ServiceYield AI defines its engineering ownership as a **functional capability framework**. Actual team members map to these specific roles upon project kickoff:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FUNCTIONAL TEAM STRUCTURE                                 │
├──────────────────────────────────┬─────────────────────────────────────────────────────┤
│ FUNCTIONAL ROLE                  │ CORE SCOPE OF OWNERSHIP & DELIVERABLES              │
├──────────────────────────────────┼─────────────────────────────────────────────────────┤
│ **1. Product & Industry Lead**   │ Owns persona workflows, user storyboards, NADA/ fixed│
│                                  │ ops research, slide deck narrative, and ROI framing.│
├──────────────────────────────────┼─────────────────────────────────────────────────────┤
│ **2. Backend & Canonical State** │ Implements FastAPI endpoints, PostgreSQL schemas,   │
│                                  │ Alembic migrations, event ingestion, and OCC logic. │
├──────────────────────────────────┼─────────────────────────────────────────────────────┤
│ **3. Optimisation & CP-SAT**     │ Owns OR-Tools integer programming models, objective │
│                                  │ formulation, T1 bitset fallback, and $\nu_b(t)$ math│
├──────────────────────────────────┼─────────────────────────────────────────────────────┤
│ **4. Recovery & Sourcing Engine**│ Re-implements two-layer branch-and-bound sourcing,  │
│                                  │ candidate filtering, and Pareto trade-off ranker.   │
├──────────────────────────────────┼─────────────────────────────────────────────────────┤
│ **5. Predictive Readiness & Data**│ Implements Layer 1 empirical Bayes quantiles, slack │
│                                  │ analyzers, readiness rules, and calibration flags.  │
├──────────────────────────────────┼─────────────────────────────────────────────────────┤
│ **6. Frontend & Decision Replay**│ Builds React 18 / Vite / Tailwind UI, Gantt board,  │
│                                  │ disruption injection modal, and comparison screens. │
├──────────────────────────────────┼─────────────────────────────────────────────────────┤
│ **7. Verification & QA Lead**    │ Owns L4 sweep-line verifier, mutation test suites,  │
│                                  │ golden fixture S-MATH-01, and benchmark simulator.  │
└──────────────────────────────────┴─────────────────────────────────────────────────────┘
```

---

## 2. Executive Judge Q&A Preparation (12 Tough Questions)

### Q1: What exact problem does ServiceYield AI solve?
**Answer:**  
*"In automotive fixed operations, when a vehicle is disassembled on a lift and a replacement part is delayed, that vehicle physically immobilizes the bay. Schedulers don't know the bay is trapped, and parts coordinators order from whichever supplier is cheapest on paper—saving $30 on an invoice while destroying hundreds of dollars in bay capacity and blowing customer promises. ServiceYield solves the holistic workshop allocation problem by calculating the true economic trade-off between expedited parts freight and freed service bay capacity."*

### Q2: Why is this not just another AI service scheduler?
**Answer:**  
*"Appointment schedulers answer: 'When can a customer drop off their vehicle?' Dispatchers answer: 'Which technician gets this ticket?' ServiceYield does something fundamentally different: it evaluates the **joint economic loop** between repair readiness, resource allocation, and disruption recovery. Schedulers don't evaluate parts sourcing trade-offs, and procurement tools don't evaluate bay occupancy physics. ServiceYield bridges that exact operational chasm."*

### Q3: What precisely is novel about your system?
**Answer:**  
*"We do not claim that constraint programming, interval scheduling, or supplier comparison is individually new. Our specific novelty is the **Bay-Hour Shadow Price ($\nu_b(t)$)** acting as a shared cross-module economic signal between Predict, Optimise, and Recover, combined with an independent sweep-line verifier and an optimistic concurrency revalidation gate. It creates an explainable economic feedback loop that public materials show does not exist in dealership software today."*

### Q4: What is the Bay-Hour Shadow Price, and how do you calculate it?
**Answer:**  
*"The Bay-Hour Shadow Price, nu, is the marginal economic contribution gained by having an additional available hour of a specific bay type at a specific time. In our engine, it is computed via discrete re-solves: we measure the change in optimal shop contribution when bay capacity is incremented or decremented. In our canonical model, an active heavy diagnostic bay during peak hours has a shadow price of $120.00 per bay-hour, or $2.00 per bay-minute."*

### Q5: How do you know the chosen supplier is economically better?
**Answer:**  
*"Because we evaluate the complete global schedule, not the part in isolation. In fixture S-MATH-01, Supplier S1 costs an extra $37.00 in hotshot courier freight, but delivers the part 110 minutes earlier. At $2.00 per bay-minute, freeing that diagnostic lift generates $220.00 of productive capacity value, plus $55.00 in avoided customer lateness penalties. Saving $275.00 in operational losses at an expense of $37.00 yields a verified net gain of +$238.00."*

### Q6: How does the system prevent physically impossible or infeasible allocations?
**Answer:**  
*"Through our L4 Independent Verifier. The verifier shares zero constraint-building code with the solver; it is a separate sweep-line occupancy oracle. It verifies that no bay has two vehicles, no tech is double-booked, vehicle physical states (like IMMOBILIZED_ON_LIFT) are respected, technician lunch breaks are honored, and parts are physically inspected before work starts. If any constraint fails, the plan cannot be presented or approved."*

### Q7: What happens when supplier data or technician telemetry is missing or stale?
**Answer:**  
*"The system strictly fails closed. In Predict, missing data yields an explicit `UNKNOWN` state—we never guess readiness. In Recover, unconfirmed supplier quotes cannot be reserved. Furthermore, at the moment of manager approval, our Optimistic Concurrency Control checks the snapshot version: if shop state has mutated while the manager was reviewing, the commit aborts with HTTP 409 Conflict, and the system recalculates fresh."*

### Q8: Why should Tekion integrate this into ARC or APC rather than building it in-house?
**Answer:**  
*"Tekion has built exceptional infrastructure in ARC and APC, but fixed-ops yield optimization requires specialized mathematical programming and domain-specific constraint modeling. By adopting ServiceYield as an advisory partner app on APC, Tekion immediately monetizes a high-margin $900/month add-on, delivers an estimated $50.3K in annual value per rooftop, protects customer retention, and accelerates its competitive moat against CDK and Reynolds—without disrupting native DMS workflows."*

### Q9: What existing Tekion capabilities overlap with your proposal, and how do you handle that?
**Answer:**  
*"Tekion publicly offers Service AI for customer booking, Technician AI for mobile inspections, parts catalog integrations, and T1 workflow automation. We deliberately do not build appointment chatbots, mobile inspection video tools, or customer marketing outreach. We position ServiceYield strictly as an advisory decision co-pilot. If ServiceYield experiences any failure, our architecture is fail-open: Tekion's native scheduling continues uninterrupted."*

### Q10: What has actually been implemented versus merely designed?
**Answer:**  
*"In Phase 0, we have completed the product architecture, canonical state schemas, constraint specifications, API contracts, financial models, and workspace agent imports. In Phase 1, we implement the synthetic data generator, OR-Tools CP-SAT model, L4 sweep-line verifier, and the interactive Decision Replay. We explicitly state that live Tekion integrations and advanced LightGBM quantile models are Tier B/D roadmap enhancements, not current claims."*

### Q11: What is your financial model based on, and are these measured results?
**Answer:**  
*"They are NOT measured results from a live deployment; they are rigorous mathematical projections based on published NADA 2025 data, McKinsey fixed ops studies, and our stated assumptions register. Our base case assumes an average rooftop doing 16,300 annual ROs with an unbenchmarked 5% parts delay rate. The very first deliverable of our pilot is running in shadow mode to empirically measure that 5% baseline."*

### Q12: What are the primary technical and commercial limitations of this product?
**Answer:**  
*"Technically, CP-SAT integer programming is computationally intensive; on massive 50-bay dealerships, solves must be bounded with our T1 priority-rule heuristic. Commercially, our financial model depends heavily on dealership technician utilization and parts delay frequency. If a dealership operates with excess bay capacity and zero demand backlog, the shadow price approaches zero, and the economic return will be closer to our low-case estimate of $13.1K."*

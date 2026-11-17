# ServiceYield AI — Project Operating Rules & Governance Policy

**Project:** ServiceYield AI  
**Tagline:** Predict · Optimise · Recover  
**Classification:** Hackathon Engineering Governance Document  
**Status:** Frozen & Active (Phase 0)  
**Authoritative Reference:** ServiceYield AI Technical, Financial and Regulatory Report (Nov 2026) & Product Blueprint (v1.0)

---

## 1. Greenfield Implementation Mandate
1. **Clean Slate Development:** ServiceYield AI is an entirely greenfield implementation. No code, scripts, database schemas, or artifacts from the previous StallBreaker repository may be cloned, copied, accessed, or incorporated.
2. **Design Inspiration Only:** The algorithms described in the technical documentation (such as the two-layer branch-and-bound search and lexicographic recovery scalarisation) must be reimplemented from first principles in the approved modern stack.
3. **No Legacy Bloat:** No legacy dependencies, technical debt, or deprecated architecture patterns from earlier iterations shall enter this codebase.

---

## 2. Locked Product Decisions
The following product decisions are immutable for the hackathon MVP. Any proposal to alter them requires explicit written justification and external review:
1. **Product Identity:** ServiceYield AI is an economic decision-intelligence platform for automotive dealership fixed operations. Its sole operational objective is:
   $$\text{Maximise economic contribution per available service-bay hour while protecting customer delivery promises.}$$
2. **Positioning:** Positioned strictly as an advisory, decision-support, and optimisation extension to Tekion Automotive Retail Cloud (ARC) or Automotive Partner Cloud (APC). It is **NOT** a Dealership Management System (DMS) replacement, appointment scheduling bot, customer marketing tool, or flat-rate payroll engine.
3. **Primary Persona:** The **Dealership Service Manager** is the sole primary persona for the initial demonstrator. Secondary personas (Service Advisors, Parts Coordinators, Workshop Controllers, Technicians) inform interfaces and workflows, but MVP workflows must address the Service Manager's daily high-stakes operational trade-offs.
4. **The Central Problem:** When a critical part becomes delayed or unavailable during an active repair order (RO), the vehicle frequently stalls in a specialised bay, cascading delays across technician schedules, customer promises, and workshop capacity. The platform solves the holistic workshop allocation problem—not merely finding a cheaper part.
5. **Core Novelty & USP:** The shared, constraint-aware economic decision loop connecting Predict, Optimise, and Recover via a unified **Bay-Hour Shadow Price** ($\nu_b(t)$). Do not claim AI scheduling or parts sourcing alone is novel.

---

## 3. Frozen Technology Direction
The architectural stack is frozen as follows. No additional frameworks, databases, or service tiers may be introduced without documented architectural review:
- **Backend Core:** Python 3.12, FastAPI, Pydantic v2.
- **Persistence & ORM:** PostgreSQL, SQLAlchemy 2.0 (async/typed), Alembic migrations.
- **Optimisation Engine:** Google OR-Tools CP-SAT (Constraint Programming - Satisfiability) with a deterministic priority-rule heuristic fallback (T1).
- **Data & Numerical Evaluation:** NumPy, Pandas.
- **Frontend Presentation:** React 18+, TypeScript, Vite, Tailwind CSS.
- **Testing & Verification:** Pytest, Hypothesis (property-based testing), mutation testing.
- **Containerisation:** Docker for reproducible local execution.
- **Machine Learning Scope:** Deterministic empirical Layer 1 baseline mandatory for MVP. LightGBM quantile regression and conformal calibration are Phase 1 Tier B enhancements and must not delay the deterministic core.
- **Workflow Orchestration:** n8n evaluated solely for external event routing, SMS/email alerts, and approval routing. CP-SAT, constraints, and economics must never run inside n8n.

---

## 4. Shared Constraint Model (C1–C7)
All three decision services (Predict, Optimise, Recover) and the independent verifier must import and respect the identical canonical constraint definitions:
- **C1 — Eligibility:** Part fitment compatibility, technician certification/skills, bay capability compatibility, customer repair order validity.
- **C2 — Part Release & Availability:** Task execution cannot begin before required parts are physically received, inspected, and usable-ready ($S_o \ge \text{usable\_ready}(p)$).
- **C3 — Operation Precedence:** Mandatory directed acyclic graph (DAG) of repair stages (e.g., diagnosis $\to$ teardown $\to$ mechanical repair $\to$ reassembly $\to$ quality check/calibration).
- **C4 — Resource Exclusivity & Vehicle-Bay Semantics:** A bay can accommodate at most one vehicle at any tick. A technician can work on at most one operation at any tick. **A vehicle is NOT a service bay**: vehicles are physical entities that occupy bays or holding areas.
- **C5 — Vehicle Movement & Physical State:** Operational state gates (`IMMOBILIZED_ON_LIFT`, `ROLLABLE`, `IN_HOLDING`, `MOVE_PENDING`, `UNKNOWN`). Vehicles cannot leave a lift unless rollable or towed; `MOVE_PENDING` does not free bay capacity until completion; `UNKNOWN` state blocks all movement.
- **C6 — Technician Shifts, Breaks & Fairness:** Technicians work strictly within active shifts; mandatory meal and rest intervals must be enforced; flat-rate allocations must remain within a $\pm 15\%$ rolling two-week fairness band across peer technicians.
- **C7 — Authority, Approvals & Financial Limits:** No repair work begins without recorded customer authorisation; safety/recall repairs cannot be reordered or deprioritised; supplier POs exceeding threshold require manager approval; commits require fresh-state revalidation.

Hard constraints **must never be traded away** for economic gain, higher contribution, or schedule compression.

---

## 5. Independent Verifier Mandate (L4)
1. **Separate Implementation:** The L4 Verifier must be an entirely independent code module. It must **not** share constraint-construction or data-structure code with the L3 CP-SAT solver or heuristic dispatchers.
2. **Occupancy Sweep Oracle:** The Verifier validates plans using an independent sweep-line occupancy oracle, re-checking resource conflicts, precedence, parts timing, and physical state transitions.
3. **Sole Authority on Feasibility:** Only the L4 Verifier is authorised to certify a plan as `FEASIBLE` or `VERIFIED`. The solver's internal `OPTIMAL` or `FEASIBLE` status is treated as an advisory claim until certified by L4.
4. **Mutation-Tested:** The test suite must include mutation tests deliberately injecting constraint violations into solver output; the Verifier must reject 100% of injected corruptions.

---

## 6. LLM Authority Restrictions & LLM-Disabled Parity
1. **Explanatory & Ingestion Role Only:** Large Language Models (LLMs) are strictly restricted to assisting human users: translating free-text advisor notes into candidate entities, drafting plain-English explanations for recommended plans, or answering conversational questions.
2. **No Authoritative Decision-Making:** An LLM may never:
   - Calculate or alter economic values, margins, or shadow prices.
   - Determine or override parts fitment or eligibility.
   - Relax or bypass hard constraints C1–C7.
   - Validate plan feasibility.
   - Authorise or commit a schedule change or parts purchase order.
3. **LLM-Disabled Parity:** The entire core system (Predict, Optimise, Recover, Verifier, Approval) must execute with 100% functional and mathematical parity when the LLM service is completely disabled or unreachable.

---

## 7. Synthetic Data Governance & Privacy
1. **100% Synthetic Data:** All demonstration and test fixtures must use synthetic, generated, or mock dealership data.
2. **Zero Confidential Data:** Under no circumstances shall real customer PII, real Vehicle Identification Numbers (VINs), real employee flat-rate payroll records, proprietary OEM warranty data, or real dealer credentials be introduced into the repository.
3. **Prominent UI Labelling:** All user-facing views, dashboards, API payloads, and presentation slides must explicitly display:  
   `[SYNTHETIC DEMO DATA — NOT A CLAIM OF LIVE TEKION INTEGRATION OR MEASURED DEALERSHIP ROI]`.
4. **Reproducible Scenario Seeds:** All synthetic scenarios must run with deterministic pseudo-random seeds to ensure reproducible evaluations and identical benchmark baselines.

---

## 8. Evidence Disciplines & Claims Integrity
Every performance metric, financial figure, or operational statement must carry an authoritative provenance tag:
- `[PUBLIC]`: Verified external public source (e.g., NADA Data 2025, McKinsey automotive studies, Tekion corporate press releases).
- `[MODEL]`: Calculated output generated directly by the financial or mathematical model.
- `[ASSUMPTION]`: Unvalidated planning input requiring empirical verification.
- `[INFERENCE]`: Strategic, product, or competitive interpretation.
- `[VALIDATE]`: Open hypothesis requiring formal confirmation from Tekion, dealerships, or legal counsel.

**Forbidden Claims:**
- Never claim "no dealership software has scheduling" or "Tekion lacks technician intelligence".
- Never claim ServiceYield is the "first-ever AI scheduler".
- Never cite synthetic demo results as "measured dealership ROI".
- Never conflate dealer economic value, Tekion software revenue, and Tekion enterprise valuation.

---

## 9. Host Fail-Open Principle
1. **Advisory Overlay:** ServiceYield AI is strictly an advisory co-pilot.
2. **Graceful Fail-Open:** If ServiceYield AI experiences network disconnection, database failure, solver timeouts, verifier rejections, or corrupted state, the host dealership system (Tekion ARC) must immediately continue its native dispatch and scheduling without interruption.
3. **Read-Only / Degraded Operation:** Under partial failure, the system falls back to cached snapshot views, marks predictions as `DEGRADED`, reverts to T1 priority rules, and disables automated writebacks.

---

## 10. Scope Control & Phase Gates
1. **Phase 0 Integrity:** In Phase 0, no application source files, migrations, or frontend code may be written. Phase 0 is complete only upon formal review of all architectural documentation and agent imports.
2. **Gate Discipline:** Implementation in Phase 1 proceeds strictly through sequential, test-gated milestones (Tier A core MVP first; Tier B/C enhancements strictly deferred until Tier A passes end-to-end replay verification).
3. **No Unilateral Scope Creep:** No engineer or agent may add new entities, unapproved third-party integrations, multi-rooftop SaaS architectures, or autonomous dispatch agents without explicit approval.

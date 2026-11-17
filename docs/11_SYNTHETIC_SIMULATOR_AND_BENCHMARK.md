# 11 — Synthetic Simulator & Benchmark Evaluation Design

**Project:** ServiceYield AI  
**Authoritative Reference:** Technical Report (Sections 10, 11) & Product Blueprint (Sections 10, 11)  
**Standard:** Rigorous Paired-Seed Experimental Protocol (Phase 0)

---

## 1. Benchmark Policy Arms

To demonstrate scientific rigor before hackathon judges and avoid strawman comparisons, ServiceYield AI defines six explicit policy arms for comparative evaluation:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              BENCHMARK POLICY TAXONOMY                                 │
├──────────┬─────────────────────────────┬───────────────────────────────────────────────┤
│ POLICY   │ FORMAL DESIGNATION          │ OPERATIONAL BEHAVIOR                          │
├──────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ **P0**   │ No Intervention             │ Freezes initial schedule; vehicles wait       │
│          │                             │ passively for original supplier delivery.     │
├──────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ **P1**   │ Manager-Style Heuristic     │ Local rules: picks cheapest in-stock part;   │
│          │                             │ dispatches first-available technician.        │
├──────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ **A2**   │ Sequential Sourcing First   │ Sourcing module selects cheapest eligible     │
│          │                             │ part; exact CP-SAT reschedules around it.    │
├──────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ **A2+**  │ Sourcing with Lookahead     │ Sourcing selects part with bay availability   │
│          │ (Strong State-of-the-Art)   │ heuristic; CP-SAT reschedules global shop.    │
├──────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│ **P3**   │ Integrated ServiceYield AI  │ Fully coupled decision loop: Predict + CP-SAT │
│          │ (Proposed Engine)           │ with Bay-Hour Shadow Price $\nu_b(t)$ feedback.│
├──────────┼─────────────────────────────┼───────────────────────────────────────────────┤
│**P3-mono** Correctness Ablation        │ P3 without vehicle physical state constraints │
│          │                             │ (proves necessity of lift-trapping gates).    │
└──────────┴─────────────────────────────┴───────────────────────────────────────────────┘
```

**Discipline Rule:** P3’s superiority claim must be proven against **A2+**, not merely against P0 (doing nothing) or P1 (crude rules).

---

## 2. Seven Scenario Families (F1–F7)

The evaluation suite tests policies across seven distinct workshop operational environments:

| Code | Scenario Family Name | Structural Characteristics & Test Focus | Expected Policy Dynamic |
| :--- | :--- | :--- | :--- |
| **F1** | **Specialised-Bay Contention** | Heavy demand for 1–2 specialist lifts (e.g. EV battery isolation or heavy alignment). | **Core Test:** Coupling via $\nu_b(t)$ should produce large gains over A2+. |
| **F2** | **Abundant-Bay Null Control** | Excess bay capacity relative to repair orders ($\text{Bays} \ge \text{ROs}$). | **Null Control:** P3 must NOT degrade performance or increase costs vs A2+. |
| **F3** | **Saturated Holding Lot** | Parking staging stalls are 100% full; vehicle relocation is physically blocked. | P3 physical state machine prevents invalid lot moves. |
| **F4** | **ETA Slip After Commit** | Part delivery slips *after* the initial recovery plan has already been committed. | Tests re-planning stability, churn penalties, and rolling horizon. |
| **F5** | **Competing Reservation** | Two active ROs simultaneously compete for the last available in-stock component. | S-MATH-01 style economic shadow price arbitration. |
| **F6** | **Unknown Part at Teardown** | RO enters shop as general complaint; teardown reveals unexpected required part. | Tests UNKNOWN state handling and dynamic BOM expansion. |
| **F7** | **Stale Supplier Quote** | Quoted supplier offer expires (ATP timeout) before Service Manager clicks approval. | Tests OCC read-set revalidation and safe abort handling. |

---

## 3. Predeclared Evaluation Metrics

The simulator logs eight predeclared metrics for every run:

1. **Net Realized Economic Value ($\Delta \text{Value}_{\text{USD}}$):** Incremental gross labor and parts contribution minus incremental expedite freight, promise penalties, and churn costs.
2. **Weighted Promise Lateness ($\sum w_r \max(0, C_r - D_r)$):** Total customer promise slip weighted by customer priority.
3. **Bay-Blocked Hours ($\text{Hours}_{\text{blocked}}$):** Hours high-value lifts sit immobilized waiting for parts without active labor.
4. **Productive Bay Utilisation ($\%$):** $\frac{\text{Active Tool Time}}{\text{Available Compatible Bay Time}} \times 100\%$.
5. **Incremental Sourcing Surcharges ($\$_{\text{freight}}$):** Total expedited delivery fees incurred.
6. **Hard Constraint Violations:** Count of C1–C7 breaches (Target: **0.00** after L4 Verifier).
7. **Schedule Churn Index:** Sum of absolute task start-time shifts imposed on already-planned jobs.
8. **Stale-State Abort Rate ($\%$):** Percentage of plans rejected at commit due to concurrent state mutation.

---

## 4. Experimental Discipline & Statistical Rigor

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAIRED-SEED SIMULATION HARNESS                            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   • Paired Common Random Numbers (CRN): For every seed $s \in [1, 100]$, policies      │
│     P0, P1, A2, A2+, and P3 receive bit-exact identical arrival times, vehicle types,   │
│     complaints, technician rosters, and disruption shock timing.                       │
│                                                                                        │
│   • Statistical Significance: Evaluated using 95% paired bootstrap confidence          │
│     intervals with Holm-Bonferroni correction across multi-family hypothesis tests.     │
│                                                                                        │
│   • Full Reproducibility: All random generators use fixed 64-bit integer seeds         │
│     recorded in the simulation telemetry headers.                                      │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Go / No-Go Acceptance Gate

Before presenting commercial or algorithmic superiority claims to hackathon judges, the system must pass this formal acceptance condition:

$$\begin{aligned}
\mathbf{Go/No\text{-}Go\ Condition:} \quad 
&1.\ \mathbb{E}[\text{Lateness}_{P3} - \text{Lateness}_{A2+}] < 0 \quad (\text{in } F_1 \text{ and } F_3, \text{CI excludes 0}) \\
&2.\ \mathbb{E}[\text{Value}_{P3} - \text{Value}_{A2+}] > 0 \quad (\text{in } F_1 \text{ and } F_3, \text{CI excludes 0}) \\
&3.\ |\mathbb{E}[\text{Value}_{P3} - \text{Value}_{A2+}]| < \epsilon \quad (\text{in } F_2 \text{ null control, no degradation}) \\
&4.\ \text{Hard Constraint Violations}_{P3} \equiv 0 \quad (\text{verified by L4 Oracle})
\end{aligned}$$

### Repositioning Protocol (If P3 Does Not Beat A2+):
If experimental results show that P3’s CP-SAT coupling does not statistically beat A2+ in contention scenarios:
- **Do NOT manufacture or falsify superiority.**
- **Reposition immediately:** Pivot the core presentation to ServiceYield’s **execution integrity, independent verification guarantee, physical state safety, and transparent economic explainability**.

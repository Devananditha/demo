# 09 — API Specifications & Module Contracts

**Project:** ServiceYield AI  
**Authoritative Reference:** Product Blueprint (Sections 8, 9) & Technical Report (Section 5.1)  
**Standard:** OpenAPI 3.1 / FastAPI / Pydantic v2 Contract Specifications

---

## 1. REST API Architecture Overview

The ServiceYield AI backend exposes a strongly-typed, versioned REST API. All mutation requests require a `snapshot_hash` to guarantee consistency under Optimistic Concurrency Control (OCC):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SERVICEYIELD REST API ENDPOINTS                           │
├──────────────────────────┬────────┬────────────────────────────────────────────────────┤
│ ENDPOINT                 │ METHOD │ DESCRIPTION                                        │
├──────────────────────────┼────────┼────────────────────────────────────────────────────┤
│ `/api/v1/events`         │ POST   │ Ingests external shop telemetry events.            │
│ `/api/v1/state`          │ GET    │ Retrieves the current canonical shop snapshot.     │
│ `/api/v1/predict/readiness`│ POST │ Calculates 4-state readiness and intervals.        │
│ `/api/v1/optimise/plan`  │ POST   │ Computes baseline schedule & $\nu_b(t)$ via CP-SAT.│
│ `/api/v1/recover/options`│ POST   │ Evaluates multi-source recovery alternatives.      │
│ `/api/v1/plans/{id}/verify`│ POST │ Runs L4 sweep-line verifier against constraints.   │
│ `/api/v1/plans/{id}/approve`│ POST│ Records Service Manager authorization.             │
│ `/api/v1/plans/{id}/commit`│ POST │ Executes OCC revalidation and simulated commit.    │
│ `/api/v1/plans/{id}`     │ GET    │ Retrieves plan assignments, economics & metrics.   │
│ `/api/v1/bay-prices`     │ GET    │ Retrieves current Bay-Hour Shadow Price surface.   │
└──────────────────────────┴────────┴────────────────────────────────────────────────────┘
```

---

## 2. Core Endpoint Specifications

### 2.1 Ingest Operational Event (`POST /api/v1/events`)
Ingests validated events from the synthetic simulator or future Tekion webhook stream.

**Request Payload:**
```json
{
  "event_id": "evt-20261118-001",
  "rooftop_id": "ROOF-01",
  "event_type": "PARTS_ETA_DELAYED",
  "entity_type": "PART_REQUIREMENT",
  "entity_id": "PART-104-SOLENOID",
  "payload": {
    "ro_id": "RO-104",
    "previous_eta": "2026-11-18T13:30:00Z",
    "new_eta": "2026-11-18T16:30:00Z",
    "delay_minutes": 180,
    "supplier_id": "OEM_PRIMARY",
    "reason_code": "COURIER_BREAKDOWN"
  },
  "occurred_at": "2026-11-18T13:15:00Z"
}
```

**Response (201 Created):**
```json
{
  "status": "ACCEPTED",
  "event_id": "evt-20261118-001",
  "new_snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "requires_recovery": true
}
```

---

### 2.2 Calculate Readiness (`POST /api/v1/predict/readiness`)
Evaluates readiness states and usable-ready intervals for all active ROs.

**Request Payload:**
```json
{
  "rooftop_id": "ROOF-01",
  "snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

**Response (200 OK):**
```json
{
  "rooftop_id": "ROOF-01",
  "snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "assessments": [
    {
      "ro_id": "RO-104",
      "state": "AT_RISK",
      "p_delay": 0.38,
      "usable_ready_ticks": { "p10": 164, "p50": 172, "p90": 188 },
      "calibration": "CALIBRATED_LIGHT",
      "reasons": ["SUPPLIER_ETA_TIGHT_SLACK", "SPECIALIST_BAY_REQUIRED"],
      "data_freshness_seconds": 30
    },
    {
      "ro_id": "RO-105",
      "state": "BLOCKED",
      "p_delay": 1.0,
      "usable_ready_ticks": null,
      "calibration": "UNCALIBRATED",
      "reasons": ["PART_BACKORDERED_NO_ETA"],
      "data_freshness_seconds": 12
    }
  ]
}
```

---

### 2.3 Generate Optimised Plan (`POST /api/v1/optimise/plan`)
Executes OR-Tools CP-SAT discrete optimization over the snapshot.

**Request Payload:**
```json
{
  "rooftop_id": "ROOF-01",
  "snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "time_budget_seconds": 2.5,
  "solver_seed": 42
}
```

**Response (200 OK):**
```json
{
  "plan_id": "PLAN-20261118-001",
  "rooftop_id": "ROOF-01",
  "snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "solver_tier": "T2_CPSAT",
  "solver_status": "OPTIMAL",
  "optimality_gap": 0.0,
  "objective_usd": 2840.00,
  "metrics": {
    "gross_contribution_usd": 2840.00,
    "sourcing_cost_usd": 0.00,
    "weighted_lateness_ticks": 0,
    "bay_blocked_ticks": 0,
    "schedule_churn_score": 0
  },
  "assignments_count": 8,
  "created_at": "2026-11-18T13:16:00Z"
}
```

---

### 2.4 Evaluate Recovery Alternatives (`POST /api/v1/recover/options`)
Evaluates multi-sourcing alternatives and computes holistic schedule trade-offs.

**Request Payload:**
```json
{
  "rooftop_id": "ROOF-01",
  "snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "disrupted_ro_id": "RO-104",
  "disrupted_part_id": "PART-104-SOLENOID"
}
```

**Response (200 OK):**
```json
{
  "disrupted_ro_id": "RO-104",
  "recommendation": "OPTION_B",
  "rationale": "Option B (Hotshot S1) pays +$37 freight but frees Diagnostic Bay 1 at 2:00 PM, preventing a 2-hour delay on RO-106. Net gain: +$238.00.",
  "options": [
    {
      "option_id": "OPTION_A",
      "supplier_name": "Sister Store S2 (Ground)",
      "sourcing_surcharge_usd": 0.00,
      "usable_ready_tick": 204,
      "weighted_lateness_ticks": 99,
      "bay_blocked_hours": 3.2,
      "net_recovery_value_usd": -275.00,
      "is_recommended": false,
      "candidate_plan_id": "PLAN-REC-OPT-A"
    },
    {
      "option_id": "OPTION_B",
      "supplier_name": "Hotshot Courier S1 (Dedicated)",
      "sourcing_surcharge_usd": 37.00,
      "usable_ready_tick": 168,
      "weighted_lateness_ticks": 33,
      "bay_blocked_hours": 1.4,
      "net_recovery_value_usd": 238.00,
      "is_recommended": true,
      "candidate_plan_id": "PLAN-REC-OPT-B"
    }
  ]
}
```

---

### 2.5 Verify Plan (`POST /api/v1/plans/{id}/verify`)
Runs the independent L4 sweep-line verifier.

**Response (200 OK):**
```json
{
  "plan_id": "PLAN-REC-OPT-B",
  "verifier_passed": true,
  "verifier_version": "v1.0-sweep-oracle",
  "checks": {
    "C1_eligibility": "PASS",
    "C2_part_release": "PASS",
    "C3_precedence": "PASS",
    "C4_resource_exclusivity": "PASS",
    "C5_vehicle_movement": "PASS",
    "C6_technician_shifts_breaks": "PASS",
    "C7_authority_approvals": "PASS"
  },
  "violations_found": 0,
  "verified_at": "2026-11-18T13:17:02Z"
}
```

---

### 2.6 Manager Approval & Commit (`POST /api/v1/plans/{id}/commit`)
Executes OCC revalidation and simulated commit.

**Request Payload:**
```json
{
  "approver_id": "USER-MARCUS-SM",
  "snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "approval_notes": "Authorized $37 hotshot freight to release Bay 1 for RO-106."
}
```

**Success Response (200 OK):**
```json
{
  "status": "COMMITTED",
  "plan_id": "PLAN-REC-OPT-B",
  "committed_at": "2026-11-18T13:17:15Z",
  "outbox_events_dispatched": 2
}
```

**Stale State Abort (409 Conflict):**
```json
{
  "status": "ABORTED_STALE_STATE",
  "error_code": "OCC_VERSION_MISMATCH",
  "message": "Dealership state changed while reviewing proposal. Commit rejected.",
  "expected_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "current_hash": "4f9b8c2d1e..."
}
```

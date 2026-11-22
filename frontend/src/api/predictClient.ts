import {
  CandidateSchedulePlan,
  CommitResult,
  DealershipReadinessReport,
  DealershipStateResponse,
  EventIngestResponse,
  RecoveryRecommendationResponse,
  ScheduleResult,
  ScheduleVerificationResult,
  StallBreakerDisruptionAnalysis,
  StallBreakerRecoveryReport,
  StoredEvent,
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000';

export async function fetchCanonicalState(): Promise<DealershipStateResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/state`);
  if (!res.ok) {
    throw new Error(`Failed to load canonical state (HTTP ${res.status}: ${res.statusText})`);
  }
  return res.json();
}

export async function fetchPredictReadiness(
  rooftopId: string,
  snapshotHash: string
): Promise<DealershipReadinessReport> {
  const res = await fetch(`${API_BASE_URL}/api/v1/predict/readiness`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      rooftop_id: rooftopId,
      snapshot_hash: snapshotHash,
    }),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // fallback to status text
    }
    throw new Error(`Predict API Error (HTTP ${res.status}): ${detail}`);
  }

  return res.json();
}

export async function fetchInitialSchedule(
  rooftopId: string,
  snapshotHash: string,
  allowEmergencyOvertime: boolean = false,
  timeBudgetSeconds: number = 2.5
): Promise<ScheduleResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/optimise/schedule`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      rooftop_id: rooftopId,
      snapshot_hash: snapshotHash,
      allow_emergency_overtime: allowEmergencyOvertime,
      time_budget_seconds: timeBudgetSeconds,
    }),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // fallback to status text
    }
    throw new Error(`Schedule API Error (HTTP ${res.status}): ${detail}`);
  }

  return res.json();
}

export async function fetchRecoveryReplan(
  rooftopId: string,
  snapshotHash: string,
  disruptedRoId: string = 'RO-104',
  primarySupplierDelayMinutes: number = 180,
  allowEmergencyOvertime: boolean = true
): Promise<RecoveryRecommendationResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/recover/replan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      rooftop_id: rooftopId,
      snapshot_hash: snapshotHash,
      disrupted_ro_id: disruptedRoId,
      disrupted_part_req_id: 'PART-REQ-104-SOLENOID',
      trigger_tick: 159,
      primary_supplier_delay_minutes: primarySupplierDelayMinutes,
      allow_emergency_overtime: allowEmergencyOvertime,
    }),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // fallback to status text
    }
    throw new Error(`Recovery Replan Error (HTTP ${res.status}): ${detail}`);
  }

  return res.json();
}

export async function fetchStallBreakerState(): Promise<DealershipStateResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stallbreaker/state`);
  if (!res.ok) {
    throw new Error(`Failed to load StallBreaker state (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchStallBreakerEvents(): Promise<StoredEvent[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stallbreaker/events`);
  if (!res.ok) {
    throw new Error(`Failed to load StallBreaker events (HTTP ${res.status})`);
  }
  return res.json();
}

export async function ingestStallBreakerEvent(event: {
  event_id: string;
  rooftop_id?: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, any>;
  signature?: string;
}): Promise<EventIngestResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stallbreaker/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(event),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // fallback
    }
    throw new Error(`Event Ingest Error (HTTP ${res.status}): ${detail}`);
  }
  return res.json();
}

export async function fetchStallBreakerDisruptionAnalysis(eventId: string): Promise<StallBreakerDisruptionAnalysis> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stallbreaker/disruption-analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_id: eventId }),
  });
  if (!res.ok) {
    throw new Error(`Disruption Analysis Error (HTTP ${res.status})`);
  }
  return res.json();
}

export async function fetchStallBreakerRecovery(
  eventId: string,
  allowEmergencyOvertime: boolean = true
): Promise<StallBreakerRecoveryReport> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stallbreaker/recovery-recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      event_id: eventId,
      allow_emergency_overtime: allowEmergencyOvertime,
    }),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // fallback
    }
    throw new Error(`Recovery Recommendations Error (HTTP ${res.status}): ${detail}`);
  }
  return res.json();
}

export async function verifyCandidatePlan(
  rooftopId: string,
  snapshotHash: string,
  plan: CandidateSchedulePlan,
  eventId?: string
): Promise<ScheduleVerificationResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/verifier/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      rooftop_id: rooftopId,
      snapshot_hash: snapshotHash,
      plan,
      ...(eventId ? { event_id: eventId } : {}),
    }),
  });
  if (!res.ok) {
    let detail = 'Verification request failed';
    try {
      const errData = await res.json();
      detail = errData.detail || detail;
    } catch {
      // fallback
    }
    throw new Error(`Verifier Error (HTTP ${res.status}): ${detail}`);
  }
  return res.json();
}

export async function approveStallBreakerRecovery(
  planId: string,
  eventId: string,
  expectedHash: string,
  approverId: string = 'MGR-MARCUS',
  approvedFreightUsd: number = 50.0
): Promise<CommitResult> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stallbreaker/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      plan_id: planId,
      event_id: eventId,
      expected_snapshot_hash: expectedHash,
      approver_id: approverId,
      approved_freight_usd: approvedFreightUsd,
      approval_notes: `Authorized StallBreaker recovery for event ${eventId}.`,
    }),
  });
  if (!res.ok) {
    throw new Error(`Approval Error (HTTP ${res.status})`);
  }
  return res.json();
}


export async function fetchBenchmarkResults(seed: number = 42): Promise<import('../types').BenchmarkSuiteReport> {
  const res = await fetch(`${API_BASE_URL}/api/v1/benchmark/results?seed=${seed}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch benchmark results (HTTP ${res.status})`);
  }
  return res.json();
}

export async function triggerBenchmarkRun(seed: number = 42): Promise<import('../types').BenchmarkSuiteReport> {
  const res = await fetch(`${API_BASE_URL}/api/v1/benchmark/run?seed=${seed}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger benchmark run (HTTP ${res.status})`);
  }
  return res.json();
}

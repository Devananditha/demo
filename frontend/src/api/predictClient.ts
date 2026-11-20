import { DealershipReadinessReport, DealershipStateResponse } from '../types';

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

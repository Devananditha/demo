export type ReadinessStatus = 'READY' | 'AT_RISK' | 'BLOCKED' | 'UNKNOWN';

export interface RepairOrder {
  roId: string;
  vehicle: string;
  customerName: string;
  customerComplaint: string;
  bay: string;
  physicalState: string;
  technician: string;
  promisedDelivery: string;
  promiseTick: number;
  readinessStatus: ReadinessStatus;
  readinessDetails: string;
  laborGrossUsd: number;
  priorityWeight: number;
}

export interface KpiSummary {
  activeRos: number;
  activeTechnicians: string;
  operationalBays: string;
  potentialLaborGross: string;
}

export interface StageInfo {
  id: number;
  name: string;
  shortLabel: string;
  status: 'active' | 'upcoming';
  description: string;
}

export interface QuantileInterval {
  p10: number;
  p50: number;
  p90: number;
}

export interface OperationalSlack {
  latest_feasible_start_tick: number;
  usable_ready_tick?: number | null;
  slack_ticks?: number | null;
  slack_minutes?: number | null;
  slack_p10_ticks?: number | null;
  slack_p50_ticks?: number | null;
  slack_p90_ticks?: number | null;
  evaluation_slack_ticks?: number | null;
  evaluation_slack_minutes?: number | null;
}

export interface RepairOrderAssessment {
  ro_id: string;
  snapshot_hash: string;
  state: ReadinessStatus;
  reasons: string[];
  p_delay: number;
  usable_ready_ticks?: QuantileInterval | null;
  slack?: OperationalSlack | null;
  calibration?: string;
  calibration_status?: string;
  data_freshness_seconds?: number;
  has_recovery_alternative?: boolean;
  best_alternative_usable_tick?: number | null;
  best_alternative_slack_minutes?: number | null;
  computed_at?: string;
}

export interface DealershipReadinessReport {
  rooftop_id: string;
  snapshot_hash: string;
  assessments: RepairOrderAssessment[];
  summary_counts: Record<string, number>;
  computed_at: string;
}

export interface DealershipStateItem {
  ro_id: string;
  status: string;
  physical_state: string;
  assigned_bay_id?: string | null;
  promise_tick: number;
}

export interface DealershipStateResponse {
  rooftop_id: string;
  snapshot_hash: string;
  evaluation_tick: number;
  operating_day_end_tick: number;
  overtime_cutoff_tick: number;
  repair_orders: DealershipStateItem[];
}

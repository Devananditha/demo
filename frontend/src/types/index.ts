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

export interface DisruptionSupplierOption {
  supplierId: string;
  supplierName: string;
  partNumber: string;
  quotedEtaTick: number;
  receivingInspectionMinutes: number;
  usableReadyTick: number;
  usableReadyTime: string;
  freightSurchargeUsd: number;
  status: string;
  impactSummary: string;
}

export interface DisruptionTimelineMilestone {
  tick: number;
  time: string;
  label: string;
  type: string;
  description: string;
  badgeColor: 'rose' | 'emerald' | 'amber' | 'orange' | 'slate' | 'purple';
}

export interface SyntheticDisruptionScenario {
  scenarioName: string;
  fixtureVersion: string;
  classification: string;
  disruptionType: string;
  triggerTick: number;
  triggerTime: string;
  delayMinutes: number;
  affectedRoId: string;
  affectedVehicle: string;
  affectedCustomer: string;
  affectedBayId: string;
  affectedBayName: string;
  vehicleState: string;
  constraintNote: string;
  stalledTask: {
    taskId: string;
    description: string;
    completedPredecessor: string;
    remainingDurationMinutes: number;
    remainingDurationTicks: number;
    requiredSkill: string;
    requiredBayType: string;
  };
  supplierComparison: {
    baseline: DisruptionSupplierOption;
    alternative: DisruptionSupplierOption;
  };
  downstreamImpact: {
    impactedRoId: string;
    impactedVehicle: string;
    impactedCustomer: string;
    complaint: string;
    requiredBayType: string;
    currentQueueState: string;
    promisedDelivery: string;
    estimatedDurationMinutes: number;
    estimatedDurationTicks: number;
    priorityWeight: number;
    dependencyNote: string;
  };
  timelineMilestones: DisruptionTimelineMilestone[];
}

export interface DecisionReplayDiff {
  baseline_plan_id: string;
  proposed_plan_id: string;
  baseline_gross_contribution_usd: string;
  proposed_gross_contribution_usd: string;
  delta_gross_contribution_usd: string;
  sourcing_freight_usd: string;
  rescheduling_churn_cost_usd: string;
  baseline_net_objective_usd: string;
  proposed_net_objective_usd: string;
  net_economic_delta_usd: string;
  baseline_weighted_lateness_ticks: number;
  proposed_weighted_lateness_ticks: number;
  delta_weighted_lateness_ticks: number;
  baseline_bay_utilization_pct: number;
  proposed_bay_utilization_pct: number;
  delta_bay_utilization_pct: number;
  baseline_idle_minutes: number;
  proposed_idle_minutes: number;
  delta_idle_minutes: number;
  baseline_constraint_violations: number;
  proposed_constraint_violations: number;
  is_verified: boolean;
  is_fully_certified: boolean;
}

export interface DecisionConstraintEvaluation {
  constraint: string;
  description: string;
  is_satisfied: boolean;
  notes: string;
}

export interface DecisionRejectedAlternative {
  option_id: string;
  rejection_reason: string;
}

export interface DecisionExplainability {
  recommendation_summary: string;
  primary_driver: string;
  constraints_considered: DecisionConstraintEvaluation[];
  objective_breakdown: Record<string, string>;
  alternatives_rejected: DecisionRejectedAlternative[];
  unresolved_risks: string[];
}

export interface RecoveryAlternativeReport {
  offer_id: string;
  plan_id: string;
  supplier_name: string;
  part_number: string;
  arrival_tick: number;
  usable_ready_tick: number;
  sourcing_cost_usd: string;
  gross_contribution_usd: string;
  lateness_penalty_usd: string;
  net_objective_usd: string;
  net_recovery_delta_usd: string;
  weighted_lateness_ticks: number;
  bay_blocked_hours: string;
  is_verified: boolean;
  is_fully_certified: boolean;
  certification_status: string;
  is_pareto_optimal: boolean;
  is_recommended: boolean;
  rationale?: string | null;
}

export interface RecoveryRecommendationResponse {
  baseline_plan_id: string;
  baseline_net_objective_usd: string;
  baseline_weighted_lateness_ticks: number;
  recommended_option_id: string | null;
  recommended_plan_id: string | null;
  recommendation_rationale: string;
  alternatives: RecoveryAlternativeReport[];
  pareto_frontier: RecoveryAlternativeReport[];
  decision_replay?: DecisionReplayDiff | null;
  explainability?: DecisionExplainability | null;
  unresolved_risks: string[];
  generated_at: string;
  replan_duration_ms: number;
}

export type StallBreakerEventType =
  | 'RO_LINE_READY'
  | 'RO_OPENED'
  | 'PARTS_ETA_CHANGED'
  | 'PART_UNAVAILABLE'
  | 'BAY_RESERVATION_CHANGED'
  | 'TECHNICIAN_UNAVAILABLE'
  | 'OPERATION_COMPLETED';

export interface StoredEvent {
  event_id: string;
  rooftop_id: string;
  event_type: StallBreakerEventType;
  entity_type: string;
  entity_id: string;
  payload: Record<string, any>;
  occurred_at: string;
  ingested_at: string;
  signature?: string | null;
  snapshot_hash_before: string;
  snapshot_hash_after: string;
}

export interface EventIngestResponse {
  status: string;
  event_id: string;
  is_duplicate: boolean;
  previous_snapshot_hash: string;
  new_snapshot_hash: string;
  requires_recovery: boolean;
  disruption_summary?: string | null;
  ingested_at: string;
}

export interface StallBreakerDisruptionAnalysis {
  event_id: string;
  event_type: StallBreakerEventType;
  disrupted_ro_ids: string[];
  affected_bay_ids: string[];
  affected_tech_ids: string[];
  invalidated_task_ids: string[];
  is_schedule_invalidated: boolean;
  constraint_violations_detected: string[];
  impact_summary: string;
  analyzed_at: string;
}

export interface StallBreakerCandidateAction {
  action_id: string;
  action_type: string;
  target_ro_id: string;
  target_task_id?: string | null;
  source_bay_id?: string | null;
  target_bay_id?: string | null;
  source_tech_id?: string | null;
  target_tech_id?: string | null;
  sourcing_offer_id?: string | null;
  freight_surcharge_usd: string;
  is_feasible: boolean;
  rejection_reason?: string | null;
  description: string;
}

export interface StallBreakerRecoveryReport {
  event_id: string;
  event_type: StallBreakerEventType;
  disruption_analysis: StallBreakerDisruptionAnalysis;
  candidate_actions: StallBreakerCandidateAction[];
  evaluated_alternatives: RecoveryAlternativeReport[];
  recommended_action?: StallBreakerCandidateAction | null;
  recommended_plan_id?: string | null;
  baseline_plan_id: string;
  is_recovery_feasible: boolean;
  infeasibility_reason?: string | null;
  decision_replay?: DecisionReplayDiff | null;
  explainability?: DecisionExplainability | null;
  solve_time_ms: number;
  generated_at: string;
}

export interface OutboxEvent {
  event_id: string;
  event_type: string;
  aggregate_id: string;
  payload: Record<string, any>;
  occurred_at: string;
}

export interface CommitResult {
  status: string;
  plan_id: string;
  committed_at?: string | null;
  expected_hash: string;
  current_hash?: string | null;
  outbox_events_dispatched: number;
  outbox_events?: OutboxEvent[];
  error_code?: string | null;
  message?: string | null;
}


// ============================================================================
// PHASE 2 & 4: BENCHMARK & STATISTICAL EVALUATION TYPES
// ============================================================================

export type BenchmarkScenarioType =
  | 'NORMAL_OPERATIONS'
  | 'SPECIALISED_BAY_CONTENTION'
  | 'PARTS_DELAY'
  | 'TECHNICIAN_SHORTAGE'
  | 'COMPETING_RESERVATIONS'
  | 'SATURATED_CAPACITY'
  | 'NULL_CONTROL';

export type DispatchMethod = 'FIFO' | 'EDF' | 'CPSAT' | 'STALLBREAKER';

export interface BenchmarkMetrics {
  method: DispatchMethod;
  gross_contribution_usd: string;
  weighted_lateness_penalty_usd: string;
  total_weighted_lateness_ticks: number;
  lateness_minutes: number;
  on_time_delivery_rate: number;
  technician_utilisation_rate: number;
  bay_utilisation_rate: number;
  workshop_idle_minutes: number;
  recovery_plan_churn: number;
  solve_time_ms: number;
  constraint_violations: number;
  is_verified: boolean;
  is_fully_certified: boolean;
  net_objective_usd: string;
}

export interface ScenarioBenchmarkResult {
  scenario_id: string;
  scenario_type: BenchmarkScenarioType;
  title: string;
  description: string;
  seed: number;
  methods: Record<string, BenchmarkMetrics>;
  stallbreaker_advantage_usd: string;
  replay_record_id?: string | null;
}

export interface StatisticalMetricSummary {
  metric_name: string;
  baseline_mean: number;
  stallbreaker_mean: number;
  mean_delta: number;
  pct_improvement: number;
  ci_95_lower: number;
  ci_95_upper: number;
  p_value: number;
  is_statistically_significant: boolean;
}

export interface BenchmarkSuiteReport {
  benchmark_id: string;
  executed_at: string;
  scenarios: ScenarioBenchmarkResult[];
  statistical_summaries: StatisticalMetricSummary[];
  total_scenarios_evaluated: number;
  all_violations_zero: boolean;
}

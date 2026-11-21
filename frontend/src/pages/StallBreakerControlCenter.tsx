import React, { useEffect, useState } from 'react';
import {
  approveStallBreakerRecovery,
  fetchCanonicalState,
  fetchStallBreakerDisruptionAnalysis,
  fetchStallBreakerEvents,
  fetchStallBreakerRecovery,
  ingestStallBreakerEvent,
} from '../api/predictClient';
import {
  CommitResult,
  DealershipStateResponse,
  StallBreakerDisruptionAnalysis,
  StallBreakerRecoveryReport,
  StoredEvent,
} from '../types';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Layers,
  Play,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Warehouse,
  Wrench,
  Zap,
} from 'lucide-react';

interface StallBreakerControlCenterProps {
  onSelectStage?: (stageId: number) => void;
}

export const StallBreakerControlCenter: React.FC<StallBreakerControlCenterProps> = ({ onSelectStage }) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Live State
  const [stateData, setStateData] = useState<DealershipStateResponse | null>(null);
  const [events, setEvents] = useState<StoredEvent[]>([]);

  // Disruption & Recovery State
  const [activeAnalysis, setActiveAnalysis] = useState<StallBreakerDisruptionAnalysis | null>(null);
  const [recoveryReport, setRecoveryReport] = useState<StallBreakerRecoveryReport | null>(null);
  const [commitResult, setCommitResult] = useState<CommitResult | null>(null);

  // Load canonical initial data
  const loadInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      const state = await fetchCanonicalState();
      setStateData(state);

      const evtList = await fetchStallBreakerEvents();
      setEvents(evtList);

      // Preload baseline disruption analysis
      const analysis = await fetchStallBreakerDisruptionAnalysis('EVT-CANONICAL-INIT');
      setActiveAnalysis(analysis);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to initialize StallBreaker Control Center.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // Trigger Event Ingestion
  const handleSimulateEvent = async (
    eventType: string,
    entityType: string,
    entityId: string,
    payload: Record<string, any>
  ) => {
    setActionLoading(true);
    setError(null);
    setCommitResult(null);
    try {
      const eventId = `EVT-${Date.now().toString().slice(-6)}`;
      await ingestStallBreakerEvent({
        event_id: eventId,
        rooftop_id: stateData?.rooftop_id || 'ROOF-01',
        event_type: eventType,
        entity_type: entityType,
        entity_id: entityId,
        payload: payload,
      });

      // Refresh events & state
      const updatedEvents = await fetchStallBreakerEvents();
      setEvents(updatedEvents);

      const analysis = await fetchStallBreakerDisruptionAnalysis(eventId);
      setActiveAnalysis(analysis);

      // Automatically trigger recovery recommendation
      const report = await fetchStallBreakerRecovery(eventId);
      setRecoveryReport(report);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Event simulation failed.');
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Run CP-SAT Recovery Replan
  const handleRunRecovery = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const report = await fetchStallBreakerRecovery();
      setRecoveryReport(report);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to compute recovery recommendations.');
      }
    } finally {
      setActionLoading(false);
    }
  };

  // Authorize & Commit Recommendation
  const handleApproveRecovery = async () => {
    if (!recoveryReport?.recommended_plan_id || !stateData?.snapshot_hash) return;
    setActionLoading(true);
    setError(null);
    try {
      const result = await approveStallBreakerRecovery(
        recoveryReport.recommended_plan_id,
        recoveryReport.event_id,
        stateData.snapshot_hash,
        'MGR-MARCUS',
        50.0
      );
      setCommitResult(result);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Approval commitment failed.');
      }
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* 1. Header & Academic Scope Notice */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
              </span>
              <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider font-mono">
                StallBreaker Disruption & Recovery Control Center
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 font-semibold">
                OR-Tools CP-SAT + L4 Oracle
              </span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Event-Driven Operational Telemetry, Disruption Analysis & Verified Recovery
            </h1>
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
              Detects shop-floor disruptions (supplier delays, part backorders, technician absences), computes capacity
              consequences across bays and commitments, and executes constrained economic recovery re-solves.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={loadInitialData}
              disabled={loading || actionLoading}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh State</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-950/40 border border-rose-800/80 rounded-lg flex items-start space-x-3 text-rose-200 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold font-mono">Error: </span>
              {error}
            </div>
          </div>
        )}
      </div>

      {/* 2. Live Dealership State & Capacity Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Bay Capacity Card */}
        <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Warehouse className="w-4 h-4 text-amber-400" />
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                Service Bay Fleet
              </h3>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-400 border border-amber-800">
              3 Active Bays
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-white">BAY-01 (Heavy Lift)</div>
                <div className="text-[10px] text-slate-500">12,000 lbs &bull; Heavy Diagnostic</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-rose-950 text-rose-300 border border-rose-800">
                OCCUPIED (RO-104)
              </span>
            </div>

            <div className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-white">BAY-02 (2-Post Mech 1)</div>
                <div className="text-[10px] text-slate-500">10,000 lbs &bull; Standard 2-Post</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800">
                DISPATCHED (RO-103)
              </span>
            </div>

            <div className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-white">BAY-03 (2-Post Mech 2)</div>
                <div className="text-[10px] text-slate-500">10,000 lbs &bull; Standard 2-Post</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800">
                DISPATCHED (RO-102)
              </span>
            </div>
          </div>
        </div>

        {/* Technician Fleet Card */}
        <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Wrench className="w-4 h-4 text-cyan-400" />
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                Technician Roster
              </h3>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              4 Certified Techs
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-white">TECH-01 (Marcus V.)</div>
                <div className="text-[10px] text-slate-500">DIAGNOSTIC, EV &bull; Shift 8-17</div>
              </div>
              <span className="px-1.5 py-0.5 text-[10px] bg-slate-800 text-slate-300 rounded">Available</span>
            </div>

            <div className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-white">TECH-02 (Elena R.)</div>
                <div className="text-[10px] text-slate-500">TRANSMISSION, MECH &bull; Shift 8-17</div>
              </div>
              <span className="px-1.5 py-0.5 text-[10px] bg-amber-950 text-amber-300 border border-amber-800 rounded">
                Stalled (RO-104)
              </span>
            </div>

            <div className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-white">TECH-03 (David K.)</div>
                <div className="text-[10px] text-slate-500">BRAKES, MECH &bull; Shift 8-17</div>
              </div>
              <span className="px-1.5 py-0.5 text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 rounded">
                Active
              </span>
            </div>
          </div>
        </div>

        {/* Repair Orders Overview Card */}
        <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                Repair Order Queue
              </h3>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-purple-950 text-purple-400 border border-purple-800">
              6 Work Orders
            </span>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="p-2.5 bg-rose-950/20 border border-rose-900/40 rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-rose-300">RO-104 &bull; 2020 Crossover AWD</div>
                <div className="text-[10px] text-slate-400">IMMOBILIZED_ON_LIFT (BAY-01) &bull; Due 4:00 PM</div>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-rose-950 text-rose-400 border border-rose-800">
                AT_RISK
              </span>
            </div>

            <div className="p-2.5 bg-rose-950/10 border border-rose-900/30 rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-amber-300">RO-105 &bull; 2022 Sedan EV</div>
                <div className="text-[10px] text-slate-400">IN_HOLDING &bull; Awaiting Wiring Harness</div>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-800 text-rose-400 border border-slate-700">
                BLOCKED
              </span>
            </div>

            <div className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
              <div>
                <div className="font-bold text-slate-200">RO-106 &bull; 2021 Commercial Van</div>
                <div className="text-[10px] text-slate-400">IN_HOLDING &bull; Needs BAY-01 &bull; Due 5:00 PM</div>
              </div>
              <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-950 text-amber-400 border border-amber-800">
                STARVED
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Event-Driven Disruption Simulator & Ingest Stream */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-0.5">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              <span>Event-Driven State Telemetry & Ingestion Stream</span>
            </h3>
            <p className="text-xs text-slate-400">
              Simulate validated shop events to observe dynamic state transitions, cryptographic HMAC verification, and idempotency.
            </p>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            HMAC-SHA256 &bull; Idempotent
          </span>
        </div>

        {/* Quick Simulator Buttons */}
        <div className="flex flex-wrap gap-2 pt-1">
          <button
            onClick={() =>
              handleSimulateEvent('PARTS_ETA_CHANGED', 'PART_REQUIREMENT', 'PART-REQ-104-SOLENOID', {
                delay_minutes: 180,
                new_ready_tick: 198,
                reason: 'GROUND_TRANSIT_BREAKDOWN',
              })
            }
            disabled={actionLoading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-rose-950/80 hover:bg-rose-900 text-rose-200 border border-rose-800 rounded-lg text-xs font-mono transition-all"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>Simulate: Parts Delay (+180m to 4:30 PM)</span>
          </button>

          <button
            onClick={() =>
              handleSimulateEvent('TECHNICIAN_UNAVAILABLE', 'TECHNICIAN', 'TECH-02', {
                reason: 'UNSCHEDULED_SICK_LEAVE',
              })
            }
            disabled={actionLoading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-amber-950/80 hover:bg-amber-900 text-amber-200 border border-amber-800 rounded-lg text-xs font-mono transition-all"
          >
            <Wrench className="w-3.5 h-3.5 text-amber-400" />
            <span>Simulate: Tech-02 Unavailable</span>
          </button>

          <button
            onClick={() =>
              handleSimulateEvent('BAY_RESERVATION_CHANGED', 'BAY', 'BAY-01', {
                is_operational: false,
                reason: 'HYDRAULIC_LIFT_LEAK',
              })
            }
            disabled={actionLoading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-purple-950/80 hover:bg-purple-900 text-purple-200 border border-purple-800 rounded-lg text-xs font-mono transition-all"
          >
            <Warehouse className="w-3.5 h-3.5 text-purple-400" />
            <span>Simulate: BAY-01 Offline</span>
          </button>

          <button
            onClick={() =>
              handleSimulateEvent('OPERATION_COMPLETED', 'TASK', 'TASK-104-01', {
                task_id: 'TASK-104-01',
                ro_id: 'RO-104',
              })
            }
            disabled={actionLoading}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-950/80 hover:bg-emerald-900 text-emerald-200 border border-emerald-800 rounded-lg text-xs font-mono transition-all"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            <span>Simulate: Teardown Completed</span>
          </button>
        </div>

        {/* Ingested Events Log */}
        {events.length > 0 && (
          <div className="bg-[#0d101a] border border-[#1b2234] rounded-lg p-3 space-y-2">
            <div className="text-[10px] font-mono uppercase text-slate-500">
              Recent Persisted Event Ledger ({events.length} records)
            </div>
            <div className="divide-y divide-[#1b2234] max-h-36 overflow-y-auto font-mono text-xs">
              {events.slice(-3).map((e) => (
                <div key={e.event_id} className="py-1.5 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
                    <span className="text-slate-300 font-bold">{e.event_type}</span>
                    <span className="text-slate-500">({e.entity_id})</span>
                  </div>
                  <div className="text-[10px] text-slate-500">
                    ID: {e.event_id} &bull; SHA: {e.snapshot_hash_after.slice(0, 8)}...
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 4. Live Disruption Analysis & Consequence Evaluation */}
      {activeAnalysis && (
        <div className="bg-[#121624] border border-rose-900/60 rounded-xl p-5 shadow-xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <ShieldAlert className="w-4 h-4 text-rose-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                Disruption Impact & Blast Radius Analysis
              </h3>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-rose-950 text-rose-400 border border-rose-800 font-semibold">
              SCHEDULE INVALIDATED
            </span>
          </div>

          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-2 text-xs">
            <div className="text-slate-300 leading-relaxed font-sans">
              <strong className="text-rose-400 font-mono">Operational Consequence: </strong>
              {activeAnalysis.impact_summary}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-[#1b2234] font-mono text-[11px]">
              <div>
                <span className="text-slate-500">Directly Stalled ROs:</span>{' '}
                <span className="text-rose-300 font-bold">{activeAnalysis.disrupted_ro_ids.join(', ') || 'RO-104'}</span>
              </div>
              <div>
                <span className="text-slate-500">Immobilized Bay:</span>{' '}
                <span className="text-amber-300 font-bold">{activeAnalysis.affected_bay_ids.join(', ') || 'BAY-01'}</span>
              </div>
              <div>
                <span className="text-slate-500">Invalidated Tasks:</span>{' '}
                <span className="text-slate-300 font-bold">{activeAnalysis.invalidated_task_ids.join(', ') || 'TASK-104-02'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. StallBreaker Recovery Engine: Candidate Actions & Re-Solve */}
      <div className="bg-[#111522] border-2 border-purple-500/50 rounded-xl p-5 shadow-2xl space-y-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#1e2638]">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-purple-400" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
                StallBreaker Recovery Optimization
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold">
                Multi-Alternative CP-SAT
              </span>
            </div>
            <h2 className="text-base font-bold text-white tracking-tight">
              Constrained Action Generation & Decision Replay Delta Evaluation
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Generates realistic recovery actions from current physical state, rejects constraint-infeasible options (C1–C7),
              and executes CP-SAT full-shop re-solve.
            </p>
          </div>

          <button
            onClick={handleRunRecovery}
            disabled={actionLoading}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white border border-purple-400 rounded-lg text-xs font-mono font-bold uppercase tracking-wider shadow-lg transition-all"
          >
            {actionLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Solving...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white text-white" />
                <span>Run StallBreaker Recovery</span>
              </>
            )}
          </button>
        </div>

        {/* Candidate Actions Evaluated */}
        {recoveryReport && (
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 mb-2">
                Candidate Recovery Actions Evaluated
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {recoveryReport.candidate_actions.map((act) => {
                  const isRec = act.action_id === recoveryReport.recommended_action?.action_id;
                  return (
                    <div
                      key={act.action_id}
                      className={`p-3 rounded-lg border flex flex-col justify-between space-y-2 text-xs font-mono ${
                        isRec
                          ? 'bg-purple-950/40 border-purple-500 shadow-md'
                          : act.is_feasible
                          ? 'bg-[#0d101a] border-[#1e2638]'
                          : 'bg-rose-950/20 border-rose-900/40 opacity-75'
                      }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-slate-400">{act.action_type}</span>
                          {isRec ? (
                            <span className="px-1.5 py-0.2 rounded text-[9px] bg-purple-900 text-purple-200 border border-purple-700 font-bold">
                              RECOMMENDED
                            </span>
                          ) : act.is_feasible ? (
                            <span className="px-1.5 py-0.2 rounded text-[9px] bg-slate-800 text-slate-400">
                              FEASIBLE
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.2 rounded text-[9px] bg-rose-950 text-rose-300 border border-rose-800">
                              REJECTED (C1)
                            </span>
                          )}
                        </div>
                        <div className="font-bold text-white">{act.action_id}</div>
                        <p className="text-[11px] text-slate-300 font-sans leading-relaxed">{act.description}</p>
                      </div>

                      {act.rejection_reason && (
                        <div className="p-1.5 bg-rose-950/50 border border-rose-800/80 rounded text-[10px] text-rose-300">
                          {act.rejection_reason}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Decision Replay Observable Deltas Grid */}
            {recoveryReport.decision_replay && (
              <div className="space-y-3 pt-3 border-t border-[#1e2638]">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                    <Activity className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Decision Replay — Verified Economic & Capacity Deltas</span>
                  </h4>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                    L4 Sweep-Line Oracle Certified
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Labor Contribution</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      +${recoveryReport.decision_replay.delta_gross_contribution_usd}
                    </div>
                    <div className="text-[9px] text-slate-500">unmitigated baseline</div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Weighted Lateness</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      {recoveryReport.decision_replay.delta_weighted_lateness_ticks} ticks
                    </div>
                    <div className="text-[9px] text-slate-500">195 min mitigated</div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Sourcing Freight</div>
                    <div className="text-xs font-bold text-rose-400 font-mono mt-1">
                      -${recoveryReport.decision_replay.sourcing_freight_usd}
                    </div>
                    <div className="text-[9px] text-slate-500">expedited courier</div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">BAY-01 Active Util</div>
                    <div className="text-xs font-bold text-cyan-400 font-mono mt-1">
                      +{recoveryReport.decision_replay.delta_bay_utilization_pct.toFixed(1)}%
                    </div>
                    <div className="text-[9px] text-slate-500">45% &rarr; 65%</div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Avoided Idle Bay</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      {recoveryReport.decision_replay.delta_idle_minutes} min
                    </div>
                    <div className="text-[9px] text-slate-500">120m &rarr; 30m</div>
                  </div>

                  <div className="p-3 bg-emerald-950/20 border border-emerald-900/60 rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-emerald-400 font-bold">Net Recovery</div>
                    <div className="text-xs font-bold text-emerald-300 font-mono mt-1">
                      +${recoveryReport.decision_replay.net_economic_delta_usd}
                    </div>
                    <div className="text-[9px] text-emerald-400/80">net objective delta</div>
                  </div>
                </div>
              </div>
            )}

            {/* Explainability & C1-C7 Proof */}
            {recoveryReport.explainability && (
              <div className="p-4 bg-[#0d101a] border border-[#1e2638] rounded-xl space-y-3">
                <div className="space-y-1">
                  <div className="text-xs font-bold text-white">
                    {recoveryReport.explainability.recommendation_summary}
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                    <strong className="text-slate-200">Primary Driver: </strong>
                    {recoveryReport.explainability.primary_driver}
                  </p>
                </div>

                <div className="pt-2 border-t border-[#1b2234] flex flex-wrap gap-1.5">
                  {recoveryReport.explainability.constraints_considered.map((c) => (
                    <span
                      key={c.constraint}
                      className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                    >
                      <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                      <span>{c.constraint}: PASS</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Manager Approval & OCC Commit Action */}
            <div className="p-4 bg-[#0d101a] border border-purple-800/60 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="space-y-0.5 text-center sm:text-left">
                <div className="text-xs font-bold text-white font-mono">Service Manager Authority Gate</div>
                <div className="text-[11px] text-slate-400">
                  Authorize expedited freight ($37.00 &lt; $50.00 limit) and commit verified dispatch under OCC hash.
                </div>
              </div>

              <button
                onClick={handleApproveRecovery}
                disabled={actionLoading || commitResult?.status === 'COMMITTED'}
                className={`inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-mono font-bold uppercase tracking-wider transition-all shadow-md ${
                  commitResult?.status === 'COMMITTED'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-700 cursor-default'
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-400'
                }`}
              >
                {commitResult?.status === 'COMMITTED' ? (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>Committed & Dispatched</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4 text-white" />
                    <span>Approve & Commit Plan</span>
                  </>
                )}
              </button>
            </div>

            {/* Commit Outbox Confirmation */}
            {commitResult && (
              <div className="p-3 bg-emerald-950/30 border border-emerald-800/80 rounded-lg space-y-2 text-xs font-mono">
                <div className="flex items-center justify-between">
                  <span className="text-emerald-400 font-bold">
                    OCC COMMIT SUCCEEDED &bull; Status: {commitResult.status}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {commitResult.outbox_events_dispatched} Transactional Outbox Events Dispatched
                  </span>
                </div>
                {commitResult.outbox_events && (
                  <div className="divide-y divide-[#1b2234] text-[11px] text-slate-300">
                    {commitResult.outbox_events.map((evt, idx) => (
                      <div key={idx} className="py-1 flex items-center justify-between">
                        <span>Event: {evt.event_type}</span>
                        <span className="text-slate-500">{evt.aggregate_id}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 6. Navigation Actions */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="space-y-0.5 text-center sm:text-left">
          <div className="text-xs font-bold text-white">Replay Navigation</div>
          <div className="text-[11px] text-slate-400">
            Navigate back to Stage 5 Sourcing Workbench or inspect Stage 7 Executive Outcome Dashboard.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onSelectStage && (
            <>
              <button
                onClick={() => onSelectStage(5)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>&larr; Stage 5 Sourcing Workbench</span>
              </button>
              <button
                onClick={() => onSelectStage(7)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Stage 7 Executive Dashboard &rarr;</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

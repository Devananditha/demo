import React, { useEffect, useState } from 'react';
import {
  fetchStallBreakerEvents,
  ingestStallBreakerEvent,
  fetchStallBreakerDisruptionAnalysis,
} from '../api/predictClient';
import { useAppState } from '../context/AppStateContext';
import { SYNTHETIC_DISRUPTION_SCENARIO } from '../data/mockData';
import { StoredEvent, StallBreakerDisruptionAnalysis } from '../types';
import {
  AlertTriangle,
  Clock,
  Warehouse,
  Wrench,
  CheckCircle2,
  RefreshCw,
  Zap,
  ArrowRight,
} from 'lucide-react';

const badgeColorMap: Record<string, string> = {
  rose:    'bg-rose-950 text-rose-300 border-rose-800',
  emerald: 'bg-emerald-950 text-emerald-300 border-emerald-800',
  amber:   'bg-amber-950 text-amber-300 border-amber-800',
  orange:  'bg-orange-950 text-orange-300 border-orange-800',
  slate:   'bg-slate-800 text-slate-300 border-slate-700',
  purple:  'bg-purple-950 text-purple-300 border-purple-800',
};

export const DisruptionsView: React.FC = () => {
  const { workshopState, setActiveSection } = useAppState();
  const scenario = SYNTHETIC_DISRUPTION_SCENARIO;

  const [events, setEvents] = useState<StoredEvent[]>([]);
  const [analysis, setAnalysis] = useState<StallBreakerDisruptionAnalysis | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStallBreakerEvents().then(setEvents).catch(() => {});
  }, []);

  const handleSimulateEvent = async (
    eventType: string,
    entityType: string,
    entityId: string,
    payload: Record<string, any>
  ) => {
    setActionLoading(true);
    setError(null);
    try {
      const eventId = `EVT-${Date.now().toString().slice(-6)}`;
      await ingestStallBreakerEvent({
        event_id: eventId,
        rooftop_id: workshopState?.rooftop_id || 'ROOF-01',
        event_type: eventType,
        entity_type: entityType,
        entity_id: entityId,
        payload,
      });
      const updatedEvents = await fetchStallBreakerEvents();
      setEvents(updatedEvents);
      const result = await fetchStallBreakerDisruptionAnalysis(eventId);
      setAnalysis(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Event simulation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-10">
      {/* Header */}
      <div className="bg-[#111522] border border-rose-900/60 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
              </span>
              <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider font-mono">
                Workshop Disruption Intelligence
              </span>
            </div>
            <h2 className="text-lg font-bold text-white">Active Bottleneck & Disruption Alert</h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Detects inbound supplier delays, immobilized service-bay cascades, and downstream customer promise risks.
            </p>
          </div>

          <button
            onClick={() => setActiveSection(3)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors self-start sm:self-auto shrink-0"
          >
            <span>Proceed to Recovery Decisions</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Impact Summary: What Happened */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-4 shadow-xl">
        <h3 className="text-sm font-bold text-white">Disruption Cascade Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-3">
            <div className="p-3.5 bg-[#0d101a] border border-rose-900/40 rounded-lg space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-rose-400 font-bold">Immobilized Lift Bottleneck</div>
              <div className="font-bold text-white text-sm">{scenario.affectedRoId} — {scenario.affectedCustomer}</div>
              <div className="text-slate-300">{scenario.affectedVehicle}</div>
              <div className="text-slate-400">Occupying: <span className="text-cyan-300 font-mono">{scenario.affectedBayName}</span></div>
              <div className="p-2 bg-rose-950/40 border border-rose-800/60 rounded text-rose-200 text-[11px] mt-1.5">
                <strong>Physical Movement Blocked:</strong> Transmission oil pan removed and fluid drained. Vehicle cannot be rolled off the lift until repair completes.
              </div>
            </div>

            <div className="p-3.5 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-slate-500 font-bold">Stalled Work Operation</div>
              <div className="text-slate-200 font-medium">{scenario.stalledTask.description}</div>
              <div className="text-slate-400 flex items-center gap-2">
                <span>Remaining Duration: <strong className="text-white font-mono">{scenario.stalledTask.remainingDurationMinutes} min</strong></span>
                <span>&bull;</span>
                <span>Required Skill: <strong className="text-cyan-300 font-mono">{scenario.stalledTask.requiredSkill}</strong></span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="p-3.5 bg-[#0d101a] border border-amber-900/40 rounded-lg space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-amber-400 font-bold">Primary Supplier Delay</div>
              <div className="font-bold text-white text-sm">+{scenario.delayMinutes} Minutes Inbound Slip</div>
              <div className="text-slate-300">Ground shuttle parts arrive at: <strong className="text-orange-300 font-mono">{scenario.supplierComparison.baseline.usableReadyTime}</strong></div>
              <div className="p-2 bg-amber-950/40 border border-amber-800/60 rounded text-amber-200 text-[11px] mt-1.5">
                <strong>Promise at Risk:</strong> Customer delivery was promised at 4:00 PM. Ground parts arriving at 4:30 PM leave zero work time, creating an unavoidable promise failure.
              </div>
            </div>

            <div className="p-3.5 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-slate-500 font-bold">Downstream Vehicle Blocked</div>
              <div className="font-bold text-white text-sm">{scenario.downstreamImpact.impactedRoId} — {scenario.downstreamImpact.impactedCustomer}</div>
              <div className="text-slate-300">{scenario.downstreamImpact.impactedVehicle} (Promise: 4:30 PM)</div>
              <div className="p-2 bg-slate-900 border border-slate-800 rounded text-slate-300 text-[11px] mt-1.5">
                <strong>Starved for Capacity:</strong> Requires BAY-01 (shop's sole Heavy Diagnostic Lift). All parts ready, but vehicle sits in holding queue unable to start.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 shadow-xl">
        <h3 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          Operating Day Timeline & Milestone Sequence
        </h3>
        <div className="relative">
          <div className="absolute left-4 top-0 bottom-0 w-px bg-[#1e2638]" />
          <div className="space-y-4">
            {scenario.timelineMilestones.map((m, idx) => {
              const badgeClass = badgeColorMap[m.badgeColor] || badgeColorMap.slate;
              return (
                <div key={idx} className="flex gap-4 pl-10 relative">
                  <div className={`absolute left-2.5 top-1 w-3 h-3 rounded-full border-2 ${
                    m.badgeColor === 'rose' ? 'border-rose-500 bg-rose-900' :
                    m.badgeColor === 'emerald' ? 'border-emerald-500 bg-emerald-900' :
                    m.badgeColor === 'amber' ? 'border-amber-500 bg-amber-900' :
                    'border-slate-600 bg-slate-900'
                  }`} />
                  <div className="flex-1 pb-1">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="font-mono text-xs font-bold text-white">{m.time}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${badgeClass}`}>
                        {m.label}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{m.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Event Simulation */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Event Ingestion Simulator</h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            HMAC-SHA256 &bull; Idempotent API
          </span>
        </div>
        <p className="text-xs text-slate-400">
          Simulate shop-floor telemetry events to observe live state mutation, disruption analysis, and event log persistence.
        </p>

        {error && (
          <div className="p-2.5 bg-rose-950/40 border border-rose-800 rounded-lg text-rose-200 text-xs">{error}</div>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleSimulateEvent('PARTS_ETA_CHANGED', 'PART_REQUIREMENT', 'PART-REQ-104-SOLENOID', {
              delay_minutes: 180, new_ready_tick: 198, reason: 'GROUND_TRANSIT_BREAKDOWN',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-950/80 hover:bg-rose-900 text-rose-200 border border-rose-800 rounded-lg text-xs font-mono transition-all"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            Parts Delay (+180m to 4:30 PM)
          </button>

          <button
            onClick={() => handleSimulateEvent('TECHNICIAN_UNAVAILABLE', 'TECHNICIAN', 'TECH-02', {
              reason: 'UNSCHEDULED_SICK_LEAVE',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-950/80 hover:bg-amber-900 text-amber-200 border border-amber-800 rounded-lg text-xs font-mono transition-all"
          >
            <Wrench className="w-3.5 h-3.5 text-amber-400" />
            Technician Elena R. Sick
          </button>

          <button
            onClick={() => handleSimulateEvent('BAY_RESERVATION_CHANGED', 'BAY', 'BAY-01', {
              is_operational: false, reason: 'HYDRAULIC_LIFT_LEAK',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-950/80 hover:bg-purple-900 text-purple-200 border border-purple-800 rounded-lg text-xs font-mono transition-all"
          >
            <Warehouse className="w-3.5 h-3.5 text-purple-400" />
            BAY-01 Hydraulic Leak
          </button>

          <button
            onClick={() => handleSimulateEvent('OPERATION_COMPLETED', 'TASK', 'TASK-104-01', {
              task_id: 'TASK-104-01', ro_id: 'RO-104',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-950/80 hover:bg-emerald-900 text-emerald-200 border border-emerald-800 rounded-lg text-xs font-mono transition-all"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            Teardown Finished
          </button>

          {actionLoading && (
            <span className="inline-flex items-center gap-1.5 text-slate-400 text-xs px-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Ingesting event…
            </span>
          )}
        </div>

        {/* Live Disruption Analysis Result */}
        {analysis && (
          <div className="p-4 bg-rose-950/20 border border-rose-900/60 rounded-lg space-y-2 text-xs">
            <div className="flex items-center gap-2 font-bold text-rose-300">
              <AlertTriangle className="w-4 h-4" /> Live Disruption Analysis Result
            </div>
            <p className="text-slate-300 leading-relaxed">{analysis.impact_summary}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-rose-900/40 font-mono text-[11px]">
              <div>
                <span className="text-slate-500">Stalled ROs: </span>
                <span className="text-rose-300 font-bold">{analysis.disrupted_ro_ids.join(', ') || 'RO-104'}</span>
              </div>
              <div>
                <span className="text-slate-500">Affected Bay: </span>
                <span className="text-amber-300 font-bold">{analysis.affected_bay_ids.join(', ') || 'BAY-01'}</span>
              </div>
              <div>
                <span className="text-slate-500">Invalidated Tasks: </span>
                <span className="text-slate-300 font-bold">{analysis.invalidated_task_ids.join(', ') || 'TASK-104-02'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Recent Events Log */}
        {events.length > 0 && (
          <div className="bg-[#0d101a] border border-[#1b2234] rounded-lg p-3 space-y-2">
            <div className="text-[10px] font-mono uppercase text-slate-500">
              Persisted Event Ledger ({events.length} records in SQLite store)
            </div>
            <div className="divide-y divide-[#1b2234] max-h-36 overflow-y-auto font-mono text-xs">
              {events.slice(-5).map((e) => (
                <div key={e.event_id} className="py-1.5 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
                    <span className="text-slate-300 font-bold">{e.event_type}</span>
                    <span className="text-slate-500">({e.entity_id})</span>
                  </div>
                  <div className="text-[10px] text-slate-500">
                    ID: {e.event_id} &bull; SHA: {e.snapshot_hash_after.slice(0, 8)}…
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom CTA to step 3 */}
      <div className="flex justify-end">
        <button
          onClick={() => setActiveSection(3)}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold rounded-lg text-xs shadow-lg transition-all"
        >
          <span>Evaluate Recovery Options</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

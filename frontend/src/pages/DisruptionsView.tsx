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
    <div className="space-y-6 pb-8">
      {/* Header Banner */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="flex h-2 w-2 relative">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-600"></span>
              </span>
              <span className="text-xs font-semibold text-amber-800 tracking-wide">
                Active Workshop Disruption
              </span>
            </div>
            <h2 className="text-xl font-bold text-stone-900 tracking-tight">Supplier Delay & Lift Bottleneck Cascade</h2>
            <p className="text-xs text-stone-500 mt-1 max-w-2xl leading-relaxed">
              Inbound supplier parts delay has immobilized BAY-01, threatening customer delivery for RO-104 and starving downstream queue access for RO-106.
            </p>
          </div>

          <button
            onClick={() => setActiveSection(3)}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-md text-xs font-medium shadow-xs transition-colors self-start sm:self-auto shrink-0"
          >
            <span>Proceed to Recovery Decisions</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Disruption Cascade Analysis Grid */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 space-y-4 shadow-xs">
        <h3 className="text-sm font-semibold text-stone-900 border-b border-[#eee8df] pb-3">Disruption Cascade Analysis</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="space-y-3">
            <div className="p-4 bg-[#faf8f5] border border-[#e5dfd5] rounded-lg space-y-2">
              <div className="text-[11px] font-semibold text-amber-800 uppercase tracking-wide">Immobilized Lift Bottleneck</div>
              <div className="font-bold text-stone-900 text-sm">{scenario.affectedRoId} — {scenario.affectedCustomer}</div>
              <div className="text-stone-700">{scenario.affectedVehicle}</div>
              <div className="text-stone-500">Occupying: <span className="font-semibold text-stone-800">{scenario.affectedBayName}</span></div>
              <div className="p-2.5 bg-amber-50 border border-amber-200/80 rounded-md text-amber-900 text-xs mt-2 leading-relaxed">
                <strong className="font-semibold">Physical State Constraint:</strong> Transmission oil pan is removed and fluid is drained. The vehicle cannot be rolled off the lift until replacement parts arrive and installation completes.
              </div>
            </div>

            <div className="p-4 bg-[#faf8f5] border border-[#e5dfd5] rounded-lg space-y-2">
              <div className="text-[11px] font-semibold text-stone-600 uppercase tracking-wide">Stalled Work Operation</div>
              <div className="text-stone-800 font-medium leading-relaxed">{scenario.stalledTask.description}</div>
              <div className="text-stone-500 flex items-center gap-2 pt-1 border-t border-[#ded7c8]">
                <span>Remaining Duration: <strong className="text-stone-800 font-mono">{scenario.stalledTask.remainingDurationMinutes} min</strong></span>
                <span>&bull;</span>
                <span>Required Skill: <strong className="text-stone-800">{scenario.stalledTask.requiredSkill}</strong></span>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="p-4 bg-[#faf8f5] border border-[#e5dfd5] rounded-lg space-y-2">
              <div className="text-[11px] font-semibold text-rose-800 uppercase tracking-wide">Primary Supplier Delay</div>
              <div className="font-bold text-stone-900 text-sm">+{scenario.delayMinutes} Minutes Inbound Ground Slip</div>
              <div className="text-stone-700">Delayed ground parts arrival: <strong className="text-stone-900 font-mono font-bold">{scenario.supplierComparison.baseline.usableReadyTime}</strong></div>
              <div className="p-2.5 bg-rose-50 border border-rose-200/80 rounded-md text-rose-900 text-xs mt-2 leading-relaxed">
                <strong className="font-semibold">Promise Breach:</strong> Customer promised delivery was 4:00 PM. Delayed arrival at 4:30 PM leaves insufficient time to complete the 120-minute repair before end of shift.
              </div>
            </div>

            <div className="p-4 bg-[#faf8f5] border border-[#e5dfd5] rounded-lg space-y-2">
              <div className="text-[11px] font-semibold text-stone-600 uppercase tracking-wide">Downstream Vehicle Blocked</div>
              <div className="font-bold text-stone-900 text-sm">{scenario.downstreamImpact.impactedRoId} — {scenario.downstreamImpact.impactedCustomer}</div>
              <div className="text-stone-700">{scenario.downstreamImpact.impactedVehicle} (Promise: 4:30 PM)</div>
              <div className="p-2.5 bg-[#f0ebdf] border border-[#ded7c8] rounded-md text-stone-700 text-xs mt-2 leading-relaxed">
                <strong className="font-semibold text-stone-900">Starved for Lift Capacity:</strong> Vehicle requires BAY-01 (sole heavy diagnostic lift). All parts are staged, but vehicle sits idle in holding awaiting bay access.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Disruption Timeline */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs">
        <h3 className="text-sm font-semibold text-stone-900 mb-4 flex items-center gap-2 border-b border-[#eee8df] pb-3">
          <Clock className="w-4 h-4 text-stone-500" />
          Shift Sequence & Impact Timeline
        </h3>
        <div className="relative">
          <div className="absolute left-3.5 top-2 bottom-2 w-0.5 bg-[#ded7c8]" />
          <div className="space-y-4">
            {scenario.timelineMilestones.map((m, idx) => {
              const isAlert = m.badgeColor === 'rose';
              const isAction = m.badgeColor === 'emerald';
              const isWarning = m.badgeColor === 'amber' || m.badgeColor === 'orange';
              return (
                <div key={idx} className="flex gap-4 pl-8 relative">
                  <div className={`absolute left-2.5 top-1.5 w-2.5 h-2.5 rounded-full border-2 ${
                    isAlert ? 'border-rose-600 bg-white' :
                    isAction ? 'border-stone-900 bg-white' :
                    isWarning ? 'border-amber-600 bg-white' :
                    'border-stone-400 bg-white'
                  }`} />
                  <div className="flex-1 pb-1">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="font-mono text-xs font-bold text-stone-900">{m.time}</span>
                      <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                        isAlert ? 'bg-rose-50 text-rose-800 border-rose-200' :
                        isAction ? 'bg-[#ede7db] text-stone-900 border-[#ded7c8]' :
                        isWarning ? 'bg-amber-50 text-amber-800 border-amber-200' :
                        'bg-[#f5f1e8] text-stone-700 border-[#ded7c8]'
                      }`}>
                        {m.label}
                      </span>
                    </div>
                    <p className="text-xs text-stone-600 leading-relaxed">{m.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Event Simulation */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-[#eee8df] pb-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-800" />
            <h3 className="text-sm font-semibold text-stone-900">Event Telemetry Simulator</h3>
          </div>
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-[#f5f1e8] text-stone-600 border border-[#ded7c8]">
            HMAC-SHA256 Validated
          </span>
        </div>
        <p className="text-xs text-stone-500">
          Simulate shop-floor telemetry updates to observe state mutation, disruption classification, and event persistence.
        </p>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-md text-rose-800 text-xs">{error}</div>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => handleSimulateEvent('PARTS_ETA_CHANGED', 'PART_REQUIREMENT', 'PART-REQ-104-SOLENOID', {
              delay_minutes: 180, new_ready_tick: 198, reason: 'GROUND_TRANSIT_BREAKDOWN',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#faf7f0] text-stone-800 border border-[#ded7c8] rounded-md text-xs font-medium shadow-xs transition-colors"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            Simulate Parts Delay (+180m to 4:30 PM)
          </button>

          <button
            onClick={() => handleSimulateEvent('TECHNICIAN_UNAVAILABLE', 'TECHNICIAN', 'TECH-02', {
              reason: 'UNSCHEDULED_SICK_LEAVE',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#faf7f0] text-stone-800 border border-[#ded7c8] rounded-md text-xs font-medium shadow-xs transition-colors"
          >
            <Wrench className="w-3.5 h-3.5 text-stone-600" />
            Simulate Tech-02 Sick Leave
          </button>

          <button
            onClick={() => handleSimulateEvent('BAY_RESERVATION_CHANGED', 'BAY', 'BAY-01', {
              is_operational: false, reason: 'HYDRAULIC_LIFT_LEAK',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#faf7f0] text-stone-800 border border-[#ded7c8] rounded-md text-xs font-medium shadow-xs transition-colors"
          >
            <Warehouse className="w-3.5 h-3.5 text-stone-600" />
            Simulate BAY-01 Offline
          </button>

          <button
            onClick={() => handleSimulateEvent('OPERATION_COMPLETED', 'TASK', 'TASK-104-01', {
              task_id: 'TASK-104-01', ro_id: 'RO-104',
            })}
            disabled={actionLoading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#faf7f0] text-stone-800 border border-[#ded7c8] rounded-md text-xs font-medium shadow-xs transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            Simulate Teardown Completed
          </button>

          {actionLoading && (
            <span className="inline-flex items-center gap-1.5 text-stone-500 text-xs px-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Ingesting event…
            </span>
          )}
        </div>

        {/* Live Disruption Analysis Result */}
        {analysis && (
          <div className="p-4 bg-amber-50/70 border border-amber-200 rounded-lg space-y-2 text-xs">
            <div className="flex items-center gap-2 font-semibold text-amber-900">
              <AlertTriangle className="w-4 h-4 text-amber-600" /> Automated Disruption Analysis Output
            </div>
            <p className="text-stone-700 leading-relaxed">{analysis.impact_summary}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-amber-200/80 font-mono text-[11px]">
              <div>
                <span className="text-stone-500">Stalled Orders: </span>
                <span className="text-stone-900 font-bold">{analysis.disrupted_ro_ids.join(', ') || 'RO-104'}</span>
              </div>
              <div>
                <span className="text-stone-500">Affected Lift: </span>
                <span className="text-stone-900 font-bold">{analysis.affected_bay_ids.join(', ') || 'BAY-01'}</span>
              </div>
              <div>
                <span className="text-stone-500">Invalidated Tasks: </span>
                <span className="text-stone-900 font-bold">{analysis.invalidated_task_ids.join(', ') || 'TASK-104-02'}</span>
              </div>
            </div>
          </div>
        )}

        {/* Persisted Events Ledger */}
        {events.length > 0 && (
          <div className="bg-[#faf8f5] border border-[#e5dfd5] rounded-md p-3 space-y-2">
            <div className="text-xs font-semibold text-stone-600 uppercase tracking-wide">
              Persisted Event Ledger ({events.length} records)
            </div>
            <div className="divide-y divide-[#eee8df] max-h-36 overflow-y-auto text-xs">
              {events.slice(-5).map((e) => (
                <div key={e.event_id} className="py-2 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-800 shrink-0" />
                    <span className="font-medium text-stone-800">{e.event_type}</span>
                    <span className="text-stone-500">({e.entity_id})</span>
                  </div>
                  <div className="text-[11px] text-stone-500 font-mono">
                    ID: {e.event_id} &bull; SHA: {e.snapshot_hash_after.slice(0, 8)}…
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom CTA to step 3 */}
      <div className="flex justify-end pt-2">
        <button
          onClick={() => setActiveSection(3)}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-stone-900 hover:bg-stone-800 text-white font-medium rounded-md text-xs shadow-xs transition-colors"
        >
          <span>Evaluate Recovery Options</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

import React, { useEffect, useState } from 'react';
import {
  fetchCanonicalState,
  fetchPredictReadiness,
} from '../api/predictClient';
import { useAppState } from '../context/AppStateContext';
import { MOCK_REPAIR_ORDERS, KPI_DATA } from '../data/mockData';
import { RepairOrder } from '../types';
import { tickToTime } from '../utils/timeUtils';
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Warehouse,
  Users,
  ClipboardList,
  DollarSign,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  ArrowRight,
} from 'lucide-react';

function ReadinessBadge({ status }: { status: string }) {
  if (status === 'READY') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
        <CheckCircle2 className="w-2.5 h-2.5" /> Ready
      </span>
    );
  }
  if (status === 'AT_RISK') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">
        <AlertTriangle className="w-2.5 h-2.5" /> At Risk
      </span>
    );
  }
  if (status === 'BLOCKED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-950 text-rose-300 border border-rose-800">
        <XCircle className="w-2.5 h-2.5" /> Blocked
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
      <Clock className="w-2.5 h-2.5" /> Checking...
    </span>
  );
}

function BayDisplay({ bay }: { bay: string }) {
  if (bay === 'No assigned bay; task is pending') return <span className="text-slate-500 italic text-xs">Queue</span>;
  if (bay.includes('In holding')) return <span className="text-slate-500 italic text-xs">Holding</span>;
  if (bay.startsWith('BAY-')) {
    const id = bay.split(',')[0].trim();
    return <span className="font-mono text-cyan-300 text-xs">{id}</span>;
  }
  return <span className="text-slate-300 text-xs">{bay.split(',')[0]}</span>;
}

export const OverviewDashboard: React.FC = () => {
  const { workshopState, readinessReport, setWorkshopState, setReadinessReport, setActiveSection } = useAppState();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedRo, setExpandedRo] = useState<string | null>('RO-104');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const state = await fetchCanonicalState();
      setWorkshopState(state);
      const report = await fetchPredictReadiness(state.rooftop_id, state.snapshot_hash);
      setReadinessReport(report);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load workshop data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!workshopState) {
      loadData();
    }
  }, []);

  // Merge readiness data into mock ROs
  const ros: RepairOrder[] = MOCK_REPAIR_ORDERS.map((ro) => {
    if (readinessReport) {
      const assessment = readinessReport.assessments.find((a) => a.ro_id === ro.roId);
      if (assessment) {
        return { ...ro, readinessStatus: assessment.state };
      }
    }
    return ro;
  });

  const counts = {
    total: ros.length,
    atRisk: ros.filter((r) => r.readinessStatus === 'AT_RISK').length,
    ready: ros.filter((r) => r.readinessStatus === 'READY').length,
    blocked: ros.filter((r) => r.readinessStatus === 'BLOCKED').length,
  };

  const evalTime = workshopState ? tickToTime(workshopState.evaluation_tick) : '1:15 PM';

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white">Workshop Overview</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Active repair orders as of <span className="text-cyan-300 font-medium">{evalTime}</span> &bull; {workshopState ? `Snapshot: ${workshopState.snapshot_hash.slice(0, 10)}…` : 'Connecting to shop telemetry…'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {counts.atRisk > 0 && (
            <button
              onClick={() => setActiveSection(2)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-950/80 hover:bg-rose-900 text-rose-200 border border-rose-800 rounded-lg text-xs font-medium transition-colors"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span>Review Disruption ({counts.atRisk})</span>
              <ArrowRight className="w-3 h-3 ml-0.5" />
            </button>
          )}
          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-950/40 border border-rose-800/80 rounded-lg text-rose-200 text-xs">
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Total Active ROs</span>
            <ClipboardList className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-white">{counts.total}</div>
          <div className="text-[11px] text-slate-500 mt-1">Shop floor pipeline</div>
        </div>

        <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Ready to Work</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-emerald-300">{counts.ready}</div>
          <div className="text-[11px] text-slate-500 mt-1">Parts & vehicle verified</div>
        </div>

        <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">At Risk</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-amber-300">{counts.atRisk}</div>
          <div className="text-[11px] text-slate-500 mt-1">Delivery promise threatened</div>
        </div>

        <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">Blocked</span>
            <XCircle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-bold font-mono text-rose-300">{counts.blocked}</div>
          <div className="text-[11px] text-slate-500 mt-1">Awaiting parts allocation</div>
        </div>
      </div>

      {/* RO Table */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl shadow-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#1e2638] flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white">Repair Order Status Board</h3>
            <p className="text-xs text-slate-400">Click any row to view customer complaint, technician assignment, and readiness details.</p>
          </div>
          {readinessReport && (
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
              Live Readiness Synced
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#1e2638] bg-[#0d111a]/60">
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">RO ID</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Vehicle</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Customer</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Bay</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Readiness</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Promise Time</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Action Needed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1b2234]">
              {ros.map((ro) => {
                const isExpanded = expandedRo === ro.roId;
                const needsAttention = ro.readinessStatus === 'AT_RISK' || ro.readinessStatus === 'BLOCKED';
                return (
                  <React.Fragment key={ro.roId}>
                    <tr
                      className={`hover:bg-[#111926] transition-colors cursor-pointer ${needsAttention ? 'bg-rose-950/10' : ''}`}
                      onClick={() => setExpandedRo(isExpanded ? null : ro.roId)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          {isExpanded ? (
                            <ChevronDown className="w-3 h-3 text-slate-500" />
                          ) : (
                            <ChevronRight className="w-3 h-3 text-slate-500" />
                          )}
                          <span className="font-mono font-bold text-cyan-300">{ro.roId}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-200">{ro.vehicle}</td>
                      <td className="px-4 py-3 text-slate-300">{ro.customerName}</td>
                      <td className="px-4 py-3">
                        <BayDisplay bay={ro.bay} />
                      </td>
                      <td className="px-4 py-3">
                        <ReadinessBadge status={ro.readinessStatus} />
                      </td>
                      <td className="px-4 py-3 font-mono text-slate-300">{ro.promisedDelivery}</td>
                      <td className="px-4 py-3">
                        {ro.readinessStatus === 'AT_RISK' && (
                          <span className="inline-flex items-center gap-1 text-amber-300 text-[10px] font-medium">
                            <AlertTriangle className="w-3 h-3" /> Supplier delay &bull; Bay stalled
                          </span>
                        )}
                        {ro.readinessStatus === 'BLOCKED' && (
                          <span className="inline-flex items-center gap-1 text-rose-300 text-[10px] font-medium">
                            <XCircle className="w-3 h-3" /> National backorder
                          </span>
                        )}
                        {ro.readinessStatus === 'READY' && (
                          <span className="text-slate-500 text-[10px]">Normal progression</span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-[#0d111a]">
                        <td colSpan={7} className="px-6 py-4">
                          <div className="space-y-2 text-xs">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              <div>
                                <span className="text-slate-500 font-mono uppercase text-[10px]">Customer Complaint: </span>
                                <p className="text-slate-200 mt-0.5">{ro.customerComplaint}</p>
                              </div>
                              <div>
                                <span className="text-slate-500 font-mono uppercase text-[10px]">Readiness Status Note: </span>
                                <p className="text-slate-300 mt-0.5">{ro.readinessDetails}</p>
                              </div>
                            </div>
                            <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-[#1b2234]">
                              <div className="flex gap-4">
                                <div>
                                  <span className="text-slate-500 font-mono text-[10px] uppercase">Labor Gross: </span>
                                  <span className="text-emerald-300 font-mono font-semibold">${ro.laborGrossUsd.toFixed(2)}</span>
                                </div>
                                <div>
                                  <span className="text-slate-500 font-mono text-[10px] uppercase">Priority Weight: </span>
                                  <span className="text-cyan-300 font-mono font-semibold">{ro.priorityWeight}</span>
                                </div>
                                <div>
                                  <span className="text-slate-500 font-mono text-[10px] uppercase">Physical State: </span>
                                  <span className="text-amber-300 font-mono font-semibold">{ro.physicalState}</span>
                                </div>
                              </div>

                              {ro.readinessStatus === 'AT_RISK' && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveSection(2);
                                  }}
                                  className="inline-flex items-center gap-1.5 px-3 py-1 bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700 rounded text-xs font-medium transition-colors"
                                >
                                  <span>Investigate Disruption Cascade</span>
                                  <ArrowRight className="w-3 h-3" />
                                </button>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bay + Technician capacity cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Bay capacity */}
        <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Warehouse className="w-4 h-4 text-amber-400" />
              <h4 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">Service Bays</h4>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-400 border border-amber-800">
              {KPI_DATA.operationalBays}
            </span>
          </div>
          <div className="space-y-2 text-xs font-mono">
            {[
              { id: 'BAY-01', name: 'Heavy Diagnostic Lift', capacity: '12,000 lbs', ro: 'RO-104', status: 'occupied', color: 'rose' },
              { id: 'BAY-02', name: '2-Post Mechanical', capacity: '10,000 lbs', ro: 'RO-101', status: 'active', color: 'emerald' },
              { id: 'BAY-03', name: '2-Post Mechanical', capacity: '10,000 lbs', ro: 'RO-102', status: 'active', color: 'emerald' },
            ].map((bay) => (
              <div key={bay.id} className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
                <div>
                  <div className="font-bold text-white">{bay.id} — {bay.name}</div>
                  <div className="text-[10px] text-slate-500">{bay.capacity}</div>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] ${
                  bay.color === 'rose'
                    ? 'bg-rose-950 text-rose-300 border border-rose-800'
                    : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                }`}>
                  {bay.status === 'occupied' ? `Stalled (${bay.ro})` : `Active (${bay.ro})`}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Technician capacity */}
        <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-cyan-400" />
              <h4 className="text-xs font-bold text-slate-200 uppercase font-mono tracking-wider">Technicians</h4>
            </div>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
              {KPI_DATA.activeTechnicians}
            </span>
          </div>
          <div className="space-y-2 text-xs font-mono">
            {[
              { id: 'TECH-01', name: 'Marcus V.', skills: 'Diagnostic, EV', status: 'Available', color: 'slate' },
              { id: 'TECH-02', name: 'Elena R.', skills: 'Transmission, Mech', status: 'Stalled (RO-104)', color: 'amber' },
              { id: 'TECH-03', name: 'David K.', skills: 'Brakes, Mech', status: 'Active', color: 'emerald' },
              { id: 'TECH-04', name: 'James P.', skills: 'Express', status: 'Active', color: 'emerald' },
            ].map((tech) => (
              <div key={tech.id} className="p-2.5 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between">
                <div>
                  <div className="font-bold text-white">{tech.name}</div>
                  <div className="text-[10px] text-slate-500">{tech.skills}</div>
                </div>
                <span className={`px-1.5 py-0.5 text-[10px] rounded ${
                  tech.color === 'amber'
                    ? 'bg-amber-950 text-amber-300 border border-amber-800'
                    : tech.color === 'emerald'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-slate-800 text-slate-300'
                }`}>
                  {tech.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Potential Labor Gross */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <DollarSign className="w-5 h-5 text-purple-400" />
          <div>
            <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">Potential Labor Gross</div>
            <div className="text-2xl font-bold font-mono text-cyan-300 mt-0.5">{KPI_DATA.potentialLaborGross}</div>
          </div>
        </div>
        <span className="text-[10px] font-mono text-slate-500 bg-slate-800/60 px-2 py-0.5 rounded border border-slate-700">
          Target gross across 6 active repair orders
        </span>
      </div>
    </div>
  );
};

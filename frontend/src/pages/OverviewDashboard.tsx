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
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Ready
      </span>
    );
  }
  if (status === 'AT_RISK') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
        <AlertTriangle className="w-3 h-3 text-amber-600" /> At Risk
      </span>
    );
  }
  if (status === 'BLOCKED') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
        <XCircle className="w-3 h-3 text-rose-600" /> Blocked
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
      <Clock className="w-3 h-3 text-slate-400" /> Evaluating
    </span>
  );
}

function BayDisplay({ bay }: { bay: string }) {
  if (bay === 'No assigned bay; task is pending') {
    return <span className="text-slate-500 italic text-xs">Unassigned</span>;
  }
  if (bay.includes('In holding')) {
    return <span className="text-slate-500 italic text-xs">Holding Queue</span>;
  }
  if (bay.startsWith('BAY-')) {
    const id = bay.split(',')[0].trim();
    return <span className="font-mono text-slate-800 font-semibold text-xs">{id}</span>;
  }
  return <span className="text-slate-700 text-xs">{bay.split(',')[0]}</span>;
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
    <div className="space-y-6 pb-8">
      {/* Page Title & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Workshop Overview</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time status across 6 active repair orders &bull; Current evaluation time: <span className="font-semibold text-slate-700">{evalTime}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {counts.atRisk > 0 && (
            <button
              onClick={() => setActiveSection(2)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded-md text-xs font-medium transition-colors"
            >
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
              <span>Review Disruption ({counts.atRisk})</span>
              <ArrowRight className="w-3 h-3 ml-0.5" />
            </button>
          )}
          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 rounded-md text-xs font-medium shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-md text-rose-800 text-xs">
          {error}
        </div>
      )}

      {/* KPI Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500">Total Active ROs</span>
            <ClipboardList className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold font-sans text-slate-900">{counts.total}</div>
          <div className="text-xs text-slate-500 mt-1">Shop floor pipeline</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500">Ready to Work</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold font-sans text-emerald-700">{counts.ready}</div>
          <div className="text-xs text-slate-500 mt-1">Parts & vehicle verified</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500">At Risk</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-sans text-amber-700">{counts.atRisk}</div>
          <div className="text-xs text-slate-500 mt-1">Delivery promise threatened</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-500">Blocked</span>
            <XCircle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="text-2xl font-bold font-sans text-rose-700">{counts.blocked}</div>
          <div className="text-xs text-slate-500 mt-1">Awaiting parts allocation</div>
        </div>
      </div>

      {/* Repair Order Table */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Repair Orders Roster</h3>
            <p className="text-xs text-slate-500">Select any order to expand customer complaint, assigned bay, and readiness status notes.</p>
          </div>
          {readinessReport && (
            <span className="text-xs text-slate-600 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200 font-medium">
              Readiness Synchronized
            </span>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold text-left">
                <th className="px-4 py-3">Order ID</th>
                <th className="px-4 py-3">Vehicle</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Assigned Bay</th>
                <th className="px-4 py-3">Readiness Status</th>
                <th className="px-4 py-3">Promised Delivery</th>
                <th className="px-4 py-3">Operational Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {ros.map((ro) => {
                const isExpanded = expandedRo === ro.roId;
                const needsAttention = ro.readinessStatus === 'AT_RISK' || ro.readinessStatus === 'BLOCKED';
                return (
                  <React.Fragment key={ro.roId}>
                    <tr
                      className={`hover:bg-slate-50/80 transition-colors cursor-pointer ${
                        isExpanded ? 'bg-blue-50/30' : needsAttention ? 'bg-amber-50/20' : ''
                      }`}
                      onClick={() => setExpandedRo(isExpanded ? null : ro.roId)}
                    >
                      <td className="px-4 py-3 font-medium">
                        <div className="flex items-center gap-1.5">
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                          )}
                          <span className="font-mono font-bold text-slate-900">{ro.roId}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-800">{ro.vehicle}</td>
                      <td className="px-4 py-3 text-slate-700">{ro.customerName}</td>
                      <td className="px-4 py-3">
                        <BayDisplay bay={ro.bay} />
                      </td>
                      <td className="px-4 py-3">
                        <ReadinessBadge status={ro.readinessStatus} />
                      </td>
                      <td className="px-4 py-3 font-mono font-medium text-slate-800">{ro.promisedDelivery}</td>
                      <td className="px-4 py-3">
                        {ro.readinessStatus === 'AT_RISK' && (
                          <span className="text-amber-800 text-xs font-medium inline-flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-amber-600" /> Supplier delay on lift
                          </span>
                        )}
                        {ro.readinessStatus === 'BLOCKED' && (
                          <span className="text-rose-800 text-xs font-medium inline-flex items-center gap-1">
                            <XCircle className="w-3 h-3 text-rose-600" /> National backorder
                          </span>
                        )}
                        {ro.readinessStatus === 'READY' && (
                          <span className="text-slate-500 text-xs">On Schedule</span>
                        )}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-slate-50/90 border-t border-slate-200">
                        <td colSpan={7} className="px-6 py-4">
                          <div className="space-y-3">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              <div className="bg-white p-3 rounded-md border border-slate-200 text-xs">
                                <span className="font-semibold text-slate-700 block mb-1">Customer Complaint</span>
                                <p className="text-slate-600 leading-relaxed">{ro.customerComplaint}</p>
                              </div>
                              <div className="bg-white p-3 rounded-md border border-slate-200 text-xs">
                                <span className="font-semibold text-slate-700 block mb-1">Readiness Assessment Notes</span>
                                <p className="text-slate-600 leading-relaxed">{ro.readinessDetails}</p>
                              </div>
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-200/80">
                              <div className="flex items-center gap-6 text-xs">
                                <div>
                                  <span className="text-slate-500">Labor Gross: </span>
                                  <span className="font-mono font-semibold text-slate-900">${ro.laborGrossUsd.toFixed(2)}</span>
                                </div>
                                <div>
                                  <span className="text-slate-500">Priority Weight: </span>
                                  <span className="font-semibold text-slate-800">Tier {ro.priorityWeight}</span>
                                </div>
                                <div>
                                  <span className="text-slate-500">Vehicle State: </span>
                                  <span className="font-medium text-slate-800">{ro.physicalState}</span>
                                </div>
                              </div>

                              {ro.readinessStatus === 'AT_RISK' && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveSection(2);
                                  }}
                                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-md text-xs font-medium shadow-xs transition-colors"
                                >
                                  <span>Inspect Bottleneck Impact</span>
                                  <ArrowRight className="w-3.5 h-3.5" />
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

      {/* Workshop Resources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Service Bays */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Warehouse className="w-4 h-4 text-slate-600" />
              <h4 className="text-sm font-semibold text-slate-900">Service Bay Allocations</h4>
            </div>
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
              {KPI_DATA.operationalBays} Operational
            </span>
          </div>

          <div className="space-y-2 text-xs">
            {[
              { id: 'BAY-01', name: 'Heavy Diagnostic Lift', spec: '12,000 lbs', ro: 'RO-104', status: 'Stalled', color: 'amber' },
              { id: 'BAY-02', name: '2-Post Mechanical Lift 1', spec: '10,000 lbs', ro: 'RO-101', status: 'Active', color: 'emerald' },
              { id: 'BAY-03', name: '2-Post Mechanical Lift 2', spec: '10,000 lbs', ro: 'RO-102', status: 'Active', color: 'emerald' },
            ].map((bay) => (
              <div key={bay.id} className="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between">
                <div>
                  <div className="font-semibold text-slate-900">{bay.id} &bull; {bay.name}</div>
                  <div className="text-[11px] text-slate-500">{bay.spec}</div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  bay.color === 'amber'
                    ? 'bg-amber-50 text-amber-800 border border-amber-200'
                    : 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                }`}>
                  {bay.status} ({bay.ro})
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Technicians */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-slate-600" />
              <h4 className="text-sm font-semibold text-slate-900">Technician Fleet Roster</h4>
            </div>
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
              {KPI_DATA.activeTechnicians} Active
            </span>
          </div>

          <div className="space-y-2 text-xs">
            {[
              { id: 'TECH-01', name: 'Marcus V.', cert: 'Diagnostic, EV Systems', status: 'Available', color: 'slate' },
              { id: 'TECH-02', name: 'Elena R.', cert: 'Transmission, Powertrain', status: 'Stalled (RO-104)', color: 'amber' },
              { id: 'TECH-03', name: 'David K.', cert: 'Brakes, Suspension', status: 'In Repair (RO-101)', color: 'emerald' },
              { id: 'TECH-04', name: 'James P.', cert: 'General Maintenance', status: 'In Inspection (RO-102)', color: 'emerald' },
            ].map((tech) => (
              <div key={tech.id} className="p-2.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between">
                <div>
                  <div className="font-semibold text-slate-900">{tech.name}</div>
                  <div className="text-[11px] text-slate-500">{tech.cert}</div>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  tech.color === 'amber'
                    ? 'bg-amber-50 text-amber-800 border border-amber-200'
                    : tech.color === 'emerald'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : 'bg-slate-100 text-slate-700 border border-slate-200'
                }`}>
                  {tech.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Target Revenue Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-700">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500">Active Shift Target Revenue</div>
            <div className="text-xl font-bold font-mono text-slate-900">{KPI_DATA.potentialLaborGross}</div>
          </div>
        </div>
        <span className="text-xs text-slate-500 bg-slate-50 px-3 py-1 rounded-md border border-slate-200">
          6 scheduled repair orders
        </span>
      </div>
    </div>
  );
};

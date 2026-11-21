import React from 'react';
import { useAppState } from '../context/AppStateContext';
import { MOCK_REPAIR_ORDERS } from '../data/mockData';
import {
  TrendingUp,
  DollarSign,
  Clock,
  CheckCircle2,
  Truck,
  Warehouse,
  ArrowRight,
  ShieldCheck,
  Award,
} from 'lucide-react';

export const PerformanceView: React.FC = () => {
  const { recoveryReport, approvalResult, hasRunRecovery, setActiveSection } = useAppState();

  const totalLaborGross = MOCK_REPAIR_ORDERS.reduce((sum, ro) => sum + ro.laborGrossUsd, 0);
  const onTimeCount = hasRunRecovery ? 5 : 4; // RO-104 protected upon recovery execution

  const dr = recoveryReport?.decision_replay;

  function KpiCard({
    label,
    value,
    sub,
    color,
    icon: Icon,
    placeholder,
  }: {
    label: string;
    value?: string | number;
    sub?: string;
    color?: string;
    icon: React.ElementType;
    placeholder?: string;
  }) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-5 flex flex-col justify-between space-y-3 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-500">{label}</span>
          <Icon className={`w-4 h-4 ${color || 'text-slate-400'}`} />
        </div>
        {hasRunRecovery && value !== undefined ? (
          <div>
            <div className={`text-2xl font-bold font-mono ${color || 'text-slate-900'}`}>{value}</div>
            {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
          </div>
        ) : (
          <div>
            <div className="text-xs text-slate-400 italic">
              {placeholder || 'Available after Recovery step'}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Header Banner */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <Award className="w-4 h-4 text-blue-700" />
              <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">
                Executive Operations Ledger
              </span>
            </div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Performance & Economic Insights</h2>
            <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
              Consolidated outcome metrics measuring contribution margin protected, customer promise adherence,
              and physical service-bay utilization under verified decision intelligence.
            </p>
          </div>

          {!hasRunRecovery && (
            <button
              onClick={() => setActiveSection(3)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white rounded-md text-xs font-medium shadow-xs transition-colors self-start sm:self-auto shrink-0"
            >
              <span>Run Recovery Optimizer</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {approvalResult?.status === 'COMMITTED' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-md text-xs font-medium self-start sm:self-auto shrink-0">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>DISPATCH COMMITTED</span>
            </div>
          )}
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Potential Labor Gross"
          value={`$${totalLaborGross.toFixed(2)}`}
          sub="6 scheduled repair orders"
          color="text-slate-900"
          icon={DollarSign}
          placeholder="Always available"
        />
        <KpiCard
          label="Expedited Freight Investment"
          value={dr ? `-$${dr.sourcing_freight_usd}` : undefined}
          sub="Dedicated hotshot courier"
          color="text-rose-700"
          icon={Truck}
        />
        <KpiCard
          label="Net Economic Improvement"
          value={dr ? `+$${dr.net_economic_delta_usd}` : undefined}
          sub="Protected vs. unmitigated stall"
          color="text-emerald-700"
          icon={TrendingUp}
        />
        <KpiCard
          label="Customer Promise Adherence"
          value={hasRunRecovery ? `${onTimeCount} / ${MOCK_REPAIR_ORDERS.length} (83%)` : `4 / 6 (67%)`}
          sub={hasRunRecovery ? "RO-104 protected on-schedule" : "RO-104 threatened by delay"}
          color="text-slate-900"
          icon={CheckCircle2}
          placeholder="Always available"
        />
      </div>

      {/* Bay Utilization & Avoided Idle Hours */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Warehouse className="w-4 h-4 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900">Physical Service-Bay Utilization</h3>
          </div>
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-700">
            BAY-01 Heavy Diagnostic Lift
          </span>
        </div>

        {hasRunRecovery && dr ? (
          <div className="space-y-4">
            {/* BAY-01 Utilization Bar */}
            <div>
              <div className="flex justify-between items-center mb-1.5 text-xs">
                <span className="text-slate-700 font-medium">BAY-01 Active Working Utilization</span>
                <span className="font-mono font-bold text-slate-900">
                  {dr.proposed_bay_utilization_pct.toFixed(1)}%
                  <span className="text-emerald-700 ml-1.5">(+{dr.delta_bay_utilization_pct.toFixed(1)}% recovered)</span>
                </span>
              </div>
              <div className="h-3 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                <div
                  className="h-full bg-blue-700 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(dr.proposed_bay_utilization_pct, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-500 mt-1.5 font-mono">
                <span>Baseline unmitigated: {dr.baseline_bay_utilization_pct.toFixed(1)}%</span>
                <span>Optimized dispatch: {dr.proposed_bay_utilization_pct.toFixed(1)}%</span>
              </div>
            </div>

            {/* Capacity Relief Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-emerald-600" />
                  <span className="text-slate-700 font-medium">Dead Lift Idle Time Avoided</span>
                </div>
                <span className="font-mono font-bold text-emerald-700 text-sm">{dr.delta_idle_minutes} minutes freed</span>
              </div>

              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-blue-600" />
                  <span className="text-slate-700 font-medium">Downstream RO-106 Unblocked</span>
                </div>
                <span className="font-medium text-slate-900">Admitted to BAY-01</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-500 italic p-4 bg-slate-50 rounded-md border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>Utilization and avoided idle time will populate once the Economic Optimizer runs in Recovery Decisions.</span>
            <button
              onClick={() => setActiveSection(3)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 rounded-md text-xs font-medium shadow-xs transition-colors shrink-0 self-start sm:self-auto"
            >
              <span>Run Optimizer</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Repair Order Delivery Outcome Ledger Table */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900">Full-Shop Delivery Outcome Ledger</h3>
          <p className="text-xs text-slate-500">Final customer delivery promise status across all 6 active repair orders.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 font-semibold text-left">
                <th className="px-4 py-3">Order ID</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Promised Delivery</th>
                <th className="px-4 py-3">Labor Value</th>
                <th className="px-4 py-3">Dispatch Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {MOCK_REPAIR_ORDERS.map((ro) => {
                const isRo104 = ro.roId === 'RO-104';
                return (
                  <tr key={ro.roId} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-slate-900">{ro.roId}</td>
                    <td className="px-4 py-3 text-slate-800">{ro.customerName}</td>
                    <td className="px-4 py-3 font-mono font-medium text-slate-700">{ro.promisedDelivery}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-900">${ro.laborGrossUsd.toFixed(2)}</td>
                    <td className="px-4 py-3">
                      {isRo104 ? (
                        hasRunRecovery ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Protected On-Time (Hotshot S1)
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
                            At Risk (Awaiting Sourcing Decision)
                          </span>
                        )
                      ) : ro.readinessStatus === 'READY' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Delivered On-Time
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                          Awaiting National Part ETA
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

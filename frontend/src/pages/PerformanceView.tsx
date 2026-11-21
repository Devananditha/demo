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

  // Totals from mock ROs
  const totalLaborGross = MOCK_REPAIR_ORDERS.reduce((sum, ro) => sum + ro.laborGrossUsd, 0);
  const onTimeCount = hasRunRecovery ? 5 : 4; // RO-104 is protected when recovery is run

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
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 flex flex-col justify-between space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">{label}</span>
          <Icon className={`w-4 h-4 ${color || 'text-slate-400'}`} />
        </div>
        {hasRunRecovery && value !== undefined ? (
          <div>
            <div className={`text-2xl font-bold font-mono ${color || 'text-white'}`}>{value}</div>
            {sub && <div className="text-[11px] text-slate-500 mt-0.5">{sub}</div>}
          </div>
        ) : (
          <div>
            <div className="text-xs font-mono text-slate-500 italic">
              {placeholder || 'Available after Recovery step'}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-10">
      {/* Header */}
      <div className="bg-[#111522] border border-emerald-800/60 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <Award className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider font-mono">
                Executive Operations Ledger
              </span>
            </div>
            <h2 className="text-lg font-bold text-white">Performance & Economic Insights</h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Consolidated outcome metrics measuring contribution margin protected, customer promise adherence,
              and physical service-bay utilization under verified decision intelligence.
            </p>
          </div>

          {!hasRunRecovery && (
            <button
              onClick={() => setActiveSection(3)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors self-start sm:self-auto shrink-0"
            >
              <span>Run Recovery Optimizer</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {approvalResult?.status === 'COMMITTED' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-950 text-emerald-300 border border-emerald-800 rounded-lg text-xs font-mono font-bold self-start sm:self-auto shrink-0">
              <CheckCircle2 className="w-3.5 h-3.5" />
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
          sub="6 active repair orders"
          color="text-cyan-300"
          icon={DollarSign}
          placeholder="Always available"
        />
        <KpiCard
          label="Expedited Freight Investment"
          value={dr ? `-$${dr.sourcing_freight_usd}` : undefined}
          sub="Regional Hotshot dedicated courier"
          color="text-rose-300"
          icon={Truck}
        />
        <KpiCard
          label="Net Contribution Improvement"
          value={dr ? `+$${dr.net_economic_delta_usd}` : undefined}
          sub="Protected vs. unmitigated stall"
          color="text-emerald-300"
          icon={TrendingUp}
        />
        <KpiCard
          label="Customer Promise Adherence"
          value={hasRunRecovery ? `${onTimeCount} / ${MOCK_REPAIR_ORDERS.length} (83%)` : `4 / 6 (67%)`}
          sub={hasRunRecovery ? "RO-104 protected on-time" : "RO-104 threatened by delay"}
          color="text-purple-300"
          icon={CheckCircle2}
          placeholder="Always available"
        />
      </div>

      {/* Bay Utilization & Avoided Idle Hours */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Warehouse className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-bold text-white">Physical Service-Bay Efficiency</h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            BAY-01 Heavy Diagnostic Lift
          </span>
        </div>

        {hasRunRecovery && dr ? (
          <div className="space-y-4">
            {/* BAY-01 utilization bar */}
            <div>
              <div className="flex justify-between items-center mb-1.5 text-xs">
                <span className="text-slate-300 font-mono font-medium">BAY-01 Active Working Utilization</span>
                <span className="text-cyan-300 font-mono font-bold">
                  {dr.proposed_bay_utilization_pct.toFixed(1)}%
                  <span className="text-emerald-400 ml-1.5">(+{dr.delta_bay_utilization_pct.toFixed(1)}% recovered)</span>
                </span>
              </div>
              <div className="h-3.5 bg-[#0d101a] rounded-full overflow-hidden border border-[#1b2234]">
                <div
                  className="h-full bg-gradient-to-r from-cyan-600 via-cyan-500 to-emerald-400 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(dr.proposed_bay_utilization_pct, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
                <span>Baseline unmitigated: {dr.baseline_bay_utilization_pct.toFixed(1)}%</span>
                <span>Optimized dispatch: {dr.proposed_bay_utilization_pct.toFixed(1)}%</span>
              </div>
            </div>

            {/* Capacity relief breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-slate-300">Dead Lift Idle Time Avoided</span>
                </div>
                <span className="font-mono font-bold text-emerald-300">{dr.delta_idle_minutes} minutes freed</span>
              </div>

              <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-slate-300">Downstream RO-106 Unblocked</span>
                </div>
                <span className="font-mono font-bold text-cyan-300">Admitted to BAY-01</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-400 italic p-4 bg-[#0d101a] rounded-lg border border-[#1b2234] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>Utilization and avoided idle time will populate once the Economic Optimizer runs in Recovery Decisions.</span>
            <button
              onClick={() => setActiveSection(3)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-900/60 hover:bg-purple-800 text-purple-200 border border-purple-700 rounded text-xs font-medium transition-colors shrink-0 self-start sm:self-auto"
            >
              <span>Run Optimizer</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* RO Summary Table */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl shadow-xl overflow-hidden">
        <div className="px-5 py-3.5 border-b border-[#1e2638]">
          <h3 className="text-sm font-bold text-white">Full-Shop Delivery Outcome Ledger</h3>
          <p className="text-xs text-slate-400">Final delivery promise status across all 6 active repair orders.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#1e2638] bg-[#0d111a]/60">
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">RO ID</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Customer</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Promise Time</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Labor Value</th>
                <th className="text-left px-4 py-2.5 font-mono uppercase text-[10px] text-slate-500 tracking-wider">Dispatch Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1b2234]">
              {MOCK_REPAIR_ORDERS.map((ro) => {
                const isRo104 = ro.roId === 'RO-104';
                return (
                  <tr key={ro.roId} className="hover:bg-[#111926] transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-cyan-300">{ro.roId}</td>
                    <td className="px-4 py-3 text-slate-200">{ro.customerName}</td>
                    <td className="px-4 py-3 font-mono text-slate-300">{ro.promisedDelivery}</td>
                    <td className="px-4 py-3 font-mono text-emerald-300">${ro.laborGrossUsd.toFixed(2)}</td>
                    <td className="px-4 py-3">
                      {isRo104 ? (
                        hasRunRecovery ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                            <CheckCircle2 className="w-2.5 h-2.5" /> Protected On-Time (Hotshot S1)
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-800">
                            At Risk (Awaiting Sourcing Decision)
                          </span>
                        )
                      ) : ro.readinessStatus === 'READY' ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                          <CheckCircle2 className="w-2.5 h-2.5" /> Delivered On-Time
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-rose-300 border border-slate-700">
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

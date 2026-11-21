import React, { useState } from 'react';
import { fetchStallBreakerRecovery } from '../api/predictClient';
import { useAppState } from '../context/AppStateContext';
import { SYNTHETIC_DISRUPTION_SCENARIO } from '../data/mockData';
import {
  Play,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Truck,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

export const RecoveryDecisionsView: React.FC = () => {
  const { recoveryReport, setRecoveryReport, setHasRunRecovery, hasRunRecovery, setActiveSection } = useAppState();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scenario = SYNTHETIC_DISRUPTION_SCENARIO;
  const { baseline, alternative } = scenario.supplierComparison;

  const handleRunRecovery = async () => {
    setLoading(true);
    setError(null);
    try {
      const report = await fetchStallBreakerRecovery();
      setRecoveryReport(report);
      setHasRunRecovery(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to compute recovery recommendations.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-10">
      {/* Context card */}
      <div className="bg-[#111522] border border-purple-800/60 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider font-mono">
                Economic Recovery Decisions
              </span>
            </div>
            <h2 className="text-lg font-bold text-white">RO-104 — 2020 CrossTour AWD Recovery Sourcing</h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
              Customer: <strong className="text-white">Robert Thorne</strong> &bull; Work: Shift solenoid valve replacement (120 min remaining).
              Vehicle is immobilized on BAY-01. Choose between ground freight baseline vs. expedited courier recovery.
            </p>
          </div>

          {hasRunRecovery && (
            <button
              onClick={() => setActiveSection(4)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold shadow-md transition-colors self-start sm:self-auto shrink-0"
            >
              <span>Proceed to Verification Gate</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Supplier option cards */}
      <div>
        <h3 className="text-sm font-bold text-white mb-3">Sourcing Alternatives Comparison</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Option A — S2 Ground (baseline, miss promise) */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                  Option A — Standard Ground Shuttle
                </span>
                <div className="text-sm font-bold text-white mt-1.5">{baseline.supplierName}</div>
              </div>
              <div className="text-right">
                <div className="text-base font-mono font-bold text-emerald-300">$0.00</div>
                <div className="text-[10px] text-slate-500">Freight surcharge</div>
              </div>
            </div>

            <div className="bg-[#0d101a] border border-[#1b2234] rounded-lg p-3 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Parts Usable Ready:</span>
                <span className="text-orange-300 font-bold">{baseline.usableReadyTime}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Customer Promise:</span>
                <span className="text-slate-200">4:00 PM</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Work Window Before Shift End:</span>
                <span className="text-rose-400 font-bold">30 min (Need 120 min)</span>
              </div>
            </div>

            <div className="flex items-center gap-2 p-2.5 bg-rose-950/30 border border-rose-900/50 rounded-lg text-xs text-rose-300 leading-relaxed">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>
                <strong>Severe Delivery Breach:</strong> Parts arrive 30 minutes after customer promise time. BAY-01 remains blocked all afternoon, starving RO-106.
              </span>
            </div>
          </div>

          {/* Option B — S1 Hotshot (alternative, feasible) */}
          <div className="bg-[#121624] border-2 border-purple-500/60 rounded-xl p-5 space-y-3 shadow-lg relative">
            <div className="flex items-center justify-between">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-950 text-purple-300 border border-purple-800 font-bold">
                  Option B — Dedicated Hotshot Courier
                </span>
                <div className="text-sm font-bold text-white mt-1.5">{alternative.supplierName}</div>
              </div>
              <div className="text-right">
                <div className="text-base font-mono font-bold text-rose-300">+${alternative.freightSurchargeUsd.toFixed(2)}</div>
                <div className="text-[10px] text-slate-500">Expedited freight</div>
              </div>
            </div>

            <div className="bg-[#0d101a] border border-[#1b2234] rounded-lg p-3 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Parts Usable Ready:</span>
                <span className="text-emerald-300 font-bold">{alternative.usableReadyTime}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Customer Promise:</span>
                <span className="text-slate-200">4:00 PM</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Work Window Available:</span>
                <span className="text-emerald-400 font-bold">135 min (Need 120 min)</span>
              </div>
            </div>

            <div className="flex items-center gap-2 p-2.5 bg-emerald-950/30 border border-emerald-900/50 rounded-lg text-xs text-emerald-300 leading-relaxed">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              <span>
                <strong>Feasible & On-Time:</strong> Parts arrive at 1:45 PM. Technician Elena finishes repair by 3:45 PM, beating customer promise and freeing BAY-01 for RO-106.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Run Optimizer */}
      <div className="bg-[#111522] border-2 border-purple-500/40 rounded-xl p-5 shadow-2xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-purple-400" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
                Workshop Economic Optimizer
              </span>
            </div>
            <h3 className="text-base font-bold text-white">Full-Shop Capacity Re-Solve</h3>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Re-optimizes scheduling across all service bays, technicians, and repair commitments to compute the exact net contribution delta.
            </p>
          </div>

          <button
            onClick={handleRunRecovery}
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white border border-purple-400 rounded-lg text-xs font-mono font-bold uppercase tracking-wider shadow-lg transition-all shrink-0"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Computing Optimal Dispatch…
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white text-white" />
                Run Economic Optimizer
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="p-3 bg-rose-950/40 border border-rose-800 rounded-lg text-rose-200 text-xs">{error}</div>
        )}

        {/* Results — only shown after execution */}
        {hasRunRecovery && recoveryReport && (
          <div className="space-y-4 pt-4 border-t border-[#1e2638] animate-fade-in">
            {/* Recommended action */}
            {recoveryReport.recommended_action && (
              <div className="p-4 bg-purple-950/30 border border-purple-700/60 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-purple-300 font-bold text-sm">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Recommended Dispatch Plan
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                    FEASIBLE & VERIFIED
                  </span>
                </div>
                <p className="text-xs text-slate-200 leading-relaxed">{recoveryReport.recommended_action.description}</p>
                {recoveryReport.recommended_action.freight_surcharge_usd && (
                  <div className="flex items-center gap-2 text-xs text-slate-400 pt-1">
                    <Truck className="w-3.5 h-3.5 text-purple-400" />
                    <span>Authorized Courier Cost: </span>
                    <span className="text-rose-300 font-mono font-bold">
                      ${recoveryReport.recommended_action.freight_surcharge_usd}
                    </span>
                    <span className="text-slate-500">(Within manager $50.00 approval authority)</span>
                  </div>
                )}
              </div>
            )}

            {/* Decision Replay delta table */}
            {recoveryReport.decision_replay && (
              <div className="space-y-2">
                <div className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                  Net Economic & Capacity Impact Ledger
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Labor Contribution</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      +${recoveryReport.decision_replay.delta_gross_contribution_usd}
                    </div>
                    <div className="text-[9px] text-slate-500">Unmitigated baseline</div>
                  </div>
                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Delivery Lateness</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      -195 min
                    </div>
                    <div className="text-[9px] text-slate-500">Customer delays avoided</div>
                  </div>
                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Courier Freight</div>
                    <div className="text-xs font-bold text-rose-400 font-mono mt-1">
                      -${recoveryReport.decision_replay.sourcing_freight_usd}
                    </div>
                    <div className="text-[9px] text-slate-500">Expedited surcharge</div>
                  </div>
                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">BAY-01 Utilization</div>
                    <div className="text-xs font-bold text-cyan-400 font-mono mt-1">
                      +{recoveryReport.decision_replay.delta_bay_utilization_pct.toFixed(1)}%
                    </div>
                    <div className="text-[9px] text-slate-500">Heavy lift uptime</div>
                  </div>
                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Avoided Idle Time</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      {recoveryReport.decision_replay.delta_idle_minutes} min
                    </div>
                    <div className="text-[9px] text-slate-500">Dead lift hours saved</div>
                  </div>
                  <div className="p-3 bg-emerald-950/20 border border-emerald-900/60 rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-emerald-400 font-bold">Net Economic Gain</div>
                    <div className="text-xs font-bold text-emerald-300 font-mono mt-1">
                      +${recoveryReport.decision_replay.net_economic_delta_usd}
                    </div>
                    <div className="text-[9px] text-emerald-400/80">Net recovery delta</div>
                  </div>
                </div>
              </div>
            )}

            {/* Explainability in plain English */}
            {recoveryReport.explainability && (
              <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-xl space-y-2 text-xs">
                <div className="font-bold text-white text-sm">{recoveryReport.explainability.recommendation_summary}</div>
                <p className="text-slate-300 leading-relaxed">
                  <strong className="text-slate-200">Operational Reason: </strong>
                  {recoveryReport.explainability.primary_driver}
                </p>
                {recoveryReport.explainability.unresolved_risks.length > 0 && (
                  <div className="pt-2 border-t border-[#1b2234]">
                    <div className="text-[10px] font-mono uppercase text-amber-400 font-bold mb-1">Active Courier Risks</div>
                    <ul className="list-disc pl-4 space-y-0.5 text-slate-400">
                      {recoveryReport.explainability.unresolved_risks.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Next Step CTA */}
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveSection(4)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-xs shadow-lg transition-all"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>Verify Plan Against Operational Rules</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

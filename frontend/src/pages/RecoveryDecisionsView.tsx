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
    <div className="space-y-6 pb-8">
      {/* Context Header Card */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-semibold text-stone-900 uppercase tracking-wide">
                Decision Support Workbench
              </span>
            </div>
            <h2 className="text-xl font-bold text-stone-900 tracking-tight">RO-104 Sourcing Recovery & Trade-Off Analysis</h2>
            <p className="text-xs text-stone-500 mt-1 max-w-2xl leading-relaxed">
              Customer: <strong className="text-stone-800">Robert Thorne</strong> &bull; Vehicle: <strong className="text-stone-800">2020 CrossTour AWD</strong> &bull; Work: Shift solenoid valve replacement (120 min duration).
              Vehicle is currently immobilized on BAY-01 awaiting replacement parts.
            </p>
          </div>

          {hasRunRecovery && (
            <button
              onClick={() => setActiveSection(4)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-md text-xs font-medium shadow-xs transition-colors self-start sm:self-auto shrink-0"
            >
              <span>Proceed to Verification Gate</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Supplier Sourcing Comparison Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-stone-900">Sourcing Alternatives Evaluation</h3>
          <span className="text-xs text-stone-500">Evaluated against customer delivery promise (4:00 PM)</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Option A — Standard Ground Shuttle */}
          <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 space-y-4 shadow-xs flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-[#eee8df] pb-3">
                <div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-[#f5f1e8] text-stone-700 border border-[#ded7c8]">
                    Option A &bull; Inactive Quote
                  </span>
                  <div className="text-base font-bold text-stone-900 mt-1.5">{baseline.supplierName}</div>
                </div>
                <div className="text-right">
                  <div className="text-base font-mono font-bold text-stone-900">$0.00</div>
                  <div className="text-[11px] text-stone-500">Freight surcharge</div>
                </div>
              </div>

              <div className="bg-[#faf8f5] border border-[#e5dfd5] rounded-md p-3 space-y-2 text-xs">
                <div className="flex justify-between text-stone-600">
                  <span>Parts Usable Ready:</span>
                  <span className="font-mono font-bold text-rose-700">{baseline.usableReadyTime}</span>
                </div>
                <div className="flex justify-between text-stone-600">
                  <span>Customer Delivery Promise:</span>
                  <span className="font-mono font-medium text-stone-800">4:00 PM</span>
                </div>
                <div className="flex justify-between text-stone-600">
                  <span>Available Shift Work Window:</span>
                  <span className="font-mono font-bold text-rose-700">30 min (Need 120 min)</span>
                </div>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-3 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-900 leading-relaxed">
              <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
              <div>
                <strong className="font-semibold text-rose-950 block">Severe Delivery Breach:</strong>
                Parts arrive 30 minutes after promise deadline. Repair extends past regular shift into unauthorized overtime, and BAY-01 remains stalled all afternoon.
              </div>
            </div>
          </div>

          {/* Option B — Expedited Hotshot Courier */}
          <div className="bg-white border-2 border-stone-900 rounded-lg p-5 space-y-4 shadow-xs flex flex-col justify-between relative">
            <div className="space-y-3">
              <div className="flex items-center justify-between border-b border-[#eee8df] pb-3">
                <div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#eae3d5] text-stone-900 border border-[#ded7c8]">
                    Option B &bull; Recommended Candidate
                  </span>
                  <div className="text-base font-bold text-stone-900 mt-1.5">{alternative.supplierName}</div>
                </div>
                <div className="text-right">
                  <div className="text-base font-mono font-bold text-stone-900">+${alternative.freightSurchargeUsd.toFixed(2)}</div>
                  <div className="text-[11px] text-stone-500">Expedited courier</div>
                </div>
              </div>

              <div className="bg-[#faf8f5] border border-[#e5dfd5] rounded-md p-3 space-y-2 text-xs">
                <div className="flex justify-between text-stone-600">
                  <span>Parts Usable Ready:</span>
                  <span className="font-mono font-bold text-emerald-800">{alternative.usableReadyTime}</span>
                </div>
                <div className="flex justify-between text-stone-600">
                  <span>Customer Delivery Promise:</span>
                  <span className="font-mono font-medium text-stone-800">4:00 PM</span>
                </div>
                <div className="flex justify-between text-stone-600">
                  <span>Available Shift Work Window:</span>
                  <span className="font-mono font-bold text-emerald-800">135 min (Need 120 min)</span>
                </div>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-3 bg-emerald-50 border border-emerald-200 rounded-md text-xs text-emerald-900 leading-relaxed">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600 mt-0.5" />
              <div>
                <strong className="font-semibold text-emerald-950 block">Promise Protected & Bay Unblocked:</strong>
                Parts usable by 1:45 PM. Technician Elena finishes repair by 3:45 PM, beating customer promise and freeing BAY-01 for downstream vehicle RO-106.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Economic Optimizer Trigger Section */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-stone-800" />
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-800">
                Economic Optimization Engine
              </span>
            </div>
            <h3 className="text-base font-bold text-stone-900">Run Full-Shop Capacity Re-Solve</h3>
            <p className="text-xs text-stone-500 max-w-2xl leading-relaxed">
              Simultaneously optimizes schedules across all bays, technicians, and work orders to calculate the exact net economic delta of adopting the expedited courier alternative.
            </p>
          </div>

          <button
            onClick={handleRunRecovery}
            disabled={loading}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-stone-900 hover:bg-stone-800 text-white rounded-md text-xs font-medium shadow-xs transition-colors shrink-0"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                Computing Optimal Dispatch…
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-white text-white" />
                Run Economic Optimizer
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-md text-rose-800 text-xs">{error}</div>
        )}

        {/* Results — Displayed Reactively After Optimizer Solve */}
        {hasRunRecovery && recoveryReport && (
          <div className="space-y-4 pt-4 border-t border-[#eee8df]">
            {/* Recommendation Overview Callout */}
            {recoveryReport.recommended_action && (
              <div className="p-4 bg-[#faf8f5] border border-[#e5dfd5] rounded-lg space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-stone-900 font-semibold text-sm">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Optimal Dispatch Recommendation
                  </div>
                  <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-900 border border-emerald-200">
                    Constraint-Feasible & Verified
                  </span>
                </div>
                <p className="text-xs text-stone-700 leading-relaxed">{recoveryReport.recommended_action.description}</p>
                {recoveryReport.recommended_action.freight_surcharge_usd && (
                  <div className="flex items-center gap-2 text-xs text-stone-600 pt-1">
                    <Truck className="w-3.5 h-3.5 text-stone-500" />
                    <span>Expedited Freight Surcharge: </span>
                    <span className="text-stone-900 font-mono font-bold">
                      ${recoveryReport.recommended_action.freight_surcharge_usd}
                    </span>
                    <span className="text-stone-500">(Within manager $50.00 approval authority)</span>
                  </div>
                )}
              </div>
            )}

            {/* Decision Replay: Verified Economic Impact Metrics */}
            {recoveryReport.decision_replay && (
              <div className="space-y-2">
                <div className="text-xs font-semibold text-stone-700 uppercase tracking-wide">
                  Verified Economic & Capacity Impact Ledger
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                  <div className="p-3 bg-[#faf8f5] border border-[#e5dfd5] rounded-md">
                    <div className="text-[11px] font-medium text-stone-500">Labor Protected</div>
                    <div className="text-sm font-bold text-stone-900 font-mono mt-1">
                      +${recoveryReport.decision_replay.delta_gross_contribution_usd}
                    </div>
                    <div className="text-[10px] text-stone-500">Unmitigated baseline</div>
                  </div>

                  <div className="p-3 bg-[#faf8f5] border border-[#e5dfd5] rounded-md">
                    <div className="text-[11px] font-medium text-stone-500">Delivery Lateness</div>
                    <div className="text-sm font-bold text-emerald-800 font-mono mt-1">
                      -195 min
                    </div>
                    <div className="text-[10px] text-stone-500">Customer delay avoided</div>
                  </div>

                  <div className="p-3 bg-[#faf8f5] border border-[#e5dfd5] rounded-md">
                    <div className="text-[11px] font-medium text-stone-500">Courier Freight</div>
                    <div className="text-sm font-bold text-stone-700 font-mono mt-1">
                      -${recoveryReport.decision_replay.sourcing_freight_usd}
                    </div>
                    <div className="text-[10px] text-stone-500">Expedited surcharge</div>
                  </div>

                  <div className="p-3 bg-[#faf8f5] border border-[#e5dfd5] rounded-md">
                    <div className="text-[11px] font-medium text-stone-500">BAY-01 Utilization</div>
                    <div className="text-sm font-bold text-stone-900 font-mono mt-1">
                      +{recoveryReport.decision_replay.delta_bay_utilization_pct.toFixed(1)}%
                    </div>
                    <div className="text-[10px] text-stone-500">Active lift uptime</div>
                  </div>

                  <div className="p-3 bg-[#faf8f5] border border-[#e5dfd5] rounded-md">
                    <div className="text-[11px] font-medium text-stone-500">Dead Lift Avoided</div>
                    <div className="text-sm font-bold text-emerald-800 font-mono mt-1">
                      {recoveryReport.decision_replay.delta_idle_minutes} min
                    </div>
                    <div className="text-[10px] text-stone-500">Wasted stall hours freed</div>
                  </div>

                  <div className="p-3 bg-emerald-50/80 border border-emerald-200 rounded-md">
                    <div className="text-[11px] font-semibold text-emerald-900">Net Economic Gain</div>
                    <div className="text-sm font-bold text-emerald-800 font-mono mt-1">
                      +${recoveryReport.decision_replay.net_economic_delta_usd}
                    </div>
                    <div className="text-[10px] text-emerald-700">Net recovery delta</div>
                  </div>
                </div>
              </div>
            )}

            {/* Operational Explainability */}
            {recoveryReport.explainability && (
              <div className="p-4 bg-[#faf8f5] border border-[#e5dfd5] rounded-md space-y-2 text-xs">
                <div className="font-semibold text-stone-900 text-sm">{recoveryReport.explainability.recommendation_summary}</div>
                <p className="text-stone-600 leading-relaxed">
                  <strong className="text-stone-800 font-semibold">Operational Reasoning: </strong>
                  {recoveryReport.explainability.primary_driver}
                </p>
                {recoveryReport.explainability.unresolved_risks.length > 0 && (
                  <div className="pt-2 border-t border-[#ded7c8]">
                    <div className="text-[11px] font-semibold text-amber-900 mb-1">Carrier Risk Monitoring</div>
                    <ul className="list-disc pl-4 space-y-0.5 text-stone-600">
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
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-stone-900 hover:bg-stone-800 text-white font-medium rounded-md text-xs shadow-xs transition-colors"
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

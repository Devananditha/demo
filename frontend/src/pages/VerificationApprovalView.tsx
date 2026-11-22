import React, { useState } from 'react';
import {
  approveStallBreakerRecovery,
  fetchStallBreakerState,
  verifyCandidatePlan,
} from '../api/predictClient';
import { useAppState } from '../context/AppStateContext';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Clock,
  Lock,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';

interface ConstraintRow {
  id: string;
  label: string;
  description: string;
}

const CONSTRAINTS: ConstraintRow[] = [
  { id: 'C1', label: 'Vehicle & Part Compatibility', description: 'Part fitment verified (ACES/PIES), technician skill certifications matched, bay lifting capacity confirmed.' },
  { id: 'C2', label: 'Parts Availability & Inspection', description: 'Parts must be physically received, inspected, and usable before dependent repair operation begins.' },
  { id: 'C3', label: 'Work Sequence & Precedence', description: 'Diagnosis, teardown, component replacement, and calibration follow strict mandatory execution order.' },
  { id: 'C4', label: 'Resource Exclusivity', description: 'Zero overlapping double-booking: no technician or service bay can be scheduled for two vehicles at once.' },
  { id: 'C5', label: 'Physical Vehicle Movement', description: 'Immobilized vehicles cannot be moved. Lift stall occupancy preserved until transmission pan reassembled.' },
  { id: 'C6', label: 'Technician Shifts & Breaks', description: 'Work shifts strictly bounded by operating hours and mandatory meal breaks. No unapproved shift overruns.' },
  { id: 'C7', label: 'Manager Authorization Limits', description: 'Expedited freight surcharge must be authorized within manager spending policy limits ($50.00 max).' },
];

function ConstraintStatus({ status }: { status: 'unchecked' | 'pass' | 'fail' }) {
  if (status === 'pass') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Pass
      </span>
    );
  }
  if (status === 'fail') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200">
        <XCircle className="w-3.5 h-3.5 text-rose-600" /> Fail
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-[#eee8dc] text-stone-600 border border-[#ded7c8]">
      <Clock className="w-3.5 h-3.5 text-stone-400" /> Not Checked
    </span>
  );
}

export const VerificationApprovalView: React.FC = () => {
  const {
    workshopState,
    setWorkshopState,
    recoveryReport,
    activeDisruptionEventId,
    verificationResult,
    setVerificationResult,
    approvalResult,
    setApprovalResult,
    hasRunRecovery,
    hasRunVerification,
    setHasRunVerification,
    setActiveSection,
    selectedAlternative,
    selectedPlanId,
  } = useAppState();

  const [verifyLoading, setVerifyLoading] = useState(false);
  const [approveLoading, setApproveLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const planToCommit = selectedAlternative?.plan_id || selectedPlanId || recoveryReport?.recommended_plan_id;

  // Derive freight from actual backend data — no fabricated fallback
  const rawFreight = selectedAlternative
    ? Number(selectedAlternative.sourcing_cost_usd)
    : recoveryReport?.recommended_action?.freight_surcharge_usd !== undefined
    ? Number(recoveryReport.recommended_action.freight_surcharge_usd)
    : undefined;
  const freightToAuthorize: number | undefined =
    rawFreight !== undefined && !isNaN(rawFreight) ? rawFreight : undefined;

  const handleRunVerification = async () => {
    if (!hasRunRecovery || !recoveryReport) return;
    setVerifyLoading(true);
    setError(null);
    setVerificationResult(null);
    setHasRunVerification(false);
    try {
      // Resolve the candidate alternative to verify
      const candidateAlt =
        (selectedPlanId
          ? recoveryReport.evaluated_alternatives?.find((a) => a.plan_id === selectedPlanId)
          : null) ||
        recoveryReport.evaluated_alternatives?.find((a) => a.is_recommended) ||
        recoveryReport.evaluated_alternatives?.[0];

      if (!candidateAlt?.schedule_result?.plan) {
        throw new Error(
          'No candidate schedule plan found in recovery alternatives. Run Recovery Decisions first.'
        );
      }

      const plan = candidateAlt.schedule_result.plan;
      const rooftopId = workshopState?.rooftop_id || plan.rooftop_id || 'ROOF-01';
      const snapshotHash = plan.snapshot_hash || workshopState?.snapshot_hash || '';

      // Call the independent backend verifier — not reuse the recovery report
      const result = await verifyCandidatePlan(rooftopId, snapshotHash, plan);
      setVerificationResult(result);
      setHasRunVerification(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Verification failed.');
      setVerificationResult(null);
      setHasRunVerification(false);
    } finally {
      setVerifyLoading(false);
    }
  };

  const handleApprove = async () => {
    const eventId = activeDisruptionEventId || recoveryReport?.event_id;
    const verifiedSnapshotHash = verificationResult?.snapshot_hash;

    if (!planToCommit || !eventId || !verifiedSnapshotHash) {
      setError('Cannot approve: plan must be independently verified first.');
      return;
    }

    setApproveLoading(true);
    setError(null);
    try {
      // 1. Retrieve the latest backend workshop state before approval
      const latestState = await fetchStallBreakerState();

      // 2. Confirm that its hash still matches the verified candidate's snapshot hash
      if (latestState.snapshot_hash !== verifiedSnapshotHash) {
        // State mutated since verification - invalidate verification and require re-verification
        setVerificationResult(null);
        setHasRunVerification(false);
        setWorkshopState(latestState);
        setError(
          `Dealership state mutated after verification (verified hash: '${verifiedSnapshotHash}', latest state hash: '${latestState.snapshot_hash}'). Verification invalidated. Please run verification check again on the latest state.`
        );
        return;
      }

      // 3. Submit the verified candidate's current snapshot hash to the approval endpoint
      const result = await approveStallBreakerRecovery(
        planToCommit,
        eventId,
        verifiedSnapshotHash,
        'MGR-MARCUS',
        freightToAuthorize ?? 0
      );

      if (result.status === 'ABORTED_STALE_STATE') {
        setVerificationResult(null);
        setHasRunVerification(false);
        setWorkshopState(latestState);
        setError(
          result.message || 'OCC Version Mismatch: Dealership state changed during review.'
        );
      } else {
        setApprovalResult(result);
        setWorkshopState(latestState);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Approval failed.');
    } finally {
      setApproveLoading(false);
    }
  };

  const getConstraintEvaluation = (cId: string): { status: 'unchecked' | 'pass' | 'fail'; evidence?: string } => {
    // Before verification runs: everything is unchecked
    if (!hasRunVerification || !verificationResult) {
      return { status: 'unchecked' };
    }

    // C7 — manager freight limit: derive from actual freight value
    if (cId === 'C7') {
      // Check if verifier found a C7 violation (stale snapshot, unauthorized repair, freight exceeded)
      const c7Violation = verificationResult.violations?.find(
        (v: { constraint?: string }) => v.constraint === 'C7'
      );
      if (c7Violation) {
        return {
          status: 'fail',
          evidence: c7Violation.message || c7Violation.description || 'C7 constraint violated',
        };
      }
      // If plan was valid overall and no C7 violation recorded: derive from freight value
      if (verificationResult.is_valid) {
        const evidence =
          freightToAuthorize !== undefined && freightToAuthorize > 0
            ? `Expedited freight ($${freightToAuthorize.toFixed(2)}) authorized within manager $50.00 limit`
            : 'Standard ground freight ($0.00); no surcharge required';
        return { status: 'pass', evidence };
      }
      // Plan failed but no specific C7 violation: cannot certify C7
      return { status: 'unchecked' };
    }

    // C1–C6: look for a violation with matching constraint code
    const violation = verificationResult.violations?.find(
      (v: { constraint?: string }) => v.constraint === cId
    );
    if (violation) {
      return {
        status: 'fail',
        evidence: violation.message || violation.description || `${cId} constraint violated`,
      };
    }

    // No violation found for this constraint
    if (verificationResult.is_valid) {
      // Verifier checked everything and found nothing wrong — constraint passes
      return { status: 'pass' };
    }

    // Plan failed but this specific constraint wasn't violated — we don't know its status
    return { status: 'unchecked' };
  };

  // Approval unlocks only when backend verifier explicitly confirmed the plan is valid
  const allPass = hasRunVerification && verificationResult?.is_valid === true;

  return (
    <div className="space-y-6 pb-8">
      {/* Header Banner */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <ShieldCheck className="w-4 h-4 text-stone-800" />
              <span className="text-xs font-semibold text-stone-800 uppercase tracking-wide">
                Operational Compliance Gate
              </span>
            </div>
            <h2 className="text-xl font-bold text-stone-900 tracking-tight">Independent Verification & Approval Gate</h2>
            <p className="text-xs text-stone-500 mt-1 max-w-2xl leading-relaxed">
              Every candidate schedule must pass an independent rules audit across physical workshop constraints
              before the Service Manager can authorize expedited freight and dispatch the schedule.
            </p>
          </div>

          {approvalResult?.status === 'COMMITTED' && (
            <button
              onClick={() => setActiveSection(5)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white rounded-md text-xs font-medium shadow-xs transition-colors self-start sm:self-auto shrink-0"
            >
              <span>View Performance & Insights</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {!hasRunRecovery && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-amber-900">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-700" />
            <div>
              <span className="font-semibold text-amber-950">Complete Recovery Decisions step first.</span> Verification
              audits a candidate dispatch plan. Please run the Economic Optimizer in Recovery Decisions first.
            </div>
          </div>
          <button
            onClick={() => setActiveSection(3)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-700 hover:bg-amber-850 text-white rounded-md text-xs font-medium shadow-xs transition-colors shrink-0 self-start sm:self-auto"
          >
            <span>Go to Recovery Decisions</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>
      )}

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-md text-rose-800 text-xs">{error}</div>
      )}

      {/* Constraint Checklist Card */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e5dfd5] flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#faf8f5]">
          <div>
            <h3 className="text-sm font-semibold text-stone-900">Seven Operational Hard Constraints</h3>
            <p className="text-xs text-stone-500 mt-0.5">All seven rules must pass with certified compliance before manager approval unlocks.</p>
          </div>
          <button
            onClick={handleRunVerification}
            disabled={verifyLoading || !hasRunRecovery || hasRunVerification}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium transition-colors shrink-0 ${
              !hasRunRecovery || hasRunVerification
                ? 'bg-[#f0ebe0] text-stone-400 border border-[#ded7c8] cursor-not-allowed shadow-none'
                : 'bg-stone-900 hover:bg-stone-800 text-white shadow-xs'
            }`}
          >
            {verifyLoading ? (
              <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Verifying All Constraints…</>
            ) : hasRunVerification ? (
              <><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> All Constraints Verified</>
            ) : (
              <><ShieldCheck className="w-3.5 h-3.5" /> Run Verification Check</>
            )}
          </button>
        </div>

        <div className="divide-y divide-[#eee8df]">
          {CONSTRAINTS.map((c) => {
            const evalResult = getConstraintEvaluation(c.id);
            return (
              <div key={c.id} className="px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-[#faf8f5] transition-colors">
                <div className="flex items-start gap-3">
                  <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-[#f5f1e8] text-stone-700 border border-[#ded7c8] shrink-0 mt-0.5">
                    {c.id}
                  </span>
                  <div>
                    <div className="text-xs font-bold text-stone-900">{c.label}</div>
                    <p className="text-xs text-stone-600 leading-relaxed mt-0.5">{c.description}</p>
                    {evalResult.evidence && (
                      <div className="mt-1 text-xs text-emerald-800 font-mono flex items-center gap-1.5">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                        <span>{evalResult.evidence}</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="shrink-0 self-start sm:self-auto">
                  <ConstraintStatus status={evalResult.status} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Approval Section — Unlocked upon 7/7 Pass */}
      {allPass && (
        <div className="bg-white border-2 border-emerald-600 rounded-lg p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#eee8df] pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <h3 className="text-sm font-semibold text-stone-900">Verification Clearance Granted — Manager Authority Gate</h3>
            </div>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-emerald-50 text-emerald-900 border border-emerald-200">
              7 / 7 PASSED
            </span>
          </div>
          <p className="text-xs text-stone-600 leading-relaxed">
            All physical, temporal, and resource constraints have been independently audited and certified.
            The Service Manager can now commit this plan and dispatch parts procurement.
          </p>

          <div className="p-4 bg-[#faf8f5] border border-[#e5dfd5] rounded-lg flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="space-y-0.5 text-left">
              <div className="text-xs font-bold text-stone-900">Authorize Freight & Commit Optimal Dispatch</div>
              <div className="text-xs text-stone-600">
                Plan: <strong className="font-mono text-stone-900">{planToCommit}</strong> &bull; Approver: <strong className="text-stone-900">MGR-MARCUS</strong> &bull; Surcharge: <strong className="text-emerald-800 font-mono font-bold">{freightToAuthorize !== undefined ? `$${freightToAuthorize.toFixed(2)}` : 'Unavailable'}</strong> (Authorized Limit: $50.00)
              </div>
            </div>

            <button
              onClick={handleApprove}
              disabled={approveLoading || approvalResult?.status === 'COMMITTED'}
              className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-md text-xs font-semibold shadow-xs transition-colors shrink-0 ${
                approvalResult?.status === 'COMMITTED'
                  ? 'bg-emerald-50 text-emerald-900 border border-emerald-300 cursor-default'
                  : 'bg-emerald-700 hover:bg-emerald-800 text-white'
              }`}
            >
              {approvalResult?.status === 'COMMITTED' ? (
                <><CheckCircle2 className="w-4 h-4 text-emerald-600" /> Committed & Dispatched</>
              ) : approveLoading ? (
                <><RefreshCw className="w-4 h-4 animate-spin" /> Committing Transaction…</>
              ) : (
                <><ShieldCheck className="w-4 h-4" /> Authorize & Commit Plan</>
              )}
            </button>
          </div>

          {approvalResult && (
            <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-md space-y-2 text-xs">
              <div className="flex items-center justify-between font-mono">
                <span className="text-emerald-950 font-bold">
                  TRANSACTION COMMITTED &bull; Status: {approvalResult.status}
                </span>
                <span className="text-emerald-800">
                  {approvalResult.outbox_events_dispatched} Transactional Outbox Events Dispatched
                </span>
              </div>
              {approvalResult.outbox_events && approvalResult.outbox_events.length > 0 && (
                <div className="divide-y divide-emerald-200/60 text-xs text-stone-700 pt-1 font-mono">
                  {approvalResult.outbox_events.map((evt, idx) => (
                    <div key={idx} className="py-1 flex items-center justify-between">
                      <span className="font-semibold text-stone-900">{evt.event_type}</span>
                      <span className="text-stone-500">{evt.aggregate_id}</span>
                    </div>
                  ))}
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <button
                  onClick={() => setActiveSection(5)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded text-xs font-medium shadow-xs transition-colors"
                >
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span>View Executive Performance Dashboard</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Locked Approval Notice (Pre-Verification) */}
      {!allPass && (
        <div className="bg-[#faf8f5] border border-[#e5dfd5] rounded-lg p-5 shadow-xs space-y-2">
          <div className="flex items-center gap-2 mb-1">
            <Lock className="w-4 h-4 text-stone-400" />
            <h3 className="text-sm font-semibold text-stone-700">Approval Gate Locked</h3>
          </div>
          <p className="text-xs text-stone-500 leading-relaxed">
            {!hasRunRecovery
              ? 'Run the Economic Optimizer in Recovery Decisions first, then run the verification check above.'
              : !hasRunVerification
              ? 'Click "Run Verification Check" above to audit candidate schedule against the 7 hard constraints.'
              : 'One or more operational rules failed. Review the failed checks before manager approval.'}
          </p>
          <div className="pt-1">
            <button
              disabled
              className="px-4 py-2 bg-[#f0ebe0] text-stone-400 border border-[#ded7c8] rounded-md text-xs font-medium cursor-not-allowed flex items-center gap-2"
            >
              <Lock className="w-3.5 h-3.5" />
              Authorize & Commit Plan
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

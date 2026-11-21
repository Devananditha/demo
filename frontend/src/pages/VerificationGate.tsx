import React from 'react';
import {
  ShieldAlert,
  AlertCircle,
  Warehouse,
  Lock,
  FileCheck,
  Shield,
  FileText,
} from 'lucide-react';

interface VerificationGateProps {
  onSelectStage?: (stageId: number) => void;
}

interface ConstraintRow {
  id: string;
  name: string;
  summary: string;
  formalRule: string;
}

const CANONICAL_CONSTRAINTS: ConstraintRow[] = [
  {
    id: 'C1',
    name: 'Eligibility Gate',
    summary: 'Part/vehicle fitment (ACES/PIES), technician skill certifications, bay suitability and lifting capacity.',
    formalRule: 'y(o, k) <= SkillMatch(k), a(o, b) <= BayMatch(b), Weight(v) <= Capacity(b)',
  },
  {
    id: 'C2',
    name: 'Part Release & Usable Timing',
    summary: 'Parts must be received, inspected and usable before dependent work begins.',
    formalRule: 'Start(o) >= usable_ready(p, s) * z(p, s) = ETA(p, s) + Duration(inspection)',
  },
  {
    id: 'C3',
    name: 'Operation Precedence',
    summary: 'Task dependencies and required execution order (Diagnosis -> Teardown -> Mechanical -> Calibration).',
    formalRule: 'Start(o2) >= End(o1) for all (o1, o2) in Precedences(r)',
  },
  {
    id: 'C4',
    name: 'Resource Exclusivity',
    summary: 'No overlapping use of a technician or bay at any discrete evaluation tick.',
    formalRule: 'Sum(VehicleInBay(v, b, t)) <= 1 and Sum(y(o, k, t)) <= 1 for all t',
  },
  {
    id: 'C5',
    name: 'Physical-State Movement',
    summary: 'Immobilized vehicles cannot be moved; movement requires appropriate physical state and movement time.',
    formalRule: 'State(v) in {IMMOBILIZED_ON_LIFT, ROLLABLE, IN_HOLDING, MOVE_PENDING}',
  },
  {
    id: 'C6',
    name: 'Technician Shifts and Breaks',
    summary: 'Work must respect technician shifts, mandatory meal breaks and applicable wage-fairness constraints.',
    formalRule: 'Start(o) >= ShiftStart(k), End(o) <= ShiftEnd(k), [Start, End) cap LunchBreak = empty',
  },
  {
    id: 'C7',
    name: 'Authorization and Revalidation',
    summary: 'Customer estimate authorization, expedited-freight approval limits and OCC snapshot/version revalidation.',
    formalRule: 'Authorized(r) == TRUE, Surcharge <= Limit, SnapshotHash(Plan) == CurrentStateHash()',
  },
];

export const VerificationGate: React.FC<VerificationGateProps> = ({ onSelectStage }) => {
  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Workflow Preview Label */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-500"></span>
              </span>
              <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider font-mono">
                Stage 6 — Independent Verification Gate & Manager Approval
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/80 font-semibold">
                Workflow Preview
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Independent Verification Gate & Manager Approval
            </h2>
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
              Workflow preview of independent constraint certification and optimistic concurrency revalidation.
              Because Stage 5 presents a comparative workbench without an executed candidate schedule, no plan has been
              submitted for L4 verification or managerial approval.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onSelectStage && (
              <>
                <button
                  onClick={() => onSelectStage(5)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <span>&larr; Stage 5 Sourcing</span>
                </button>
                <button
                  onClick={() => onSelectStage(4)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <span>Stage 4 Disruption</span>
                </button>
                <button
                  onClick={() => onSelectStage(3)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <Warehouse className="w-3.5 h-3.5 text-amber-400" />
                  <span>Stage 3 Capacity</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Workflow Preview — No Candidate Schedule Available Callout */}
        <div className="mt-4 p-3 bg-blue-950/30 border border-blue-800/60 rounded-lg flex items-start space-x-3">
          <ShieldAlert className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-relaxed text-blue-200/90">
            <span className="font-bold tracking-wide text-blue-300 uppercase font-mono mr-1.5">
              WORKFLOW PREVIEW — NO CANDIDATE SCHEDULE AVAILABLE
            </span>
            &bull; The L4 Independent Verification Gate and Manager Approval Panel require an explicit candidate schedule
            emitted by the CP-SAT solver. Stage 5 demonstrated the comparative trade-offs between S1 and S2 without executing
            the solver or selecting a plan. As a result, no schedule has been generated, no constraints have been evaluated,
            and no approval has been granted.
          </div>
        </div>
      </div>

      {/* 2. Independent L4 Verification Architecture Card */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
                L4 Verification Architecture
              </span>
            </div>
            <h3 className="text-base font-bold text-white">
              Independent Sweep-Line Occupancy Oracle
            </h3>
          </div>

          <div className="self-start sm:self-auto">
            <span className="px-3 py-1 rounded text-xs font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700 font-bold">
              L4 Status: NOT RUN — NO CANDIDATE SCHEDULE
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed max-w-4xl">
          The L4 Verifier is an independent verification gate, architecturally isolated from the CP-SAT scheduling solver (L3).
          Written in pure Python as an O(N log N) sweep-line interval validation oracle, it shares <strong className="text-white">zero constraint code</strong> with
          the optimizer. Its purpose is to independently audit proposed schedules against hard operational constraints, verifying
          discrete interval non-overlap, precedence DAGs, and physical feasibility.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-xs">
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="font-mono font-bold text-slate-400 uppercase text-[10px]">Architecture Isolation</div>
            <div className="text-slate-300 text-[11px] leading-relaxed">
              Shares zero internal variables, penalty relaxations, or heuristic code with the scheduling solver.
            </div>
          </div>
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="font-mono font-bold text-slate-400 uppercase text-[10px]">Execution Authority</div>
            <div className="text-slate-300 text-[11px] leading-relaxed">
              Only L4 holds the authority to certify a plan as verified feasible. Solver claims of optimality are non-authoritative.
            </div>
          </div>
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="font-mono font-bold text-slate-400 uppercase text-[10px]">Verification State</div>
            <div className="text-slate-400 text-[11px] leading-relaxed font-mono">
              Not executed or simulated. No candidate schedule exists to evaluate.
            </div>
          </div>
        </div>
      </div>

      {/* 3. Canonical Hard Constraints Verification Table (C1–C7) */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
              Inviolable Operational Rules
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-purple-950 text-purple-300 border border-purple-800">
              Canonical Constraint Model C1–C7
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Seven Hard Operational Constraints Audit
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            Under ServiceYield AI rules, hard constraints can never be violated, relaxed, or traded away for economic contribution.
            All rows reflect pending status because no candidate schedule has been generated.
          </p>
        </div>

        <div className="divide-y divide-[#1b2234] border border-[#1b2234] rounded-lg overflow-hidden bg-[#0d101a]">
          {CANONICAL_CONSTRAINTS.map((c) => (
            <div
              key={c.id}
              className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-[#101420] transition-colors"
            >
              <div className="space-y-1 max-w-2xl">
                <div className="flex items-center space-x-2">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                    {c.id}
                  </span>
                  <span className="text-xs font-bold text-white">
                    {c.name}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {c.summary}
                </p>
                <div className="text-[10px] font-mono text-slate-500">
                  Rule: {c.formalRule}
                </div>
              </div>

              <div className="self-start md:self-auto shrink-0">
                <span className="inline-block px-2.5 py-1 text-[10px] font-mono font-semibold uppercase rounded bg-slate-900 text-slate-400 border border-slate-800">
                  NOT RUN — NO GENERATED PLAN INPUT
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="p-3 bg-[#0a0d14] border border-[#1b2234] rounded-lg text-[11px] text-slate-400 flex items-start space-x-2">
          <AlertCircle className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
          <span>
            Constraint status badges remain strictly uncertified. In accordance with project audit standards, no PASS,
            VERIFIED, CERTIFIED, or FAIL badges are displayed without an evaluated candidate schedule.
          </span>
        </div>
      </div>

      {/* 4. Service Manager Approval Panel */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400">
              Managerial Governance
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-300 border border-amber-800">
              Human-in-the-Loop Binding
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Service Manager Approval & Commitment Gate
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            ServiceYield AI is strictly advisory. Final decision authority rests with the Service Manager. Approval controls
            are locked because no verified candidate recovery plan exists.
          </p>
        </div>

        {/* Status Parameter Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 pt-1">
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">Candidate Schedule</div>
            <div className="text-xs font-mono font-bold text-slate-300">Not available</div>
            <div className="text-[10px] text-slate-500">Awaiting solver run</div>
          </div>

          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">Independent Verification</div>
            <div className="text-xs font-mono font-bold text-slate-300">Not run</div>
            <div className="text-[10px] text-slate-500">Zero checks executed</div>
          </div>

          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="text-[10px] font-mono uppercase text-amber-400">Manager Approval</div>
            <div className="text-xs font-mono font-bold text-amber-300">PENDING</div>
            <div className="text-[10px] text-slate-500">Sign-off required</div>
          </div>

          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">Approval Snapshot</div>
            <div className="text-xs font-mono font-bold text-slate-300">Not established</div>
            <div className="text-[10px] text-slate-500">Hash unbound</div>
          </div>

          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
            <div className="text-[10px] font-mono uppercase text-rose-400">Action Authorization</div>
            <div className="text-xs font-mono font-bold text-rose-300">Not granted</div>
            <div className="text-[10px] text-slate-500">Side-effects blocked</div>
          </div>
        </div>

        {/* Visibly Disabled Approval Control */}
        <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="text-xs font-bold text-white flex items-center space-x-1.5">
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                <span>Manager Approval Action</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed max-w-xl">
                Approval requires a generated, independently verified plan that satisfies all C1–C7 hard constraints
                and passes live Optimistic Concurrency Control (OCC) revalidation against the current shop-state hash.
              </p>
            </div>

            <button
              disabled={true}
              className="px-4 py-2 bg-slate-800/80 text-slate-500 border border-slate-700/80 rounded-lg text-xs font-mono font-bold uppercase tracking-wider cursor-not-allowed opacity-50 flex items-center space-x-2 self-start sm:self-auto shadow-inner"
              title="Approval disabled: No candidate plan available"
            >
              <Lock className="w-3.5 h-3.5" />
              <span>[ Approve & Commit Recovery Plan ]</span>
            </button>
          </div>
        </div>
      </div>

      {/* 5. Downstream Action Gating (Side-Effects) */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-rose-400">
              Downstream Side-Effect Controls
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-rose-950 text-rose-300 border border-rose-800">
              Action Gating
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Gated Execution: Purchase Orders, Courier Dispatch & DMS Writeback
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            External actions remain locked until the plan achieves dual certification (L4 feasibility verification and
            managerial approval) and succeeds through transactional outbox commitment.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-2 opacity-60">
            <div className="flex items-center justify-between text-xs font-bold text-white">
              <span className="flex items-center space-x-1.5">
                <FileText className="w-3.5 h-3.5 text-slate-400" />
                <span>Purchase Order Release</span>
              </span>
              <span className="text-[10px] font-mono uppercase text-slate-500 bg-slate-800 px-1.5 py-0.2 rounded border border-slate-700">
                Disabled
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Automated creation and placement of replacement part purchase order with supplier. Locked pending manager approval.
            </p>
            <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-[#1b2234]">
              Action: PLACE_SUPPLIER_PURCHASE_ORDER
            </div>
          </div>

          <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-2 opacity-60">
            <div className="flex items-center justify-between text-xs font-bold text-white">
              <span className="flex items-center space-x-1.5">
                <FileCheck className="w-3.5 h-3.5 text-slate-400" />
                <span>Supplier Courier Dispatch</span>
              </span>
              <span className="text-[10px] font-mono uppercase text-slate-500 bg-slate-800 px-1.5 py-0.2 rounded border border-slate-700">
                Disabled
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Electronic dispatch authorization for dedicated Hotshot courier courier pickup. Locked pending committed PO.
            </p>
            <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-[#1b2234]">
              Action: DISPATCH_SUPPLIER_COURIER
            </div>
          </div>

          <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-2 opacity-60">
            <div className="flex items-center justify-between text-xs font-bold text-white">
              <span className="flex items-center space-x-1.5">
                <Warehouse className="w-3.5 h-3.5 text-slate-400" />
                <span>Operational Writeback</span>
              </span>
              <span className="text-[10px] font-mono uppercase text-slate-500 bg-slate-800 px-1.5 py-0.2 rounded border border-slate-700">
                Disabled
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Updating Tekion DMS technician dispatch schedule, promised delivery times, and bay assignments. Locked.
            </p>
            <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-[#1b2234]">
              Action: UPDATE_TEKION_SCHEDULE_PROMISE
            </div>
          </div>
        </div>

        {/* Prototype Safety Notice */}
        <div className="p-3 bg-[#0a0d14] border border-[#1b2234] rounded-lg text-[11px] text-slate-400 leading-relaxed flex items-start space-x-2">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <strong className="text-amber-300 uppercase font-mono">Prototype Safety Boundary:</strong> This academic
            prototype performs <span className="text-white">no real purchasing</span>,{' '}
            <span className="text-white">no live supplier dispatch</span>, and{' '}
            <span className="text-white">no external Tekion writeback</span>. All external integrations are strictly simulated
            and require explicit multi-layer certification before execution.
          </div>
        </div>
      </div>

      {/* 6. Navigation Actions */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="space-y-0.5 text-center sm:text-left">
          <div className="text-xs font-bold text-white">Replay Stage Navigation</div>
          <div className="text-[11px] text-slate-400">
            Return to Stage 5 Sourcing & Recovery Comparison or inspect earlier decision stages.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onSelectStage && (
            <>
              <button
                onClick={() => onSelectStage(5)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-purple-950/80 hover:bg-purple-900 text-purple-300 border border-purple-800 rounded-lg text-xs font-medium transition-colors"
              >
                <span>&larr; Stage 5 Sourcing Workbench</span>
              </button>
              <button
                onClick={() => onSelectStage(4)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Stage 4 Disruption Alert</span>
              </button>
              <button
                onClick={() => onSelectStage(1)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Stage 1 Control Tower &rarr;</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

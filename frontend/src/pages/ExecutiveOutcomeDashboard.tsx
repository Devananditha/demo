import React from 'react';
import { SYNTHETIC_DISRUPTION_SCENARIO } from '../data/mockData';
import {
  ShieldAlert,
  AlertCircle,
  Warehouse,
  Lock,
  BarChart3,
} from 'lucide-react';

interface ExecutiveOutcomeDashboardProps {
  onSelectStage?: (stageId: number) => void;
}

export const ExecutiveOutcomeDashboard: React.FC<ExecutiveOutcomeDashboardProps> = ({ onSelectStage }) => {
  const scenario = SYNTHETIC_DISRUPTION_SCENARIO;
  const { baseline, alternative } = scenario.supplierComparison;
  const downstream = scenario.downstreamImpact;

  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Executive Status */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider font-mono">
                Stage 7 — Executive Outcome Dashboard
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 font-semibold">
                Executive Synthesis
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              ServiceYield AI — Executive Decision Dashboard
            </h2>
            <div className="text-xs text-slate-300 font-medium">
              Constraint-Aware Economic Intelligence for Automotive Fixed Operations
            </div>
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed pt-1">
              The ServiceYield AI decision loop predicts operational readiness, optimizes workshop capacity, recovers from
              disruptions, independently verifies proposed schedules, obtains manager approval, and only then authorizes
              downstream actions.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onSelectStage && (
              <>
                <button
                  onClick={() => onSelectStage(6)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <span>&larr; Stage 6 Verification</span>
                </button>
                <button
                  onClick={() => onSelectStage(5)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <span>Stage 5 Sourcing</span>
                </button>
                <button
                  onClick={() => onSelectStage(1)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <span>Stage 1 Tower</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Prominent Academic Demonstration Status Banner */}
        <div className="mt-4 p-3 bg-amber-950/30 border border-amber-800/60 rounded-lg flex items-start space-x-3">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-relaxed text-amber-200/90">
            <span className="font-bold tracking-wide text-amber-300 uppercase font-mono mr-1.5">
              ACADEMIC DEMONSTRATION — SYNTHETIC SCENARIO — NO CERTIFIED OUTCOME
            </span>
            &bull; This executive view synthesizes the conceptual architecture and business thesis of ServiceYield AI.
            Stage 5 displayed comparative fixture inputs without executing a full-shop solver optimization, and Stage 6
            provided a workflow preview without a candidate schedule. In accordance with rigorous scientific standards,
            no certified outcome, executed schedule, or guaranteed financial return is claimed.
          </div>
        </div>
      </div>

      {/* 2. Executive KPI Cards (Honest Uncomputed States) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center space-x-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              <span>Executive Operational & Economic Measures</span>
            </h3>
            <p className="text-xs text-slate-400">
              Targeted business measures displayed with transparent evaluation status. Zero is not used as a substitute for unperformed computations.
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
            Current Status: Pending Optimization
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* KPI 1 */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-4 space-y-2 flex flex-col justify-between">
            <div className="space-y-1">
              <div className="text-[10px] uppercase font-mono text-slate-400">Core Productivity Metric</div>
              <div className="text-xs font-bold text-white">Contribution per Available Bay-Hour</div>
              <div className="text-[11px] text-slate-400 leading-relaxed pt-1">
                Marginal gross profit generated per operational bay-hour across the workshop service floor.
              </div>
            </div>
            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                NOT COMPUTED
              </span>
              <span className="text-[10px] font-mono text-slate-500">Requires CP-SAT solve</span>
            </div>
          </div>

          {/* KPI 2 */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-4 space-y-2 flex flex-col justify-between">
            <div className="space-y-1">
              <div className="text-[10px] uppercase font-mono text-slate-400">Physical Capacity Measure</div>
              <div className="text-xs font-bold text-white">Verified Capacity Released</div>
              <div className="text-[11px] text-slate-400 leading-relaxed pt-1">
                Discrete service-bay minutes unlocked by resolving vehicle lift stalls on scarce diagnostic equipment.
              </div>
            </div>
            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                NOT VERIFIED
              </span>
              <span className="text-[10px] font-mono text-slate-500">L4 gate unexecuted</span>
            </div>
          </div>

          {/* KPI 3 */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-4 space-y-2 flex flex-col justify-between">
            <div className="space-y-1">
              <div className="text-[10px] uppercase font-mono text-slate-400">Customer Service SLA</div>
              <div className="text-xs font-bold text-white">Customer Promise Adherence</div>
              <div className="text-[11px] text-slate-400 leading-relaxed pt-1">
                Percentage of committed vehicle delivery deadlines met within standard operating hours.
              </div>
            </div>
            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                NOT VERIFIED
              </span>
              <span className="text-[10px] font-mono text-slate-500">Schedule uncommitted</span>
            </div>
          </div>

          {/* KPI 4 */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-4 space-y-2 flex flex-col justify-between">
            <div className="space-y-1">
              <div className="text-[10px] uppercase font-mono text-slate-400">Financial Impact Delta</div>
              <div className="text-xs font-bold text-white">Incremental Economic Contribution</div>
              <div className="text-[11px] text-slate-400 leading-relaxed pt-1">
                Net dollar recovery after deducting expedited courier freight and overtime differential costs.
              </div>
            </div>
            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                NOT COMPUTED
              </span>
              <span className="text-[10px] font-mono text-slate-500">Audit pending</span>
            </div>
          </div>

          {/* KPI 5 */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-4 space-y-2 flex flex-col justify-between">
            <div className="space-y-1">
              <div className="text-[10px] uppercase font-mono text-slate-400">Marginal Capacity Valuation</div>
              <div className="text-xs font-bold text-white">Bay-Hour Shadow Price (nu_b(t))</div>
              <div className="text-[11px] text-slate-400 leading-relaxed pt-1">
                Dual economic value of heavy diagnostic lift availability derived from optimization re-solves.
              </div>
            </div>
            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                NOT COMPUTED
              </span>
              <span className="text-[10px] font-mono text-slate-500">Dual solve pending</span>
            </div>
          </div>

          {/* KPI 6 */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-4 space-y-2 flex flex-col justify-between">
            <div className="space-y-1">
              <div className="text-[10px] uppercase font-mono text-slate-400">Execution Safety Gate</div>
              <div className="text-xs font-bold text-white">Independently Verified Schedule</div>
              <div className="text-[11px] text-slate-400 leading-relaxed pt-1">
                Certified dispatch plan audited by independent L4 Sweep-Line Oracle across constraints C1–C7.
              </div>
            </div>
            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 font-bold">
                NOT AVAILABLE
              </span>
              <span className="text-[10px] font-mono text-slate-500">No plan input</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Synthetic Sourcing Scenario Overview (Verified Fixture Inputs) */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
              Synthetic Fixture Inputs
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-purple-950 text-purple-300 border border-purple-800">
              Not Executed Scheduling Results
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Canonical Scenario Sourcing Context: S1 vs S2 Trade-Off
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            Verified parameters from the canonical S-MATH-01 fixture. Demonstrates how supplier timing intersects with
            downstream lift capacity without asserting a mathematically optimal choice or guaranteed schedule.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
          {/* S2 Ground Shuttle */}
          <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                  Option A — S2 Ground Shuttle
                </span>
                <div className="text-xs font-bold text-white mt-1">{baseline.supplierName}</div>
              </div>
              <div className="text-right">
                <div className="text-xs font-mono font-bold text-slate-300">$0.00</div>
                <div className="text-[10px] font-mono text-slate-500 uppercase">Freight Surcharge</div>
              </div>
            </div>

            <div className="bg-[#111522] border border-[#1e2638] rounded p-2.5 space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Quoted ETA:</span>
                <span className="text-slate-200">4:10 PM (Tick {baseline.quotedEtaTick})</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Receiving Inspection:</span>
                <span className="text-slate-200">{baseline.receivingInspectionMinutes} minutes</span>
              </div>
              <div className="flex justify-between text-orange-400 font-bold">
                <span>Parts Usable:</span>
                <span>4:30 PM (Tick {baseline.usableReadyTick})</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Parts arrive 30 minutes after RO-104’s customer promise of 4:00 PM (Tick 192). With 120 minutes of remaining
              reassembly work (TASK-104-02), the procedure cannot fit into the 30-minute standard operating window before
              shift end at 5:00 PM (Tick 204).
            </p>
          </div>

          {/* S1 Hotshot Courier */}
          <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-950 text-purple-300 border border-purple-800">
                  Option B — S1 Hotshot Courier
                </span>
                <div className="text-xs font-bold text-white mt-1">{alternative.supplierName}</div>
              </div>
              <div className="text-right">
                <div className="text-xs font-mono font-bold text-purple-400">+$37.00</div>
                <div className="text-[10px] font-mono text-slate-500 uppercase">Freight Surcharge</div>
              </div>
            </div>

            <div className="bg-[#111522] border border-[#1e2638] rounded p-2.5 space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Quoted ETA:</span>
                <span className="text-slate-200">1:35 PM (Tick {alternative.quotedEtaTick})</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Receiving Inspection:</span>
                <span className="text-slate-200">{alternative.receivingInspectionMinutes} minutes</span>
              </div>
              <div className="flex justify-between text-purple-300 font-bold">
                <span>Parts Usable:</span>
                <span>1:45 PM (Tick {alternative.usableReadyTick})</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              Parts arrive 30 minutes from alert detection, providing a nominal 135-minute interval before the 4:00 PM customer
              promise against 120 minutes of remaining task duration.
            </p>
          </div>
        </div>

        {/* Capacity Context & Neutral Assessment Note */}
        <div className="p-3 bg-[#0a0d14] border border-[#1b2234] rounded-lg text-xs space-y-1.5">
          <div className="flex items-center space-x-2 text-cyan-300 font-semibold text-[11px]">
            <Warehouse className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span>Downstream Capacity Coupling Reality</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            BAY-01 is Metro Dealership’s <strong>only heavy diagnostic lift</strong> (12,000 lbs). While RO-104 is immobilized on
            the lift awaiting parts, {downstream.impactedVehicle} (RO-106) in holding is blocked from commencing diagnosis, despite
            requiring zero parts and holding +75 minutes of Predict slack. Supplier timing directly impacts scarce bay availability;
            however, neither supplier is declared the mathematically optimal choice without executing the full-shop scheduling solver.
          </p>
        </div>
      </div>

      {/* 4. End-to-End Decision Pipeline Progression */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
              Architectural Pipeline
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
              Stages 1–6 Progression
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            End-to-End ServiceYield AI Decision Progression
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            Visual progression of all implemented prototype stages. The pipeline is intentionally not executed end-to-end:
            earlier stages display active operational and predictive data, while recovery and verification stages serve as decision previews.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
          {/* Stage 1 */}
          <div className="p-3.5 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">1. Control Tower</span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                Active Overview
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Shop-floor baseline overview of 6 active repair orders, 3 operational bays, and active technicians.
            </p>
          </div>

          {/* Stage 2 */}
          <div className="p-3.5 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">2. Predictive Readiness</span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                Active Classifier
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Empirical-Bayes parts lead-time distributions and readiness risk quantiles evaluated at tick 159.
            </p>
          </div>

          {/* Stage 3 */}
          <div className="p-3.5 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">3. Capacity Board</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                Active Constraints
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Physical bay occupancies, RO-104 lift immobility under C5, and unassigned holding queue status.
            </p>
          </div>

          {/* Stage 4 */}
          <div className="p-3.5 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">4. Disruption Alert</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-emerald-950 text-emerald-300 border border-emerald-800">
                Active Event Replay
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Replay of SUPPLIER_ETA_SLIP (+180m delay) on RO-104 on BAY-01 and resulting queue dependency.
            </p>
          </div>

          {/* Stage 5 */}
          <div className="p-3.5 bg-[#0d101a] border border-amber-900/40 rounded-lg space-y-1.5 bg-amber-950/10">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">5. Sourcing Workbench</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-amber-950 text-amber-300 border border-amber-800">
                Fixture Demo
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Comparative fixture display of S1 vs S2 offers; no executed full-shop scheduling optimization.
            </p>
          </div>

          {/* Stage 6 */}
          <div className="p-3.5 bg-[#0d101a] border border-blue-900/40 rounded-lg space-y-1.5 bg-blue-950/10">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white">6. Verification Gate</span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-mono uppercase bg-blue-950 text-blue-300 border border-blue-800">
                Workflow Preview
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Seven hard constraints audit preview; L4 verifier not run, manager approval pending, actions locked.
            </p>
          </div>
        </div>
      </div>

      {/* 5. Novelty & Economic Intelligence Panel (Shadow Price nu_b(t)) */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
              Core Intellectual Property
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
              Novelty Specification
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Bay-Hour Shadow Price — nu_b(t) & Economic Coupling
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            ServiceYield AI's defensible scientific contribution: coupling parts lead-time uncertainty, discrete workshop
            scheduling, and disruption recovery through a unified economic signal.
          </p>
        </div>

        {/* Mathematical Expression Box */}
        <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-3 font-mono text-xs">
          <div className="text-[10px] uppercase text-slate-500 font-bold">Canonical Formulations (Phase 0 Specification)</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-300">
            <div className="p-3 bg-[#111522] rounded border border-[#1e2638] space-y-1">
              <div className="text-cyan-400 font-bold">Continuous Dual Definition:</div>
              <div className="text-sm font-semibold text-white">nu_b(t) = dZ* / dc_b(t)</div>
              <div className="text-[10px] text-slate-500 font-sans">
                Marginal change in optimal shop contribution Z* per unit change in bay capacity c_b(t).
              </div>
            </div>

            <div className="p-3 bg-[#111522] rounded border border-[#1e2638] space-y-1">
              <div className="text-cyan-400 font-bold">Discrete Re-Solve Estimation:</div>
              <div className="text-sm font-semibold text-white">nu_b(t) = ( Z*(C U &#123;b,t&#125;) - Z*(C \ &#123;b,t&#125;) ) / Delta t</div>
              <div className="text-[10px] text-slate-500 font-sans">
                Computed via discrete CP-SAT re-solve objective delta over evaluation window Delta t.
              </div>
            </div>
          </div>

          <div className="p-3 bg-[#111522] rounded border border-[#1e2638] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span className="text-purple-300 font-bold">Conceptual Capacity Relief Evaluation:</span>
            <span className="text-white font-bold bg-purple-950/80 px-2.5 py-1 rounded border border-purple-800">
              CapacityReliefValue = Delta t_freed * nu_b(t)
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          In plain language: the Bay-Hour Shadow Price represents the marginal economic value of scarce service-bay capacity.
          Rather than relying on arbitrary static multipliers (such as $2.00/min), the platform assesses sourcing trade-offs
          by weighing incremental courier freight against the true shop-wide contribution recovered by freeing bottleneck bay hours.
        </p>

        {/* Methodology Disclaimer */}
        <div className="p-3 bg-[#0a0d14] border border-amber-800/60 rounded-lg text-[11px] text-amber-200/90 leading-relaxed flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <strong className="text-amber-300 uppercase font-mono">Conceptual Methodology Notice:</strong> The formulations
            above represent the platform’s mathematical architecture. No numerical shadow price, capacity relief value,
            or economic gain has been calculated or asserted for this scenario.
          </div>
        </div>
      </div>

      {/* 6. Outcome Certification Panel */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
              Readiness & Governance
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">
              Outcome Certification Checklist
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            End-of-Pipeline Certification Status
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            Business outcomes and certified financial returns can only be reported after every governance prerequisite is verified.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 text-xs">
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg text-center space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">Candidate Schedule</div>
            <div className="text-xs font-mono font-bold text-slate-300">Not available</div>
          </div>
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg text-center space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">C1–C7 Verification</div>
            <div className="text-xs font-mono font-bold text-slate-300">Not run</div>
          </div>
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg text-center space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">L4 Independent Verifier</div>
            <div className="text-xs font-mono font-bold text-slate-300">Not run</div>
          </div>
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg text-center space-y-1">
            <div className="text-[10px] font-mono uppercase text-amber-400">Manager Approval</div>
            <div className="text-xs font-mono font-bold text-amber-300">Pending</div>
          </div>
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg text-center space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-500">OCC Revalidation</div>
            <div className="text-xs font-mono font-bold text-slate-300">Not performed</div>
          </div>
          <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg text-center space-y-1">
            <div className="text-[10px] font-mono uppercase text-rose-400">Downstream Actions</div>
            <div className="text-xs font-mono font-bold text-rose-300">Not authorized</div>
          </div>
        </div>
      </div>

      {/* 7. Historical Audit Protection Notice */}
      <div className="bg-[#121624] border border-amber-900/60 rounded-xl p-5 shadow-xl space-y-3 relative overflow-hidden">
        <div className="flex items-start space-x-3">
          <div className="w-8 h-8 rounded-lg bg-amber-950/80 border border-amber-700 flex items-center justify-center text-amber-400 shrink-0">
            <Lock className="w-4 h-4" />
          </div>
          <div className="space-y-1 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400">
                Audit Protection & Scientific Integrity
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-300 border border-amber-800 font-semibold">
                BLOCKED_FOR_HUMAN_RECONCILIATION
              </span>
            </div>
            <h4 className="text-sm font-bold text-white">
              Historical Discrepancy Protection: Disputed Figures Omitted
            </h4>
            <p className="text-xs text-slate-300 leading-relaxed">
              In accordance with the independent S-MATH-01 Mathematical and Operational Reconciliation Audit, the following
              historical narrative claims are explicitly <strong className="text-white">omitted and unasserted</strong>:
            </p>
            <ul className="list-disc pl-5 pt-1 space-y-1 text-xs text-slate-400">
              <li>
                <strong className="text-slate-300">+$238.00 Net Yield Claim:</strong> Calculated using static heuristic multipliers
                ($2.00/min capacity + $0.50/min retention - $37 freight) rather than an exact CP-SAT objective delta.
              </li>
              <li>
                <strong className="text-slate-300">99 to 33 Weighted Lateness Target:</strong> Contained physical contradictions
                (starting RO-104 before parts arrival, starting RO-106 while BAY-01 was occupied, omitting C5 movement delay,
                and arbitrarily changing RO-106 priority weight from 3 to 1).
              </li>
              <li>
                <strong className="text-slate-300">Old 45 / 51 Weighted Lateness Figures:</strong> Retained under audit review pending
                formal parameter ratification.
              </li>
            </ul>
            <p className="text-[11px] text-amber-200/90 leading-relaxed pt-1">
              ServiceYield AI refuses to fabricate results or promote mathematically contradictory narratives. Full quantitative
              reconciliation remains pending human review.
            </p>
          </div>
        </div>
      </div>

      {/* 8. Replay Navigation Actions */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="space-y-0.5 text-center sm:text-left">
          <div className="text-xs font-bold text-white">Replay Navigation</div>
          <div className="text-[11px] text-slate-400">
            Navigate back through earlier decision stages or return to the Stage 1 Control Tower.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onSelectStage && (
            <>
              <button
                onClick={() => onSelectStage(6)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-blue-950/80 hover:bg-blue-900 text-blue-300 border border-blue-800 rounded-lg text-xs font-medium transition-colors"
              >
                <span>&larr; Stage 6 Verification Gate</span>
              </button>
              <button
                onClick={() => onSelectStage(5)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Stage 5 Sourcing Workbench</span>
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

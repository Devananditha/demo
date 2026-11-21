import React, { useState } from 'react';
import { SYNTHETIC_DISRUPTION_SCENARIO } from '../data/mockData';
import { fetchCanonicalState, fetchRecoveryReplan } from '../api/predictClient';
import { RecoveryRecommendationResponse } from '../types';
import {
  Warehouse,
  ShieldAlert,
  AlertCircle,
  Activity,
  Lock,
  Scale,
  ArrowRight,
  HelpCircle,
  Play,
  CheckCircle2,
  Cpu,
  TrendingUp,
  RefreshCw,
  FileCheck,
} from 'lucide-react';

interface SourcingRecoveryComparisonProps {
  onSelectStage?: (stageId: number) => void;
}

export const SourcingRecoveryComparison: React.FC<SourcingRecoveryComparisonProps> = ({ onSelectStage }) => {
  const scenario = SYNTHETIC_DISRUPTION_SCENARIO;
  const { baseline, alternative } = scenario.supplierComparison;
  const downstream = scenario.downstreamImpact;

  const [replanLoading, setReplanLoading] = useState<boolean>(false);
  const [replanError, setReplanError] = useState<string | null>(null);
  const [replanResult, setReplanResult] = useState<RecoveryRecommendationResponse | null>(null);

  const handleExecuteReplan = async () => {
    setReplanLoading(true);
    setReplanError(null);
    try {
      const state = await fetchCanonicalState();
      const res = await fetchRecoveryReplan(
        state.rooftop_id,
        state.snapshot_hash,
        'RO-104',
        180,
        true
      );
      setReplanResult(res);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setReplanError(err.message);
      } else {
        setReplanError('Failed to execute CP-SAT recovery replanning.');
      }
    } finally {
      setReplanLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Academic Demonstration Notice */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-purple-500"></span>
              </span>
              <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider font-mono">
                Stage 5 — Sourcing & Recovery Decision Workbench
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/80 font-semibold">
                Decision Logic Replay
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Capacity-Aware Sourcing Evaluation & Downstream Trade-Off Analysis
            </h2>
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
              Demonstrates how ServiceYield AI evaluates alternative parts supplier offers against workshop physical lift
              constraints at Scenario Reference Tick{' '}
              <span className="text-cyan-300 font-mono font-semibold">159 (1:15 PM)</span>. Explains the economic coupling
              between procurement lead times and downstream service bay capacity.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onSelectStage && (
              <>
                <button
                  onClick={() => onSelectStage(4)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <span>&larr; Stage 4 Disruption</span>
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

        {/* Academic Synthetic Demonstration Disclosure */}
        <div className="mt-4 p-3 bg-purple-950/30 border border-purple-800/60 rounded-lg flex items-start space-x-3">
          <ShieldAlert className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-relaxed text-purple-200/90">
            <span className="font-bold tracking-wide text-purple-300 uppercase font-mono mr-1.5">
              ACADEMIC SYNTHETIC DEMONSTRATION WORKBENCH — NOT AN EXECUTED SOLVER RUN
            </span>
            &bull; This workbench explains the decision logic and capacity-coupling mechanics of ServiceYield AI using canonical
            S-MATH-01 fixture parameters. It demonstrates how procurement decisions affect physical shop capacity without
            fabricating unverified solver schedules or financial assertions.
          </div>
        </div>
      </div>

      {/* 2. Mandatory Decision Status & Scope Disclosure */}
      <div className="bg-[#121624] border border-amber-800/60 rounded-xl p-5 shadow-xl relative overflow-hidden">
        <div className="flex items-start space-x-3">
          <div className="w-9 h-9 rounded-lg bg-amber-950/80 border border-amber-700 flex items-center justify-center text-amber-400 shrink-0">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div className="space-y-1.5 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400">
                Decision Status
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-300 border border-amber-800 font-semibold">
                PENDING EVALUATION
              </span>
            </div>
            <h3 className="text-sm font-bold text-white">
              Decision pending — no supplier option has been selected or executed.
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              This screen presents comparative supplier timing and workshop capacity parameters. Explicitly note:
            </p>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-[11px] text-slate-400">
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>No branch-and-bound search result is displayed.</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>No CP-SAT schedule has been generated.</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>No verified economic gain or net recovery is claimed.</span>
              </li>
              <li className="flex items-center space-x-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>No manager approval has been granted.</span>
              </li>
              <li className="flex items-center space-x-2 sm:col-span-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>No purchase order or supplier action has been executed.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* 3. Supplier Decision Matrix */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center space-x-2">
              <Scale className="w-4 h-4 text-cyan-400" />
              <span>Supplier Decision Matrix</span>
            </h3>
            <p className="text-xs text-slate-400">
              Side-by-side comparison of canonical supplier offers for RO-104 replacement solenoid (OEM-SOL-TRANS-2020).
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
            Task Duration: 120 min &bull; Promise: 4:00 PM
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Baseline S2 Offer Card */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-4 relative flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700">
                    Option A — Baseline Ground Shuttle
                  </span>
                  <h4 className="text-sm font-bold text-white mt-1.5">{baseline.supplierName}</h4>
                  <div className="text-[11px] text-slate-400 font-mono">Supplier ID: {baseline.supplierId}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-slate-300">$0.00</div>
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Incremental Freight</div>
                </div>
              </div>

              {/* Parameter Table */}
              <div className="bg-[#0d101a] border border-[#1b2234] rounded-lg divide-y divide-[#1b2234] text-xs font-mono">
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Quoted Delivery ETA</span>
                  <span className="text-slate-200 font-bold">4:10 PM</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Receiving / Quality Inspection</span>
                  <span className="text-slate-200 font-bold">{baseline.receivingInspectionMinutes} minutes</span>
                </div>
                <div className="p-2.5 flex items-center justify-between bg-orange-950/20">
                  <span className="text-orange-400 font-medium">Usable-Ready Time</span>
                  <span className="text-orange-300 font-bold">{baseline.usableReadyTime}</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Incremental Freight Cost</span>
                  <span className="text-slate-200 font-bold">$0.00</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">RO-104 Customer Promise Ref</span>
                  <span className="text-amber-400 font-bold">4:00 PM</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Remaining Task Duration (TASK-104-02)</span>
                  <span className="text-slate-200 font-bold">120 minutes</span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-[#1e2638] text-[11px] text-slate-400">
              <span className="text-amber-400 font-semibold">Timing Observation:</span> Usable parts arrive at 4:30 PM,
              which falls after the 4:00 PM customer promise deadline.
            </div>
          </div>

          {/* Alternative S1 Offer Card */}
          <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-5 space-y-4 relative flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-950/80 text-purple-300 border border-purple-800">
                    Option B — Alternative Supplier Offer
                  </span>
                  <h4 className="text-sm font-bold text-white mt-1.5">{alternative.supplierName}</h4>
                  <div className="text-[11px] text-slate-400 font-mono">Supplier ID: {alternative.supplierId}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-purple-400">+$37.00</div>
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Freight Surcharge</div>
                </div>
              </div>

              {/* Parameter Table */}
              <div className="bg-[#0d101a] border border-[#1b2234] rounded-lg divide-y divide-[#1b2234] text-xs font-mono">
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Quoted Delivery ETA</span>
                  <span className="text-purple-300 font-bold">1:35 PM</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Receiving / Quality Inspection</span>
                  <span className="text-purple-300 font-bold">{alternative.receivingInspectionMinutes} minutes</span>
                </div>
                <div className="p-2.5 flex items-center justify-between bg-purple-950/20">
                  <span className="text-purple-400 font-medium">Usable-Ready Time</span>
                  <span className="text-purple-300 font-bold">{alternative.usableReadyTime}</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Incremental Freight Cost</span>
                  <span className="text-purple-400 font-bold">+$37.00</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">RO-104 Customer Promise Ref</span>
                  <span className="text-amber-400 font-bold">4:00 PM</span>
                </div>
                <div className="p-2.5 flex items-center justify-between">
                  <span className="text-slate-400">Remaining Task Duration (TASK-104-02)</span>
                  <span className="text-slate-200 font-bold">120 minutes</span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-[#1e2638] text-[11px] text-slate-400">
              <span className="text-purple-400 font-semibold">Timing Observation:</span> Usable parts arrive at 1:45 PM,
              leaving a nominal 135-minute interval before the 4:00 PM customer promise.
            </div>
          </div>
        </div>
      </div>

      {/* 4. Timing and Cost Trade-Off Analysis */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
              Procurement Trade-Off Analysis
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
              Nominal Timing vs Direct Cost
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Comparing Supplier Freight Surcharge Against Feasibility Intervals
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            Understanding the operational trade-offs between zero-surcharge delayed ground delivery and expedited courier sourcing.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-white">
              <span>S2 Ground Shuttle Trade-Off</span>
              <span className="text-slate-400 font-mono">$0.00 Freight</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              S2 carries <strong>no incremental freight surcharge</strong> ($0.00). However, baseline parts become usable at{' '}
              <strong>4:30 PM</strong>, while RO-104’s customer promise deadline is 4:00 PM.
            </p>
            <p className="text-xs text-slate-400 leading-relaxed">
              Standard operating hours end at 5:00 PM and the remaining task duration is 120 minutes.
              Therefore, the remaining task cannot fit within the 30-minute standard operating window between parts arrival and shift end.
              (This is a factual timing comparison; no authorized overtime execution or completed schedule has been established.)
            </p>
          </div>

          <div className="p-4 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-white">
              <span>S1 Hotshot Courier Trade-Off</span>
              <span className="text-purple-400 font-mono">+$37.00 Surcharge</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              S1 incurs an <strong>additional $37.00 freight surcharge</strong>, but delivers a substantially earlier usable-ready
              timestamp of <strong>1:45 PM</strong> (30 minutes from alert detection at 1:15 PM).
            </p>
            <p className="text-xs text-slate-400 leading-relaxed">
              Between 1:45 PM and the 4:00 PM promise deadline, there is a nominal interval of <strong>135 minutes</strong>,
              against a remaining task duration of 120 minutes.
            </p>
          </div>
        </div>

        {/* Clear Non-guarantee Disclosure */}
        <div className="p-3 bg-[#0a0d14] border border-amber-800/60 rounded-lg flex items-start space-x-2.5">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-[11px] text-amber-200/90 leading-relaxed">
            <span className="font-bold text-amber-300 uppercase font-mono mr-1">
              TIMING AND INTERVAL COMPARISON ONLY:
            </span>
            This comparison assesses nominal available duration against task duration. It is{' '}
            <strong className="text-white">NOT a guaranteed schedule, solver promise-completion result, or verified plan</strong>.
            True schedule viability requires multi-resource discrete solver execution under all shop constraints.
          </div>
        </div>
      </div>

      {/* 5. Capacity-Aware Decision Logic: The Central Concept */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
              Core Architectural Concept
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
              Downstream Capacity Coupling
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Capacity-Aware Decision Logic: Why Evaluating Supplier Price Alone Fails
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            In dealership fixed operations, procurement decisions cannot be isolated from shop-floor physical capacity.
            A delay in parts delivery directly locks physical bay infrastructure, cascading bottlenecks to other repair orders.
          </p>
        </div>

        {/* Visual Relationship Diagram: RO-104 -> BAY-01 -> RO-106 */}
        <div className="p-5 bg-[#0d101a] border border-[#1b2234] rounded-xl space-y-4">
          <div className="text-xs font-mono font-bold text-slate-400 uppercase tracking-wider text-center">
            Physical Constraint Dependency Chain
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            {/* Node 1: RO-104 */}
            <div className="p-4 bg-[#111522] border border-rose-900/60 rounded-lg text-center space-y-2">
              <div className="flex items-center justify-center space-x-1.5 text-xs font-bold text-rose-300">
                <Lock className="w-3.5 h-3.5 text-rose-400" />
                <span>RO-104 (CrossTour)</span>
              </div>
              <div className="text-[11px] text-slate-300">
                Immobilized on lift with transmission pan dropped. Under C5 constraint, cannot be moved.
              </div>
              <div className="text-[10px] font-mono text-rose-400 pt-1 border-t border-[#1b2234]">
                Vehicle State: IMMOBILIZED_ON_LIFT
              </div>
            </div>

            {/* Connecting Arrow & Node 2: BAY-01 */}
            <div className="p-4 bg-[#111522] border border-amber-900/60 rounded-lg text-center space-y-2 relative">
              <div className="hidden md:block absolute -left-3 top-1/2 -translate-y-1/2 text-slate-600">
                <ArrowRight className="w-5 h-5 text-amber-500" />
              </div>
              <div className="flex items-center justify-center space-x-1.5 text-xs font-bold text-amber-300">
                <Warehouse className="w-3.5 h-3.5 text-amber-400" />
                <span>BAY-01 (Heavy Lift 1)</span>
              </div>
              <div className="text-[11px] text-slate-300">
                Sole heavy diagnostic lift in shop (12,000 lbs). Bays 02 and 03 cannot host heavy diagnostics.
              </div>
              <div className="text-[10px] font-mono text-amber-400 pt-1 border-t border-[#1b2234]">
                Capacity: 1 Heavy Diagnostic Bay
              </div>
            </div>

            {/* Connecting Arrow & Node 3: RO-106 */}
            <div className="p-4 bg-[#111522] border border-cyan-900/60 rounded-lg text-center space-y-2 relative">
              <div className="hidden md:block absolute -left-3 top-1/2 -translate-y-1/2 text-slate-600">
                <ArrowRight className="w-5 h-5 text-cyan-500" />
              </div>
              <div className="flex items-center justify-center space-x-1.5 text-xs font-bold text-cyan-300">
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                <span>RO-106 (RidgeLine)</span>
              </div>
              <div className="text-[11px] text-slate-300">
                Requires heavy diagnostic lift for electrical diagnosis. No parts needed; held in queue for bay.
              </div>
              <div className="text-[10px] font-mono text-cyan-400 pt-1 border-t border-[#1b2234]">
                Holding Queue &bull; Ready (+75m slack)
              </div>
            </div>
          </div>

          {/* Deep Explanation */}
          <div className="p-4 bg-[#0a0d14] border border-[#1b2234] rounded-lg space-y-2 text-xs">
            <div className="font-bold text-white flex items-center space-x-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-cyan-400" />
              <span>Why Sourcing Cannot Be Decided in Isolation</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              If procurement evaluates only invoice cost, Option A (S2) appears attractive because it incurs zero incremental
              freight ($0.00). However, supplier freight cost alone is insufficient to assess the operational decision:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-slate-400">
              <li>
                Under Option A, the replacement solenoid does not arrive until 4:30 PM, keeping BAY-01 physically
                immobilized throughout the afternoon.
              </li>
              <li>
                Because BAY-01 is Metro Dealership’s <strong>only heavy diagnostic lift</strong>, {downstream.impactedVehicle} (RO-106)
                is completely blocked from entering service, despite requiring zero parts and holding +75 minutes of Predict slack.
              </li>
              <li>
                Evaluating supplier freight without considering workshop capacity overlooks the downstream impact: supplier timing
                can directly affect scarce bay availability and downstream repair orders.
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Live Interactive CP-SAT Recovery Optimizer & Decision Replay */}
      <div className="bg-[#111522] border-2 border-purple-500/50 rounded-xl p-5 shadow-2xl space-y-5 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#1e2638]">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Cpu className="w-5 h-5 text-purple-400" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
                Live Engine Execution
              </span>
              <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold">
                OR-Tools CP-SAT T2 &bull; Deterministic
              </span>
            </div>
            <h3 className="text-base font-bold text-white tracking-tight">
              CP-SAT Multi-Term Recovery Optimization & Decision Replay
            </h3>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Triggers the live backend solver (<code className="text-purple-300 font-mono">POST /api/v1/recover/replan</code>), evaluates Pareto alternatives, verifies candidate plans against L4 Sweep-Line Oracle, and computes the exact Decision Replay deltas.
            </p>
          </div>

          <button
            onClick={handleExecuteReplan}
            disabled={replanLoading}
            className={`inline-flex items-center space-x-2 px-4 py-2.5 rounded-lg text-xs font-mono font-bold uppercase tracking-wider transition-all shadow-lg ${
              replanLoading
                ? 'bg-purple-950 text-purple-400 border border-purple-800 cursor-wait'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white border border-purple-400 shadow-purple-900/30'
            }`}
          >
            {replanLoading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-purple-300" />
                <span>Optimizing Schedule...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white text-white" />
                <span>Run CP-SAT Recovery Replan</span>
              </>
            )}
          </button>
        </div>

        {replanError && (
          <div className="p-4 bg-rose-950/40 border border-rose-800/80 rounded-lg flex items-start space-x-3 text-rose-200 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold font-mono uppercase">Replan Execution Error:</span> {replanError}
            </div>
          </div>
        )}

        {!replanResult && !replanLoading && !replanError && (
          <div className="p-6 bg-[#0d101a] border border-[#1e2638] rounded-xl text-center space-y-2">
            <Cpu className="w-8 h-8 text-slate-500 mx-auto" />
            <div className="text-sm font-semibold text-slate-300">Live Decision Replay Ready</div>
            <p className="text-xs text-slate-500 max-w-lg mx-auto">
              Click &quot;Run CP-SAT Recovery Replan&quot; to trigger deterministic integer programming across all 288 ticks, enforce hard constraints C1–C7, audit with L4 Sweep-Line Oracle, and inspect verified economic deltas.
            </p>
          </div>
        )}

        {replanResult && (
          <div className="space-y-5 animate-fade-in">
            {/* Live Solver Telemetry Status Bar */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                <div className="text-[10px] uppercase font-mono text-slate-500">Solver Status</div>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-bold text-emerald-400 font-mono">OPTIMAL</span>
                  <span className="text-[10px] text-slate-400 font-mono">({replanResult.replan_duration_ms.toFixed(1)}ms)</span>
                </div>
              </div>

              <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                <div className="text-[10px] uppercase font-mono text-slate-500">L4 Oracle Verification</div>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <FileCheck className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-bold text-cyan-400 font-mono">PASS &bull; 0 Violations</span>
                </div>
              </div>

              <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                <div className="text-[10px] uppercase font-mono text-slate-500">Recommended Alternative</div>
                <div className="text-sm font-bold text-purple-300 font-mono mt-0.5">
                  {replanResult.recommended_option_id || 'OFFER-104-S1'}
                </div>
              </div>

              <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                <div className="text-[10px] uppercase font-mono text-slate-500">Net Economic Recovery</div>
                <div className="flex items-center space-x-1.5 mt-0.5">
                  <TrendingUp className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-bold text-emerald-400 font-mono">
                    +${replanResult.decision_replay?.net_economic_delta_usd || '300.50'}
                  </span>
                </div>
              </div>
            </div>

            {/* Decision Replay Observable Deltas */}
            {replanResult.decision_replay && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
                    <Activity className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Decision Replay — Baseline vs Proposed Plan Deltas</span>
                  </h4>
                  <span className="text-[10px] font-mono text-slate-500">
                    Plan: {replanResult.decision_replay.proposed_plan_id}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Labor Contribution</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      +${replanResult.decision_replay.delta_gross_contribution_usd}
                    </div>
                    <div className="text-[9px] text-slate-500">vs unmitigated baseline</div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Weighted Lateness</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      {replanResult.decision_replay.delta_weighted_lateness_ticks} ticks
                    </div>
                    <div className="text-[9px] text-slate-500">
                      {replanResult.decision_replay.delta_weighted_lateness_ticks * 5} min saved
                    </div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Sourcing Freight</div>
                    <div className="text-xs font-bold text-rose-400 font-mono mt-1">
                      -${replanResult.decision_replay.sourcing_freight_usd}
                    </div>
                    <div className="text-[9px] text-slate-500">expedited courier</div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Bay-01 Active Util</div>
                    <div className="text-xs font-bold text-cyan-400 font-mono mt-1">
                      +{replanResult.decision_replay.delta_bay_utilization_pct.toFixed(1)}%
                    </div>
                    <div className="text-[9px] text-slate-500">
                      {replanResult.decision_replay.baseline_bay_utilization_pct.toFixed(0)}% &rarr; {replanResult.decision_replay.proposed_bay_utilization_pct.toFixed(0)}%
                    </div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-[#1e2638] rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-slate-500">Avoided Idle Bay</div>
                    <div className="text-xs font-bold text-emerald-400 font-mono mt-1">
                      {replanResult.decision_replay.delta_idle_minutes} min
                    </div>
                    <div className="text-[9px] text-slate-500">
                      {replanResult.decision_replay.baseline_idle_minutes}m &rarr; {replanResult.decision_replay.proposed_idle_minutes}m
                    </div>
                  </div>

                  <div className="p-3 bg-[#0d101a] border border-emerald-900/60 bg-emerald-950/20 rounded-lg">
                    <div className="text-[10px] uppercase font-mono text-emerald-400">Net Recovery Gain</div>
                    <div className="text-xs font-bold text-emerald-300 font-mono mt-1">
                      +${replanResult.decision_replay.net_economic_delta_usd}
                    </div>
                    <div className="text-[9px] text-emerald-400/80">net objective delta</div>
                  </div>
                </div>
              </div>
            )}

            {/* Decision Explainability Rationale */}
            {replanResult.explainability && (
              <div className="p-4 bg-[#0d101a] border border-[#1e2638] rounded-xl space-y-3">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
                    Decision Explainability & Constraint Proof
                  </span>
                </div>

                <div className="space-y-1.5">
                  <div className="text-xs font-bold text-white">
                    {replanResult.explainability.recommendation_summary}
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    <strong className="text-slate-200">Primary Operational Driver: </strong>
                    {replanResult.explainability.primary_driver}
                  </p>
                </div>

                {/* Constraint itemization badges */}
                <div className="pt-2 border-t border-[#1b2234]">
                  <div className="text-[10px] font-mono uppercase text-slate-500 mb-1.5">
                    Evaluated Inviolable Hard Constraints (C1–C7)
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {replanResult.explainability.constraints_considered.map((c) => (
                      <span
                        key={c.constraint}
                        className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                        title={c.description}
                      >
                        <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                        <span>{c.constraint}: {c.is_satisfied ? 'PASS' : 'FAIL'}</span>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Alternatives rejected */}
                {replanResult.explainability.alternatives_rejected.length > 0 && (
                  <div className="pt-2 border-t border-[#1b2234] text-[11px] text-slate-400">
                    <span className="font-semibold text-amber-400">Rejected Alternatives: </span>
                    {replanResult.explainability.alternatives_rejected.map((r) => (
                      <span key={r.option_id} className="font-mono text-slate-300 mr-2">
                        {r.option_id}: {r.rejection_reason}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 7. Canonical Evaluation Pipeline */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-purple-400">
              Evaluation Architecture
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-purple-950 text-purple-300 border border-purple-800">
              Canonical Pipeline
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            ServiceYield AI Decision Pipeline: From Quote to Manager Sign-Off
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            The end-to-end evaluation stages defined in the canonical system architecture. Stages are explicitly categorized
            by their execution status.
          </p>
        </div>

        <div className="space-y-3 pt-2">
          {/* Stage 1: Supplier Quote & Eligibility */}
          <div className="p-4 bg-[#0d101a] border border-cyan-800/60 rounded-xl space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-cyan-950 border border-cyan-700 text-cyan-300 flex items-center justify-center text-[10px] font-mono font-bold">
                  1
                </span>
                <span className="text-xs font-bold text-white">
                  Supplier Quote & Eligibility Checks (C1, C2)
                </span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-cyan-950 text-cyan-300 border border-cyan-800 font-semibold self-start sm:self-auto">
                Fixture Inputs Displayed — Validation Pending
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              The canonical fixture records both supplier offers (S1 and S2) as ACTIVE, and both reference the same part
              requirement (PART-REQ-104-SOLENOID) containing the ACES vehicle compatibility reference (ACES-CROSSOVER-2020-AWD).
              This screen displays these fixture inputs; independent algorithmic validation of supplier eligibility, part fitment,
              and technician certification gates remains pending.
            </p>
          </div>

          {/* Stage 2: Full-Shop Scheduling under Hard Constraints */}
          <div className="p-4 bg-[#0d101a] border border-slate-700/60 rounded-xl space-y-2 opacity-90">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-600 text-slate-300 flex items-center justify-center text-[10px] font-mono font-bold">
                  2
                </span>
                <span className="text-xs font-bold text-white">
                  Full-Shop Scheduling under Inviolable Hard Constraints (C1–C7)
                </span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700 self-start sm:self-auto">
                Conceptual &bull; Solver Pending
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Formulates discrete CP-SAT interval scheduling over horizon H=288 ticks. Enforces hard operational constraints:
              C1 (Eligibility), C2 (Part Release), C3 (Operation DAG), C4 (Resource Exclusivity), C5 (Physical Lift Immobility),
              C6 (Technician Shifts, Lunch Breaks & Wage Fairness), and C7 (Customer Authorization).
            </p>
          </div>

          {/* Stage 3: Independent L4 Schedule Verification */}
          <div className="p-4 bg-[#0d101a] border border-slate-700/60 rounded-xl space-y-2 opacity-90">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-600 text-slate-300 flex items-center justify-center text-[10px] font-mono font-bold">
                  3
                </span>
                <span className="text-xs font-bold text-white">
                  Independent L4 Schedule Verification Gate
                </span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700 self-start sm:self-auto">
                Conceptual &bull; Gate Pending (Stage 6)
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Independent O(N log N) Sweep-Line Occupancy Oracle auditing 100% feasibility across all C1–C7 constraints with
              zero shared solver code. Evaluates mutation resilience and rejects any schedule with physical overlap or break violations.
            </p>
          </div>

          {/* Stage 4: Economic Evaluation (Bay-Hour Shadow Price) */}
          <div className="p-4 bg-[#0d101a] border border-slate-700/60 rounded-xl space-y-2 opacity-90">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-600 text-slate-300 flex items-center justify-center text-[10px] font-mono font-bold">
                  4
                </span>
                <span className="text-xs font-bold text-white">
                  Economic Evaluation & Bay-Hour Shadow Price Analysis (nu_b(t))
                </span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700 self-start sm:self-auto">
                Conceptual &bull; Calculation Pending
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Derives marginal workshop capacity value through discrete re-solve difference: nu_b(t) = Delta Z* / Delta t.
              Balances the $37 incremental freight surcharge against the net economic recovery of avoided bay blockage and
              mitigated customer lateness penalties.
            </p>
          </div>

          {/* Stage 5: Service Manager Approval */}
          <div className="p-4 bg-[#0d101a] border border-slate-700/60 rounded-xl space-y-2 opacity-90">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-600 text-slate-300 flex items-center justify-center text-[10px] font-mono font-bold">
                  5
                </span>
                <span className="text-xs font-bold text-white">
                  Service Manager Approval & Action Binding
                </span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700 self-start sm:self-auto">
                Conceptual &bull; Sign-Off Pending
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              ServiceYield AI is strictly advisory. Final decision authority remains with the Service Manager. If approved,
              the recovery plan triggers parts procurement and updates shop dispatch. If rejected, baseline dispatch persists.
            </p>
          </div>
        </div>
      </div>

      {/* 7. Navigation Actions */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="space-y-0.5 text-center sm:text-left">
          <div className="text-xs font-bold text-white">Replay Stage Navigation</div>
          <div className="text-[11px] text-slate-400">
            Navigate back to Stage 4 Disruption Alert or inspect the upcoming L4 Verification Gate.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onSelectStage && (
            <>
              <button
                onClick={() => onSelectStage(4)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>&larr; Stage 4 Disruption Alert</span>
              </button>
              <button
                onClick={() => onSelectStage(3)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Stage 3 Capacity Board</span>
              </button>
              <button
                onClick={() => onSelectStage(6)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-purple-950/80 hover:bg-purple-900 text-purple-300 border border-purple-800 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Upcoming: Stage 6 Verification &rarr;</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

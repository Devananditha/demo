import React from 'react';
import { SYNTHETIC_DISRUPTION_SCENARIO } from '../data/mockData';
import {
  AlertTriangle,
  Clock,
  Truck,
  Warehouse,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Activity,
  Lock,
  Package,
  Timer,
  Zap,
} from 'lucide-react';

interface DisruptionAlertProps {
  onSelectStage?: (stageId: number) => void;
}

export const DisruptionAlert: React.FC<DisruptionAlertProps> = ({ onSelectStage }) => {
  const scenario = SYNTHETIC_DISRUPTION_SCENARIO;
  const { baseline, alternative } = scenario.supplierComparison;
  const downstream = scenario.downstreamImpact;

  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Preloaded Synthetic Scenario Disclosure */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
              </span>
              <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider font-mono">
                Stage 4 — Disruption Alert & Impact
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800/80 font-semibold">
                Event Replay
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Supplier ETA Slip & Workshop Bottleneck Cascade
            </h2>
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
              Demonstrates synthetic disruption replay from canonical S-MATH-01 fixture at evaluation tick{' '}
              <span className="text-cyan-300 font-mono font-semibold">159 (1:15 PM)</span>. Explains how an inbound
              supplier freight slip propagates into a severe physical lift stall and holding queue dependency.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onSelectStage && (
              <>
                <button
                  onClick={() => onSelectStage(3)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <Warehouse className="w-3.5 h-3.5 text-amber-400" />
                  <span>Stage 3 Capacity</span>
                </button>
                <button
                  onClick={() => onSelectStage(2)}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-mono transition-colors"
                >
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Stage 2 Predict</span>
                </button>
              </>
            )}
          </div>
        </div>

        {/* Prominent Synthetic Scenario Disclosure Banner */}
        <div className="mt-4 p-3 bg-amber-950/30 border border-amber-800/60 rounded-lg flex items-start space-x-3">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-relaxed text-amber-200/90">
            <span className="font-bold tracking-wide text-amber-300 uppercase font-mono mr-1.5">
              {scenario.classification}
            </span>
            &bull; This is an offline scenario replay of the canonical fixture disruption. It visualizes operational
            bottleneck mechanics and comparative recovery options. No live event-ingestion endpoint (POST /api/v1/events)
            is claimed or required for this stage.
          </div>
        </div>
      </div>

      {/* 2. Disruption Event Card */}
      <div className="bg-[#121624] border border-rose-900/60 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-rose-500 via-amber-500 to-rose-600" />

        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
          <div className="space-y-4 flex-1">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-lg bg-rose-950/80 border border-rose-800 flex items-center justify-center text-rose-400 shadow-inner">
                <AlertTriangle className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-rose-400">
                    Disruption Event Detected
                  </span>
                  <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-rose-950 text-rose-300 border border-rose-800/80">
                    {scenario.disruptionType}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white">
                  Primary Inbound Freight Delay (+{scenario.delayMinutes} Minutes)
                </h3>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
              <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
                <div className="text-[10px] uppercase font-mono text-slate-400 flex items-center space-x-1">
                  <Clock className="w-3 h-3 text-cyan-400" />
                  <span>Detection Timestamp</span>
                </div>
                <div className="text-xs font-mono font-bold text-cyan-300">
                  {scenario.triggerTime} (Tick {scenario.triggerTick})
                </div>
                <div className="text-[10px] text-slate-500">Evaluation Horizon</div>
              </div>

              <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
                <div className="text-[10px] uppercase font-mono text-slate-400 flex items-center space-x-1">
                  <Package className="w-3 h-3 text-rose-400" />
                  <span>Primary Affected RO</span>
                </div>
                <div className="text-xs font-bold text-rose-200">{scenario.affectedRoId}</div>
                <div className="text-[10px] text-slate-400 truncate">{scenario.affectedVehicle}</div>
              </div>

              <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
                <div className="text-[10px] uppercase font-mono text-slate-400 flex items-center space-x-1">
                  <Warehouse className="w-3 h-3 text-amber-400" />
                  <span>Assigned Bay</span>
                </div>
                <div className="text-xs font-bold text-amber-300">{scenario.affectedBayId}</div>
                <div className="text-[10px] text-slate-400 truncate">Heavy Diagnostic Lift 1</div>
              </div>

              <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg space-y-1">
                <div className="text-[10px] uppercase font-mono text-slate-400 flex items-center space-x-1">
                  <Lock className="w-3 h-3 text-rose-400" />
                  <span>Physical State</span>
                </div>
                <div className="text-xs font-mono font-bold text-rose-300">{scenario.vehicleState}</div>
                <div className="text-[10px] text-rose-400/90 font-medium">Immobilized on Lift</div>
              </div>
            </div>

            {/* Stalled Task and Physical Constraint Detail */}
            <div className="p-4 bg-rose-950/20 border border-rose-900/40 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-xs font-medium">
                <span className="text-rose-300 font-semibold flex items-center space-x-1.5">
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span>Task Breakdown & Physical Immobility</span>
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {scenario.stalledTask.taskId} &bull; {scenario.stalledTask.remainingDurationMinutes} min remaining
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                <strong className="text-white">Predecessor Status:</strong> {scenario.stalledTask.completedPredecessor}.
              </p>
              <p className="text-xs text-slate-300 leading-relaxed">
                <strong className="text-white">Stalled Procedure:</strong> {scenario.stalledTask.description}.
              </p>
              <div className="p-2.5 bg-[#0a0d14] border border-rose-900/60 rounded text-[11px] text-rose-200/90 flex items-start space-x-2">
                <Lock className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Constraint Enforcement:</strong> {scenario.constraintNote} The vehicle cannot be rolled, pushed,
                  or transferred off BAY-01 until the replacement shift solenoid is installed and fluid is replenished.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Supplier Timing & Sourcing Comparison */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center space-x-2">
              <Truck className="w-4 h-4 text-cyan-400" />
              <span>Supplier Lead-Time & Sourcing Options</span>
            </h3>
            <p className="text-xs text-slate-400">
              Comparative arrival times and shop-floor completion implications for RO-104 replacement solenoid.
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-500 uppercase">
            Part: OEM-SOL-TRANS-2020
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Baseline Ground Shuttle Option */}
          <div className="bg-[#121624] border border-orange-900/60 rounded-xl p-5 space-y-4 relative flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-orange-950/80 text-orange-300 border border-orange-800">
                    Option A — Baseline Ground Shuttle
                  </span>
                  <h4 className="text-sm font-bold text-white mt-1.5">{baseline.supplierName}</h4>
                  <div className="text-[11px] text-slate-400 font-mono">Supplier ID: {baseline.supplierId}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-orange-400">$0.00</div>
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Incremental Freight</div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 py-2 border-y border-[#1e2638] text-center font-mono text-xs">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Quoted ETA</div>
                  <div className="font-bold text-slate-300">4:10 PM</div>
                  <div className="text-[9px] text-slate-500">Tick {baseline.quotedEtaTick}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Inspection</div>
                  <div className="font-bold text-slate-300">20 min</div>
                  <div className="text-[9px] text-slate-500">+4 ticks</div>
                </div>
                <div>
                  <div className="text-[10px] text-orange-400 uppercase font-bold">Usable Ready</div>
                  <div className="font-bold text-orange-300">{baseline.usableReadyTime}</div>
                  <div className="text-[9px] text-orange-400/80">Tick {baseline.usableReadyTick}</div>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center space-x-1.5 text-rose-400 font-medium">
                  <XCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>Customer Promise: Missed by ~150 minutes</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed bg-[#0a0d14] p-3 rounded border border-[#1b2234]">
                  {baseline.impactSummary}
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Lift Stalled:</span>
              <span className="text-rose-400 font-mono font-semibold">BAY-01 locked until ~6:30 PM (Tick 222)</span>
            </div>
          </div>

          {/* Alternative Expedited Hotshot Courier Option */}
          <div className="bg-[#121624] border border-emerald-900/60 rounded-xl p-5 space-y-4 relative flex flex-col justify-between">
            <div className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                    Option B — Admissible Expedited Recovery
                  </span>
                  <h4 className="text-sm font-bold text-white mt-1.5">{alternative.supplierName}</h4>
                  <div className="text-[11px] text-slate-400 font-mono">Supplier ID: {alternative.supplierId}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-emerald-400">+${alternative.freightSurchargeUsd.toFixed(2)}</div>
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Freight Surcharge</div>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 py-2 border-y border-[#1e2638] text-center font-mono text-xs">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Quoted ETA</div>
                  <div className="font-bold text-emerald-300">1:35 PM</div>
                  <div className="text-[9px] text-slate-500">Tick {alternative.quotedEtaTick}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Inspection</div>
                  <div className="font-bold text-emerald-300">10 min</div>
                  <div className="text-[9px] text-slate-500">+2 ticks</div>
                </div>
                <div>
                  <div className="text-[10px] text-emerald-400 uppercase font-bold">Usable Ready</div>
                  <div className="font-bold text-emerald-300">{alternative.usableReadyTime}</div>
                  <div className="text-[9px] text-emerald-400/80">Tick {alternative.usableReadyTick}</div>
                </div>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex items-center space-x-1.5 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  <span>Customer Promise: Met on-time (~3:45 PM finish)</span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed bg-[#0a0d14] p-3 rounded border border-[#1b2234]">
                  {alternative.impactSummary}
                </p>
              </div>
            </div>

            <div className="pt-3 border-t border-[#1e2638] flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Lift Freed:</span>
              <span className="text-emerald-400 font-mono font-semibold">BAY-01 available at 3:45 PM (Tick 189)</span>
            </div>
          </div>
        </div>

        <div className="p-3 bg-[#0d101a] border border-[#1b2234] rounded-lg text-xs text-slate-400 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>
              Synthetic comparison for decision replay. Economic net recovery ($238 net gain) and branch-and-bound verification
              will be explored in Stage 5. No purchase order has been executed.
            </span>
          </div>
        </div>
      </div>

      {/* 4. Workshop Impact & Bay Dependency Cascade */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-5">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400">
              Downstream Workshop Impact
            </span>
            <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-300 border border-amber-800">
              Physical Bay Dependency
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">
            Bay Dependency Cascade: Why RO-106 is Blocked from Bay Entry
          </h3>
          <p className="text-xs text-slate-400 max-w-3xl leading-relaxed mt-1">
            Understanding the physical constraint propagation: even though RO-106 has all parts in stock and is classified
            READY by Predict Layer 1 (+75 min slack), it cannot start because the shop’s only heavy diagnostic lift is immobilized.
          </p>
        </div>

        {/* Step-by-Step Dependency Cascade */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative">
          {/* Node 1: Primary Stall */}
          <div className="p-4 bg-[#0d101a] border border-rose-900/50 rounded-xl space-y-2 relative">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-rose-950 text-rose-300 border border-rose-800">
                1. Primary Stall
              </span>
              <Lock className="w-3.5 h-3.5 text-rose-400" />
            </div>
            <div className="text-xs font-bold text-white">RO-104 Immobilized on Lift</div>
            <div className="text-[11px] text-slate-300 leading-relaxed">
              Transmission oil pan removed. Fluid drained. Cannot be rolled or relocated. Occupies BAY-01 indefinitely
              under baseline delivery delay.
            </div>
            <div className="text-[10px] font-mono text-rose-300 pt-1 border-t border-[#1b2234]">
              Location: BAY-01 &bull; Status: STALLED
            </div>
          </div>

          {/* Node 2: Exclusive Bay Bottleneck */}
          <div className="p-4 bg-[#0d101a] border border-amber-900/50 rounded-xl space-y-2 relative">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-950 text-amber-300 border border-amber-800">
                2. Bay Bottleneck
              </span>
              <Warehouse className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-xs font-bold text-white">BAY-01 Sole Heavy Lift</div>
            <div className="text-[11px] text-slate-300 leading-relaxed">
              BAY-01 is Metro Dealership’s only HEAVY_DIAGNOSTIC_LIFT (12,000 lbs). Bays 02 and 03 are standard 2-post lifts
              (10,000 lbs) and cannot host heavy diagnostic procedures.
            </div>
            <div className="text-[10px] font-mono text-amber-300 pt-1 border-t border-[#1b2234]">
              Capacity: 1 Heavy Diagnostic Bay in Rooftop
            </div>
          </div>

          {/* Node 3: Dependent Queue Vehicle */}
          <div className="p-4 bg-[#0d101a] border border-cyan-900/50 rounded-xl space-y-2 relative">
            <div className="flex items-center justify-between">
              <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-cyan-950 text-cyan-300 border border-cyan-800">
                3. Cascade Victim
              </span>
              <AlertTriangle className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-xs font-bold text-white">RO-106 Awaiting Lift</div>
            <div className="text-[11px] text-slate-300 leading-relaxed">
              {downstream.impactedVehicle} requires HEAVY_DIAGNOSTIC_LIFT for electrical stall diagnostic sweep (120 min).
              Cannot enter bay until RO-104 is cleared.
            </div>
            <div className="text-[10px] font-mono text-cyan-300 pt-1 border-t border-[#1b2234]">
              Holding Queue &bull; Customer Promise: {downstream.promisedDelivery}
            </div>
          </div>
        </div>

        {/* Factual Clarification Note */}
        <div className="p-3.5 bg-[#0a0d14] border border-[#1b2234] rounded-lg space-y-1.5 text-xs">
          <div className="flex items-center space-x-2 text-cyan-300 font-semibold">
            <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
            <span>Classification Fidelity Note</span>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">
            {downstream.dependencyNote} RO-106 is <span className="text-emerald-400 font-semibold">NOT blocked by parts lead times</span> (all parts are ready).
            Its vulnerability arises entirely from physical bay exclusivity and RO-104’s prolonged lift occupation.
          </p>
        </div>
      </div>

      {/* 5. Scenario Timeline */}
      <div className="bg-[#121624] border border-[#1e2638] rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center space-x-2">
              <Timer className="w-4 h-4 text-cyan-400" />
              <span>Scenario Timeline & Operational Milestones</span>
            </h3>
            <p className="text-xs text-slate-400">
              Chronological mapping of disruption events, recovery alternatives, customer promises, and shift cutoffs.
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
            Current Tick: 159 (1:15 PM)
          </span>
        </div>

        <div className="space-y-3 pt-2">
          {scenario.timelineMilestones.map((milestone, idx) => {
            const isCurrent = milestone.tick === 159;
            const badgeClasses = {
              rose: 'bg-rose-950/80 text-rose-300 border-rose-800',
              emerald: 'bg-emerald-950/80 text-emerald-300 border-emerald-800',
              amber: 'bg-amber-950/80 text-amber-300 border-amber-800',
              orange: 'bg-orange-950/80 text-orange-300 border-orange-800',
              slate: 'bg-slate-800 text-slate-300 border-slate-700',
              purple: 'bg-purple-950/80 text-purple-300 border-purple-800',
            }[milestone.badgeColor];

            return (
              <div
                key={idx}
                className={`p-3.5 rounded-lg border flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors ${
                  isCurrent
                    ? 'bg-rose-950/20 border-rose-800/80'
                    : 'bg-[#0d101a] border-[#1b2234] hover:border-slate-700'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className="w-16 shrink-0 text-center">
                    <div className="text-xs font-mono font-bold text-cyan-300">{milestone.time}</div>
                    <div className="text-[10px] font-mono text-slate-500">Tick {milestone.tick}</div>
                  </div>
                  <div className="h-8 w-px bg-[#1e2638] hidden sm:block" />
                  <div className="space-y-0.5">
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border ${badgeClasses}`}>
                        {milestone.label}
                      </span>
                      {isCurrent && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-mono uppercase bg-rose-500 text-slate-950 font-bold">
                          Now
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{milestone.description}</p>
                  </div>
                </div>

                <div className="text-[10px] font-mono text-slate-500 uppercase shrink-0 text-right">
                  {milestone.type}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 6. Navigation Actions & Stage Transitions */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="space-y-0.5 text-center sm:text-left">
          <div className="text-xs font-bold text-white">Continue Scenario Replay</div>
          <div className="text-[11px] text-slate-400">
            Inspect previous baseline capacity or proceed to Stage 5 Sourcing & Recovery Comparison.
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {onSelectStage && (
            <>
              <button
                onClick={() => onSelectStage(3)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <span>&larr; Stage 3 Capacity Board</span>
              </button>
              <button
                onClick={() => onSelectStage(5)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 rounded-lg text-xs font-medium transition-colors"
              >
                <span>Preview Stage 5 Sourcing &rarr;</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

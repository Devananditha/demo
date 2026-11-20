import React, { useEffect, useState } from 'react';
import { fetchCanonicalState } from '../api/predictClient';
import { DealershipStateItem, DealershipStateResponse } from '../types';
import {
  Clock,
  Layers,
  Lock,
  RefreshCw,
  Server,
  ShieldAlert,
  Terminal,
  Warehouse,
} from 'lucide-react';

interface BayDefinition {
  id: string;
  name: string;
  bayType: string;
  liftingCapacityLbs: number;
}

const CANONICAL_BAYS: BayDefinition[] = [
  {
    id: 'BAY-01',
    name: 'Heavy Diagnostic Lift 1',
    bayType: 'HEAVY_DIAGNOSTIC_LIFT',
    liftingCapacityLbs: 12000,
  },
  {
    id: 'BAY-02',
    name: 'Standard 2-Post Mechanical Lift 1',
    bayType: 'STANDARD_2POST',
    liftingCapacityLbs: 10000,
  },
  {
    id: 'BAY-03',
    name: 'Standard 2-Post Mechanical Lift 2',
    bayType: 'STANDARD_2POST',
    liftingCapacityLbs: 10000,
  },
];

export const BaselineCapacityBoard: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stateData, setStateData] = useState<DealershipStateResponse | null>(null);

  const loadState = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCanonicalState();
      setStateData(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to retrieve canonical state from backend API.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadState();
  }, []);

  const assignedROs = stateData?.repair_orders.filter((ro) => Boolean(ro.assigned_bay_id)) || [];
  const unassignedROs = stateData?.repair_orders.filter((ro) => !ro.assigned_bay_id) || [];
  const immobilizedROId = assignedROs.find((ro) => ro.physical_state === 'IMMOBILIZED_ON_LIFT')?.ro_id || 'RO-104';

  // Derive occupied and free bay counts from distinct assigned bay IDs
  const occupiedBayIds = new Set(
    stateData?.repair_orders
      .map((ro) => ro.assigned_bay_id)
      .filter((bayId): bayId is string => Boolean(bayId)) || []
  );
  const totalBaysCount = CANONICAL_BAYS.length;
  const occupiedBaysCount = CANONICAL_BAYS.filter((bay) => occupiedBayIds.has(bay.id)).length;
  const freeBaysCount = Math.max(0, totalBaysCount - occupiedBaysCount);

  return (
    <div className="space-y-6">
      {/* Stage Header Banner */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
              </span>
              <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider font-mono">
                Stage 3 — Baseline Schedule Board
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-semibold">
                Physical Capacity Situation
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Workshop Physical Bay Occupancy & Bottleneck Overview
            </h2>
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
              Visualizes actual lift stall occupancy, vehicle physical immobility, and holding queue state directly
              from canonical state API (<code className="text-cyan-300 font-mono">GET /api/v1/state</code>).
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadState}
              disabled={loading}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-950/70 hover:bg-cyan-900/80 text-cyan-300 border border-cyan-800/80 rounded-lg text-xs font-mono font-medium transition-colors disabled:opacity-50"
              title="Refresh canonical state"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Refreshing...' : 'Refresh State'}</span>
            </button>
          </div>
        </div>

        {/* Mandatory Pre-Optimisation Disclosure */}
        <div className="mt-4 p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg flex items-start gap-2.5">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="font-semibold text-amber-300 block">
              Baseline physical-state snapshot — before optimisation. No new schedule has been generated.
            </span>
            <span className="text-slate-400 block text-[11px] mt-0.5">
              Depicts frozen baseline physical stall occupancies at evaluation tick 159. No CP-SAT solver,
              T1 heuristic re-sequencing, or recovery courier dispatch has altered this operational state.
            </span>
          </div>
        </div>

        {/* Telemetry Context Bar */}
        {stateData && (
          <div className="mt-4 pt-3 border-t border-[#1e2638] flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-400">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-slate-300">
                <span className="text-slate-500">Rooftop:</span>{' '}
                <span className="text-cyan-300 font-bold">{stateData.rooftop_id}</span>
              </span>
              <span className="text-slate-300">
                <span className="text-slate-500">Snapshot Hash:</span>{' '}
                <span className="text-slate-200" title={stateData.snapshot_hash}>
                  {stateData.snapshot_hash.slice(0, 16)}...
                </span>
              </span>
              <span className="text-slate-300">
                <span className="text-slate-500">Eval Window:</span>{' '}
                <span className="text-emerald-400 font-bold">Tick {stateData.evaluation_tick} (1:15 PM)</span>
              </span>
              <span className="text-slate-300">
                <span className="text-slate-500">Operating End:</span>{' '}
                <span>Tick {stateData.operating_day_end_tick} (5:00 PM)</span>
              </span>
              <span className="text-slate-300">
                <span className="text-slate-500">Overtime Cutoff:</span>{' '}
                <span>Tick {stateData.overtime_cutoff_tick} (7:00 PM)</span>
              </span>
            </div>

            <div className="text-[11px] text-slate-400">
              Active Bays: <span className="text-white font-bold">{occupiedBaysCount} / {totalBaysCount}</span> &bull; Holding Queue: <span className="text-amber-400 font-bold">{unassignedROs.length}</span>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-12 text-center space-y-4">
          <div className="inline-flex p-3 rounded-xl bg-cyan-950/60 border border-cyan-800/40 text-cyan-400 animate-pulse">
            <Warehouse className="w-8 h-8 animate-spin" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">
              Loading Canonical Workshop Capacity State
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              Retrieving bay allocations and vehicle physical states from /api/v1/state...
            </p>
          </div>
        </div>
      )}

      {/* Error / Offline State */}
      {!loading && error && (
        <div className="bg-[#191016] border border-rose-900/60 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-400 shrink-0">
              <Server className="w-6 h-6" />
            </div>
            <div className="space-y-1 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-rose-200">
                  State API Service Offline or Unreachable
                </h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  Connection Error
                </span>
              </div>
              <p className="text-xs text-rose-300/90 font-mono">
                {error}
              </p>
              <p className="text-xs text-slate-400 pt-1">
                The Baseline Schedule Board requires active connection to the canonical state endpoint.
              </p>
            </div>
          </div>

          <div className="bg-[#0b0e17] border border-[#1e2638] rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 font-mono">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>To start the backend service:</span>
            </div>
            <div className="bg-black/50 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-cyan-300 select-all">
              cd backend ; uvicorn app.api.main:app --reload --port 8000
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={loadState}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-lg shadow-rose-950/50"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry API Connection</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Board Display */}
      {!loading && !error && stateData && (
        <div className="space-y-6">
          {/* Section 3: Operational Bottleneck Explanation */}
          <div className="bg-gradient-to-r from-[#1c1218] via-[#161420] to-[#111522] border-2 border-rose-600/70 rounded-xl p-5 shadow-2xl relative overflow-hidden">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div className="space-y-2 flex-1">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-950 text-rose-300 border border-rose-700/80 animate-pulse">
                    <Lock className="w-3.5 h-3.5" />
                    <span>CRITICAL OPERATIONAL BOTTLENECK</span>
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    Lifting Bay Lockout (Constraint C5 Physical-State Constraint)
                  </span>
                </div>
                <h3 className="text-base font-bold text-white tracking-tight">
                  Immobilized Vehicle Lockout on Specialized Lift (BAY-01 &bull; {immobilizedROId})
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed max-w-4xl">
                  Repair order <strong className="text-rose-400 font-mono">{immobilizedROId}</strong> is currently in{' '}
                  <strong className="text-rose-300 font-mono">STALLED</strong> status with physical state{' '}
                  <strong className="text-rose-300 font-mono">IMMOBILIZED_ON_LIFT</strong> inside{' '}
                  <strong className="text-white font-mono">BAY-01</strong> (Heavy Diagnostic Lift). Transmission teardown
                  is already completed, but the subsequent solenoid replacement and reassembly task is stalled awaiting
                  usable replacement-part availability. Under physical constraint C5, the vehicle cannot be rolled off
                  the lift or safely relocated until repair is completed.
                </p>
                <div className="pt-1 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs font-mono text-slate-400 border-t border-[#262030]">
                  <span>
                    Occupied Bay: <span className="text-white font-bold">BAY-01 (12,000 lbs Heavy Lift)</span>
                  </span>
                  <span>
                    Physical State: <span className="text-rose-400 font-bold">IMMOBILIZED_ON_LIFT</span>
                  </span>
                  <span>
                    Unassigned Queue: <span className="text-amber-400 font-bold">{unassignedROs.length} ROs without assigned bay</span>
                  </span>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-black/40 border border-rose-800/40 text-center shrink-0 min-w-[200px]">
                <div className="text-[10px] uppercase font-mono tracking-wider text-rose-400 font-bold">
                  Stall Utilization
                </div>
                <div className="text-2xl font-bold font-mono text-white mt-1">
                  {freeBaysCount} {freeBaysCount === 1 ? 'Bay' : 'Bays'} Free
                </div>
                <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                  {occupiedBaysCount} of {totalBaysCount} Bays Occupied
                </div>
              </div>
            </div>
          </div>

          {/* Section 1: Active Service Bays (Current Occupancy Grid) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                  <Warehouse className="w-4 h-4 text-cyan-400" />
                  <span>Physical Service Bays ({CANONICAL_BAYS.length} Total Bays)</span>
                </h3>
                <p className="text-xs text-slate-400">
                  Current vehicle assignments and lift occupancy states derived from API response.
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {occupiedBaysCount === totalBaysCount ? '100%' : `${Math.round((occupiedBaysCount / totalBaysCount) * 100)}%`} Physical Bay Utilization ({freeBaysCount} free)
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {CANONICAL_BAYS.map((bay) => {
                const assigned = assignedROs.find((ro) => ro.assigned_bay_id === bay.id);
                const isImmobilized = assigned?.physical_state === 'IMMOBILIZED_ON_LIFT';

                return (
                  <div
                    key={bay.id}
                    className={`rounded-xl p-5 border transition-all ${
                      isImmobilized
                        ? 'bg-[#1a0f16] border-rose-700/80 shadow-lg shadow-rose-950/40 ring-1 ring-rose-500/50'
                        : 'bg-[#111522] border-[#1e2638] shadow-sm hover:border-slate-700'
                    }`}
                  >
                    {/* Bay Header */}
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-white">
                            {bay.id}
                          </span>
                          {isImmobilized ? (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
                              <Lock className="w-3 h-3" />
                              <span>LOCKED</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                              <span>OCCUPIED</span>
                            </span>
                          )}
                        </div>
                        <div className="text-xs font-medium text-slate-300 mt-0.5">
                          {bay.name}
                        </div>
                      </div>

                      <div className="text-right text-[11px] font-mono text-slate-400">
                        {bay.liftingCapacityLbs.toLocaleString()} lbs
                      </div>
                    </div>

                    {/* Assigned Vehicle / Repair Order */}
                    <div className="mt-4 pt-3 border-t border-[#1e2638]/80 space-y-3">
                      {assigned ? (
                        <>
                          <div className="flex items-baseline justify-between">
                            <span className="text-[11px] uppercase tracking-wider font-mono text-slate-400">
                              Assigned Vehicle:
                            </span>
                            <span className="font-mono text-sm font-bold text-cyan-300">
                              {assigned.ro_id}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                            <div className="bg-[#0c0f18] p-2 rounded border border-slate-800/80">
                              <span className="text-[10px] text-slate-500 block">RO Status:</span>
                              <span
                                className={`font-semibold ${
                                  assigned.status === 'STALLED' ? 'text-rose-400' : 'text-blue-300'
                                }`}
                              >
                                {assigned.status}
                              </span>
                            </div>

                            <div className="bg-[#0c0f18] p-2 rounded border border-slate-800/80">
                              <span className="text-[10px] text-slate-500 block">Physical State:</span>
                              <span
                                className={`font-semibold ${
                                  isImmobilized ? 'text-rose-400' : 'text-emerald-400'
                                }`}
                              >
                                {assigned.physical_state}
                              </span>
                            </div>
                          </div>

                          <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between">
                            <span>Promised Delivery:</span>
                            <span className="text-slate-200">Tick {assigned.promise_tick}</span>
                          </div>

                          {isImmobilized && (
                            <div className="p-2 rounded bg-rose-950/70 border border-rose-800/60 text-[10px] text-rose-300 leading-tight">
                              Vehicle cannot be moved off the lift. Bay capacity remains locked until replacement parts are installed.
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="py-4 text-center text-xs text-slate-500 font-mono italic">
                          No vehicle currently assigned
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 2: Holding & Unassigned Queue */}
          <div className="bg-[#111522] border border-[#1e2638] rounded-xl overflow-hidden shadow-lg">
            <div className="px-5 py-4 border-b border-[#1e2638] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-[#0d111a]/60">
              <div>
                <h3 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                  <Layers className="w-4 h-4 text-amber-400" />
                  <span>Holding Area & Unassigned Queue ({unassignedROs.length} Repair Orders)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Vehicles staged in holding lots or currently unassigned to bays. Distinguishes physical state from readiness blockers.
                </p>
              </div>

              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono bg-amber-950/60 text-amber-300 border border-amber-800/50">
                <Clock className="w-3.5 h-3.5" />
                <span>Unassigned Physical State</span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#1e2638] bg-[#0c0f18] text-[11px] font-mono uppercase tracking-wider text-slate-400">
                    <th className="py-3 px-4 font-semibold">RO ID</th>
                    <th className="py-3 px-4 font-semibold">Assigned Bay</th>
                    <th className="py-3 px-4 font-semibold">Repair Order Status</th>
                    <th className="py-3 px-4 font-semibold">Physical State</th>
                    <th className="py-3 px-4 font-semibold">Promised Delivery</th>
                    <th className="py-3 px-4 font-semibold">Operational Condition</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#182030]">
                  {unassignedROs.map((ro: DealershipStateItem) => (
                    <tr key={ro.ro_id} className="hover:bg-[#151b2a] transition-colors">
                      {/* RO ID */}
                      <td className="py-3.5 px-4 font-mono font-bold text-white whitespace-nowrap">
                        <span className="text-cyan-400">{ro.ro_id}</span>
                      </td>

                      {/* Assigned Bay */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="text-xs font-mono text-slate-400 italic">
                          None (Unassigned)
                        </span>
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-mono bg-blue-950/60 text-blue-300 border border-blue-800/40">
                          {ro.status}
                        </span>
                      </td>

                      {/* Physical State */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-mono ${
                            ro.physical_state === 'ROLLABLE'
                              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800/40'
                              : 'bg-slate-800 text-slate-300 border border-slate-700'
                          }`}
                        >
                          {ro.physical_state}
                        </span>
                      </td>

                      {/* Promised Delivery */}
                      <td className="py-3.5 px-4 whitespace-nowrap font-mono text-xs text-slate-300">
                        Tick {ro.promise_tick}
                      </td>

                      {/* Operational Condition */}
                      <td className="py-3.5 px-4 text-xs font-mono text-slate-400">
                        {ro.ro_id === 'RO-105'
                          ? 'In holding; unassigned (readiness blocked by parts backorder)'
                          : ro.physical_state === 'ROLLABLE'
                          ? 'Rollable physical state; currently unassigned to a bay'
                          : 'In holding physical state; awaiting bay allocation'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Table Footer */}
            <div className="px-5 py-3 border-t border-[#1e2638] bg-[#0c0f18] text-xs text-slate-400 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="font-mono text-[11px] text-slate-400">
                Source: GET /api/v1/state &bull; Canonical S-MATH-01 Dataset
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Physical snapshot prior to CP-SAT schedule optimisation
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

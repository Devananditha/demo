import React from 'react';
import { KpiCards } from '../components/KpiCards';
import { RepairOrderTable } from '../components/RepairOrderTable';
import { Info } from 'lucide-react';
import { EVALUATION_TICK, OPERATING_DAY_END_TICK, OVERTIME_CUTOFF_TICK, SHARED_SNAPSHOT_TIME } from '../data/mockData';

export const ControlTower: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Workshop Static Synthetic Snapshot Context Banner */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider font-mono">
                Stage 1 — Synthetic Fixture Snapshot
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Fixed Operations Control Tower (1:15 PM Benchmark Snapshot)
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Static benchmark snapshot of dealership repair orders, bay occupancy, physical vehicle states,
              and fixture-validated reference readiness classifications from canonical test fixture (s_math_01).
            </p>
          </div>

          <div className="flex items-center space-x-3 bg-[#0b0e17]/80 border border-[#1e2638] px-4 py-2.5 rounded-lg text-xs">
            <Info className="w-4 h-4 text-cyan-400 flex-shrink-0" />
            <div className="text-slate-300 font-mono">
              <span className="text-white font-medium">Timeline: </span>
              Evaluation Tick {EVALUATION_TICK} ({SHARED_SNAPSHOT_TIME}) &bull; Operating End Tick {OPERATING_DAY_END_TICK} (5:00 PM) &bull; Overtime Cutoff Tick {OVERTIME_CUTOFF_TICK} (7:00 PM)
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <KpiCards />

      {/* Master Repair Order Table */}
      <RepairOrderTable />
    </div>
  );
};

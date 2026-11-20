import React from 'react';
import { ClipboardList, Users, Warehouse, DollarSign } from 'lucide-react';
import { KPI_DATA } from '../data/mockData';

export const KpiCards: React.FC = () => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Card 1: Active Repair Orders */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
            Active Repair Orders
          </span>
          <div className="p-2 rounded-lg bg-blue-950/60 text-blue-400 border border-blue-800/40">
            <ClipboardList className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-white tracking-tight">
            {KPI_DATA.activeRos}
          </span>
          <span className="text-xs text-slate-400 font-medium">RO-101 to RO-106</span>
        </div>
        <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
          <span>Canonical fixture snapshot</span>
        </div>
      </div>

      {/* Card 2: Technicians Clocked In */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
            Technicians
          </span>
          <div className="p-2 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
            <Users className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-white tracking-tight">
            {KPI_DATA.techniciansClockedIn}
          </span>
          <span className="text-xs text-emerald-400 font-medium font-mono">100% Active</span>
        </div>
        <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>Master EV, Transmission, Brakes, Express</span>
        </div>
      </div>

      {/* Card 3: Active Service Bays */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
            Active Bays
          </span>
          <div className="p-2 rounded-lg bg-amber-950/60 text-amber-400 border border-amber-800/40">
            <Warehouse className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-white tracking-tight">
            {KPI_DATA.activeBays}
          </span>
          <span className="text-xs text-amber-400 font-medium font-mono">Full Capacity</span>
        </div>
        <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          <span>Bay 01 (Heavy Lift), Bay 02 & 03 (2-Post)</span>
        </div>
      </div>

      {/* Card 4: Potential Labor Gross */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-4 shadow-sm hover:border-slate-700 transition-colors">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400 uppercase tracking-wider font-mono">
            Potential Labor Gross
          </span>
          <div className="p-2 rounded-lg bg-purple-950/60 text-purple-400 border border-purple-800/40">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-3xl font-bold font-mono text-cyan-300 tracking-tight">
            {KPI_DATA.potentialLaborGross}
          </span>
          <span className="text-xs text-slate-400 font-medium font-mono">@ $120/hr</span>
        </div>
        <div className="mt-2 text-[11px] text-slate-400 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
          <span>Target labor yield before lateness penalties</span>
        </div>
      </div>
    </div>
  );
};

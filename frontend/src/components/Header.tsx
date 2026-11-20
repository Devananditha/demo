import React from 'react';
import { Activity, Clock, ShieldAlert } from 'lucide-react';
import { DEALERSHIP_NAME, SIMULATED_DATE, SIMULATED_TIME, SYNTHETIC_DISCLOSURE } from '../data/mockData';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-[#1e2433] bg-[#0d111a] sticky top-0 z-50">
      {/* Top Banner: Synthetic Disclosure */}
      <div className="bg-[#121826] border-b border-[#1b2234] px-4 py-1 text-center flex items-center justify-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 text-amber-400 shrink-0" />
        <span className="text-[11px] font-mono tracking-wider font-semibold text-amber-300 uppercase">
          {SYNTHETIC_DISCLOSURE}
        </span>
      </div>

      {/* Main Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Left: Branding & Dealership Info */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400/30">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white font-sans">
                ServiceYield <span className="text-cyan-400">AI</span>
              </h1>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 font-medium">
                Decision Replay
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">
              {DEALERSHIP_NAME}
            </p>
          </div>
        </div>

        {/* Right: Simulation Snapshot Clock & Status */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 bg-[#121724] border border-[#1e2638] rounded-lg px-3 py-1.5 shadow-inner">
            <Clock className="w-4 h-4 text-cyan-400" />
            <div className="text-left">
              <div className="text-[10px] text-slate-400 uppercase tracking-wider font-mono font-semibold">
                Simulated Time
              </div>
              <div className="text-sm font-mono font-bold text-white tracking-wide flex items-center gap-1.5">
                <span>{SIMULATED_TIME}</span>
                <span className="text-xs text-slate-500 font-normal">({SIMULATED_DATE})</span>
              </div>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 border-l border-[#1e2433] pl-4">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-mono text-emerald-400 font-medium">
              SIMULATION ACTIVE
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};

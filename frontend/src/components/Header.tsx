import React from 'react';
import { Activity, Clock, ShieldAlert } from 'lucide-react';
import { DEALERSHIP_NAME, SIMULATED_DATE, SIMULATED_TIME, SYNTHETIC_DISCLOSURE } from '../data/mockData';

export const Header: React.FC = () => {
  return (
    <header className="border-b border-[#e5dfd5] bg-[#faf8f5] sticky top-0 z-50 shadow-xs">
      {/* Top Banner: Restrained Synthetic Disclosure */}
      <div className="bg-[#ede7db]/70 border-b border-[#e2ddd0] px-4 py-1 text-center flex items-center justify-center gap-2">
        <ShieldAlert className="w-3.5 h-3.5 text-stone-500 shrink-0" />
        <span className="text-[11px] font-medium tracking-wide text-stone-600">
          {SYNTHETIC_DISCLOSURE}
        </span>
      </div>

      {/* Main Header Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Left: Branding & Rooftop Info */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-md bg-stone-900 flex items-center justify-center shadow-xs text-white">
            <Activity className="w-5 h-5 text-amber-300" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight text-stone-900 font-sans">
                ServiceYield <span className="text-amber-800 font-semibold">AI</span>
              </h1>
              <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#eee8dc] text-stone-700 border border-[#ded7c8]">
                Decision Intelligence
              </span>
            </div>
            <p className="text-xs text-stone-500">
              {DEALERSHIP_NAME}
            </p>
          </div>
        </div>

        {/* Right: Simulation Clock & Operations Status */}
        <div className="flex items-center gap-3 self-end md:self-auto">
          <div className="flex items-center gap-2 bg-[#f5f2ea] border border-[#ded7c8] rounded-md px-3 py-1.5 shadow-xs">
            <Clock className="w-3.5 h-3.5 text-stone-500" />
            <div className="text-left leading-none">
              <span className="text-[10px] uppercase tracking-wider font-semibold text-stone-500 block">
                Simulated Clock
              </span>
              <span className="text-xs font-mono font-bold text-stone-900">
                {SIMULATED_TIME} <span className="text-[11px] font-sans font-normal text-stone-500">({SIMULATED_DATE})</span>
              </span>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-2 border-l border-[#ded7c8] pl-3">
            <span className="flex h-2 w-2 relative">
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
            </span>
            <span className="text-xs text-stone-600 font-medium">
              Live Simulation
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};

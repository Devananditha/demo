import React from 'react';
import { STAGES } from '../data/mockData';

interface NavigationTabsProps {
  activeStage: number;
  onSelectStage: (stageId: number) => void;
}

export const NavigationTabs: React.FC<NavigationTabsProps> = ({ activeStage, onSelectStage }) => {
  return (
    <nav className="border-b border-[#1b2234] bg-[#0d111a]/80 backdrop-blur-sm overflow-x-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex space-x-1 py-2 min-w-max">
          {STAGES.map((stage) => {
            const isActive = stage.id === activeStage;
            const isImplemented = stage.id <= 9;

            return (
              <button
                key={stage.id}
                onClick={() => onSelectStage(stage.id)}
                className={`group flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-md transition-all ${
                  isActive
                    ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-700/60 shadow-sm'
                    : isImplemented
                    ? 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                    : 'text-slate-500 hover:text-slate-400 hover:bg-slate-900/40 opacity-75'
                }`}
              >
                <span
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-mono font-bold ${
                    isActive
                      ? 'bg-cyan-500 text-slate-950'
                      : 'bg-slate-800 text-slate-400 group-hover:text-slate-300'
                  }`}
                >
                  {stage.id}
                </span>
                <span>{stage.name}</span>
                {!isImplemented && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1 py-0.2 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60">
                    Upcoming
                  </span>
                )}
                {stage.id === 2 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                    API Output
                  </span>
                )}
                {stage.id === 3 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-amber-950/80 text-amber-300 border border-amber-800/60">
                    Capacity
                  </span>
                )}
                {stage.id === 4 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-rose-950/80 text-rose-300 border border-rose-800/60">
                    Disruption
                  </span>
                )}
                {stage.id === 5 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-purple-950/80 text-purple-300 border border-purple-800/60">
                    Workbench
                  </span>
                )}
                {stage.id === 6 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-blue-950/80 text-blue-300 border border-blue-800/60">
                    Preview
                  </span>
                )}
                {stage.id === 7 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                    Executive
                  </span>
                )}
                {stage.id === 8 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-cyan-950/90 text-cyan-300 border border-cyan-500/80 font-bold animate-pulse">
                    LIVE STALLBREAKER
                  </span>
                )}
                {stage.id === 9 && (
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1.5 py-0.2 rounded bg-violet-950/80 text-violet-300 border border-violet-800/60 font-medium">
                    BENCHMARK
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

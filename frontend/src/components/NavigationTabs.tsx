import React from 'react';
import {
  LayoutDashboard,
  AlertTriangle,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  BarChart2,
} from 'lucide-react';
import { useAppState } from '../context/AppStateContext';

const NAV_SECTIONS = [
  { id: 1, label: 'Overview', icon: LayoutDashboard, color: 'cyan', isSecondary: false },
  { id: 2, label: 'Disruptions', icon: AlertTriangle, color: 'rose', isSecondary: false },
  { id: 3, label: 'Recovery Decisions', icon: RefreshCw, color: 'purple', isSecondary: false },
  { id: 4, label: 'Verification & Approval', icon: ShieldCheck, color: 'blue', isSecondary: false },
  { id: 5, label: 'Performance & Insights', icon: TrendingUp, color: 'emerald', isSecondary: false },
  { id: 6, label: 'Evaluation', icon: BarChart2, color: 'slate', isSecondary: true },
];

const colorMap: Record<string, { active: string; icon: string }> = {
  cyan:    { active: 'bg-cyan-950/60 text-cyan-300 border border-cyan-700/60', icon: 'text-cyan-400' },
  rose:    { active: 'bg-rose-950/60 text-rose-300 border border-rose-700/60', icon: 'text-rose-400' },
  purple:  { active: 'bg-purple-950/60 text-purple-300 border border-purple-700/60', icon: 'text-purple-400' },
  blue:    { active: 'bg-blue-950/60 text-blue-300 border border-blue-700/60', icon: 'text-blue-400' },
  emerald: { active: 'bg-emerald-950/60 text-emerald-300 border border-emerald-700/60', icon: 'text-emerald-400' },
  slate:   { active: 'bg-slate-800/80 text-slate-300 border border-slate-600/60', icon: 'text-slate-400' },
};

export const NavigationTabs: React.FC = () => {
  const { activeSection, setActiveSection } = useAppState();

  return (
    <nav className="border-b border-[#1b2234] bg-[#0d111a]/80 backdrop-blur-sm overflow-x-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center py-2 min-w-max">
          {/* Primary sections */}
          <div className="flex items-center space-x-1">
            {NAV_SECTIONS.filter((s) => !s.isSecondary).map((section) => {
              const isActive = section.id === activeSection;
              const colors = colorMap[section.color];
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`group flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-md transition-all ${
                    isActive
                      ? `${colors.active} shadow-sm`
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/50'
                  }`}
                >
                  <Icon
                    className={`w-3.5 h-3.5 ${isActive ? colors.icon : 'text-slate-500 group-hover:text-slate-300'}`}
                  />
                  <span>{section.label}</span>
                </button>
              );
            })}
          </div>

          {/* Separator */}
          <div className="mx-3 h-5 w-px bg-[#1b2234]" />

          {/* Secondary sections (Evaluation / Benchmarks) */}
          <div className="flex items-center space-x-1">
            {NAV_SECTIONS.filter((s) => s.isSecondary).map((section) => {
              const isActive = section.id === activeSection;
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`group flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-md transition-all ${
                    isActive
                      ? 'bg-slate-800/80 text-slate-300 border border-slate-600/60 shadow-sm'
                      : 'text-slate-500 hover:text-slate-400 hover:bg-slate-900/40'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-400" />
                  <span>{section.label}</span>
                  <span className="text-[9px] uppercase tracking-wider font-mono px-1 py-0.5 rounded bg-slate-800/80 text-slate-500 border border-slate-700/60">
                    Suite
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
};

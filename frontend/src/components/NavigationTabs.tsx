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
  { id: 1, label: 'Overview', icon: LayoutDashboard, isSecondary: false },
  { id: 2, label: 'Disruptions', icon: AlertTriangle, isSecondary: false },
  { id: 3, label: 'Recovery Decisions', icon: RefreshCw, isSecondary: false },
  { id: 4, label: 'Verification & Approval', icon: ShieldCheck, isSecondary: false },
  { id: 5, label: 'Performance & Insights', icon: TrendingUp, isSecondary: false },
  { id: 6, label: 'Evaluation', icon: BarChart2, isSecondary: true },
];

export const NavigationTabs: React.FC = () => {
  const { activeSection, setActiveSection } = useAppState();

  return (
    <nav className="border-b border-[#e5dfd5] bg-[#faf8f5] shadow-xs overflow-x-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between py-2 min-w-max">
          {/* Primary Operations Sections */}
          <div className="flex items-center space-x-1">
            {NAV_SECTIONS.filter((s) => !s.isSecondary).map((section) => {
              const isActive = section.id === activeSection;
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`group flex items-center gap-2 px-3.5 py-2 text-xs rounded-md transition-all ${
                    isActive
                      ? 'bg-[#eae3d5] text-stone-900 font-semibold border border-[#d8cebd] shadow-xs'
                      : 'text-stone-600 hover:text-stone-900 hover:bg-[#ede7dc]/60 font-medium'
                  }`}
                >
                  <Icon
                    className={`w-3.5 h-3.5 ${
                      isActive ? 'text-stone-900' : 'text-stone-400 group-hover:text-stone-600'
                    }`}
                  />
                  <span>{section.label}</span>
                </button>
              );
            })}
          </div>

          {/* Secondary Evaluation Suite */}
          <div className="flex items-center pl-4 border-l border-[#ded7c8]">
            {NAV_SECTIONS.filter((s) => s.isSecondary).map((section) => {
              const isActive = section.id === activeSection;
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={`group flex items-center gap-2 px-3 py-1.5 text-xs rounded-md transition-all ${
                    isActive
                      ? 'bg-[#eae3d5] text-stone-900 font-semibold border border-[#d8cebd] shadow-xs'
                      : 'text-stone-500 hover:text-stone-800 hover:bg-[#ede7dc]/50 font-medium'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 text-stone-400 group-hover:text-stone-600" />
                  <span>{section.label}</span>
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#eee8dc] text-stone-600 border border-[#ded7c8]">
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

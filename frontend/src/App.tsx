import React, { useState } from 'react';
import { Header } from './components/Header';
import { NavigationTabs } from './components/NavigationTabs';
import { ControlTower } from './pages/ControlTower';
import { STAGES } from './data/mockData';
import { Layers, ArrowRight, ShieldAlert } from 'lucide-react';

export const App: React.FC = () => {
  const [activeStage, setActiveStage] = useState<number>(1);
  const currentStageInfo = STAGES.find((s) => s.id === activeStage);

  return (
    <div className="min-h-screen bg-sy-navy text-slate-100 flex flex-col font-sans selection:bg-sy-accent selection:text-white">
      {/* Persistent Operations Header */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Stage Navigation */}
        <NavigationTabs activeStage={activeStage} onSelectStage={setActiveStage} />

        {/* View Routing */}
        {activeStage === 1 ? (
          <ControlTower />
        ) : (
          <div className="bg-sy-card border border-sy-border rounded-lg p-12 text-center space-y-4 shadow-xl">
            <div className="mx-auto w-12 h-12 rounded-full bg-sy-elevated border border-sy-border flex items-center justify-center text-sy-accent">
              <Layers className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <div className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sy-accent/10 text-sy-accent border border-sy-accent/20 mb-2">
                Upcoming Stage {activeStage}
              </div>
              <h2 className="text-xl font-bold text-white">
                {currentStageInfo?.name}
              </h2>
              <p className="text-sm text-slate-400 max-w-lg mx-auto">
                {currentStageInfo?.description}
              </p>
            </div>
            <p className="text-xs text-slate-500 max-w-md mx-auto pt-2 border-t border-sy-border/50">
              This stage is scheduled for implementation in subsequent Decision Replay steps.
              Return to Stage 1 to monitor active workshop telemetry.
            </p>
            <div className="pt-2">
              <button
                onClick={() => setActiveStage(1)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-sy-accent hover:bg-sy-accentHover text-white text-xs font-medium rounded-md transition-colors"
              >
                <span>Return to Control Tower</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-sy-border/60 bg-sy-navy/80 py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-500/80" />
            <span>
              Synthetic Golden Demo Environment &bull; Advisory Decision Intelligence for Dealership Fixed Operations
            </span>
          </div>
          <div>
            &copy; {new Date().getFullYear()} ServiceYield AI. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;

import React, { useState } from 'react';
import { Header } from './components/Header';
import { NavigationTabs } from './components/NavigationTabs';
import { ControlTower } from './pages/ControlTower';
import { ReadinessRiskDetail } from './pages/ReadinessRiskDetail';
import { BaselineCapacityBoard } from './pages/BaselineCapacityBoard';
import { DisruptionAlert } from './pages/DisruptionAlert';
import { SourcingRecoveryComparison } from './pages/SourcingRecoveryComparison';
import { VerificationGate } from './pages/VerificationGate';
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
        ) : activeStage === 2 ? (
          <ReadinessRiskDetail />
        ) : activeStage === 3 ? (
          <BaselineCapacityBoard />
        ) : activeStage === 4 ? (
          <DisruptionAlert onSelectStage={setActiveStage} />
        ) : activeStage === 5 ? (
          <SourcingRecoveryComparison onSelectStage={setActiveStage} />
        ) : activeStage === 6 ? (
          <VerificationGate onSelectStage={setActiveStage} />
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
              Return to Stage 1 for Workshop Control Tower, Stage 2 for Readiness & Risk, Stage 3 for Baseline Capacity Board, Stage 4 for Disruption Alert, Stage 5 for Sourcing Comparison, or Stage 6 for Verification Gate.
            </p>
            <div className="pt-2 flex flex-wrap justify-center gap-3">
              <button
                onClick={() => setActiveStage(1)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-sy-accent hover:bg-sy-accentHover text-white text-xs font-medium rounded-md transition-colors"
              >
                <span>Stage 1 Control Tower</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setActiveStage(2)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-md border border-slate-700 transition-colors"
              >
                <span>Stage 2 Readiness</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setActiveStage(3)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-md border border-slate-700 transition-colors"
              >
                <span>Stage 3 Capacity Board</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setActiveStage(4)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-md border border-slate-700 transition-colors"
              >
                <span>Stage 4 Disruption Alert</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setActiveStage(5)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-md border border-slate-700 transition-colors"
              >
                <span>Stage 5 Sourcing Trade-Off</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setActiveStage(6)}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-md border border-slate-700 transition-colors"
              >
                <span>Stage 6 Verification Gate</span>
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

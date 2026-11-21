import React from 'react';
import { Header } from './components/Header';
import { NavigationTabs } from './components/NavigationTabs';
import { AppStateProvider, useAppState } from './context/AppStateContext';
import { OverviewDashboard } from './pages/OverviewDashboard';
import { DisruptionsView } from './pages/DisruptionsView';
import { RecoveryDecisionsView } from './pages/RecoveryDecisionsView';
import { VerificationApprovalView } from './pages/VerificationApprovalView';
import { PerformanceView } from './pages/PerformanceView';
import { BenchmarkEvaluationView } from './pages/BenchmarkEvaluationView';
import { ShieldAlert } from 'lucide-react';

const AppContent: React.FC = () => {
  const { activeSection, setActiveSection } = useAppState();

  const handleSelectLegacyStage = (legacyStageId: number) => {
    // Map legacy stage IDs to the 5 operational sections
    if (legacyStageId === 1 || legacyStageId === 2 || legacyStageId === 3) {
      setActiveSection(1); // Overview
    } else if (legacyStageId === 4) {
      setActiveSection(2); // Disruptions
    } else if (legacyStageId === 5 || legacyStageId === 8) {
      setActiveSection(3); // Recovery Decisions
    } else if (legacyStageId === 6) {
      setActiveSection(4); // Verification & Approval
    } else if (legacyStageId === 7) {
      setActiveSection(5); // Performance & Insights
    } else if (legacyStageId === 9) {
      setActiveSection(6); // Evaluation / Benchmarks
    } else {
      setActiveSection(1);
    }
  };

  return (
    <div className="min-h-screen bg-sy-navy text-slate-100 flex flex-col font-sans selection:bg-sy-accent selection:text-white">
      {/* Persistent Operations Header */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Navigation Tabs */}
        <NavigationTabs />

        {/* View Routing */}
        {activeSection === 1 ? (
          <OverviewDashboard />
        ) : activeSection === 2 ? (
          <DisruptionsView />
        ) : activeSection === 3 ? (
          <RecoveryDecisionsView />
        ) : activeSection === 4 ? (
          <VerificationApprovalView />
        ) : activeSection === 5 ? (
          <PerformanceView />
        ) : activeSection === 6 ? (
          <BenchmarkEvaluationView onSelectStage={handleSelectLegacyStage} />
        ) : null}
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

export const App: React.FC = () => {
  return (
    <AppStateProvider>
      <AppContent />
    </AppStateProvider>
  );
};

export default App;

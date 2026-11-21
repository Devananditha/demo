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
    if (legacyStageId === 1 || legacyStageId === 2 || legacyStageId === 3) {
      setActiveSection(1);
    } else if (legacyStageId === 4) {
      setActiveSection(2);
    } else if (legacyStageId === 5 || legacyStageId === 8) {
      setActiveSection(3);
    } else if (legacyStageId === 6) {
      setActiveSection(4);
    } else if (legacyStageId === 7) {
      setActiveSection(5);
    } else if (legacyStageId === 9) {
      setActiveSection(6);
    } else {
      setActiveSection(1);
    }
  };

  return (
    <div className="min-h-screen bg-[#f5f2ea] text-stone-900 flex flex-col font-sans selection:bg-amber-100 selection:text-stone-900">
      {/* Persistent Enterprise Operations Header */}
      <Header />

      {/* Main Navigation Bar */}
      <NavigationTabs />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
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
      <footer className="border-t border-[#e5dfd5] bg-[#faf8f5] py-4 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-stone-500 gap-2">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-3.5 h-3.5 text-stone-400" />
            <span>
              Synthetic Demonstration Environment &bull; Advisory Decision Intelligence for Automotive Fixed Operations
            </span>
          </div>
          <div className="text-stone-400">
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

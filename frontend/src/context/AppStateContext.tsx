import React, { createContext, useContext, useState } from 'react';
import {
  CommitResult,
  DealershipReadinessReport,
  DealershipStateResponse,
  ScheduleResult,
  ScheduleVerificationResult,
  StallBreakerRecoveryReport,
} from '../types';

export interface AppState {
  activeSection: number;
  setActiveSection: (section: number) => void;
  workshopState: DealershipStateResponse | null;
  readinessReport: DealershipReadinessReport | null;
  initialSchedule: ScheduleResult | null;
  initialSnapshotHash: string | null;
  activeDisruptionEventId: string | null;
  recoveryReport: StallBreakerRecoveryReport | null;
  selectedPlanId: string | null;
  setSelectedPlanId: (id: string | null) => void;
  selectedAlternative: any | null;
  verificationResult: ScheduleVerificationResult | null;
  approvalResult: CommitResult | null;
  hasRunRecovery: boolean;
  hasRunVerification: boolean;
  setWorkshopState: (state: DealershipStateResponse | null) => void;
  setReadinessReport: (report: DealershipReadinessReport | null) => void;
  setInitialSchedule: (schedule: ScheduleResult | null, snapshotHash?: string | null) => void;
  setActiveDisruptionEventId: (id: string | null) => void;
  setRecoveryReport: (report: StallBreakerRecoveryReport | null) => void;
  setVerificationResult: (result: ScheduleVerificationResult | null) => void;
  setApprovalResult: (result: CommitResult | null) => void;
  setHasRunRecovery: (val: boolean) => void;
  setHasRunVerification: (val: boolean) => void;
}

const AppStateContext = createContext<AppState | null>(null);

export const AppStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeSection, setActiveSection] = useState<number>(1);
  const [workshopState, setWorkshopState] = useState<DealershipStateResponse | null>(null);
  const [readinessReport, setReadinessReport] = useState<DealershipReadinessReport | null>(null);
  const [initialSchedule, setInitialScheduleState] = useState<ScheduleResult | null>(null);
  const [initialSnapshotHash, setInitialSnapshotHash] = useState<string | null>(null);
  const [activeDisruptionEventId, setActiveDisruptionEventId] = useState<string | null>(null);
  const [recoveryReport, setRecoveryReport] = useState<StallBreakerRecoveryReport | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<ScheduleVerificationResult | null>(null);
  const [approvalResult, setApprovalResult] = useState<CommitResult | null>(null);
  const [hasRunRecovery, setHasRunRecovery] = useState<boolean>(false);
  const [hasRunVerification, setHasRunVerification] = useState<boolean>(false);

  // Preserve pre-disruption baseline: never overwrite if already captured
  const setInitialSchedule = (schedule: ScheduleResult | null, snapshotHash?: string | null) => {
    setInitialScheduleState((prev) => {
      if (prev && schedule !== null) {
        return prev;
      }
      return schedule;
    });
    if (snapshotHash) {
      setInitialSnapshotHash((prev) => prev || snapshotHash);
    }
  };

  // Single Source of Truth: derive the selected alternative
  const activePlanId = selectedPlanId || recoveryReport?.recommended_plan_id || null;
  const selectedAlternative = recoveryReport?.evaluated_alternatives?.find(
    (a: any) => a.plan_id === activePlanId
  ) || (recoveryReport?.evaluated_alternatives?.[0] ?? null);

  const handleSetRecoveryReport = (report: StallBreakerRecoveryReport | null) => {
    setRecoveryReport(report);
    if (report?.recommended_plan_id) {
      setSelectedPlanId(report.recommended_plan_id);
    }
  };

  return (
    <AppStateContext.Provider
      value={{
        activeSection,
        setActiveSection,
        workshopState,
        readinessReport,
        initialSchedule,
        initialSnapshotHash,
        activeDisruptionEventId,
        recoveryReport,
        selectedPlanId,
        setSelectedPlanId,
        selectedAlternative,
        verificationResult,
        approvalResult,
        hasRunRecovery,
        hasRunVerification,
        setWorkshopState,
        setReadinessReport,
        setInitialSchedule,
        setActiveDisruptionEventId,
        setRecoveryReport: handleSetRecoveryReport,
        setVerificationResult,
        setApprovalResult,
        setHasRunRecovery,
        setHasRunVerification,
      }}
    >
      {children}
    </AppStateContext.Provider>
  );
};

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}

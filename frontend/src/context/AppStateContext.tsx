import React, { createContext, useContext, useState } from 'react';
import {
  CommitResult,
  DealershipReadinessReport,
  DealershipStateResponse,
  StallBreakerRecoveryReport,
} from '../types';

export interface AppState {
  activeSection: number;
  setActiveSection: (section: number) => void;
  workshopState: DealershipStateResponse | null;
  readinessReport: DealershipReadinessReport | null;
  recoveryReport: StallBreakerRecoveryReport | null;
  verificationResult: any | null;
  approvalResult: CommitResult | null;
  hasRunRecovery: boolean;
  hasRunVerification: boolean;
  setWorkshopState: (state: DealershipStateResponse | null) => void;
  setReadinessReport: (report: DealershipReadinessReport | null) => void;
  setRecoveryReport: (report: StallBreakerRecoveryReport | null) => void;
  setVerificationResult: (result: any | null) => void;
  setApprovalResult: (result: CommitResult | null) => void;
  setHasRunRecovery: (val: boolean) => void;
  setHasRunVerification: (val: boolean) => void;
}

const AppStateContext = createContext<AppState | null>(null);

export const AppStateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeSection, setActiveSection] = useState<number>(1);
  const [workshopState, setWorkshopState] = useState<DealershipStateResponse | null>(null);
  const [readinessReport, setReadinessReport] = useState<DealershipReadinessReport | null>(null);
  const [recoveryReport, setRecoveryReport] = useState<StallBreakerRecoveryReport | null>(null);
  const [verificationResult, setVerificationResult] = useState<any | null>(null);
  const [approvalResult, setApprovalResult] = useState<CommitResult | null>(null);
  const [hasRunRecovery, setHasRunRecovery] = useState<boolean>(false);
  const [hasRunVerification, setHasRunVerification] = useState<boolean>(false);

  return (
    <AppStateContext.Provider
      value={{
        activeSection,
        setActiveSection,
        workshopState,
        readinessReport,
        recoveryReport,
        verificationResult,
        approvalResult,
        hasRunRecovery,
        hasRunVerification,
        setWorkshopState,
        setReadinessReport,
        setRecoveryReport,
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

export type ReadinessStatus = 'READY' | 'AT_RISK' | 'BLOCKED' | 'UNKNOWN';

export interface RepairOrder {
  roId: string;
  vehicle: string;
  customerName: string;
  customerComplaint: string;
  bay: string;
  physicalState: string;
  technician: string;
  promisedDelivery: string;
  promiseTick: number;
  readinessStatus: ReadinessStatus;
  readinessDetails: string;
  laborGrossUsd: number;
  priorityWeight: number;
}

export interface KpiSummary {
  activeRos: number;
  activeTechnicians: string;
  operationalBays: string;
  potentialLaborGross: string;
}

export interface StageInfo {
  id: number;
  name: string;
  shortLabel: string;
  status: 'active' | 'upcoming';
  description: string;
}

import { KpiSummary, RepairOrder, StageInfo } from '../types';

export const SIMULATED_TIME = '1:15 PM';
export const SIMULATED_DATE = 'Nov 18, 2026';
export const DEALERSHIP_NAME = 'Metro Auto Group — Rooftop #01';
export const SYNTHETIC_DISCLOSURE = 'SYNTHETIC DEMO DATA — NOT A CLAIM OF LIVE TEKION INTEGRATION';

export const EVALUATION_TICK = 159;
export const OPERATING_DAY_END_TICK = 204;
export const OVERTIME_CUTOFF_TICK = 228;
export const SHARED_SNAPSHOT_TIME = '1:15 PM (Tick 159)';
export const SHARED_SNAPSHOT_TIMESTAMP = '2026-11-18 13:15:00 UTC (Tick 159)';

export const KPI_DATA: KpiSummary = {
  activeRos: 6,
  techniciansClockedIn: '4 / 4',
  activeBays: '3 / 3',
  potentialLaborGross: '$2,840.00',
};

export const STAGES: StageInfo[] = [
  {
    id: 1,
    name: 'Workshop Control Tower',
    shortLabel: '1. Control Tower',
    status: 'active',
    description: 'Current shop-floor overview of active repair orders, lift bay occupancies, and labor targets.',
  },
  {
    id: 2,
    name: 'Readiness & Risk Detail',
    shortLabel: '2. Readiness & Risk',
    status: 'upcoming',
    description: 'Predict Layer 1 Empirical-Bayes lead-time distributions and readiness risk quantiles.',
  },
  {
    id: 3,
    name: 'Baseline Schedule Board',
    shortLabel: '3. Schedule Board',
    status: 'upcoming',
    description: 'T2 CP-SAT discrete 5-min dispatch grid, technician shifts, and bay shadow-price surface strip.',
  },
  {
    id: 4,
    name: 'Disruption Alert Modal',
    shortLabel: '4. Disruption Shock',
    status: 'upcoming',
    description: 'Disruption shock injection, bay blockage cascade, and blast-radius dependency graph.',
  },
  {
    id: 5,
    name: 'Sourcing & Recovery Comparison',
    shortLabel: '5. Sourcing Trade-Off',
    status: 'upcoming',
    description: 'Admissible branch-and-bound alternatives: Option A (Wait) vs Option B (Hotshot Courier).',
  },
  {
    id: 6,
    name: 'Independent Verification Gate',
    shortLabel: '6. L4 Verification',
    status: 'upcoming',
    description: 'Independent O(N log N) sweep-line oracle verification and Manager approval binding.',
  },
  {
    id: 7,
    name: 'Executive Outcome Dashboard',
    shortLabel: '7. Outcome Ledger',
    status: 'upcoming',
    description: 'Before-vs-after financial and operational reconciliation with verifiable net yield delta.',
  },
];

export const MOCK_REPAIR_ORDERS: RepairOrder[] = [
  {
    roId: 'RO-101',
    vehicle: '2022 Sedan - Apex GL (V6)',
    customerName: 'John Miller',
    customerComplaint: 'Front brake rotor and pad wear, squealing noise',
    bay: 'BAY-02',
    physicalState: 'ROLLABLE',
    technician: 'Not recorded in fixture',
    promisedDelivery: '12:00 PM',
    promiseTick: 144,
    readinessStatus: 'READY',
    readinessDetails: 'Pads & rotors verified in-stock at wholesale intake (usable tick 96)',
    laborGrossUsd: 300.0,
    priorityWeight: 1,
  },
  {
    roId: 'RO-102',
    vehicle: '2024 SUV - Horizon AWD',
    customerName: 'Sarah Connor',
    customerComplaint: '30,000-mile factory recommended maintenance inspection',
    bay: 'BAY-03',
    physicalState: 'ROLLABLE',
    technician: 'Not recorded in fixture',
    promisedDelivery: '11:00 AM',
    promiseTick: 132,
    readinessStatus: 'READY',
    readinessDetails: 'Filters verified staged in parts intake room (usable tick 96)',
    laborGrossUsd: 240.0,
    priorityWeight: 1,
  },
  {
    roId: 'RO-103',
    vehicle: '2021 Truck - Titan V8',
    customerName: 'Marcus Brody',
    customerComplaint: 'Front suspension knocking over bumps; strut replacement',
    bay: 'No assigned bay; task is pending',
    physicalState: 'ROLLABLE',
    technician: 'Not recorded in fixture',
    promisedDelivery: '3:00 PM',
    promiseTick: 180,
    readinessStatus: 'READY',
    readinessDetails: 'Struts inspected and certified ready on parts cart',
    laborGrossUsd: 480.0,
    priorityWeight: 2,
  },
  {
    roId: 'RO-104',
    vehicle: '2020 Crossover - CrossTour',
    customerName: 'Robert Thorne',
    customerComplaint: 'Transmission slipping 2nd to 3rd gear; shift solenoid valve failure',
    bay: 'BAY-01, stalled and immobilized on lift',
    physicalState: 'IMMOBILIZED_ON_LIFT',
    technician: 'Not recorded in fixture',
    promisedDelivery: '4:00 PM',
    promiseTick: 192,
    readinessStatus: 'AT_RISK',
    readinessDetails: 'OEM ground freight delayed to tick 198; Hotshot courier alternative tick 165',
    laborGrossUsd: 720.0,
    priorityWeight: 3,
  },
  {
    roId: 'RO-105',
    vehicle: '2023 EV - VoltRunner',
    customerName: 'Elena Rostova',
    customerComplaint: 'High voltage battery inverter wiring harness diagnostic fault code',
    bay: 'In holding; no assigned bay',
    physicalState: 'IN_HOLDING',
    technician: 'Not recorded in fixture',
    promisedDelivery: '5:00 PM',
    promiseTick: 204,
    readinessStatus: 'BLOCKED',
    readinessDetails: 'Inverter harness backordered nationally; zero OEM or sister store ETA',
    laborGrossUsd: 600.0,
    priorityWeight: 2,
  },
  {
    roId: 'RO-106',
    vehicle: '2022 SUV - RidgeLine',
    customerName: 'David Zhang',
    customerComplaint: 'Intermittent engine stalling on deceleration; full diagnostic sweep required',
    bay: 'In holding; no assigned bay',
    physicalState: 'IN_HOLDING',
    technician: 'Not recorded in fixture',
    promisedDelivery: '4:30 PM',
    promiseTick: 198,
    readinessStatus: 'UNKNOWN',
    readinessDetails: 'Vehicle in holding staging; awaiting Bay 01 lift release after RO-104 teardown',
    laborGrossUsd: 500.0,
    priorityWeight: 3,
  },
];

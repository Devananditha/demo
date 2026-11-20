import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';
import { MOCK_REPAIR_ORDERS } from '../data/mockData';
import { ReadinessStatus, RepairOrder } from '../types';

const getStatusBadge = (status: ReadinessStatus) => {
  switch (status) {
    case 'READY':
      return {
        bg: 'bg-emerald-950/50',
        text: 'text-emerald-300',
        border: 'border-emerald-600/60',
        icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
        label: 'READY',
      };
    case 'AT_RISK':
      return {
        bg: 'bg-amber-950/50',
        text: 'text-amber-300',
        border: 'border-amber-600/60',
        icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
        label: 'AT_RISK',
      };
    case 'BLOCKED':
      return {
        bg: 'bg-rose-950/50',
        text: 'text-rose-300',
        border: 'border-rose-600/60',
        icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
        label: 'BLOCKED',
      };
    case 'UNKNOWN':
    default:
      return {
        bg: 'bg-slate-900/60',
        text: 'text-slate-300',
        border: 'border-slate-700/60',
        icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400" />,
        label: 'UNKNOWN',
      };
  }
};

export const RepairOrderTable: React.FC = () => {
  return (
    <div className="bg-[#111522] border border-[#1e2638] rounded-xl overflow-hidden shadow-lg">
      <div className="px-5 py-4 border-b border-[#1e2638] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-[#0d111a]/60">
        <div>
          <h2 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
            <span>Active Workshop Repair Orders</span>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {MOCK_REPAIR_ORDERS.length} Active
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time shop floor status across lifting bays, technician allocations, and promised customer deliveries.
          </p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[#1e2638] bg-[#0c0f18] text-[11px] font-mono uppercase tracking-wider text-slate-400">
              <th className="py-3 px-4 font-semibold">RO ID</th>
              <th className="py-3 px-4 font-semibold">Vehicle & Customer</th>
              <th className="py-3 px-4 font-semibold">Customer Complaint</th>
              <th className="py-3 px-4 font-semibold">Bay Assignment</th>
              <th className="py-3 px-4 font-semibold">Technician</th>
              <th className="py-3 px-4 font-semibold">Promised Delivery</th>
              <th className="py-3 px-4 font-semibold text-center">Readiness Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#182030]">
            {MOCK_REPAIR_ORDERS.map((ro: RepairOrder) => {
              const badge = getStatusBadge(ro.readinessStatus);

              return (
                <tr
                  key={ro.roId}
                  className="hover:bg-[#151b2a] transition-colors group cursor-default"
                >
                  {/* RO ID */}
                  <td className="py-3.5 px-4 font-mono font-bold text-white whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="text-cyan-400 group-hover:underline">
                        {ro.roId}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        w={ro.priorityWeight}
                      </span>
                    </div>
                  </td>

                  {/* Vehicle & Customer */}
                  <td className="py-3.5 px-4">
                    <div className="font-medium text-slate-200">
                      {ro.vehicle}
                    </div>
                    <div className="text-xs text-slate-400 font-sans">
                      {ro.customerName}
                    </div>
                  </td>

                  {/* Customer Complaint */}
                  <td className="py-3.5 px-4 max-w-xs xl:max-w-md">
                    <div className="text-xs text-slate-300 line-clamp-2">
                      {ro.customerComplaint}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      Est. Gross: ${ro.laborGrossUsd.toFixed(2)}
                    </div>
                  </td>

                  {/* Bay */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="text-xs font-mono font-medium text-slate-200">
                      {ro.bay}
                    </div>
                  </td>

                  {/* Technician */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="text-xs font-medium text-slate-200">
                      {ro.technician}
                    </div>
                  </td>

                  {/* Promised Delivery */}
                  <td className="py-3.5 px-4 whitespace-nowrap">
                    <div className="font-mono text-xs font-semibold text-white">
                      {ro.promisedDelivery}
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">
                      Tick {ro.promiseTick}
                    </div>
                  </td>

                  {/* Readiness Status */}
                  <td className="py-3.5 px-4 whitespace-nowrap text-center">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-bold border shadow-sm ${badge.bg} ${badge.text} ${badge.border}`}
                    >
                      {badge.icon}
                      <span>{badge.label}</span>
                    </span>
                    <div className="text-[10px] text-slate-400 font-mono mt-0.5 text-center">
                      {ro.freshness}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer Info Strip */}
      <div className="px-5 py-3 border-t border-[#1e2638] bg-[#0c0f18] text-xs text-slate-400 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>3 Ready</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
            <span>1 At Risk (RO-104)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-rose-400"></span>
            <span>1 Blocked (RO-105)</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
            <span>1 Unknown (RO-106)</span>
          </span>
        </div>
        <div className="font-mono text-[11px] text-slate-400">
          Showing 6 of 6 Active Repair Orders
        </div>
      </div>
    </div>
  );
};

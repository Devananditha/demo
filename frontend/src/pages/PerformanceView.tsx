import React from 'react';
import { useAppState } from '../context/AppStateContext';
import { MOCK_REPAIR_ORDERS } from '../data/mockData';
import { ScheduledAssignment } from '../types';
import { tickToTime } from '../utils/timeUtils';
import {
  TrendingUp,
  DollarSign,
  Clock,
  CheckCircle2,
  XCircle,
  Truck,
  Warehouse,
  ArrowRight,
  ShieldCheck,
  Award,
  Scale,
} from 'lucide-react';

export const PerformanceView: React.FC = () => {
  const {
    workshopState,
    initialSchedule,
    recoveryReport,
    selectedAlternative,
    approvalResult,
    hasRunRecovery,
    setActiveSection,
  } = useAppState();

  const totalLaborGross = MOCK_REPAIR_ORDERS.reduce((sum, ro) => sum + ro.laborGrossUsd, 0);

  const baselineSchedule = initialSchedule || null;
  const recoveredSchedule = (hasRunRecovery ? selectedAlternative?.schedule_result : null) || null;
  const dr = recoveryReport?.decision_replay;

  // Sourcing freight investment: derived strictly from backend metrics without manufactured fallbacks
  const rawFreight =
    selectedAlternative?.sourcing_cost_usd !== undefined
      ? Number(selectedAlternative.sourcing_cost_usd)
      : dr?.sourcing_freight_usd !== undefined
      ? Number(dr.sourcing_freight_usd)
      : recoveryReport?.recommended_action?.freight_surcharge_usd !== undefined
      ? Number(recoveryReport.recommended_action.freight_surcharge_usd)
      : undefined;
  const freightUsd = rawFreight !== undefined && !isNaN(rawFreight) ? rawFreight : undefined;

  // Net economic improvement: derived strictly from backend metrics without manufactured fallbacks
  const rawDelta =
    selectedAlternative?.net_recovery_delta_usd !== undefined
      ? Number(selectedAlternative.net_recovery_delta_usd)
      : dr?.net_economic_delta_usd !== undefined
      ? Number(dr.net_economic_delta_usd)
      : undefined;
  const netDeltaUsd = rawDelta !== undefined && !isNaN(rawDelta) ? rawDelta : undefined;

  // Supplier Name: derived strictly from backend candidate or alternative
  const supplierName =
    selectedAlternative?.sourcing_candidate?.supplier_name ||
    selectedAlternative?.supplier_name ||
    (hasRunRecovery ? 'Sourcing Alternative' : 'Unavailable');

  // Avoided idle time: absolute avoided minutes (no negative display)
  const avoidedIdleMinutes =
    dr?.delta_idle_minutes !== undefined ? Math.abs(dr.delta_idle_minutes) : undefined;

  // Derive outcome dynamically per repair order from a schedule
  const deriveRoOutcome = (
    ro: (typeof MOCK_REPAIR_ORDERS)[0],
    schedule: typeof initialSchedule,
    isRecoveredPlan: boolean
  ) => {
    if (!schedule) {
      return {
        ro,
        finishTick: null,
        finishTime: null,
        promiseTick: ro.promiseTick,
        promisedTime: ro.promisedDelivery || tickToTime(ro.promiseTick),
        isOnTime: false,
        isOvertime: false,
        isScheduled: false,
        isComplete: false,
        delayMinutes: 0,
        statusLabel: isRecoveredPlan ? 'Not calculated' : 'Unavailable',
        statusType: 'unavailable' as const,
        detail: isRecoveredPlan ? 'Recovery optimizer not executed' : 'Initial schedule not loaded',
      };
    }

    const assignments = schedule.plan?.assignments?.filter((a) => a.ro_id === ro.roId) || [];
    const compStatus =
      schedule.ro_completion_statuses?.[ro.roId] ||
      schedule.metrics?.ro_completion_statuses?.[ro.roId];
    const unscheduledReason =
      schedule.unscheduled_tasks?.[ro.roId] ||
      (schedule.unscheduled_tasks &&
        Object.entries(schedule.unscheduled_tasks).find(([k]) =>
          k.includes(ro.roId.replace('RO-', ''))
        )?.[1]);

    const promiseTick =
      workshopState?.repair_orders?.find((r) => r.ro_id === ro.roId)?.promise_tick ?? ro.promiseTick;
    const promisedTime = ro.promisedDelivery || tickToTime(promiseTick);

    if (assignments.length === 0) {
      let label = 'Unscheduled';
      if (compStatus === 'BLOCKED_BY_PARTS' || ro.readinessStatus === 'BLOCKED') {
        label = 'Blocked — Parts Unavailable';
      } else if (compStatus === 'UNSCHEDULABLE_IN_HORIZON') {
        label = 'Unscheduled — Exceeds Shift Horizon';
      } else if (unscheduledReason) {
        label = `Unscheduled — ${unscheduledReason}`;
      }
      return {
        ro,
        finishTick: null,
        finishTime: null,
        promiseTick,
        promisedTime,
        isOnTime: false,
        isOvertime: false,
        isScheduled: false,
        isComplete: false,
        delayMinutes: 0,
        statusLabel: label,
        statusType: 'blocked' as const,
        detail: 'No assignments allocated in schedule',
      };
    }

    const finishTick = Math.max(...assignments.map((a) => a.end_tick));
    const finishTime = tickToTime(finishTick);
    const isComplete =
      compStatus === 'COMPLETED' || compStatus === 'FULLY_SCHEDULED' || !compStatus;
    const isOvertime = finishTick > (workshopState?.operating_day_end_tick ?? 204);
    const isOnTime = isComplete && finishTick <= promiseTick;
    const delayMinutes = finishTick > promiseTick ? (finishTick - promiseTick) * 5 : 0;

    if (!isComplete) {
      return {
        ro,
        finishTick,
        finishTime,
        promiseTick,
        promisedTime,
        isOnTime: false,
        isOvertime,
        isScheduled: true,
        isComplete: false,
        delayMinutes,
        statusLabel: 'Partially Scheduled',
        statusType: 'incomplete' as const,
        detail: `Incomplete work; final scheduled segment ends at ${finishTime}`,
      };
    }

    if (isOnTime) {
      return {
        ro,
        finishTick,
        finishTime,
        promiseTick,
        promisedTime,
        isOnTime: true,
        isOvertime: false,
        isScheduled: true,
        isComplete: true,
        delayMinutes: 0,
        statusLabel: 'Delivered On-Time',
        statusType: 'ontime' as const,
        detail: `Completed at ${finishTime} (Promise: ${promisedTime})`,
      };
    }

    if (isOvertime) {
      return {
        ro,
        finishTick,
        finishTime,
        promiseTick,
        promisedTime,
        isOnTime: false,
        isOvertime: true,
        isScheduled: true,
        isComplete: true,
        delayMinutes,
        statusLabel: `Recovered into Overtime (${delayMinutes}m late)`,
        statusType: 'overtime_late' as const,
        detail: `Completed at ${finishTime} in overtime (Promise: ${promisedTime})`,
      };
    }

    return {
      ro,
      finishTick,
      finishTime,
      promiseTick,
      promisedTime,
      isOnTime: false,
      isOvertime: false,
      isScheduled: true,
      isComplete: true,
      delayMinutes,
      statusLabel: `Delayed (${delayMinutes}m late)`,
      statusType: 'late' as const,
      detail: `Completed at ${finishTime} (Promise: ${promisedTime})`,
    };
  };

  const baselineOutcomes = MOCK_REPAIR_ORDERS.map((ro) =>
    deriveRoOutcome(ro, baselineSchedule, false)
  );
  const recoveredOutcomes = MOCK_REPAIR_ORDERS.map((ro) =>
    deriveRoOutcome(ro, recoveredSchedule, true)
  );

  const activeOutcomes = hasRunRecovery && recoveredSchedule ? recoveredOutcomes : baselineOutcomes;
  const activeSchedule = hasRunRecovery && recoveredSchedule ? recoveredSchedule : baselineSchedule;

  const baselineOnTimeCount = baselineSchedule
    ? baselineOutcomes.filter((o) => o.isOnTime).length
    : undefined;
  const recoveredOnTimeCount = recoveredSchedule
    ? recoveredOutcomes.filter((o) => o.isOnTime).length
    : undefined;
  const activeOnTimeCount = activeSchedule
    ? activeOutcomes.filter((o) => o.isOnTime).length
    : undefined;

  const ro104Outcome = activeOutcomes.find((o) => o.ro.roId === 'RO-104');
  const ro106Outcome = activeOutcomes.find((o) => o.ro.roId === 'RO-106');

  // Bay unblocking status for RO-106
  const ro106Assignment = recoveredSchedule?.plan?.assignments?.find(
    (a: ScheduledAssignment) => a.ro_id === 'RO-106'
  );
  const ro106BayStatus = ro106Assignment
    ? `Admitted to ${ro106Assignment.bay_id} (${tickToTime(ro106Assignment.start_tick)} – ${tickToTime(ro106Assignment.end_tick)})`
    : hasRunRecovery
    ? 'In holding'
    : 'Awaiting BAY-01 release';

  function KpiCard({
    label,
    value,
    sub,
    color,
    icon: Icon,
    placeholder,
  }: {
    label: string;
    value?: string | number;
    sub?: string;
    color?: string;
    icon: React.ElementType;
    placeholder?: string;
  }) {
    return (
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 flex flex-col justify-between space-y-3 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-stone-500">{label}</span>
          <Icon className={`w-4 h-4 ${color || 'text-stone-400'}`} />
        </div>
        {value !== undefined ? (
          <div>
            <div className={`text-2xl font-bold font-mono ${color || 'text-stone-900'}`}>{value}</div>
            {sub && <div className="text-xs text-stone-500 mt-1">{sub}</div>}
          </div>
        ) : (
          <div>
            <div className="text-xs text-stone-400 italic">
              {placeholder || 'Unavailable'}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* Header Banner */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <Award className="w-4 h-4 text-stone-800" />
              <span className="text-xs font-semibold text-stone-800 uppercase tracking-wide">
                Executive Operations Ledger
              </span>
            </div>
            <h2 className="text-xl font-bold text-stone-900 tracking-tight">Performance & Economic Insights</h2>
            <p className="text-xs text-stone-500 mt-1 max-w-2xl leading-relaxed">
              Consolidated outcome metrics comparing the pre-disruption baseline against verified recovered dispatch.
              Evaluates contribution margin protected, customer promise adherence, and physical service-bay utilization.
            </p>
          </div>

          {!hasRunRecovery && (
            <button
              onClick={() => setActiveSection(3)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-md text-xs font-medium shadow-xs transition-colors self-start sm:self-auto shrink-0"
            >
              <span>Run Recovery Optimizer</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {approvalResult?.status === 'COMMITTED' && (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-900 border border-emerald-200 rounded-md text-xs font-medium self-start sm:self-auto shrink-0">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>DISPATCH COMMITTED</span>
            </div>
          )}
        </div>
      </div>

      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Total Potential Labor Gross"
          value={`$${totalLaborGross.toFixed(2)}`}
          sub="6 scheduled repair orders"
          color="text-stone-900"
          icon={DollarSign}
          placeholder="Always available"
        />
        <KpiCard
          label="Expedited Freight Investment"
          value={freightUsd !== undefined ? `-$${freightUsd.toFixed(2)}` : undefined}
          sub={freightUsd !== undefined ? supplierName : undefined}
          color="text-rose-800"
          icon={Truck}
          placeholder="Unavailable (no freight incurred)"
        />
        <KpiCard
          label="Net Economic Improvement"
          value={netDeltaUsd !== undefined ? `+$${netDeltaUsd.toFixed(2)}` : undefined}
          sub={netDeltaUsd !== undefined ? 'Protected vs. unmitigated baseline' : undefined}
          color="text-emerald-800"
          icon={TrendingUp}
          placeholder="Not calculated (run recovery)"
        />
        <KpiCard
          label="Customer Promise Adherence"
          value={
            activeOnTimeCount !== undefined
              ? `${activeOnTimeCount} / ${MOCK_REPAIR_ORDERS.length} (${Math.round(
                  (activeOnTimeCount / MOCK_REPAIR_ORDERS.length) * 100
                )}%)`
              : undefined
          }
          sub={
            activeOnTimeCount !== undefined
              ? hasRunRecovery
                ? `${ro104Outcome?.isOnTime ? 'RO-104 on-time' : 'RO-104 delayed'}; ${
                    ro106Outcome?.isOvertime
                      ? `RO-106 in overtime (${ro106Outcome.delayMinutes}m late)`
                      : ro106Outcome?.isScheduled
                      ? 'RO-106 scheduled'
                      : 'RO-106 unscheduled'
                  }`
                : 'Baseline unmitigated schedule'
              : undefined
          }
          color="text-stone-900"
          icon={CheckCircle2}
          placeholder="Unavailable"
        />
      </div>

      {/* Schedule Comparison Ledger: Pre-Disruption Baseline vs. Recovered Schedule */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e5dfd5] bg-[#faf8f5] flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-stone-800" />
              <h3 className="text-sm font-semibold text-stone-900">
                Schedule Comparison: Pre-Disruption Baseline vs. Recovered Schedule
              </h3>
            </div>
            <p className="text-xs text-stone-500 mt-0.5">
              Reconciliation of constraint-verified operational and economic metrics.
            </p>
          </div>
          <span className="text-[11px] font-mono px-2.5 py-1 rounded bg-[#eee8dc] text-stone-700 border border-[#ded7c8] self-start sm:self-auto">
            Baseline: {baselineSchedule?.plan_id || 'Unavailable'} &bull; Recovered:{' '}
            {recoveredSchedule?.plan_id || 'Not calculated'}
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#e5dfd5] bg-[#f5f1e8] text-stone-700 font-semibold text-left">
                <th className="px-4 py-3">Performance Dimension</th>
                <th className="px-4 py-3">Original Baseline Schedule</th>
                <th className="px-4 py-3">Recovered Schedule (Selected)</th>
                <th className="px-4 py-3">Variance / Net Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eee8df] font-mono">
              <tr className="hover:bg-[#faf8f5] transition-colors">
                <td className="px-4 py-3 font-sans font-medium text-stone-900">Net Economic Objective (Z)</td>
                <td className="px-4 py-3 text-stone-700">
                  {dr?.baseline_net_objective_usd
                    ? `$${Number(dr.baseline_net_objective_usd).toFixed(2)}`
                    : baselineSchedule?.metrics?.net_objective_usd
                    ? `$${Number(baselineSchedule.metrics.net_objective_usd).toFixed(2)}`
                    : 'Unavailable'}
                </td>
                <td className="px-4 py-3 font-bold text-stone-900">
                  {dr?.proposed_net_objective_usd
                    ? `$${Number(dr.proposed_net_objective_usd).toFixed(2)}`
                    : recoveredSchedule?.metrics?.net_objective_usd
                    ? `$${Number(recoveredSchedule.metrics.net_objective_usd).toFixed(2)}`
                    : 'Not calculated'}
                </td>
                <td className="px-4 py-3 text-emerald-800 font-bold">
                  {netDeltaUsd !== undefined ? `+$${netDeltaUsd.toFixed(2)}` : 'Not calculated'}
                </td>
              </tr>
              <tr className="hover:bg-[#faf8f5] transition-colors">
                <td className="px-4 py-3 font-sans font-medium text-stone-900">Customer Promise Adherence</td>
                <td className="px-4 py-3 text-stone-700 font-sans">
                  {baselineOnTimeCount !== undefined
                    ? `${baselineOnTimeCount} / ${MOCK_REPAIR_ORDERS.length} (${Math.round(
                        (baselineOnTimeCount / MOCK_REPAIR_ORDERS.length) * 100
                      )}%)`
                    : 'Unavailable'}
                </td>
                <td className="px-4 py-3 font-bold text-stone-900 font-sans">
                  {recoveredOnTimeCount !== undefined
                    ? `${recoveredOnTimeCount} / ${MOCK_REPAIR_ORDERS.length} (${Math.round(
                        (recoveredOnTimeCount / MOCK_REPAIR_ORDERS.length) * 100
                      )}%)`
                    : 'Not calculated'}
                </td>
                <td className="px-4 py-3 text-stone-800 font-sans">
                  {baselineOnTimeCount !== undefined && recoveredOnTimeCount !== undefined
                    ? `${recoveredOnTimeCount >= baselineOnTimeCount ? '+' : ''}${
                        recoveredOnTimeCount - baselineOnTimeCount
                      } on-time ROs`
                    : 'Not calculated'}
                </td>
              </tr>
              <tr className="hover:bg-[#faf8f5] transition-colors">
                <td className="px-4 py-3 font-sans font-medium text-stone-900">Total Weighted Lateness</td>
                <td className="px-4 py-3 text-stone-700">
                  {dr?.baseline_weighted_lateness_ticks !== undefined
                    ? `${dr.baseline_weighted_lateness_ticks} ticks (${dr.baseline_weighted_lateness_ticks * 5}m)`
                    : baselineSchedule?.metrics?.weighted_lateness_ticks !== undefined
                    ? `${baselineSchedule.metrics.weighted_lateness_ticks} ticks`
                    : 'Unavailable'}
                </td>
                <td className="px-4 py-3 text-stone-900">
                  {dr?.proposed_weighted_lateness_ticks !== undefined
                    ? `${dr.proposed_weighted_lateness_ticks} ticks (${dr.proposed_weighted_lateness_ticks * 5}m)`
                    : recoveredSchedule?.metrics?.weighted_lateness_ticks !== undefined
                    ? `${recoveredSchedule.metrics.weighted_lateness_ticks} ticks`
                    : 'Not calculated'}
                </td>
                <td className="px-4 py-3 text-emerald-800">
                  {dr?.delta_weighted_lateness_ticks !== undefined
                    ? `${dr.delta_weighted_lateness_ticks > 0 ? '+' : ''}${
                        dr.delta_weighted_lateness_ticks
                      } ticks (${Math.abs(dr.delta_weighted_lateness_ticks * 5)}m avoided)`
                    : 'Not calculated'}
                </td>
              </tr>
              <tr className="hover:bg-[#faf8f5] transition-colors">
                <td className="px-4 py-3 font-sans font-medium text-stone-900">Expedited Sourcing Freight</td>
                <td className="px-4 py-3 text-stone-700">$0.00</td>
                <td className="px-4 py-3 text-rose-800 font-bold">
                  {freightUsd !== undefined ? `-$${freightUsd.toFixed(2)}` : 'Not calculated'}
                </td>
                <td className="px-4 py-3 text-rose-800">
                  {freightUsd !== undefined ? `-$${freightUsd.toFixed(2)}` : 'Not calculated'}
                </td>
              </tr>
              <tr className="hover:bg-[#faf8f5] transition-colors">
                <td className="px-4 py-3 font-sans font-medium text-stone-900">Physical Bay Utilization (BAY-01)</td>
                <td className="px-4 py-3 text-stone-700">
                  {dr?.baseline_bay_utilization_pct !== undefined
                    ? `${dr.baseline_bay_utilization_pct.toFixed(1)}%`
                    : 'Unavailable'}
                </td>
                <td className="px-4 py-3 text-stone-900 font-bold">
                  {dr?.proposed_bay_utilization_pct !== undefined
                    ? `${dr.proposed_bay_utilization_pct.toFixed(1)}%`
                    : 'Not calculated'}
                </td>
                <td className="px-4 py-3 text-emerald-800 font-bold">
                  {dr?.delta_bay_utilization_pct !== undefined
                    ? `+${dr.delta_bay_utilization_pct.toFixed(1)}%`
                    : 'Not calculated'}
                </td>
              </tr>
              <tr className="hover:bg-[#faf8f5] transition-colors">
                <td className="px-4 py-3 font-sans font-medium text-stone-900">Dead Lift Idle Time Avoided</td>
                <td className="px-4 py-3 text-stone-700">
                  {dr?.baseline_idle_minutes !== undefined ? `${dr.baseline_idle_minutes} min` : 'Unavailable'}
                </td>
                <td className="px-4 py-3 text-stone-900">
                  {dr?.proposed_idle_minutes !== undefined ? `${dr.proposed_idle_minutes} min` : 'Not calculated'}
                </td>
                <td className="px-4 py-3 text-emerald-800 font-bold">
                  {avoidedIdleMinutes !== undefined ? `${avoidedIdleMinutes} min avoided` : 'Not calculated'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Bay Utilization & Avoided Idle Hours */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg p-5 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-[#eee8df] pb-3">
          <div className="flex items-center gap-2">
            <Warehouse className="w-4 h-4 text-stone-600" />
            <h3 className="text-sm font-semibold text-stone-900">Physical Service-Bay Utilization</h3>
          </div>
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-[#f5f1e8] text-stone-700 border border-[#ded7c8]">
            BAY-01 Heavy Diagnostic Lift
          </span>
        </div>

        {hasRunRecovery && dr ? (
          <div className="space-y-4">
            {/* BAY-01 Utilization Bar */}
            <div>
              <div className="flex justify-between items-center mb-1.5 text-xs">
                <span className="text-stone-700 font-medium">BAY-01 Active Working Utilization</span>
                <span className="font-mono font-bold text-stone-900">
                  {dr.proposed_bay_utilization_pct.toFixed(1)}%
                  <span className="text-emerald-800 ml-1.5">
                    (+{dr.delta_bay_utilization_pct.toFixed(1)}% recovered)
                  </span>
                </span>
              </div>
              <div className="h-3 bg-[#f0ebe0] rounded-full overflow-hidden border border-[#ded7c8]">
                <div
                  className="h-full bg-stone-900 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(dr.proposed_bay_utilization_pct, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-stone-500 mt-1.5 font-mono">
                <span>Baseline unmitigated: {dr.baseline_bay_utilization_pct.toFixed(1)}%</span>
                <span>Optimized dispatch: {dr.proposed_bay_utilization_pct.toFixed(1)}%</span>
              </div>
            </div>

            {/* Capacity Relief Breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3.5 bg-[#faf8f5] border border-[#e5dfd5] rounded-md flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-emerald-600" />
                  <span className="text-stone-700 font-medium">Dead Lift Idle Time Avoided</span>
                </div>
                <span className="font-mono font-bold text-emerald-800 text-sm">
                  {avoidedIdleMinutes !== undefined ? `${avoidedIdleMinutes} minutes avoided` : 'Unavailable'}
                </span>
              </div>

              <div className="p-3.5 bg-[#faf8f5] border border-[#e5dfd5] rounded-md flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-stone-700" />
                  <span className="text-stone-700 font-medium">Downstream RO-106 Status</span>
                </div>
                <span className="font-medium text-stone-900">{ro106BayStatus}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-stone-500 italic p-4 bg-[#faf8f5] rounded-md border border-[#e5dfd5] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <span>Utilization and avoided idle time will populate once the Economic Optimizer runs in Recovery Decisions.</span>
            <button
              onClick={() => setActiveSection(3)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#faf7f0] text-stone-800 border border-[#ded7c8] rounded-md text-xs font-medium shadow-xs transition-colors shrink-0 self-start sm:self-auto"
            >
              <span>Run Optimizer</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Repair Order Delivery Outcome Ledger Table */}
      <div className="bg-white border border-[#e5dfd5] rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-[#e5dfd5] bg-[#faf8f5]">
          <h3 className="text-sm font-semibold text-stone-900">Full-Shop Delivery Outcome Ledger</h3>
          <p className="text-xs text-stone-500">
            Final customer delivery promise status derived from actual scheduled assignments and completion timestamps.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[#e5dfd5] bg-[#f5f1e8] text-stone-700 font-semibold text-left">
                <th className="px-4 py-3">Order ID</th>
                <th className="px-4 py-3">Customer & Vehicle</th>
                <th className="px-4 py-3">Promised Delivery</th>
                <th className="px-4 py-3">Scheduled Finish</th>
                <th className="px-4 py-3">Labor Value</th>
                <th className="px-4 py-3">Dispatch Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#eee8df]">
              {activeOutcomes.map((outcome) => {
                const { ro } = outcome;
                return (
                  <tr key={ro.roId} className="hover:bg-[#faf8f5] transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-stone-900">{ro.roId}</td>
                    <td className="px-4 py-3 text-stone-800">
                      <div className="font-medium">{ro.customerName}</div>
                      <div className="text-[11px] text-stone-500">{ro.vehicle}</div>
                    </td>
                    <td className="px-4 py-3 font-mono font-medium text-stone-700">{outcome.promisedTime}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-stone-900">
                      {outcome.finishTime || '—'}
                    </td>
                    <td className="px-4 py-3 font-mono font-semibold text-stone-900">
                      ${ro.laborGrossUsd.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      {outcome.statusType === 'ontime' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-900 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>Delivered On-Time</span>
                        </span>
                      )}
                      {outcome.statusType === 'overtime_late' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200">
                          <Clock className="w-3 h-3 text-amber-600" />
                          <span>Recovered into Overtime ({outcome.delayMinutes}m late)</span>
                        </span>
                      )}
                      {outcome.statusType === 'late' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200">
                          <Clock className="w-3 h-3 text-amber-600" />
                          <span>Delayed ({outcome.delayMinutes}m late)</span>
                        </span>
                      )}
                      {outcome.statusType === 'incomplete' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-stone-100 text-stone-700 border border-stone-300">
                          <Clock className="w-3 h-3 text-stone-500" />
                          <span>Partially Scheduled</span>
                        </span>
                      )}
                      {outcome.statusType === 'blocked' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-800 border border-rose-200">
                          <XCircle className="w-3 h-3 text-rose-600" />
                          <span>{outcome.statusLabel}</span>
                        </span>
                      )}
                      {outcome.statusType === 'unavailable' && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#eee8dc] text-stone-600 border border-[#ded7c8]">
                          <Clock className="w-3 h-3 text-stone-400" />
                          <span>Unavailable</span>
                        </span>
                      )}
                      <div className="text-[10px] text-stone-500 mt-0.5">{outcome.detail}</div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

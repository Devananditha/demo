import React, { useEffect, useState } from 'react';
import { fetchCanonicalState, fetchPredictReadiness } from '../api/predictClient';
import {
  DealershipReadinessReport,
  DealershipStateResponse,
  ReadinessStatus,
  RepairOrderAssessment,
} from '../types';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Server,
  Activity,
  ShieldAlert,
  ArrowUpRight,
  Terminal,
} from 'lucide-react';

const getStatusBadge = (status: ReadinessStatus) => {
  switch (status) {
    case 'READY':
      return {
        bg: 'bg-emerald-950/60',
        text: 'text-emerald-300',
        border: 'border-emerald-600/70',
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
        label: 'READY',
      };
    case 'AT_RISK':
      return {
        bg: 'bg-amber-950/60',
        text: 'text-amber-300',
        border: 'border-amber-600/70',
        icon: <AlertTriangle className="w-4 h-4 text-amber-400" />,
        label: 'AT_RISK',
      };
    case 'BLOCKED':
      return {
        bg: 'bg-rose-950/60',
        text: 'text-rose-300',
        border: 'border-rose-600/70',
        icon: <XCircle className="w-4 h-4 text-rose-400" />,
        label: 'BLOCKED',
      };
    case 'UNKNOWN':
    default:
      return {
        bg: 'bg-slate-900/70',
        text: 'text-slate-300',
        border: 'border-slate-700/70',
        icon: <HelpCircle className="w-4 h-4 text-slate-400" />,
        label: 'UNKNOWN',
      };
  }
};

export const ReadinessRiskDetail: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [stateData, setStateData] = useState<DealershipStateResponse | null>(null);
  const [report, setReport] = useState<DealershipReadinessReport | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch canonical state
      const state = await fetchCanonicalState();
      setStateData(state);

      // 2. Fetch readiness report using state rooftop_id and snapshot_hash
      const readinessReport = await fetchPredictReadiness(
        state.rooftop_id,
        state.snapshot_hash
      );
      setReport(readinessReport);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred while communicating with the Predict API.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Stage Header Banner */}
      <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-5 shadow-lg relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
              </span>
              <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider font-mono">
                Stage 2 — API-backed Synthetic Predict Output
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/60 font-semibold">
                Read-Only Prototype
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Readiness & Risk Quantile Detail
            </h2>
            <p className="text-xs text-slate-400 max-w-3xl leading-relaxed">
              Consumes actual outputs from <code className="text-cyan-300 font-mono">PredictReadinessClassifier</code> via{' '}
              <code className="text-cyan-300 font-mono">GET /api/v1/state</code> and{' '}
              <code className="text-cyan-300 font-mono">POST /api/v1/predict/readiness</code>. Evaluates empirical lead-time distributions,
              schedule slacks, and delay probabilities across all active repair orders.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-cyan-950/70 hover:bg-cyan-900/80 text-cyan-300 border border-cyan-800/80 rounded-lg text-xs font-mono font-medium transition-colors disabled:opacity-50"
              title="Re-query Predict API"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Refreshing...' : 'Re-evaluate'}</span>
            </button>
          </div>
        </div>

        {/* Telemetry Context Bar */}
        {stateData && (
          <div className="mt-4 pt-3 border-t border-[#1e2638] flex flex-wrap items-center justify-between gap-3 text-xs font-mono text-slate-400">
            <div className="flex flex-wrap items-center gap-4">
              <span className="text-slate-300">
                <span className="text-slate-500">Rooftop:</span>{' '}
                <span className="text-cyan-300 font-bold">{stateData.rooftop_id}</span>
              </span>
              <span className="text-slate-300">
                <span className="text-slate-500">Snapshot Hash:</span>{' '}
                <span className="text-slate-200" title={stateData.snapshot_hash}>
                  {stateData.snapshot_hash.slice(0, 16)}...
                </span>
              </span>
              <span className="text-slate-300">
                <span className="text-slate-500">Eval Window:</span>{' '}
                <span className="text-emerald-400 font-bold">Tick {stateData.evaluation_tick} (1:15 PM)</span>
              </span>
              <span className="text-slate-300">
                <span className="text-slate-500">Shift End:</span>{' '}
                <span>Tick {stateData.operating_day_end_tick} (5:00 PM)</span>
              </span>
            </div>

            <div className="text-[11px] text-amber-400/90 flex items-center gap-1.5 font-sans">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
              <span>Synthetic demonstration data &bull; No live DMS integration</span>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-[#111522] border border-[#1e2638] rounded-xl p-12 text-center space-y-4">
          <div className="inline-flex p-3 rounded-xl bg-cyan-950/60 border border-cyan-800/40 text-cyan-400 animate-pulse">
            <Activity className="w-8 h-8 animate-spin" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">
              Querying Predict Readiness Service
            </h3>
            <p className="text-xs text-slate-400 font-mono">
              Connecting to FastAPI backend at http://127.0.0.1:8000/api/v1/predict/readiness...
            </p>
          </div>
        </div>
      )}

      {/* API Offline / Error State */}
      {!loading && error && (
        <div className="bg-[#191016] border border-rose-900/60 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-400 shrink-0">
              <Server className="w-6 h-6" />
            </div>
            <div className="space-y-1 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-rose-200">
                  FastAPI Predict Service Offline or Unreachable
                </h3>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                  Connection Error
                </span>
              </div>
              <p className="text-xs text-rose-300/90 font-mono">
                {error}
              </p>
              <p className="text-xs text-slate-400 pt-1">
                The Stage 2 screen requires the read-only FastAPI service to calculate and return live classifier results.
              </p>
            </div>
          </div>

          <div className="bg-[#0b0e17] border border-[#1e2638] rounded-lg p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 font-mono">
              <Terminal className="w-4 h-4 text-cyan-400" />
              <span>To start the backend service:</span>
            </div>
            <div className="bg-black/50 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-cyan-300 select-all">
              cd backend ; uvicorn app.api.main:app --reload --port 8000
            </div>
            <p className="text-[11px] text-slate-500">
              Ensure the backend is running on port 8000. Once started, click below to establish connection.
            </p>
          </div>

          <div className="flex justify-end">
            <button
              onClick={loadData}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-lg shadow-rose-950/50"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry API Connection</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Readiness Data Display */}
      {!loading && !error && report && (
        <>
          {/* Summary Cards of Four Readiness States */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Ready */}
            <div className="bg-[#111522] border border-emerald-900/40 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider font-mono">
                  READY
                </span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono text-emerald-300">
                  {report.summary_counts['READY'] ?? 0}
                </span>
                <span className="text-xs text-slate-400 font-mono">Active ROs</span>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400 leading-tight">
                Slack &ge; 30 min, parts verified usable, all hard operational constraints satisfied.
              </p>
            </div>

            {/* At Risk */}
            <div className="bg-[#111522] border border-amber-900/40 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider font-mono">
                  AT_RISK
                </span>
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono text-amber-300">
                  {report.summary_counts['AT_RISK'] ?? 0}
                </span>
                <span className="text-xs text-slate-400 font-mono">Anchor: RO-104</span>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400 leading-tight">
                Slack &lt; 30 min or in-transit parts risk. Baseline delay recoverable via alternative offer.
              </p>
            </div>

            {/* Blocked */}
            <div className="bg-[#111522] border border-rose-900/40 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-rose-400 uppercase tracking-wider font-mono">
                  BLOCKED
                </span>
                <XCircle className="w-4 h-4 text-rose-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono text-rose-300">
                  {report.summary_counts['BLOCKED'] ?? 0}
                </span>
                <span className="text-xs text-slate-400 font-mono">Anchor: RO-105</span>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400 leading-tight">
                Hard operational blocker. Part backordered nationally with no ETA or supplier quote.
              </p>
            </div>

            {/* Unknown */}
            <div className="bg-[#111522] border border-slate-800 rounded-xl p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">
                  UNKNOWN
                </span>
                <HelpCircle className="w-4 h-4 text-slate-400" />
              </div>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-bold font-mono text-slate-300">
                  {report.summary_counts['UNKNOWN'] ?? 0}
                </span>
                <span className="text-xs text-slate-400 font-mono">Fails Closed</span>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400 leading-tight">
                Missing, stale, or unconfirmed telemetry. Fail-closed safety gate prevents invalid dispatch.
              </p>
            </div>
          </div>

          {/* Assessment Detail Table */}
          <div className="bg-[#111522] border border-[#1e2638] rounded-xl overflow-hidden shadow-lg">
            <div className="px-5 py-4 border-b border-[#1e2638] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-[#0d111a]/60">
              <div>
                <h3 className="text-base font-semibold text-white tracking-tight flex items-center gap-2">
                  <span>Repair Order Predictive Assessments</span>
                  <span className="text-xs font-mono font-medium px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                    {report.assessments.length} API Records
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Actual quantiles, delay probabilities, and schedule buffers computed by the Empirical-Bayes engine.
                </p>
              </div>
              <div className="text-xs font-mono text-slate-400">
                Evaluation Ref: <span className="text-white">Tick 159 (1:15 PM)</span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[#1e2638] bg-[#0c0f18] text-[11px] font-mono uppercase tracking-wider text-slate-400">
                    <th className="py-3 px-4 font-semibold">RO ID</th>
                    <th className="py-3 px-4 font-semibold text-center">Readiness State</th>
                    <th className="py-3 px-4 font-semibold text-center">Delay Prob P(delay)</th>
                    <th className="py-3 px-4 font-semibold">Usable-Ready Quantiles</th>
                    <th className="py-3 px-4 font-semibold">Operational Slack Buffer</th>
                    <th className="py-3 px-4 font-semibold">Diagnostic Reason Codes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#182030]">
                  {report.assessments.map((a: RepairOrderAssessment) => {
                    const badge = getStatusBadge(a.state);
                    const calibrationLabel = a.calibration || a.calibration_status || 'UNCALIBRATED';

                    return (
                      <tr key={a.ro_id} className="hover:bg-[#151b2a] transition-colors">
                        {/* RO ID */}
                        <td className="py-4 px-4 font-mono font-bold text-white whitespace-nowrap align-top">
                          <span className="text-cyan-400">{a.ro_id}</span>
                          <div className="text-[10px] text-slate-500 font-normal">
                            Calib: {calibrationLabel}
                          </div>
                        </td>

                        {/* State */}
                        <td className="py-4 px-4 whitespace-nowrap text-center align-top">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-bold border shadow-sm ${badge.bg} ${badge.text} ${badge.border}`}
                          >
                            {badge.icon}
                            <span>{badge.label}</span>
                          </span>
                        </td>

                        {/* Delay Prob */}
                        <td className="py-4 px-4 whitespace-nowrap text-center align-top">
                          <div className="font-mono text-sm font-bold text-white">
                            {(a.p_delay * 100).toFixed(0)}%
                          </div>
                          <div className="w-16 h-1.5 bg-slate-800 rounded-full mx-auto mt-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                a.p_delay > 0.5 ? 'bg-rose-500' : a.p_delay > 0.2 ? 'bg-amber-400' : 'bg-emerald-500'
                              }`}
                              style={{ width: `${Math.max(5, a.p_delay * 100)}%` }}
                            />
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                            P(delay) = {a.p_delay.toFixed(2)}
                          </div>
                        </td>

                        {/* Quantiles */}
                        <td className="py-4 px-4 align-top whitespace-nowrap">
                          {a.usable_ready_ticks ? (
                            <div className="space-y-1 font-mono text-xs">
                              <div className="flex items-center justify-between gap-3 text-slate-400">
                                <span className="text-[11px]">P10:</span>
                                <span className="text-slate-200">Tick {a.usable_ready_ticks.p10}</span>
                              </div>
                              <div className="flex items-center justify-between gap-3 text-cyan-300 font-semibold bg-cyan-950/40 px-1.5 py-0.5 rounded border border-cyan-800/40">
                                <span className="text-[11px]">P50 (Median):</span>
                                <span>Tick {a.usable_ready_ticks.p50}</span>
                              </div>
                              <div className="flex items-center justify-between gap-3 text-slate-400">
                                <span className="text-[11px]">P90:</span>
                                <span className="text-slate-200">Tick {a.usable_ready_ticks.p90}</span>
                              </div>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-500 italic font-mono">
                              No part intervals (N/A)
                            </span>
                          )}
                        </td>

                        {/* Slack */}
                        <td className="py-4 px-4 align-top">
                          {a.slack ? (
                            <div className="space-y-1 text-xs font-mono">
                              <div className="flex items-center gap-2">
                                <span className="text-slate-400">Buffer:</span>
                                <span
                                  className={`font-bold ${
                                    (a.slack.slack_minutes ?? 0) < 0
                                      ? 'text-rose-400'
                                      : (a.slack.slack_minutes ?? 0) < 30
                                      ? 'text-amber-400'
                                      : 'text-emerald-400'
                                  }`}
                                >
                                  {a.slack.slack_minutes !== undefined && a.slack.slack_minutes !== null
                                    ? `${a.slack.slack_minutes > 0 ? '+' : ''}${a.slack.slack_minutes} min`
                                    : 'N/A'}
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-400">
                                LFS: Tick {a.slack.latest_feasible_start_tick}
                                {a.slack.usable_ready_tick !== null && a.slack.usable_ready_tick !== undefined
                                  ? ` • Ready: Tick ${a.slack.usable_ready_tick}`
                                  : ''}
                              </div>

                              {/* Recovery Offer Note */}
                              {a.has_recovery_alternative && (
                                <div className="mt-1.5 p-1.5 rounded bg-emerald-950/50 border border-emerald-700/60 text-[10px] text-emerald-300">
                                  <div className="font-semibold flex items-center gap-1">
                                    <ArrowUpRight className="w-3 h-3 text-emerald-400" />
                                    <span>Hotshot S1 Recovery Offer</span>
                                  </div>
                                  <div className="text-slate-300">
                                    Usable Tick: {a.best_alternative_usable_tick} &bull; Recovered Slack: +
                                    {a.best_alternative_slack_minutes} min
                                  </div>
                                </div>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-slate-500 italic font-mono">
                              No slack computed
                            </span>
                          )}
                        </td>

                        {/* Diagnostic Reasons */}
                        <td className="py-4 px-4 align-top max-w-xs xl:max-w-md">
                          <div className="flex flex-wrap gap-1">
                            {a.reasons.length > 0 ? (
                              a.reasons.map((reason, idx) => {
                                const isWarning =
                                  reason.includes('NEGATIVE') ||
                                  reason.includes('DELAY') ||
                                  reason.includes('BACKORDER') ||
                                  reason.includes('STALLED');
                                return (
                                  <span
                                    key={idx}
                                    className={`inline-block px-2 py-0.5 rounded text-[10px] font-mono ${
                                      isWarning
                                        ? 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
                                        : 'bg-slate-800 text-slate-300 border border-slate-700'
                                    }`}
                                  >
                                    {reason}
                                  </span>
                                );
                              })
                            ) : (
                              <span className="text-xs text-slate-500 italic font-mono">
                                None recorded
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Table Footer */}
            <div className="px-5 py-3 border-t border-[#1e2638] bg-[#0c0f18] text-xs text-slate-400 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div className="font-mono text-[11px] text-slate-400">
                Predict Layer 1 API Source: POST /api/v1/predict/readiness &bull; Snapshot: {report.snapshot_hash.slice(0, 16)}...
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Fixed Reference Evaluation: 1:15 PM UTC (Tick 159) &bull; Static Synthetic Snapshot
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

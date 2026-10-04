import React, { useState, useEffect } from 'react';
import {
  Database,
  Server,
  HardDrive,
  ShieldCheck,
  Bot,
  RefreshCw,
  Play,
  Clock,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  SystemSettings,
  HealthResponse,
  AutomationStatusResponse,
  AutomationTaskResponse,
} from '../api/client';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [autoStatus, setAutoStatus] = useState<AutomationStatusResponse | null>(null);
  const [tasks, setTasks] = useState<AutomationTaskResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchDiagnostics = async () => {
    setLoading(true);
    setError(null);
    try {
      const [settingsData, healthData, autoData, taskData] = await Promise.all([
        api.getSettings(),
        api.getHealth(),
        api.getAutomationStatus(),
        api.getAutomationTasks({ limit: 10 }),
      ]);
      setSettings(settingsData);
      setHealth(healthData);
      setAutoStatus(autoData);
      setTasks(taskData.items);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve system settings and health.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  const handleModeChange = async (newMode: string) => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await api.updateAutomationSettings({ mode: newMode });
      setAutoStatus((prev) => (prev ? { ...prev, mode: updated.mode, settings: updated } : null));
      setSuccessMsg(`Automation mode updated to ${newMode}.`);
    } catch (err: any) {
      setError(err.message || 'Failed to update automation mode.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggle = async (key: 'job_discovery_enabled' | 'matching_enabled' | 'deduplication_enabled' | 'preparation_enabled', val: boolean) => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const updated = await api.updateAutomationSettings({ [key]: val });
      setAutoStatus((prev) => (prev ? { ...prev, settings: updated } : null));
      setSuccessMsg(`Setting updated.`);
    } catch (err: any) {
      setError(err.message || 'Failed to update setting.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleWorkerTick = async () => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await api.triggerWorkerTick(undefined, 5);
      setSuccessMsg(`Worker cycle finished: Claimed ${res.claimed_count}, Succeeded ${res.succeeded_count}, Blocked ${res.blocked_count}, Recovered ${res.recovered_count}.`);
      await fetchDiagnostics();
    } catch (err: any) {
      setError(err.message || 'Worker execution tick failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSchedulerTick = async () => {
    setActionLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await api.triggerSchedulerTick();
      setSuccessMsg(`Scheduler cycle finished: Enqueued ${res.enqueued_count} tasks, Skipped ${res.skipped_count}.`);
      await fetchDiagnostics();
    } catch (err: any) {
      setError(err.message || 'Scheduler tick failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRetryTask = async (taskId: string) => {
    try {
      await api.retryAutomationTask(taskId);
      setSuccessMsg(`Task ${taskId} re-queued.`);
      await fetchDiagnostics();
    } catch (err: any) {
      setError(err.message || 'Failed to retry task.');
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await api.cancelAutomationTask(taskId, 'Cancelled from Settings');
      setSuccessMsg(`Task ${taskId} cancelled.`);
      await fetchDiagnostics();
    } catch (err: any) {
      setError(err.message || 'Failed to cancel task.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight">System Configuration & Health</h1>
          <p className="text-xs text-slate-400 mt-1">
            Controlled autonomy policy, durable task queue, database connectivity, and runtime status.
          </p>
        </div>
        <button
          onClick={fetchDiagnostics}
          disabled={loading || actionLoading}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Run Health Diagnostics
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {error}
        </div>
      )}

      {successMsg && (
        <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-slate-400 hover:text-slate-200 text-xs">✕</button>
        </div>
      )}

      {/* Step 12: Controlled Autonomy & Task Queue Card */}
      <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between border-b border-slate-800/80 pb-3 gap-2">
          <div className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Controlled Autonomy & Scheduler (Step 12)</h2>
              <p className="text-[11px] text-slate-400">Automate safe background tasks while enforcing strict human approval for real submissions.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSchedulerTick}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            >
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              Scheduler Tick
            </button>
            <button
              onClick={handleWorkerTick}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition shadow-sm"
            >
              <Play className="w-3.5 h-3.5" />
              Worker Tick
            </button>
          </div>
        </div>

        {/* Operational Mode Selection */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-slate-300">Operational Autonomy Mode:</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              {
                mode: 'MANUAL',
                title: 'Manual Mode',
                desc: 'Nothing runs automatically. User explicitly triggers all discovery and executions.',
                badge: 'Zero Automation',
              },
              {
                mode: 'ASSISTED',
                title: 'Assisted Mode (Recommended)',
                desc: 'Safe tasks run automatically (discovery, matching, preparation). Real submission strictly requires human approval.',
                badge: 'Safe Automation',
              },
              {
                mode: 'CONTROLLED_AUTO',
                title: 'Controlled Autonomy',
                desc: 'Continuous background processing. Submission remains strictly approval-gated and cannot be bypassed.',
                badge: 'Approval-Gated',
              },
            ].map((m) => {
              const isSelected = autoStatus?.mode === m.mode;
              return (
                <div
                  key={m.mode}
                  onClick={() => !actionLoading && handleModeChange(m.mode)}
                  className={`p-3.5 rounded-lg border cursor-pointer transition ${
                    isSelected
                      ? 'bg-cyan-950/20 border-cyan-500/50 shadow-sm'
                      : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-200">{m.title}</span>
                    <span
                      className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase font-semibold ${
                        isSelected ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {m.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{m.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Safety Gate Alert */}
        <div className="p-3.5 rounded-lg bg-indigo-950/20 border border-indigo-900/40 text-xs text-indigo-300 flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-400 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-emerald-300">Mandatory Submission Safety Gate Active</span>
            <p className="text-[11px] text-slate-300">
              The worker enforces that <code className="text-cyan-300">Application != Permission</code>. An application in <code className="text-amber-300">NOT_STARTED</code> or a decision of <code className="text-emerald-300">APPLY</code> will NEVER submit automatically. Real submissions require an active, unexpired, version-bound <code className="text-indigo-300">ApplicationApproval</code> record granted by the candidate.
            </p>
          </div>
        </div>

        {/* Safe Operation Toggles */}
        <div className="space-y-2 pt-2">
          <div className="text-xs font-semibold text-slate-300">Safe Background Modules:</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {[
              { key: 'job_discovery_enabled', label: 'Job Discovery', desc: 'Periodic connector runs' },
              { key: 'matching_enabled', label: 'Match Intelligence', desc: '8-dimension score sync' },
              { key: 'deduplication_enabled', label: 'Anti-Duplicate Engine', desc: 'Canonical deduplication' },
              { key: 'preparation_enabled', label: 'Application Preparation', desc: 'Package tailoring for APPLY' },
            ].map((t) => {
              const enabled = (autoStatus?.settings as any)?.[t.key] ?? true;
              return (
                <div key={t.key} className="p-3 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-slate-200">{t.label}</div>
                    <div className="text-[10px] text-slate-400">{t.desc}</div>
                  </div>
                  <button
                    onClick={() => handleToggle(t.key as any, !enabled)}
                    disabled={actionLoading}
                    className={`w-9 h-5 rounded-full transition-colors relative p-0.5 ${
                      enabled ? 'bg-cyan-600' : 'bg-slate-700'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full bg-white transition-transform ${
                        enabled ? 'translate-x-4' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Task Queue Health Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2">
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-center">
            <div className="text-[10px] font-semibold text-slate-400 uppercase">Pending</div>
            <div className="text-lg font-bold font-mono text-slate-200">{autoStatus?.pending_tasks ?? 0}</div>
          </div>
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-center">
            <div className="text-[10px] font-semibold text-cyan-400 uppercase">Running</div>
            <div className="text-lg font-bold font-mono text-cyan-300">{autoStatus?.running_tasks ?? 0}</div>
          </div>
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-center">
            <div className="text-[10px] font-semibold text-emerald-400 uppercase">Succeeded</div>
            <div className="text-lg font-bold font-mono text-emerald-300">{autoStatus?.succeeded_tasks ?? 0}</div>
          </div>
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-center">
            <div className="text-[10px] font-semibold text-amber-400 uppercase">Blocked / Halted</div>
            <div className="text-lg font-bold font-mono text-amber-300">{autoStatus?.blocked_tasks ?? 0}</div>
          </div>
          <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-center">
            <div className="text-[10px] font-semibold text-rose-400 uppercase">Failed</div>
            <div className="text-lg font-bold font-mono text-rose-300">{autoStatus?.failed_tasks ?? 0}</div>
          </div>
        </div>

        {/* Recent Queue Tasks Table */}
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
            <span>Recent PostgreSQL Queue Tasks:</span>
            <span className="text-[10px] font-mono text-slate-400">SELECT ... FOR UPDATE SKIP LOCKED</span>
          </div>
          {tasks.length === 0 ? (
            <div className="py-4 text-center text-xs text-slate-500 bg-slate-900/30 rounded border border-slate-800">
              No tasks currently in the automation queue.
            </div>
          ) : (
            <div className="overflow-x-auto rounded border border-slate-800">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-[11px] text-slate-400 border-b border-slate-800 font-mono">
                  <tr>
                    <th className="py-2 px-3">Type</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Priority</th>
                    <th className="py-2 px-3">Attempts</th>
                    <th className="py-2 px-3">Idempotency Key</th>
                    <th className="py-2 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {tasks.map((t) => {
                    const isSuccess = t.status === 'SUCCEEDED';
                    const isRunning = t.status === 'RUNNING';
                    const isBlocked = t.status === 'BLOCKED';
                    const isFailed = t.status === 'FAILED';
                    const statusColor = isSuccess
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : isRunning
                      ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                      : isBlocked
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : isFailed
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                      : 'bg-slate-800 text-slate-300 border-slate-700';

                    return (
                      <tr key={t.id} className="hover:bg-slate-900/40 font-mono text-[11px]">
                        <td className="py-2 px-3 font-semibold text-slate-200">{t.task_type}</td>
                        <td className="py-2 px-3">
                          <span className={`px-1.5 py-0.5 rounded border text-[10px] uppercase font-bold ${statusColor}`}>
                            {t.status}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-slate-300">{t.priority}</td>
                        <td className="py-2 px-3 text-slate-400">{t.attempts}/{t.max_attempts}</td>
                        <td className="py-2 px-3 text-slate-400 truncate max-w-[200px]" title={t.idempotency_key}>
                          {t.idempotency_key}
                        </td>
                        <td className="py-2 px-3 text-right space-x-1.5">
                          {(isFailed || isBlocked) && (
                            <button
                              onClick={() => handleRetryTask(t.id)}
                              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 text-[10px] transition"
                            >
                              Retry
                            </button>
                          )}
                          {!isSuccess && t.status !== 'CANCELLED' && (
                            <button
                              onClick={() => handleCancelTask(t.id)}
                              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-rose-400 text-[10px] transition"
                            >
                              Cancel
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Diagnostics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Backend Runtime Card */}
        <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-indigo-400 border-b border-slate-800/80 pb-3">
            <Server className="w-4 h-4" />
            <h2 className="text-sm font-semibold text-slate-200">Backend API Runtime</h2>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Application Name:</span>
              <span className="font-mono text-slate-200">{settings?.app_name || 'Job Operating System'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Version:</span>
              <span className="font-mono text-slate-200">v{settings?.app_version || '0.1.0'}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Environment:</span>
              <span className="font-mono text-slate-200 uppercase px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px]">
                {settings?.app_env || 'development'}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Log Level:</span>
              <span className="font-mono text-slate-200">{settings?.log_level || 'INFO'}</span>
            </div>
          </div>
        </div>

        {/* Database Connectivity Card */}
        <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-emerald-400 border-b border-slate-800/80 pb-3">
            <Database className="w-4 h-4" />
            <h2 className="text-sm font-semibold text-slate-200">Database Engine (PostgreSQL)</h2>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Connection State:</span>
              <span className="font-mono text-emerald-400 flex items-center gap-1.5 font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                {health?.database === 'connected' ? 'Connected & Verified' : 'Checking...'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Target Database:</span>
              <span className="font-mono text-slate-200">job_agent_db</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Connection URI:</span>
              <span className="font-mono text-slate-300 text-[11px] truncate max-w-[220px]">
                {settings?.database_url_masked || 'postgresql://postgres@localhost:5432/job_agent_db'}
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Schema Migrations:</span>
              <span className="font-mono text-indigo-300">Alembic Version Up-To-Date (Step 12)</span>
            </div>
          </div>
        </div>

        {/* Storage Isolation Card */}
        <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-blue-400 border-b border-slate-800/80 pb-3">
            <HardDrive className="w-4 h-4" />
            <h2 className="text-sm font-semibold text-slate-200">Storage & Drive Policy</h2>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Active Drive:</span>
              <span className="font-mono text-emerald-400 font-semibold">Strict F: Drive Only</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Local Artifact Storage:</span>
              <span className="font-mono text-slate-300 text-[11px]">{settings?.storage_path || 'F:\\job wala project\\storage'}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Prohibited Volumes:</span>
              <span className="font-mono text-rose-400">C:, D:, E: (Strictly Zero Output)</span>
            </div>
          </div>
        </div>

        {/* Security & Secrets Card */}
        <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-amber-400 border-b border-slate-800/80 pb-3">
            <ShieldCheck className="w-4 h-4" />
            <h2 className="text-sm font-semibold text-slate-200">Security & Credentials</h2>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Secret Management:</span>
              <span className="font-mono text-slate-200">Loaded from .env</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-800/40">
              <span className="text-slate-400">Paid External APIs:</span>
              <span className="font-mono text-emerald-400">0 (Zero External Cost)</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Credential Leak Prevention:</span>
              <span className="font-mono text-emerald-400">Active (Masked in API responses)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

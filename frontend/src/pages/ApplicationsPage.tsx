import React, { useState, useEffect } from 'react';
import {
  FileText,
  RefreshCw,
  Target,
  CheckCircle2,
  Building2,
  MapPin,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Play,
  History,
  TrendingUp,
} from 'lucide-react';
import { api } from '../api/client';
import type { ApplicationItem, JobItem } from '../api/client';
import { ApplicationPreparationModal } from '../components/ApplicationPreparationModal';
import { ApplicationExecutionModal } from '../components/ApplicationExecutionModal';
import { ApplicationMemoryModal } from '../components/ApplicationMemoryModal';
import { ApplicationFeedbackDashboard } from '../components/ApplicationFeedbackDashboard';

export const ApplicationsPage: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [applyQueueJobs, setApplyQueueJobs] = useState<JobItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Main Page Tab: 'applications' or 'analytics'
  const [mainTab, setMainTab] = useState<'applications' | 'analytics'>('applications');

  // Preparation Modal State
  const [showPrepModal, setShowPrepModal] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | undefined>(undefined);
  const [selectedAppId, setSelectedAppId] = useState<string | undefined>(undefined);

  // Step 9 Execution Modal State
  const [showExecModal, setShowExecModal] = useState(false);
  const [execAppId, setExecAppId] = useState<string | undefined>(undefined);
  const [execJobId, setExecJobId] = useState<string | undefined>(undefined);
  const [execJobTitle, setExecJobTitle] = useState<string | undefined>(undefined);
  const [execCompany, setExecCompany] = useState<string | undefined>(undefined);
  const [execJobUrl, setExecJobUrl] = useState<string | undefined>(undefined);

  // Step 10 Memory Modal State
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [memoryAppId, setMemoryAppId] = useState<string | undefined>(undefined);


  const fetchApplications = async () => {
    setLoading(true);
    setError(null);
    try {
      const [appData, jobsData] = await Promise.all([
        api.getApplications(),
        api.getJobs({ decision: 'APPLY', limit: 12 }),
      ]);
      setApplications(appData.items);
      setTotal(appData.total);
      setApplyQueueJobs(jobsData.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const handleOpenJobPreparation = (jobId: string) => {
    setSelectedJobId(jobId);
    setSelectedAppId(undefined);
    setShowPrepModal(true);
  };

  const handleOpenAppPreparation = (appId: string) => {
    setSelectedAppId(appId);
    setSelectedJobId(undefined);
    setShowPrepModal(true);
  };

  const handleOpenAppExecution = (app: ApplicationItem) => {
    setExecAppId(app.id);
    setExecJobId(app.job_id || undefined);
    setExecJobTitle('Application Execution');
    setExecCompany(app.source || 'Target Employer');
    setExecJobUrl(app.application_url || undefined);
    setShowExecModal(true);
  };

  const handleOpenJobExecution = (job: JobItem) => {
    setExecJobId(job.id);
    setExecAppId(undefined);
    setExecJobTitle(job.title);
    setExecCompany(job.company);
    setExecJobUrl(job.application_url || undefined);
    setShowExecModal(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-slate-100 tracking-tight">Applications & Career Memory</h1>
          <p className="text-xs text-slate-400 mt-1">
            Track submission states, generate tailor packages, review chronological timelines, and analyze career feedback. Total tracked: {total}
          </p>
        </div>
        <button
          onClick={fetchApplications}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Main View Tab Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setMainTab('applications')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
            mainTab === 'applications'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Pipeline & Submissions ({applications.length})
        </button>
        <button
          onClick={() => setMainTab('analytics')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
            mainTab === 'analytics'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
          }`}
        >
          <TrendingUp className="w-3.5 h-3.5" />
          Memory & Feedback Analytics
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          {error}
        </div>
      )}

      {/* VIEW 1: Applications Pipeline */}
      {mainTab === 'applications' ? (
        <div className="space-y-6">
          {/* Decision Engine Apply Queue */}
          {applyQueueJobs.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-emerald-400" />
                  <h2 className="text-sm font-bold text-slate-100">
                    Application Decision Engine: Ready to Prepare ({applyQueueJobs.length})
                  </h2>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  Deterministic Step 7 decisions ready for Step 8 preparation
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {applyQueueJobs.map((job) => (
                  <div
                    key={job.id}
                    className="p-3.5 rounded-lg bg-[#0e1626] border border-slate-800 hover:border-slate-700 transition space-y-2 text-xs"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="font-semibold text-slate-100 text-sm">{job.title}</h3>
                        <div className="flex items-center gap-2 text-slate-400 mt-0.5">
                          <span className="flex items-center gap-1 font-medium text-slate-300">
                            <Building2 className="w-3 h-3 text-slate-500" />
                            {job.company}
                          </span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-slate-500" />
                            {job.location || 'Remote'}
                          </span>
                        </div>
                      </div>

                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 shrink-0">
                        <CheckCircle2 className="w-3 h-3" />
                        APPLY
                      </span>
                    </div>

                    {job.decision_reason && (
                      <p className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded border border-slate-800/80">
                        {job.decision_reason}
                      </p>
                    )}

                    <div className="flex items-center justify-between pt-2 border-t border-slate-850">
                      <div className="flex items-center gap-3">
                        {job.match_score !== undefined && job.match_score !== null ? (
                          <span className="font-medium text-indigo-300 flex items-center gap-1">
                            <Sparkles className="w-3 h-3 text-indigo-400" />
                            {job.match_score}/100 Match
                          </span>
                        ) : (
                          <span className="text-slate-500 font-mono">Source: {job.source}</span>
                        )}

                        {job.application_url && (
                          <a
                            href={job.application_url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-slate-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                          >
                            Posting <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleOpenJobPreparation(job.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs transition"
                        >
                          <FileText className="w-3.5 h-3.5 text-indigo-400" />
                          Prepare
                        </button>
                        <button
                          onClick={() => handleOpenJobExecution(job)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs shadow-sm shadow-emerald-600/20 transition"
                        >
                          <Play className="w-3.5 h-3.5" />
                          Execute
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Applications Table Section */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h2 className="text-sm font-bold text-slate-100">
                Tracked Applications & Historical Milestones
              </h2>
              <span className="text-[11px] font-mono text-slate-400">
                Full lifecycle memory and provenance
              </span>
            </div>

            {loading ? (
              <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin text-slate-500" />
                <span>Retrieving application records...</span>
              </div>
            ) : applications.length === 0 ? (
              <div className="p-12 rounded-lg bg-[#0e1626] border border-slate-800 text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
                  <FileText className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-slate-200">No application packages created yet.</h2>
                  <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                    Select an APPLY or REVIEW job from the queue above and click "Prepare Package" to generate verified application materials.
                  </p>
                </div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-400">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Step 10 Memory Ready
                </div>
              </div>
            ) : (
              <div className="border border-slate-800 rounded-lg overflow-hidden bg-[#0e1626]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 font-mono text-[11px] uppercase">
                    <tr>
                      <th className="px-4 py-3">Job / Target</th>
                      <th className="px-4 py-3">Lifecycle Stage</th>
                      <th className="px-4 py-3">Notes / Scope</th>
                      <th className="px-4 py-3">Source</th>
                      <th className="px-4 py-3">Last Updated</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80 text-slate-200">
                    {applications.map((app) => (
                      <tr key={app.id} className="hover:bg-slate-900/40 transition">
                        <td className="px-4 py-3 font-semibold text-slate-100">
                          {app.job_id ? (
                            <span className="font-mono text-slate-300">{app.job_id.slice(0, 8)}...</span>
                          ) : (
                            'Direct / Manual'
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-mono capitalize border ${
                            app.lifecycle_stage === 'OFFER' || app.lifecycle_stage === 'ACCEPTED'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : app.lifecycle_stage === 'INTERVIEW' || app.lifecycle_stage === 'SCREENING'
                              ? 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                              : app.lifecycle_stage === 'REJECTED'
                              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                              : app.lifecycle_stage === 'NO_RESPONSE'
                              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                              : 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20'
                          }`}>
                            {app.lifecycle_stage || app.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300 max-w-xs truncate">
                          {app.notes || 'General Application Record'}
                        </td>
                        <td className="px-4 py-3 text-slate-400 font-mono">
                          {app.source || '—'}
                        </td>
                        <td className="px-4 py-3 text-slate-400 font-mono">
                          {new Date(app.updated_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-right space-x-1.5">
                          <button
                            onClick={() => {
                              setMemoryAppId(app.id);
                              setShowMemoryModal(true);
                            }}
                            className="px-2.5 py-1 rounded bg-indigo-950/60 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-850 text-[11px] font-medium transition inline-flex items-center gap-1"
                          >
                            <History className="w-3 h-3 text-indigo-400" />
                            Memory
                          </button>
                          <button
                            onClick={() => handleOpenAppPreparation(app.id)}
                            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-medium transition inline-flex items-center gap-1"
                          >
                            <FileText className="w-3 h-3 text-slate-400" />
                            Package
                          </button>
                          <button
                            onClick={() => handleOpenAppExecution(app)}
                            className="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-semibold transition inline-flex items-center gap-1 shadow-sm"
                          >
                            <Play className="w-3 h-3" />
                            Execute
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* VIEW 2: Feedback & Memory Analytics */
        <ApplicationFeedbackDashboard />
      )}

      {/* Step 8 Preparation Modal */}
      <ApplicationPreparationModal
        jobId={selectedJobId}
        applicationId={selectedAppId}
        isOpen={showPrepModal}
        onClose={() => {
          setShowPrepModal(false);
          setSelectedJobId(undefined);
          setSelectedAppId(undefined);
        }}
        onSuccess={fetchApplications}
      />

      {/* Step 9 Execution Modal */}
      <ApplicationExecutionModal
        applicationId={execAppId}
        jobId={execJobId}
        jobTitle={execJobTitle}
        company={execCompany}
        jobUrl={execJobUrl}
        isOpen={showExecModal}
        onClose={() => {
          setShowExecModal(false);
          setExecAppId(undefined);
          setExecJobId(undefined);
        }}
        onExecutionCompleted={fetchApplications}
      />

      {/* Step 10 Memory Modal */}
      <ApplicationMemoryModal
        applicationId={memoryAppId}
        isOpen={showMemoryModal}
        onClose={() => {
          setShowMemoryModal(false);
          setMemoryAppId(undefined);
        }}
        onUpdated={fetchApplications}
      />
    </div>
  );
};



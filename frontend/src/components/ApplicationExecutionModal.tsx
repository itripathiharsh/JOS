import React, { useState, useEffect } from 'react';
import {
  X,
  Play,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Copy,
  Check,
  RefreshCw,
  ShieldAlert,
  FileText,
  User,
  Clock,
  RotateCcw,
  Ban,
  Send,
  Lock,
} from 'lucide-react';
import { api } from '../api/client';
import type { ApplicationExecutionItem } from '../api/client';

interface ApplicationExecutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  applicationId?: string;
  jobId?: string;
  jobTitle?: string;
  company?: string;
  jobUrl?: string;
  onExecutionCompleted?: () => void;
}

export const ApplicationExecutionModal: React.FC<ApplicationExecutionModalProps> = ({
  isOpen,
  onClose,
  applicationId,
  jobId,
  jobTitle,
  company,
  jobUrl,
  onExecutionCompleted,
}) => {
  const [activeTab, setActiveTab] = useState<'manual_kit' | 'field_mapping' | 'submission_gate' | 'history'>('manual_kit');
  const [execution, setExecution] = useState<ApplicationExecutionItem | null>(null);
  const [history, setHistory] = useState<ApplicationExecutionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Form field edit state
  const [fieldInputs, setFieldInputs] = useState<Record<string, string>>({});
  const [executionMode, setExecutionMode] = useState<'MANUAL' | 'ASSISTED' | 'AUTOMATED'>('MANUAL');

  // Manual submission confirmation modal
  const [confirmationNumber, setConfirmationNumber] = useState<string>('');
  const [submissionNotes, setSubmissionNotes] = useState<string>('');

  const fetchExecutionData = async () => {
    setLoading(true);
    setError(null);
    try {
      let currentExec: ApplicationExecutionItem | null = null;
      if (applicationId) {
        try {
          currentExec = await api.getApplicationExecution(applicationId);
        } catch {
          // May not exist yet
        }
      } else if (jobId) {
        try {
          currentExec = await api.getJobExecution(jobId);
        } catch {
          // May not exist yet
        }
      }

      setExecution(currentExec);
      if (currentExec) {
        setExecutionMode((currentExec.mode as any) || 'MANUAL');
        if (currentExec.mode === 'MANUAL') {
          setActiveTab('manual_kit');
        } else if (currentExec.status === 'READY_TO_SUBMIT') {
          setActiveTab('submission_gate');
        } else {
          setActiveTab('field_mapping');
        }

        // Initialize field values
        if (currentExec.field_mappings) {
          const initialValues: Record<string, string> = {};
          currentExec.field_mappings.forEach((m) => {
            const k = m.form_field.name || m.form_field.field_id;
            initialValues[k] = m.proposed_value != null ? String(m.proposed_value) : '';
          });
          setFieldInputs(initialValues);
        }

        // Fetch execution history if application ID is known
        if (currentExec.application_id) {
          try {
            const histRes = await api.getApplicationExecutions(currentExec.application_id);
            setHistory(histRes.items);
          } catch {
            // non-fatal
          }
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load execution record');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchExecutionData();
    }
  }, [isOpen, applicationId, jobId]);

  const handleStartExecution = async (selectedMode?: 'MANUAL' | 'ASSISTED' | 'AUTOMATED') => {
    setLoading(true);
    setError(null);
    const modeToUse = selectedMode || executionMode;
    try {
      let newExec: ApplicationExecutionItem;
      if (applicationId) {
        newExec = await api.executeApplication(applicationId, {
          mode: modeToUse,
          source: modeToUse === 'MANUAL' ? 'manual' : 'generic_web',
        });
      } else if (jobId) {
        newExec = await api.executeJob(jobId, {
          mode: modeToUse,
          source: modeToUse === 'MANUAL' ? 'manual' : 'generic_web',
        });
      } else {
        throw new Error('Either applicationId or jobId must be provided.');
      }

      setExecution(newExec);
      setExecutionMode(modeToUse);
      if (modeToUse === 'MANUAL') {
        setActiveTab('manual_kit');
      } else {
        setActiveTab(newExec.status === 'READY_TO_SUBMIT' ? 'submission_gate' : 'field_mapping');
      }
      fetchExecutionData();
    } catch (err: any) {
      setError(err.message || 'Failed to start execution');
    } finally {
      setLoading(false);
    }
  };

  const handleResumeConfirmFields = async () => {
    if (!execution) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.resumeApplicationExecution(execution.application_id, execution.id, {
        user_inputs: {
          action: 'confirm_fields',
          field_values: fieldInputs,
        },
      });
      setExecution(updated);
      if (updated.status === 'READY_TO_SUBMIT') {
        setActiveTab('submission_gate');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save confirmed fields');
    } finally {
      setLoading(false);
    }
  };

  const handleManualConfirmSubmit = async () => {
    if (!execution) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.resumeApplicationExecution(execution.application_id, execution.id, {
        user_inputs: {
          action: 'confirm_submitted',
          confirmation_number: confirmationNumber,
          notes: submissionNotes || 'Completed manually by user on employer portal',
        },
      });
      setExecution(updated);
      if (onExecutionCompleted) onExecutionCompleted();
    } catch (err: any) {
      setError(err.message || 'Failed to confirm manual submission');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveAndSubmit = async () => {
    if (!execution) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.approveAndSubmitApplication(execution.application_id, execution.id);
      setExecution(updated);
      if (onExecutionCompleted) onExecutionCompleted();
    } catch (err: any) {
      setError(err.message || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelExecution = async () => {
    if (!execution) return;
    if (!window.confirm('Are you sure you want to cancel this execution attempt?')) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await api.cancelApplicationExecution(execution.application_id, execution.id);
      setExecution(updated);
    } catch (err: any) {
      setError(err.message || 'Failed to cancel execution');
    } finally {
      setLoading(false);
    }
  };

  const handleRetryExecution = async () => {
    if (!execution) return;
    setLoading(true);
    setError(null);
    try {
      const retried = await api.retryApplicationExecution(execution.application_id, execution.id, {
        mode: executionMode,
      });
      setExecution(retried);
      fetchExecutionData();
    } catch (err: any) {
      setError(err.message || 'Failed to retry execution');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  if (!isOpen) return null;

  const targetJobUrl = jobUrl || execution?.browser_metadata?.url || 'https://remotive.com';
  const manualKit = execution?.step_details?.manual_kit;
  const status = execution?.status || 'NOT_STARTED';

  const getStatusBadge = () => {
    switch (status) {
      case 'SUBMITTED':
        return <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5" /> SUBMITTED</span>;
      case 'READY_TO_SUBMIT':
        return <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1.5 animate-pulse"><Check className="w-3.5 h-3.5" /> READY TO SUBMIT</span>;
      case 'AWAITING_USER':
        return <span className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-semibold flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> AWAITING USER</span>;
      case 'BLOCKED':
        return <span className="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 text-xs font-semibold flex items-center gap-1.5"><ShieldAlert className="w-3.5 h-3.5" /> BLOCKED</span>;
      case 'FAILED':
        return <span className="px-2.5 py-1 rounded bg-red-500/20 text-red-300 border border-red-500/40 text-xs font-semibold flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> FAILED</span>;
      case 'CANCELLED':
        return <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700 text-xs font-semibold flex items-center gap-1.5"><Ban className="w-3.5 h-3.5" /> CANCELLED</span>;
      case 'OPENING':
      case 'NAVIGATING':
      case 'FILLING':
      case 'SUBMITTING':
        return <span className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 border border-blue-500/40 text-xs font-semibold flex items-center gap-1.5"><RefreshCw className="w-3.5 h-3.5 animate-spin" /> {status}</span>;
      default:
        return <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold">NOT STARTED</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Play className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100">{jobTitle || 'Application Execution'}</h2>
                <span className="text-xs text-slate-400">@ {company || 'Company'}</span>
                {getStatusBadge()}
                {execution && (
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-slate-400 border border-slate-700">
                    Attempt #{execution.attempt_number}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Controlled application execution layer with deterministic field mapping, bot guards, and strict human approval gate.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchExecutionData}
              disabled={loading}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Execution Mode Selector Bar */}
        <div className="px-6 py-2.5 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-medium">Execution Mode:</span>
            <div className="flex rounded-md bg-slate-900 p-0.5 border border-slate-800">
              {(['MANUAL', 'ASSISTED', 'AUTOMATED'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => {
                    setExecutionMode(m);
                    if (!execution || execution.status === 'NOT_STARTED') {
                      handleStartExecution(m);
                    }
                  }}
                  className={`px-3 py-1 rounded text-xs font-semibold transition ${
                    executionMode === m
                      ? 'bg-emerald-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <span className="text-[11px] text-slate-500">
              {executionMode === 'MANUAL' && 'User completes application manually with prepared answers and resume kit.'}
              {executionMode === 'ASSISTED' && 'Automates safe form fields and halts for human review before submission.'}
              {executionMode === 'AUTOMATED' && 'Controlled pipeline stopping at bot challenges and requiring final human approval.'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {targetJobUrl && (
              <a
                href={targetJobUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 font-medium transition"
              >
                Open Job Portal <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>

        {/* Human Action / Blocker Prompt Callout */}
        {execution?.requires_user_action && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
            <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
            <div className="flex-1">
              <h4 className="text-xs font-bold text-amber-300">Human Action Required</h4>
              <p className="text-xs text-amber-200/90 mt-0.5">{execution.user_action_prompt}</p>
            </div>
            {execution.status === 'READY_TO_SUBMIT' && (
              <button
                onClick={() => setActiveTab('submission_gate')}
                className="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition shadow-sm"
              >
                Go to Approval Gate
              </button>
            )}
          </div>
        )}

        {/* Blocker Callout */}
        {execution?.blocker_reason && (
          <div className="mx-6 mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start gap-3">
            <ShieldAlert className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
            <div className="flex-1">
              <h4 className="text-xs font-bold text-rose-300">Execution Blocked: {execution.blocker_reason}</h4>
              <p className="text-xs text-rose-200/90 mt-0.5">{execution.failure_reason || execution.user_action_prompt}</p>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex items-center border-b border-slate-800 px-6 pt-3 gap-6 bg-slate-900">
          <button
            onClick={() => setActiveTab('manual_kit')}
            className={`pb-2.5 text-xs font-medium border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'manual_kit'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            Manual Application Kit
          </button>
          <button
            onClick={() => setActiveTab('field_mapping')}
            className={`pb-2.5 text-xs font-medium border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'field_mapping'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Form Field Detection ({execution?.field_mappings?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('submission_gate')}
            className={`pb-2.5 text-xs font-medium border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'submission_gate'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Lock className="w-3.5 h-3.5" />
            Human Submission Gate
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`pb-2.5 text-xs font-medium border-b-2 transition flex items-center gap-1.5 ${
              activeTab === 'history'
                ? 'border-emerald-500 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            Attempt History ({history.length})
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
              {error}
            </div>
          )}

          {/* TAB 1: MANUAL APPLICATION KIT */}
          {activeTab === 'manual_kit' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <h3 className="text-sm font-bold text-slate-200">Interactive Manual Kit (Harsh Vardhan Tripathi)</h3>
                  <p className="text-xs text-slate-400">
                    Click copy on any verified field to paste directly into the employer's application form.
                  </p>
                </div>
                {targetJobUrl && (
                  <a
                    href={targetJobUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-2 transition"
                  >
                    Open Application Portal <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>

              {/* Verified Identity Quick-Copy Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {[
                  { label: 'Full Name', value: 'Harsh Vardhan Tripathi', key: 'name' },
                  { label: 'Email', value: 'harsh.tripathi.cs@gmail.com', key: 'email' },
                  { label: 'Phone', value: '+91 95652 49247', key: 'phone' },
                  { label: 'Location', value: 'Lucknow, India', key: 'location' },
                  { label: 'GitHub', value: 'https://github.com/itripathiharsh', key: 'github' },
                  { label: 'LinkedIn', value: 'https://www.linkedin.com/in/iamharshvardhantripathi/', key: 'linkedin' },
                  { label: 'Portfolio', value: 'https://harshtripathi.vercel.app/', key: 'portfolio' },
                  { label: 'Experience Years', value: '2.0 years (verified across 4 roles)', key: 'exp' },
                  { label: 'Education', value: 'B.Tech CSE (BBDITM) & BS Data Science (IIT Madras)', key: 'edu' },
                ].map((item) => (
                  <div key={item.key} className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/60 flex items-center justify-between">
                    <div>
                      <div className="text-[10px] uppercase font-mono text-slate-400 tracking-wider">{item.label}</div>
                      <div className="text-xs text-slate-200 font-medium truncate max-w-[200px]">{item.value}</div>
                    </div>
                    <button
                      onClick={() => copyToClipboard(item.value, item.key)}
                      className="p-1 text-slate-400 hover:text-emerald-400 rounded transition"
                      title="Copy"
                    >
                      {copiedKey === item.key ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                ))}
              </div>

              {/* Master Resume Card */}
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-slate-200">Recommended Master Resume: Harsh_Resume.pdf</div>
                    <div className="text-[11px] font-mono text-slate-400">storage/documents/Harsh_Resume.pdf (Verified on local disk)</div>
                  </div>
                </div>
                <button
                  onClick={() => copyToClipboard('storage/documents/Harsh_Resume.pdf', 'resume_path')}
                  className="px-2.5 py-1 rounded bg-slate-700 hover:bg-slate-600 text-xs text-slate-200 font-medium flex items-center gap-1.5 transition"
                >
                  {copiedKey === 'resume_path' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  Copy Path
                </button>
              </div>

              {/* Tailored Cover Letter / Note */}
              {manualKit?.draft_materials?.cover_letter && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-300">Tailored Cover Letter / Message Draft</span>
                    <button
                      onClick={() => copyToClipboard(manualKit.draft_materials.cover_letter, 'cover_letter')}
                      className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition"
                    >
                      {copiedKey === 'cover_letter' ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      Copy Letter
                    </button>
                  </div>
                  <textarea
                    readOnly
                    value={manualKit.draft_materials.cover_letter}
                    className="w-full h-36 bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-300 font-mono resize-none focus:outline-none"
                  />
                </div>
              )}

              {/* Manual Confirmation Section */}
              <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20 space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-xs font-bold text-slate-200">Finished applying on the portal?</h4>
                </div>
                <p className="text-xs text-slate-400">
                  Enter any reference ID or notes from your submission, then click 'Confirm Manual Submission' to update your application status.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <input
                    type="text"
                    placeholder="Application Ref Number (optional)"
                    value={confirmationNumber}
                    onChange={(e) => setConfirmationNumber(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                  <input
                    type="text"
                    placeholder="Notes (e.g. Applied via Careers Page)"
                    value={submissionNotes}
                    onChange={(e) => setSubmissionNotes(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <button
                  onClick={handleManualConfirmSubmit}
                  disabled={loading || status === 'SUBMITTED'}
                  className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold transition flex items-center gap-2"
                >
                  <Check className="w-4 h-4" />
                  {status === 'SUBMITTED' ? 'Application Confirmed Submitted' : 'Confirm Manual Submission'}
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: FORM FIELD DETECTION & MAPPING */}
          {activeTab === 'field_mapping' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <h3 className="text-sm font-bold text-slate-200">Detected Form Inputs & Confidence Mappings</h3>
                  <p className="text-xs text-slate-400">
                    High-confidence fields are mapped automatically. Sensitive fields require human confirmation before submission.
                  </p>
                </div>
                <button
                  onClick={handleResumeConfirmFields}
                  disabled={loading}
                  className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
                >
                  <Check className="w-3.5 h-3.5" />
                  Save & Confirm Mapped Fields
                </button>
              </div>

              {(!execution?.field_mappings || execution.field_mappings.length === 0) ? (
                <div className="text-center py-8 text-slate-500 text-xs">
                  No automated form fields detected yet. Start Assisted or Automated mode to analyze page.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 font-mono text-[11px] uppercase border-b border-slate-800">
                      <tr>
                        <th className="p-3">Field Label</th>
                        <th className="p-3">Input Type</th>
                        <th className="p-3">Matched Key</th>
                        <th className="p-3">Confidence</th>
                        <th className="p-3">Value</th>
                        <th className="p-3">Human Confirmation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 bg-slate-900/40">
                      {execution.field_mappings.map((m, idx) => {
                        const key = m.form_field.name || m.form_field.field_id;
                        const isSensitive = m.form_field.is_sensitive;
                        return (
                          <tr key={idx} className="hover:bg-slate-800/30 transition">
                            <td className="p-3 font-medium text-slate-200">
                              {m.form_field.label || m.form_field.name}
                              {m.form_field.is_required && <span className="text-rose-400 ml-1">*</span>}
                              {isSensitive && (
                                <span className="ml-2 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-semibold border border-amber-500/40">
                                  Sensitive
                                </span>
                              )}
                            </td>
                            <td className="p-3 font-mono text-slate-400">{m.form_field.input_type}</td>
                            <td className="p-3 font-mono text-emerald-400">{m.matched_key}</td>
                            <td className="p-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                  m.confidence === 'HIGH'
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                    : m.confidence === 'MEDIUM'
                                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                                }`}
                              >
                                {m.confidence}
                              </span>
                            </td>
                            <td className="p-3">
                              <input
                                type="text"
                                value={fieldInputs[key] ?? (m.proposed_value != null ? String(m.proposed_value) : '')}
                                onChange={(e) => setFieldInputs({ ...fieldInputs, [key]: e.target.value })}
                                className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                              />
                            </td>
                            <td className="p-3">
                              {m.requires_human_confirmation ? (
                                <span className="text-amber-400 font-medium flex items-center gap-1">
                                  <AlertTriangle className="w-3.5 h-3.5" /> Requires Confirm
                                </span>
                              ) : (
                                <span className="text-emerald-400 font-medium flex items-center gap-1">
                                  <Check className="w-3.5 h-3.5" /> Auto Safe
                                </span>
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
          )}

          {/* TAB 3: HUMAN SUBMISSION GATE */}
          {activeTab === 'submission_gate' && (
            <div className="space-y-6">
              <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-3">
                <div className="flex items-center gap-2">
                  <Lock className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-sm font-bold text-slate-200">Critical Human Submission Gate</h3>
                </div>
                <p className="text-xs text-slate-400">
                  This safety gate prevents unauthorized or automatic submissions.
                  The application will only be dispatched when you explicitly click 'Approve & Submit'.
                </p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 text-xs">
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-mono text-[10px] block">JOB & COMPANY</span>
                    <span className="text-slate-200 font-semibold">{jobTitle} @ {company}</span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-mono text-[10px] block">RESUME USED</span>
                    <span className="text-slate-200 font-semibold">Harsh_Resume.pdf</span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-mono text-[10px] block">TOTAL FIELDS</span>
                    <span className="text-slate-200 font-semibold">{execution?.field_mappings?.length || 0} mapped</span>
                  </div>
                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-mono text-[10px] block">STATE STATUS</span>
                    <span className="text-emerald-400 font-semibold">{status}</span>
                  </div>
                </div>
              </div>

              {/* Submission Evidence Preview if already submitted */}
              {execution?.submission_confirmed && execution.confirmation_evidence && (
                <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 space-y-2">
                  <div className="flex items-center gap-2 text-emerald-300 font-bold text-xs">
                    <CheckCircle2 className="w-4 h-4" /> Submission Confirmed by Observable Evidence
                  </div>
                  <div className="text-xs font-mono text-emerald-200/90">
                    Evidence Type: {execution.confirmation_evidence.evidence_type}
                    {execution.confirmation_evidence.confirmation_number && ` | Ref: ${execution.confirmation_evidence.confirmation_number}`}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleCancelExecution}
                    disabled={loading || status === 'SUBMITTED' || status === 'CANCELLED'}
                    className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition"
                  >
                    Cancel Execution
                  </button>
                  <button
                    onClick={handleRetryExecution}
                    disabled={loading}
                    className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" /> Retry Attempt
                  </button>
                </div>

                <button
                  onClick={handleApproveAndSubmit}
                  disabled={loading || status !== 'READY_TO_SUBMIT'}
                  className="px-6 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold flex items-center gap-2 transition shadow-lg shadow-emerald-900/30"
                >
                  <Send className="w-4 h-4" />
                  Approve & Submit Application
                </button>
              </div>
            </div>
          )}

          {/* TAB 4: ATTEMPT HISTORY */}
          {activeTab === 'history' && (
            <div className="space-y-4">
              <h3 className="text-sm font-bold text-slate-200">Execution Attempt Audit Log</h3>
              {history.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-xs">No prior attempts recorded for this application.</div>
              ) : (
                <div className="space-y-3">
                  {history.map((h) => (
                    <div key={h.id} className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-200">Attempt #{h.attempt_number}</span>
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 font-mono">{h.mode}</span>
                          <span className="text-[11px] text-emerald-400 font-semibold">{h.status}</span>
                        </div>
                        <p className="text-slate-400 text-[11px]">{h.current_step || 'Execution record'}</p>
                      </div>
                      <div className="text-right text-[11px] text-slate-500 font-mono">
                        Started: {new Date(h.started_at).toLocaleTimeString()}
                        {h.completed_at && <div>Completed: {new Date(h.completed_at).toLocaleTimeString()}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

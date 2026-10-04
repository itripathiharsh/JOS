import React, { useState, useEffect } from 'react';
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  User,
  Building2,
  Sparkles,
  MessageSquare,
  ShieldCheck,
  X,
  Plus,
  RefreshCw,
  Layers,
  History,
} from 'lucide-react';
import { api } from '../api/client';
import type { ApplicationMemoryItem } from '../api/client';


interface ApplicationMemoryModalProps {
  applicationId?: string;
  isOpen: boolean;
  onClose: () => void;
  onUpdated?: () => void;
}

export const ApplicationMemoryModal: React.FC<ApplicationMemoryModalProps> = ({
  applicationId,
  isOpen,
  onClose,
  onUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<'timeline' | 'outcome' | 'snapshots' | 'notes'>('timeline');
  const [memory, setMemory] = useState<ApplicationMemoryItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Outcome Form State
  const [selectedStage, setSelectedStage] = useState<string>('SUBMITTED');
  const [selectedProvenance, setSelectedProvenance] = useState<string>('USER_CONFIRMED');
  const [selectedRejectionCat, setSelectedRejectionCat] = useState<string>('unknown');
  const [rejectionReasonText, setRejectionReasonText] = useState<string>('');
  const [outcomeNotes, setOutcomeNotes] = useState<string>('');
  const [submittingOutcome, setSubmittingOutcome] = useState(false);

  // Note Form State
  const [noteContent, setNoteContent] = useState('');
  const [noteCategory, setNoteCategory] = useState('general');
  const [submittingNote, setSubmittingNote] = useState(false);

  // Override Form State
  const [overrideDecision, setOverrideDecision] = useState('APPLY');
  const [overrideReason, setOverrideReason] = useState('');
  const [submittingOverride, setSubmittingOverride] = useState(false);

  const fetchMemory = async () => {
    if (!applicationId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getApplicationMemory(applicationId);
      setMemory(data);
      setSelectedStage(data.lifecycle_stage || 'SUBMITTED');
      setSelectedProvenance(data.outcome_provenance || 'USER_CONFIRMED');
      if (data.rejection_category) setSelectedRejectionCat(data.rejection_category);
      if (data.rejection_reason) setRejectionReasonText(data.rejection_reason);
    } catch (err: any) {
      setError(err.message || 'Failed to load application memory.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && applicationId) {
      fetchMemory();
    } else {
      setMemory(null);
      setError(null);
      setActionSuccess(null);
    }
  }, [isOpen, applicationId]);

  if (!isOpen || !applicationId) return null;

  const handleUpdateOutcome = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!applicationId) return;
    setSubmittingOutcome(true);
    setError(null);
    setActionSuccess(null);
    try {
      const updated = await api.updateApplicationOutcome(applicationId, {
        lifecycle_stage: selectedStage,
        provenance: selectedProvenance,
        rejection_category: selectedStage === 'REJECTED' ? selectedRejectionCat : undefined,
        rejection_reason: selectedStage === 'REJECTED' ? rejectionReasonText : undefined,
        notes: outcomeNotes || undefined,
      });
      setMemory(updated);
      setActionSuccess(`Lifecycle stage updated to ${selectedStage} successfully.`);
      if (onUpdated) onUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to update outcome.');
    } finally {
      setSubmittingOutcome(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!applicationId || !noteContent.trim()) return;
    setSubmittingNote(true);
    setError(null);
    try {
      await api.addApplicationNote(applicationId, {
        content: noteContent.trim(),
        category: noteCategory,
        author: 'candidate',
      });
      setNoteContent('');
      await fetchMemory();
      setActionSuccess('Note appended to memory history.');
      if (onUpdated) onUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to add note.');
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleRecordOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!applicationId) return;
    setSubmittingOverride(true);
    setError(null);
    try {
      await api.recordApplicationOverride(applicationId, {
        override_decision: overrideDecision,
        original_decision: memory?.decision_snapshot?.decision || 'REVIEW',
        override_type: 'decision',
        reason: overrideReason.trim() || undefined,
      });
      setOverrideReason('');
      await fetchMemory();
      setActionSuccess('Decision override recorded while preserving original recommendation.');
      if (onUpdated) onUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to record override.');
    } finally {
      setSubmittingOverride(false);
    }
  };

  const getStageBadgeColor = (stage: string) => {
    switch (stage) {
      case 'OFFER':
      case 'ACCEPTED':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'INTERVIEW':
      case 'SCREENING':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'SUBMITTED':
      case 'ACKNOWLEDGED':
        return 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30';
      case 'REJECTED':
      case 'WITHDRAWN':
      case 'EXPIRED':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      case 'NO_RESPONSE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getProvenanceBadge = (prov: string) => {
    switch (prov) {
      case 'USER_CONFIRMED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">User Confirmed</span>;
      case 'SYSTEM_DETECTED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">System Detected</span>;
      case 'IMPORTED':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">Imported</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">Unknown</span>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm overflow-y-auto">
      <div className="bg-[#0b1322] border border-slate-800 rounded-xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden my-auto text-xs text-slate-200">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <History className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-100">Application Memory & Provenance</h2>
                {memory && (
                  <span className={`px-2 py-0.5 rounded text-[11px] font-mono border ${getStageBadgeColor(memory.lifecycle_stage)}`}>
                    {memory.lifecycle_stage}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {memory?.job_snapshot?.title || 'Application'} @ {memory?.job_snapshot?.company || 'Employer'} • ID: {applicationId.slice(0, 8)}...
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 px-4 border-b border-slate-800 bg-[#0e1626]">
          <button
            onClick={() => { setActiveTab('timeline'); setActionSuccess(null); }}
            className={`flex items-center gap-2 py-2.5 px-3 border-b-2 font-medium text-xs transition ${
              activeTab === 'timeline'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            Chronological Timeline ({memory?.timeline?.length || 0})
          </button>

          <button
            onClick={() => { setActiveTab('outcome'); setActionSuccess(null); }}
            className={`flex items-center gap-2 py-2.5 px-3 border-b-2 font-medium text-xs transition ${
              activeTab === 'outcome'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Outcome & Status Manager
          </button>

          <button
            onClick={() => { setActiveTab('snapshots'); setActionSuccess(null); }}
            className={`flex items-center gap-2 py-2.5 px-3 border-b-2 font-medium text-xs transition ${
              activeTab === 'snapshots'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Immutable Snapshots
          </button>

          <button
            onClick={() => { setActiveTab('notes'); setActionSuccess(null); }}
            className={`flex items-center gap-2 py-2.5 px-3 border-b-2 font-medium text-xs transition ${
              activeTab === 'notes'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Notes & Overrides ({memory?.notes?.length || 0})
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {actionSuccess && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{actionSuccess}</span>
            </div>
          )}

          {loading ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-indigo-400" />
              <span>Reconstructing application memory & timeline...</span>
            </div>
          ) : !memory ? (
            <div className="p-8 text-center text-slate-400">No application memory available.</div>
          ) : (
            <>
              {/* TAB 1: TIMELINE */}
              {activeTab === 'timeline' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Unified Lifecycle Provenance ({memory.timeline.length} Milestones)
                    </span>
                    <span className="text-[11px] font-mono text-slate-400">
                      Chronological Order
                    </span>
                  </div>

                  <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                    {memory.timeline.map((item, idx) => (
                      <div key={item.id || idx} className="relative group">
                        {/* Timeline Bullet */}
                        <div className="absolute -left-[22px] top-1 w-3.5 h-3.5 rounded-full bg-slate-900 border-2 border-indigo-500 group-hover:border-emerald-400 transition" />

                        <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 space-y-1.5 hover:border-slate-700 transition">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-slate-200 text-xs">{item.title}</span>
                              {getProvenanceBadge(item.provenance)}
                            </div>
                            <span className="text-[10px] font-mono text-slate-400">
                              {new Date(item.timestamp).toLocaleString()}
                            </span>
                          </div>

                          {item.description && (
                            <p className="text-[11px] text-slate-300 leading-relaxed">
                              {item.description}
                            </p>
                          )}

                          <div className="flex items-center gap-3 pt-1 text-[10px] font-mono text-slate-400">
                            <span>Actor: <strong className="text-slate-300">{item.actor}</strong></span>
                            <span>•</span>
                            <span>Type: <strong className="text-slate-300">{item.event_type}</strong></span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 2: OUTCOME MANAGER */}
              {activeTab === 'outcome' && (
                <form onSubmit={handleUpdateOutcome} className="space-y-4">
                  <div className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 space-y-1">
                    <h3 className="font-semibold text-slate-200">Record Application Milestone or Final Outcome</h3>
                    <p className="text-[11px] text-slate-400">
                      Manually record candidate interview progression, offer terms, or rejection categories.
                      Guards strictly against confusing "No Response" with "Rejected".
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Lifecycle Stage */}
                    <div className="space-y-1.5">
                      <label className="block text-[11px] font-semibold text-slate-300">
                        Lifecycle Stage
                      </label>
                      <select
                        value={selectedStage}
                        onChange={(e) => setSelectedStage(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 font-mono"
                      >
                        <optgroup label="Initial & In-Flight">
                          <option value="NOT_STARTED">NOT_STARTED — Discovered / Queued</option>
                          <option value="PREPARED">PREPARED — Package Ready</option>
                          <option value="IN_PROGRESS">IN_PROGRESS — Filling / Navigating</option>
                          <option value="AWAITING_USER">AWAITING_USER — Human Action Needed</option>
                        </optgroup>
                        <optgroup label="Submitted & Awaiting">
                          <option value="SUBMITTED">SUBMITTED — Application Dispatched</option>
                          <option value="ACKNOWLEDGED">ACKNOWLEDGED — Employer Receipt Confirmed</option>
                          <option value="NO_RESPONSE">NO_RESPONSE — Awaiting Initial Reply</option>
                        </optgroup>
                        <optgroup label="Positive Outcomes">
                          <option value="SCREENING">SCREENING — Recruiter Call / Assessment</option>
                          <option value="INTERVIEW">INTERVIEW — Technical / Team Rounds</option>
                          <option value="OFFER">OFFER — Job Offer Received</option>
                          <option value="ACCEPTED">ACCEPTED — Offer Accepted</option>
                        </optgroup>
                        <optgroup label="Negative Outcomes">
                          <option value="REJECTED">REJECTED — Application Not Selected</option>
                          <option value="WITHDRAWN">WITHDRAWN — Candidate Withdrawn</option>
                          <option value="EXPIRED">EXPIRED — Job Posting Closed / Expired</option>
                        </optgroup>
                      </select>
                    </div>

                    {/* Outcome Provenance */}
                    <div className="space-y-1.5">
                      <label className="block text-[11px] font-semibold text-slate-300">
                        Outcome Provenance
                      </label>
                      <select
                        value={selectedProvenance}
                        onChange={(e) => setSelectedProvenance(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 font-mono"
                      >
                        <option value="USER_CONFIRMED">USER_CONFIRMED — Explicitly verified by candidate</option>
                        <option value="SYSTEM_DETECTED">SYSTEM_DETECTED — Detected by system / email keyword</option>
                        <option value="IMPORTED">IMPORTED — Imported from external ATS history</option>
                        <option value="UNKNOWN">UNKNOWN — Unspecified provenance</option>
                      </select>
                    </div>
                  </div>

                  {/* Rejection Details (Only if REJECTED) */}
                  {selectedStage === 'REJECTED' && (
                    <div className="p-3.5 rounded-lg bg-rose-500/5 border border-rose-500/20 space-y-3">
                      <div className="flex items-center gap-2 text-rose-400 font-semibold">
                        <AlertCircle className="w-4 h-4" />
                        <span>Rejection Pattern Classification</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <label className="text-[11px] text-slate-300">Rejection Category</label>
                          <select
                            value={selectedRejectionCat}
                            onChange={(e) => setSelectedRejectionCat(e.target.value)}
                            className="w-full px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-indigo-500 font-mono"
                          >
                            <option value="experience_gap">experience_gap — Years or seniority gap</option>
                            <option value="missing_skill">missing_skill — Lacked specific mandatory technology</option>
                            <option value="role_mismatch">role_mismatch — Profile not aligned with role scope</option>
                            <option value="location">location — Work authorization or country restriction</option>
                            <option value="salary">salary — Compensation expectations misaligned</option>
                            <option value="resume_issue">resume_issue — Formatting or ATS parsing deficiency</option>
                            <option value="interview_performance">interview_performance — Behavioral or system round</option>
                            <option value="technical_assessment">technical_assessment — Coding challenge / takehome</option>
                            <option value="position_closed">position_closed — Requisition cancelled or filled</option>
                            <option value="unknown">unknown — Generic rejection notice without reason</option>
                            <option value="other">other — Specific unlisted reason</option>
                          </select>
                        </div>

                        <div className="space-y-1">
                          <label className="text-[11px] text-slate-300">Employer Feedback Text (Optional)</label>
                          <input
                            type="text"
                            value={rejectionReasonText}
                            onChange={(e) => setRejectionReasonText(e.target.value)}
                            placeholder="e.g. Seeking candidate with 5+ years Kubernetes experience"
                            className="w-full px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Outcome Note */}
                  <div className="space-y-1.5">
                    <label className="block text-[11px] font-semibold text-slate-300">
                      Context / Notes for this update
                    </label>
                    <textarea
                      value={outcomeNotes}
                      onChange={(e) => setOutcomeNotes(e.target.value)}
                      placeholder="e.g. Received confirmation email from recruiter stating 1st round next Tuesday..."
                      rows={2}
                      className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      disabled={submittingOutcome}
                      className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2 transition disabled:opacity-50"
                    >
                      {submittingOutcome && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                      Update Lifecycle Outcome
                    </button>
                  </div>
                </form>
              )}

              {/* TAB 3: IMMUTABLE SNAPSHOTS */}
              {activeTab === 'snapshots' && (
                <div className="space-y-4">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 inline mr-1" />
                    <strong>Immutable Historical Fidelity:</strong> These point-in-time snapshots preserve the exact candidate facts, job requirements, decision metrics, and submitted materials as they existed when this application was processed. Updating your active candidate profile later will never alter this record.
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Candidate Snapshot */}
                    <div className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 space-y-2">
                      <div className="flex items-center gap-2 text-indigo-300 font-semibold border-b border-slate-800 pb-1.5">
                        <User className="w-4 h-4 text-indigo-400" />
                        <span>Candidate Profile Snapshot</span>
                      </div>
                      {memory.candidate_snapshot ? (
                        <div className="space-y-1 font-mono text-[11px] text-slate-300">
                          <div>Name: <span className="text-slate-100">{memory.candidate_snapshot.name}</span></div>
                          <div>Email: <span className="text-slate-100">{memory.candidate_snapshot.email}</span></div>
                          <div>Experience: <span className="text-slate-100">{memory.candidate_snapshot.total_experience_years} years</span></div>
                          <div>Location: <span className="text-slate-100">{memory.candidate_snapshot.location}</span></div>
                          <div className="pt-1 text-[10px] text-slate-400">
                            Target Roles: {memory.candidate_snapshot.target_roles?.join(', ') || 'N/A'}
                          </div>
                          <div className="text-[10px] text-slate-400">
                            Captured: {new Date(memory.candidate_snapshot.captured_at).toLocaleDateString()}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-500 font-mono">No candidate snapshot captured yet.</span>
                      )}
                    </div>

                    {/* Job Snapshot */}
                    <div className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 space-y-2">
                      <div className="flex items-center gap-2 text-indigo-300 font-semibold border-b border-slate-800 pb-1.5">
                        <Building2 className="w-4 h-4 text-indigo-400" />
                        <span>Job Posting Snapshot</span>
                      </div>
                      {memory.job_snapshot ? (
                        <div className="space-y-1 font-mono text-[11px] text-slate-300">
                          <div>Role: <span className="text-slate-100">{memory.job_snapshot.title}</span></div>
                          <div>Company: <span className="text-slate-100">{memory.job_snapshot.company}</span></div>
                          <div>Work Mode: <span className="text-slate-100">{memory.job_snapshot.work_mode || 'Unknown'}</span></div>
                          <div>Source: <span className="text-slate-100">{memory.job_snapshot.source}</span></div>
                          <div className="text-[10px] text-slate-400">
                            Captured: {new Date(memory.job_snapshot.captured_at).toLocaleDateString()}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-500 font-mono">No job snapshot captured yet.</span>
                      )}
                    </div>

                    {/* Decision Snapshot */}
                    <div className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 space-y-2">
                      <div className="flex items-center gap-2 text-indigo-300 font-semibold border-b border-slate-800 pb-1.5">
                        <Sparkles className="w-4 h-4 text-indigo-400" />
                        <span>Decision Engine Snapshot</span>
                      </div>
                      {memory.decision_snapshot ? (
                        <div className="space-y-1 font-mono text-[11px] text-slate-300">
                          <div>Recommendation: <strong className="text-emerald-400">{memory.decision_snapshot.decision}</strong></div>
                          <div>Match Score: <span>{memory.decision_snapshot.match_score ?? 'N/A'}/100</span></div>
                          <div>Risk Level: <span>{memory.decision_snapshot.risk_level}</span></div>
                          <div className="text-[10px] text-slate-400 pt-1">
                            Reasons: {memory.decision_snapshot.reasons?.slice(0, 2).join('; ') || 'Standard match'}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-500 font-mono">No decision snapshot recorded.</span>
                      )}
                    </div>

                    {/* Artifacts Snapshot */}
                    <div className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 space-y-2">
                      <div className="flex items-center gap-2 text-indigo-300 font-semibold border-b border-slate-800 pb-1.5">
                        <FileText className="w-4 h-4 text-indigo-400" />
                        <span>Artifacts & Materials Snapshot</span>
                      </div>
                      {memory.artifacts_snapshot ? (
                        <div className="space-y-1 font-mono text-[11px] text-slate-300">
                          <div>Resume: <span className="text-slate-100">{memory.artifacts_snapshot.resume_name}</span></div>
                          <div>Version: <span className="text-slate-100">{memory.artifacts_snapshot.resume_version}</span></div>
                          <div>Cover Letter: <span className="text-slate-100">{memory.artifacts_snapshot.cover_letter ? 'Attached' : 'None'}</span></div>
                          <div>Screening Answers: <span className="text-slate-100">{memory.artifacts_snapshot.screening_answers?.length || 0} items</span></div>
                        </div>
                      ) : (
                        <span className="text-slate-500 font-mono">No artifacts snapshot captured yet.</span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: NOTES & OVERRIDES */}
              {activeTab === 'notes' && (
                <div className="space-y-6">
                  {/* Append Note Section */}
                  <form onSubmit={handleAddNote} className="p-3.5 rounded-lg bg-slate-900/70 border border-slate-800 space-y-3">
                    <h3 className="font-semibold text-slate-200">Append Timestamped Note</h3>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                      <div className="md:col-span-1 space-y-1">
                        <label className="text-[11px] text-slate-300">Category</label>
                        <select
                          value={noteCategory}
                          onChange={(e) => setNoteCategory(e.target.value)}
                          className="w-full px-2.5 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-200 text-xs font-mono"
                        >
                          <option value="general">general</option>
                          <option value="recruiter">recruiter</option>
                          <option value="interview">interview</option>
                          <option value="compensation">compensation</option>
                          <option value="referral">referral</option>
                          <option value="follow_up">follow_up</option>
                        </select>
                      </div>
                      <div className="md:col-span-3 space-y-1">
                        <label className="text-[11px] text-slate-300">Note Content</label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={noteContent}
                            onChange={(e) => setNoteContent(e.target.value)}
                            placeholder="e.g. Recruiter confirmed remote flexibility; technical round is with Senior Staff Engineer."
                            className="flex-1 px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                          />
                          <button
                            type="submit"
                            disabled={submittingNote || !noteContent.trim()}
                            className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1.5 transition disabled:opacity-50"
                          >
                            <Plus className="w-3.5 h-3.5" />
                            Add
                          </button>
                        </div>
                      </div>
                    </div>
                  </form>

                  {/* Notes History */}
                  <div className="space-y-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Historical Notes Log ({memory.notes.length})
                    </span>
                    {memory.notes.length === 0 ? (
                      <p className="text-slate-500 italic text-xs">No notes appended yet.</p>
                    ) : (
                      <div className="space-y-2">
                        {memory.notes.map((n) => (
                          <div key={n.id} className="p-3 rounded-lg bg-slate-900/50 border border-slate-800 space-y-1">
                            <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                              <span className="capitalize px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                                {n.category}
                              </span>
                              <span>{new Date(n.created_at).toLocaleString()}</span>
                            </div>
                            <p className="text-xs text-slate-200 mt-1">{n.content}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Decision Overrides Section */}
                  <div className="space-y-3 pt-4 border-t border-slate-800">
                    <div className="p-3.5 rounded-lg bg-amber-500/5 border border-amber-500/20 space-y-2">
                      <h3 className="font-semibold text-amber-300">Record System Decision Override</h3>
                      <p className="text-[11px] text-slate-400">
                        If the Decision Engine classified this job as SKIP or REVIEW and you intentionally override it to APPLY (or vice versa), record your rationale here. The original system recommendation is permanently preserved for feedback loop learning.
                      </p>
                      <form onSubmit={handleRecordOverride} className="grid grid-cols-1 md:grid-cols-4 gap-2 pt-1">
                        <div className="md:col-span-1 space-y-1">
                          <label className="text-[10px] text-slate-300">Override To</label>
                          <select
                            value={overrideDecision}
                            onChange={(e) => setOverrideDecision(e.target.value)}
                            className="w-full px-2 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-200 text-xs font-mono"
                          >
                            <option value="APPLY">APPLY</option>
                            <option value="REVIEW">REVIEW</option>
                            <option value="SKIP">SKIP</option>
                          </select>
                        </div>
                        <div className="md:col-span-3 space-y-1">
                          <label className="text-[10px] text-slate-300">Override Rationale</label>
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={overrideReason}
                              onChange={(e) => setOverrideReason(e.target.value)}
                              placeholder="e.g. Willing to relocate; referral from college alumni."
                              className="flex-1 px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-amber-500"
                            />
                            <button
                              type="submit"
                              disabled={submittingOverride}
                              className="px-3 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-slate-900 font-bold text-xs flex items-center gap-1 transition disabled:opacity-50"
                            >
                              Record
                            </button>
                          </div>
                        </div>
                      </form>
                    </div>

                    {/* Historical Overrides List */}
                    {memory.overrides.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-bold uppercase text-slate-400">Preserved Overrides:</span>
                        {memory.overrides.map((ov) => (
                          <div key={ov.id} className="p-2.5 rounded bg-slate-900/60 border border-slate-800 text-[11px] space-y-0.5">
                            <div className="flex items-center justify-between font-mono">
                              <span className="text-amber-400 font-bold">
                                {ov.original_decision} → {ov.override_decision}
                              </span>
                              <span className="text-slate-500 text-[10px]">{new Date(ov.created_at).toLocaleString()}</span>
                            </div>
                            {ov.reason && <p className="text-slate-300 text-xs">{ov.reason}</p>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-800 flex items-center justify-between bg-slate-900/40 text-[11px] text-slate-400">
          <div className="flex items-center gap-2 font-mono">
            <span>Last Outcome: {memory?.last_outcome_date ? new Date(memory.last_outcome_date).toLocaleDateString() : 'None'}</span>
            <span>•</span>
            <span>Provenance: {memory?.outcome_provenance || 'UNKNOWN'}</span>
          </div>
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

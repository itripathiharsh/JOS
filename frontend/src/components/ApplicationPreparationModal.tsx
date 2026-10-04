import React, { useState, useEffect } from 'react';
import {
  X,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  FileText,
  CheckCircle2,
  RefreshCw,
  Copy,
  Check,
  Building2,
  MapPin,
  Layers,
  HelpCircle,
  AlertCircle,
  Save,
  ExternalLink,
} from 'lucide-react';
import { api } from '../api/client';
import type { ApplicationPreparationItem } from '../api/client';

interface ApplicationPreparationModalProps {
  jobId?: string;
  applicationId?: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const ApplicationPreparationModal: React.FC<ApplicationPreparationModalProps> = ({
  jobId,
  applicationId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'evidence' | 'resume' | 'content' | 'questions' | 'warnings'>('evidence');
  const [preparation, setPreparation] = useState<ApplicationPreparationItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Editable user overrides
  const [editedCoverLetter, setEditedCoverLetter] = useState('');
  const [userNotes, setUserNotes] = useState('');
  const [questionOverrides, setQuestionOverrides] = useState<Record<string, string>>({});

  const loadPreparation = async (forceRegenerate = false) => {
    if (!jobId && !applicationId) return;
    if (forceRegenerate) {
      setRegenerating(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      let prep: ApplicationPreparationItem;
      if (jobId) {
        if (forceRegenerate) {
          prep = await api.regenerateJobPreparation(jobId);
        } else {
          try {
            prep = await api.getJobPreparation(jobId);
          } catch (e: any) {
            // Not prepared yet, prepare now
            prep = await api.prepareJobApplication(jobId);
          }
        }
      } else if (applicationId) {
        if (forceRegenerate) {
          prep = await api.regenerateApplicationPreparation(applicationId);
        } else {
          try {
            prep = await api.getApplicationPreparation(applicationId);
          } catch (e: any) {
            prep = await api.prepareApplication(applicationId);
          }
        }
      } else {
        throw new Error('Neither jobId nor applicationId provided');
      }

      setPreparation(prep);
      setEditedCoverLetter(prep.user_overrides?.cover_letter || prep.generated_content.cover_letter);
      setUserNotes(prep.user_notes || '');

      // Initialize question overrides
      const overrides: Record<string, string> = { ...(prep.user_overrides || {}) };
      for (const qa of prep.question_answers) {
        if (qa.confirmed_answer) {
          overrides[qa.category] = qa.confirmed_answer;
        }
      }
      setQuestionOverrides(overrides);

      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to prepare application package.');
    } finally {
      setLoading(false);
      setRegenerating(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadPreparation();
    }
  }, [isOpen, jobId, applicationId]);

  if (!isOpen) return null;

  const handleCopy = (text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleSaveOverrides = async () => {
    if (!preparation) return;
    setSaving(true);
    setError(null);
    try {
      const overrides = {
        ...questionOverrides,
        cover_letter: editedCoverLetter,
      };

      let updated: ApplicationPreparationItem;
      if (jobId) {
        updated = await api.updateJobPreparation(jobId, {
          user_overrides: overrides,
          user_notes: userNotes,
        });
      } else if (applicationId) {
        updated = await api.updateApplicationPreparation(applicationId, {
          user_overrides: overrides,
          user_notes: userNotes,
        });
      } else {
        return;
      }
      setPreparation(updated);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to save changes.');
    } finally {
      setSaving(false);
    }
  };

  const readinessColor =
    preparation?.readiness_status === 'READY'
      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
      : preparation?.readiness_status === 'BLOCKED'
      ? 'text-rose-400 bg-rose-500/10 border-rose-500/30'
      : 'text-amber-400 bg-amber-500/10 border-amber-500/30';

  const decisionColor =
    preparation?.decision_snapshot?.decision === 'APPLY'
      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
      : 'text-amber-400 bg-amber-500/10 border-amber-500/30';

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#0e1626] border border-slate-700/80 rounded-xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-start justify-between bg-slate-900/60">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold tracking-wider uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Step 8 — Preparation Engine
              </span>
              {preparation && (
                <span className="text-[11px] font-mono text-slate-400">
                  v{preparation.version} • Engine {preparation.engine_version}
                </span>
              )}
            </div>
            <h2 className="text-lg font-bold text-slate-100 mt-1">
              Application Package: {preparation?.job_snapshot?.title || 'Job Preparation'}
            </h2>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span className="flex items-center gap-1 font-medium text-slate-300">
                <Building2 className="w-3.5 h-3.5 text-slate-500" />
                {preparation?.job_snapshot?.company || 'Company'}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                {preparation?.job_snapshot?.location || 'Remote'}
              </span>
              {preparation?.job_snapshot?.application_url && (
                <>
                  <span>•</span>
                  <a
                    href={preparation.job_snapshot.application_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                  >
                    View Original Posting <ExternalLink className="w-3 h-3" />
                  </a>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {preparation && (
              <div className="flex items-center gap-2">
                <div className={`px-2.5 py-1 rounded-md text-xs font-bold border flex items-center gap-1.5 ${readinessColor}`}>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  {preparation.readiness_status} ({preparation.readiness_score}/100)
                </div>
                <div className={`px-2.5 py-1 rounded-md text-xs font-bold border ${decisionColor}`}>
                  {preparation.decision_snapshot?.decision}
                </div>
              </div>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="px-6 py-2.5 bg-rose-500/10 border-b border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200 text-xs">
              Dismiss
            </button>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="px-6 pt-3 border-b border-slate-800 bg-slate-900/30 flex gap-2">
          {[
            { id: 'evidence', label: 'Evidence & Requirements', icon: Layers },
            { id: 'resume', label: 'Resume & Skills', icon: FileText },
            { id: 'content', label: 'Draft Materials', icon: Sparkles },
            { id: 'questions', label: 'Screening Questions', icon: HelpCircle },
            { id: 'warnings', label: 'Human Checklist & Warnings', icon: AlertTriangle },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition ${
                  active
                    ? 'border-indigo-500 text-indigo-300 bg-indigo-500/10 rounded-t'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs">
          {loading ? (
            <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
              <span className="font-medium text-slate-300">
                Running Application Preparation Engine...
              </span>
              <span className="text-[11px] text-slate-500 max-w-sm">
                Extracting requirements, mapping candidate evidence, enforcing claim safety, and synthesizing application materials.
              </span>
            </div>
          ) : !preparation ? (
            <div className="p-12 text-center text-slate-400">
              No preparation data available.
            </div>
          ) : (
            <>
              {/* TAB 1: Evidence & Requirements */}
              {activeTab === 'evidence' && (
                <div className="space-y-6">
                  {/* Readiness Banner */}
                  <div className={`p-4 rounded-lg border ${readinessColor} flex items-start gap-3`}>
                    <ShieldCheck className="w-5 h-5 shrink-0 mt-0.5" />
                    <div className="space-y-1">
                      <div className="font-bold text-sm">
                        Application Readiness: {preparation.readiness_status} ({preparation.readiness_score}/100)
                      </div>
                      <p className="text-slate-300 text-xs">
                        {preparation.readiness_reasons?.join(' ')}
                      </p>
                    </div>
                  </div>

                  {/* Requirements Breakdown */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                      <h4 className="font-bold text-slate-200 uppercase tracking-wider text-[11px]">
                        Required Qualifications
                      </h4>
                      <ul className="space-y-1.5 text-slate-300">
                        {preparation.extracted_requirements.required_qualifications.map((req, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-indigo-400 font-bold">•</span>
                            <span>{req}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                      <h4 className="font-bold text-slate-200 uppercase tracking-wider text-[11px]">
                        Preferred Qualifications & Responsibilities
                      </h4>
                      <ul className="space-y-1.5 text-slate-300">
                        {preparation.extracted_requirements.preferred_qualifications.map((pref, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-emerald-400 font-bold">•</span>
                            <span>{pref}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Evidence Mapping Table */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                        Candidate Evidence Mapping ({preparation.evidence_mapping.length} Items)
                      </h4>
                      <span className="text-[11px] text-slate-400">
                        Evaluated against verified profile facts. MISSING / UNKNOWN are never converted to DIRECT.
                      </span>
                    </div>

                    <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-900/40">
                      <table className="w-full text-left">
                        <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 font-mono text-[11px] uppercase">
                          <tr>
                            <th className="px-3 py-2.5">Requirement</th>
                            <th className="px-3 py-2.5">Evidence Status</th>
                            <th className="px-3 py-2.5">Candidate Evidence</th>
                            <th className="px-3 py-2.5">Source / Notes</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/80">
                          {preparation.evidence_mapping.map((item, idx) => {
                            const badgeClass =
                              item.match_type === 'DIRECT'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                                : item.match_type === 'TRANSFERABLE'
                                ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                                : item.match_type === 'WEAK'
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                                : item.match_type === 'MISSING'
                                ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                                : 'bg-slate-700/20 text-slate-400 border-slate-700/40';

                            return (
                              <tr key={idx} className="hover:bg-slate-900/50 transition">
                                <td className="px-3 py-2.5 font-medium text-slate-200 max-w-xs">
                                  {item.requirement}
                                </td>
                                <td className="px-3 py-2.5">
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border font-mono ${badgeClass}`}>
                                    {item.match_type}
                                  </span>
                                </td>
                                <td className="px-3 py-2.5 text-slate-300 max-w-sm">
                                  {item.candidate_evidence || '—'}
                                </td>
                                <td className="px-3 py-2.5 text-slate-400 text-[11px] max-w-xs">
                                  <div className="font-mono text-slate-300">{item.source}</div>
                                  {item.notes && <div className="text-slate-500 mt-0.5">{item.notes}</div>}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: Resume & Skills */}
              {activeTab === 'resume' && (
                <div className="space-y-6">
                  {/* Recommended Document */}
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="w-5 h-5 text-indigo-400" />
                        <div>
                          <div className="font-bold text-slate-100 text-sm">
                            Recommended Resume: {preparation.resume_recommendation.document_name}
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono">
                            Path: {preparation.resume_recommendation.file_path}
                          </div>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 font-medium">
                        Master Document Unaltered
                      </span>
                    </div>

                    <p className="text-slate-300 leading-relaxed">
                      {preparation.resume_recommendation.why_recommended}
                    </p>

                    <div className="p-2.5 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-slate-300">
                      <span className="font-semibold text-indigo-300">Sufficiency Assessment: </span>
                      {preparation.resume_recommendation.sufficiency_assessment}
                    </div>
                  </div>

                  {/* Tailoring Suggestions */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* KEEP */}
                    <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20 space-y-2">
                      <div className="font-bold text-emerald-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" />
                        Keep in Resume (Direct Evidence)
                      </div>
                      <ul className="space-y-1 text-slate-300 text-[11px]">
                        {preparation.resume_recommendation.keep_points.map((pt, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="text-emerald-400 font-bold">•</span>
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* EMPHASIZE */}
                    <div className="p-4 rounded-lg bg-indigo-500/5 border border-indigo-500/20 space-y-2">
                      <div className="font-bold text-indigo-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4" />
                        Emphasize Prominently
                      </div>
                      <ul className="space-y-1 text-slate-300 text-[11px]">
                        {preparation.resume_recommendation.emphasize_points.map((pt, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="text-indigo-400 font-bold">•</span>
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* DE-EMPHASIZE */}
                    <div className="p-4 rounded-lg bg-slate-800/20 border border-slate-700/30 space-y-2">
                      <div className="font-bold text-slate-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
                        <Layers className="w-4 h-4" />
                        De-Emphasize Less Relevant Items
                      </div>
                      <ul className="space-y-1 text-slate-400 text-[11px]">
                        {preparation.resume_recommendation.deemphasize_points.map((pt, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="text-slate-500 font-bold">•</span>
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* ADD IF TRUE */}
                    <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/20 space-y-2">
                      <div className="font-bold text-amber-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4" />
                        Add If True (Manual Input Required)
                      </div>
                      <ul className="space-y-1 text-slate-300 text-[11px]">
                        {preparation.resume_recommendation.add_if_true_points.map((pt, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{pt}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Skills Recommendation */}
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-4">
                    <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                      Skills Recommendation & Guardrails
                    </h4>

                    <div className="space-y-3">
                      <div>
                        <div className="text-[11px] font-mono text-emerald-400 mb-1.5 font-semibold">
                          STRONG MATCH ({preparation.skills_recommendation.strong_match.length}):
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {preparation.skills_recommendation.strong_match.map((s) => (
                            <span key={s} className="px-2 py-0.5 rounded text-[11px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="text-[11px] font-mono text-sky-400 mb-1.5 font-semibold">
                          SUPPORTING SKILLS ({preparation.skills_recommendation.supporting_skills.length}):
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {preparation.skills_recommendation.supporting_skills.map((s) => (
                            <span key={s} className="px-2 py-0.5 rounded text-[11px] bg-sky-500/10 text-sky-300 border border-sky-500/30">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* DO NOT CLAIM GUARDRAIL */}
                      <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 space-y-1.5">
                        <div className="text-[11px] font-mono text-rose-300 font-bold flex items-center gap-1.5">
                          <AlertTriangle className="w-4 h-4 text-rose-400" />
                          DO NOT CLAIM (SAFETY GUARDRAIL):
                        </div>
                        <p className="text-[11px] text-rose-200">
                          These technologies appear in the job specification but cannot be substantiated from your profile. Never assert factual proficiency in them:
                        </p>
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {preparation.skills_recommendation.do_not_claim.map((s) => (
                            <span key={s} className="px-2 py-0.5 rounded text-[11px] bg-rose-500/20 text-rose-300 border border-rose-500/40 font-mono">
                              ✗ {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: Draft Application Content */}
              {activeTab === 'content' && (
                <div className="space-y-6">
                  {/* Claim Safety Audit Card */}
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-400" />
                      <div>
                        <div className="font-bold text-emerald-300 text-xs">
                          Claim Safety Audit: {preparation.generated_content.claim_safety_audit.safety_verdict} (Zero Hallucination)
                        </div>
                        <div className="text-[11px] text-slate-300">
                          Verified practical experience (~{preparation.generated_content.claim_safety_audit.verified_years_used} years) strictly enforced. Zero fake metrics or companies.
                        </div>
                      </div>
                    </div>
                    <span className="text-[11px] font-mono text-emerald-400">
                      Deterministic $0 Engine
                    </span>
                  </div>

                  {/* Application Summary */}
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                        Tailored Candidate Summary
                      </h4>
                      <button
                        onClick={() => handleCopy(preparation.generated_content.application_summary, 'summary')}
                        className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
                      >
                        {copiedField === 'summary' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedField === 'summary' ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                    <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded border border-slate-800/80">
                      {preparation.generated_content.application_summary}
                    </p>
                  </div>

                  {/* Cover Letter (Editable) */}
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                          Cover Letter / Application Message (Editable)
                        </h4>
                        <span className="text-[11px] text-slate-400">
                          Personalize this draft before submitting in Step 9.
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleCopy(editedCoverLetter, 'letter')}
                          className="flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                        >
                          {copiedField === 'letter' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                          {copiedField === 'letter' ? 'Copied' : 'Copy Text'}
                        </button>
                      </div>
                    </div>
                    <textarea
                      rows={12}
                      value={editedCoverLetter}
                      onChange={(e) => setEditedCoverLetter(e.target.value)}
                      className="w-full bg-slate-950/80 border border-slate-800 rounded p-3 text-slate-200 text-xs leading-relaxed font-sans focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  {/* Short Application Message */}
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                        Short Direct Message (e.g. LinkedIn / Recruiter InMail)
                      </h4>
                      <button
                        onClick={() => handleCopy(preparation.generated_content.short_message, 'short')}
                        className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200"
                      >
                        {copiedField === 'short' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        {copiedField === 'short' ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                    <p className="text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded border border-slate-800/80">
                      {preparation.generated_content.short_message}
                    </p>
                  </div>
                </div>
              )}

              {/* TAB 4: Screening Questions */}
              {activeTab === 'questions' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                        Application Screening Questions & Proposed Answers
                      </h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Sensitive legal, salary, and authorization questions strictly require human review before use.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {preparation.question_answers.map((qa, idx) => {
                      const isSensitive = qa.requires_human_confirmation;
                      const currentValue = questionOverrides[qa.category] ?? qa.confirmed_answer ?? qa.proposed_answer ?? '';

                      return (
                        <div
                          key={idx}
                          className={`p-3.5 rounded-lg border transition ${
                            isSensitive
                              ? 'bg-amber-500/5 border-amber-500/30'
                              : 'bg-slate-900/60 border-slate-800'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="space-y-1 flex-1">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                  {qa.category}
                                </span>
                                {isSensitive && (
                                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" />
                                    REQUIRES CONFIRMATION
                                  </span>
                                )}
                                <span className="text-[10px] font-mono text-slate-500">
                                  Confidence: {qa.confidence}
                                </span>
                              </div>
                              <h5 className="font-semibold text-slate-200 text-xs">
                                {qa.question}
                              </h5>
                            </div>
                          </div>

                          <div className="mt-2 space-y-1.5">
                            <label className="text-[10px] font-mono text-slate-400 uppercase">
                              Proposed Answer (Editable Confirmation):
                            </label>
                            <input
                              type="text"
                              value={currentValue}
                              onChange={(e) => {
                                setQuestionOverrides((prev) => ({
                                  ...prev,
                                  [qa.category]: e.target.value,
                                }));
                              }}
                              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                            />
                            <div className="text-[10px] text-slate-400 flex items-center gap-2">
                              <span>Source: {qa.answer_source}</span>
                              <span>•</span>
                              <span>Evidence: {qa.evidence}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* TAB 5: Human Checklist & Warnings */}
              {activeTab === 'warnings' && (
                <div className="space-y-4">
                  {/* Sensitive Confirmation Checklist */}
                  <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-3">
                    <div className="font-bold text-amber-300 text-xs uppercase tracking-wider flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                      Pending Human Confirmations ({preparation.human_confirmation_required.length})
                    </div>
                    {preparation.human_confirmation_required.length === 0 ? (
                      <p className="text-emerald-300 text-xs flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4" />
                        All sensitive questions and declarations have been confirmed!
                      </p>
                    ) : (
                      <ul className="space-y-2 text-slate-300 text-xs">
                        {preparation.human_confirmation_required.map((hc, i) => (
                          <li key={i} className="p-2.5 rounded bg-slate-900/60 border border-amber-500/20 space-y-1">
                            <div className="font-semibold text-slate-200">{hc.question}</div>
                            <div className="text-[11px] text-amber-300">Proposed: {hc.proposed_answer}</div>
                            {hc.reason && <div className="text-[10px] text-slate-400">{hc.reason}</div>}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Warnings List */}
                  {preparation.warnings && preparation.warnings.length > 0 && (
                    <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                      <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                        System Warnings & Notices
                      </h4>
                      <ul className="space-y-1 text-slate-300 text-xs">
                        {preparation.warnings.map((w, i) => (
                          <li key={i} className="flex items-start gap-1.5">
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{w}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* User Notes */}
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                    <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider">
                      Preparation Notes (Internal)
                    </h4>
                    <textarea
                      rows={3}
                      value={userNotes}
                      onChange={(e) => setUserNotes(e.target.value)}
                      placeholder="Add personal notes, follow-up checklist items, or interview targets for this job..."
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between">
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
            <span className="w-2 h-2 rounded-full bg-indigo-400" />
            Step 8: Preparation Only. Auto-Apply disabled until Step 9.
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => loadPreparation(true)}
              disabled={loading || regenerating}
              className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${regenerating ? 'animate-spin' : ''}`} />
              {regenerating ? 'Regenerating...' : 'Regenerate Package'}
            </button>

            <button
              onClick={handleSaveOverrides}
              disabled={saving || !preparation}
              className="px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-sm shadow-indigo-500/20 flex items-center gap-1.5 transition disabled:opacity-50"
            >
              <Save className="w-3.5 h-3.5" />
              {saving ? 'Saving...' : 'Save Confirmations & Edits'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

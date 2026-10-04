import React, { useState, useEffect } from 'react';
import {
  User,
  GraduationCap,
  Briefcase,
  Code,
  FolderGit2,
  Link as LinkIcon,
  Sliders,
  Plus,
  Trash2,
  Save,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ExternalLink,
  Award,
  FileText,
  UploadCloud,
  ArrowUp,
  ArrowDown,
  Sparkles,
  Check,
  ChevronDown
} from 'lucide-react';
import { api } from '../api/client';
import type {
  CandidateProfile,
  CandidatePreference,
  EducationItem,
  ExperienceItem,
  SkillItem,
  ProjectItem,
  CertificationItem,
  DocumentItem
} from '../api/client';

export const ProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<CandidateProfile>({
    name: 'Harsh Vardhan Tripathi',
    email: 'harsh.tripathi.cs@gmail.com',
    phone: '+91 95652 49247',
    location: 'Lucknow, India',
    summary: '',
    preferences: {},
    links: {
      github: 'https://github.com/itripathiharsh',
      linkedin: 'https://linkedin.com/in/iamharshvardhantripathi',
      portfolio: 'https://harshtripathi.vercel.app/',
    },
    preference_record: {
      target_roles: ['AI Engineer', 'ML Engineer', 'Backend Engineer', 'Forward Deployed Engineer (FDE)', 'Technical Consultant'],
      role_priority: ['AI Engineer', 'ML Engineer', 'Backend Engineer', 'Forward Deployed Engineer (FDE)', 'Technical Consultant'],
      preferred_locations: ['Remote', 'Uttar Pradesh', 'Anywhere in India'],
      location_priority: ['Remote', 'Uttar Pradesh', 'Anywhere in India'],
      work_modes: ['Remote', 'Hybrid', 'On-site'],
      minimum_salary: 350000,
      currency: 'INR',
      experience_preference: '0-1 years',
      employment_types: ['Full-time', 'Internship', 'Contract'],
      relocation_allowed: true,
      startup_allowed: true,
      service_company_allowed: true,
      product_company_allowed: true,
      internship_allowed: true,
      contract_allowed: true,
    },
    educations: [],
    experiences: [],
    skills: [],
    projects: [],
    certifications: [],
    documents: [],
  });

  const [activeTab, setActiveTab] = useState<
    'personal' | 'preferences' | 'education' | 'experience' | 'skills' | 'projects' | 'certifications' | 'documents' | 'links'
  >('personal');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [showCompletenessModal, setShowCompletenessModal] = useState(false);
  const [showIngestModal, setShowIngestModal] = useState(false);
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // New item drafts
  const [newSkill, setNewSkill] = useState({ name: '', category: 'AI / Machine Learning', proficiency: 'Competent' });
  const [selectedSkillCategory, setSelectedSkillCategory] = useState<string>('All');
  const [newRoleInput, setNewRoleInput] = useState('');
  const [newLocationInput, setNewLocationInput] = useState('');
  const [editingSalary, setEditingSalary] = useState(false);
  const [salaryInput, setSalaryInput] = useState<number>(350000);

  // Draft certification
  const [newCert, setNewCert] = useState<Partial<CertificationItem>>({
    name: '',
    issuing_organization: '',
    issue_date: '',
    credential_id: '',
    credential_url: '',
    source_url: '',
    status: 'CONFIRMED'
  });

  // Draft document
  const [newDoc, setNewDoc] = useState<Partial<DocumentItem>>({
    name: '',
    type: 'resume',
    file_path: '',
    source: 'local'
  });

  const fetchProfile = async () => {
    setLoading(true);
    setSaveStatus(null);
    try {
      const data = await api.getProfile();
      if (data) {
        setProfile((prev) => ({
          ...prev,
          ...data,
          preference_record: data.preference_record || prev.preference_record,
          links: data.links || prev.links,
          educations: data.educations || [],
          experiences: data.experiences || [],
          skills: data.skills || [],
          projects: data.projects || [],
          certifications: data.certifications || [],
          documents: data.documents || [],
        }));
      }
    } catch (err: any) {
      setSaveStatus({ type: 'error', message: err.message || 'Failed to load candidate profile' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!profile.name.trim() || !profile.email.trim()) {
      setSaveStatus({ type: 'error', message: 'Name and Email are required fields.' });
      return;
    }

    setSaving(true);
    setSaveStatus(null);
    try {
      const payload: CandidateProfile = {
        ...profile,
        preferences: profile.preference_record ? { ...profile.preference_record } : profile.preferences,
      };
      const saved = await api.saveProfile(payload);
      setProfile(saved);
      setSaveStatus({ type: 'success', message: 'Candidate profile successfully saved to database.' });
      setTimeout(() => setSaveStatus(null), 4000);
    } catch (err: any) {
      setSaveStatus({ type: 'error', message: err.message || 'Failed to save profile' });
    } finally {
      setSaving(false);
    }
  };

  const handleIngestResume = async (file?: File) => {
    setIngesting(true);
    setSaveStatus(null);
    try {
      let formData: FormData | undefined;
      if (file) {
        formData = new FormData();
        formData.append('file', file);
      }
      const res = await api.ingestResume(formData);
      setSaveStatus({
        type: 'success',
        message: `Resume successfully ingested! Extracted ${res.experiences.length} experiences, ${res.educations.length} educations, ${res.skills.length} skills, and ${res.certifications.length} certifications.`,
      });
      setShowIngestModal(false);
      await fetchProfile();
    } catch (err: any) {
      setSaveStatus({ type: 'error', message: err.message || 'Failed to ingest resume.' });
    } finally {
      setIngesting(false);
    }
  };

  // ----------------------------------------------------
  // Preferences Helpers
  // ----------------------------------------------------
  const updatePref = (updater: (prev: CandidatePreference) => CandidatePreference) => {
    const current = profile.preference_record || {
      target_roles: [],
      role_priority: [],
      preferred_locations: [],
      location_priority: [],
      work_modes: ['Remote'],
      minimum_salary: 350000,
      currency: 'INR',
      experience_preference: '0-1 years',
      employment_types: ['Full-time'],
      relocation_allowed: true,
      startup_allowed: true,
      service_company_allowed: true,
      product_company_allowed: true,
      internship_allowed: true,
      contract_allowed: true,
    };
    const updated = updater(current);
    setProfile({ ...profile, preference_record: updated });
  };

  const confirmSalary = async (salaryVal?: number) => {
    const val = salaryVal !== undefined ? salaryVal : (profile.preference_record?.minimum_salary ?? 350000);
    updatePref((p) => ({ ...p, minimum_salary: val, salary_status: 'CONFIRMED' }));
    setEditingSalary(false);
    try {
      await api.updatePreferences({ minimum_salary: val, salary_status: 'CONFIRMED' });
      setSaveStatus({ type: 'success', message: `Minimum salary confirmed at ₹${(val / 100000).toFixed(1)} LPA (${val.toLocaleString()} INR).` });
      setTimeout(() => setSaveStatus(null), 4000);
    } catch (err: any) {
      setSaveStatus({ type: 'error', message: err.message || 'Failed to update preferences.' });
    }
  };

  const moveRole = (index: number, direction: 'up' | 'down') => {
    updatePref((p) => {
      const roles = [...(p.target_roles || [])];
      const targetIdx = direction === 'up' ? index - 1 : index + 1;
      if (targetIdx < 0 || targetIdx >= roles.length) return p;
      const temp = roles[index];
      roles[index] = roles[targetIdx];
      roles[targetIdx] = temp;
      return { ...p, target_roles: roles, role_priority: roles };
    });
  };

  const addRole = () => {
    if (!newRoleInput.trim()) return;
    updatePref((p) => {
      const roles = p.target_roles || [];
      if (roles.includes(newRoleInput.trim())) return p;
      const updated = [...roles, newRoleInput.trim()];
      return { ...p, target_roles: updated, role_priority: updated };
    });
    setNewRoleInput('');
  };

  const removeRole = (index: number) => {
    updatePref((p) => {
      const roles = (p.target_roles || []).filter((_, i) => i !== index);
      return { ...p, target_roles: roles, role_priority: roles };
    });
  };

  const moveLocation = (index: number, direction: 'up' | 'down') => {
    updatePref((p) => {
      const locs = [...(p.preferred_locations || [])];
      const targetIdx = direction === 'up' ? index - 1 : index + 1;
      if (targetIdx < 0 || targetIdx >= locs.length) return p;
      const temp = locs[index];
      locs[index] = locs[targetIdx];
      locs[targetIdx] = temp;
      return { ...p, preferred_locations: locs, location_priority: locs };
    });
  };

  const addLocation = () => {
    if (!newLocationInput.trim()) return;
    updatePref((p) => {
      const locs = p.preferred_locations || [];
      if (locs.includes(newLocationInput.trim())) return p;
      const updated = [...locs, newLocationInput.trim()];
      return { ...p, preferred_locations: updated, location_priority: updated };
    });
    setNewLocationInput('');
  };

  const removeLocation = (index: number) => {
    updatePref((p) => {
      const locs = (p.preferred_locations || []).filter((_, i) => i !== index);
      return { ...p, preferred_locations: locs, location_priority: locs };
    });
  };

  // ----------------------------------------------------
  // Skill Categories Filter & Add
  // ----------------------------------------------------
  const skillCategories = [
    'All',
    'Programming',
    'AI / Machine Learning',
    'Generative AI / LLM',
    'AI Frameworks',
    'Backend / Databases',
    'Vector Search / Retrieval',
    'Cloud / DevOps / Deployment',
    'Engineering',
  ];

  const filteredSkills = (profile.skills || []).filter((s) => {
    if (selectedSkillCategory === 'All') return true;
    return s.category?.toLowerCase() === selectedSkillCategory.toLowerCase();
  });

  const addSkill = () => {
    if (!newSkill.name.trim()) return;
    const item: SkillItem = {
      name: newSkill.name.trim(),
      category: newSkill.category,
      proficiency: newSkill.proficiency,
      status: 'USER_PROVIDED',
    };
    setProfile({
      ...profile,
      skills: [...(profile.skills || []), item],
    });
    setNewSkill({ name: '', category: newSkill.category, proficiency: 'Competent' });
  };

  const removeSkill = (index: number) => {
    const next = [...(profile.skills || [])];
    next.splice(index, 1);
    setProfile({ ...profile, skills: next });
  };

  // ----------------------------------------------------
  // Education Helpers
  // ----------------------------------------------------
  const addEducation = () => {
    setProfile({
      ...profile,
      educations: [
        ...(profile.educations || []),
        { institution: '', degree: '', field: '', start_date: '', end_date: '', location: '', status: 'CONFIRMED' },
      ],
    });
  };

  const updateEducation = (index: number, field: keyof EducationItem, val: string) => {
    const next = [...(profile.educations || [])];
    next[index] = { ...next[index], [field]: val };
    setProfile({ ...profile, educations: next });
  };

  const removeEducation = (index: number) => {
    const next = [...(profile.educations || [])];
    next.splice(index, 1);
    setProfile({ ...profile, educations: next });
  };

  // ----------------------------------------------------
  // Experience Helpers
  // ----------------------------------------------------
  const addExperience = () => {
    setProfile({
      ...profile,
      experiences: [
        ...(profile.experiences || []),
        {
          company: '',
          title: '',
          description: '',
          start_date: '',
          end_date: '',
          current: false,
          location: '',
          employment_type: 'Full-time',
          responsibilities: [],
          status: 'CONFIRMED',
        },
      ],
    });
  };

  const updateExperience = (index: number, field: keyof ExperienceItem, val: any) => {
    const next = [...(profile.experiences || [])];
    next[index] = { ...next[index], [field]: val };
    setProfile({ ...profile, experiences: next });
  };

  const removeExperience = (index: number) => {
    const next = [...(profile.experiences || [])];
    next.splice(index, 1);
    setProfile({ ...profile, experiences: next });
  };

  // ----------------------------------------------------
  // Project Helpers
  // ----------------------------------------------------
  const addProject = () => {
    setProfile({
      ...profile,
      projects: [
        ...(profile.projects || []),
        {
          name: '',
          description: '',
          technologies: '',
          role: 'Lead Developer',
          url: '',
          repo_url: '',
          demo_url: '',
          status: 'CONFIRMED',
        },
      ],
    });
  };

  const updateProject = (index: number, field: keyof ProjectItem, val: string) => {
    const next = [...(profile.projects || [])];
    next[index] = { ...next[index], [field]: val };
    setProfile({ ...profile, projects: next });
  };

  const removeProject = (index: number) => {
    const next = [...(profile.projects || [])];
    next.splice(index, 1);
    setProfile({ ...profile, projects: next });
  };

  // ----------------------------------------------------
  // Certifications Helpers
  // ----------------------------------------------------
  const addCert = () => {
    if (!newCert.name?.trim() || !newCert.issuing_organization?.trim()) return;
    setProfile({
      ...profile,
      certifications: [
        ...(profile.certifications || []),
        {
          name: newCert.name.trim(),
          issuing_organization: newCert.issuing_organization.trim(),
          issue_date: newCert.issue_date || null,
          credential_id: newCert.credential_id || null,
          credential_url: newCert.credential_url || null,
          source_url: newCert.source_url || null,
          status: 'CONFIRMED',
        },
      ],
    });
    setNewCert({ name: '', issuing_organization: '', issue_date: '', credential_id: '', credential_url: '', source_url: '', status: 'CONFIRMED' });
  };

  const removeCert = (index: number) => {
    const next = [...(profile.certifications || [])];
    next.splice(index, 1);
    setProfile({ ...profile, certifications: next });
  };

  // ----------------------------------------------------
  // Documents Helpers
  // ----------------------------------------------------
  const addDoc = () => {
    if (!newDoc.name?.trim() || !newDoc.file_path?.trim()) return;
    setProfile({
      ...profile,
      documents: [
        ...(profile.documents || []),
        {
          name: newDoc.name.trim(),
          type: newDoc.type || 'resume',
          file_path: newDoc.file_path.trim(),
          source: 'manual',
          file_size: 154000,
        },
      ],
    });
    setNewDoc({ name: '', type: 'resume', file_path: '', source: 'manual' });
  };

  const removeDoc = (index: number) => {
    const next = [...(profile.documents || [])];
    next.splice(index, 1);
    setProfile({ ...profile, documents: next });
  };

  // Completeness score
  const completeness = profile.completeness;
  const score = completeness?.score ?? 0;
  const scoreBadgeColor =
    score >= 85
      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
      : score >= 60
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
      : 'bg-rose-500/20 text-rose-300 border-rose-500/30';

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-20">
      {/* ==================================================== */}
      {/* Top Banner / Header */}
      {/* ==================================================== */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-900/90 to-slate-950 p-6 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-5">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-500 text-white shadow-lg shadow-cyan-500/20 ring-4 ring-cyan-500/10">
              <User className="h-8 w-8" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold tracking-tight text-white">{profile.name || 'Candidate Profile'}</h1>
                <span className="inline-flex items-center gap-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 text-xs font-semibold text-cyan-300">
                  <Sparkles className="h-3 w-3" /> Canonical Single Source of Truth
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-400">
                {profile.email} • {profile.location || 'India'} • {profile.phone || '+91 95652 49247'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4">
            {/* Completeness gauge button */}
            <button
              onClick={() => setShowCompletenessModal(!showCompletenessModal)}
              className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 text-sm font-semibold transition hover:scale-[1.02] ${scoreBadgeColor}`}
            >
              <div className="relative flex h-8 w-8 items-center justify-center">
                <svg className="h-8 w-8 -rotate-90">
                  <circle cx="16" cy="16" r="13" stroke="currentColor" strokeWidth="3" className="text-slate-800" fill="none" />
                  <circle
                    cx="16"
                    cy="16"
                    r="13"
                    stroke="currentColor"
                    strokeWidth="3"
                    className="text-current transition-all duration-700"
                    strokeDasharray={81.68}
                    strokeDashoffset={81.68 - (81.68 * score) / 100}
                    fill="none"
                  />
                </svg>
                <span className="absolute text-[10px] font-bold">{score}%</span>
              </div>
              <div className="text-left">
                <div className="text-xs uppercase tracking-wider text-slate-400">Profile Completeness</div>
                <div className="font-bold">{completeness?.level || 'Active'}</div>
              </div>
              <ChevronDown className="h-4 w-4 opacity-70" />
            </button>

            {/* Ingest Resume Button */}
            <button
              onClick={() => setShowIngestModal(true)}
              className="flex items-center gap-2 rounded-xl border border-indigo-500/40 bg-indigo-500/10 px-4 py-2.5 text-sm font-semibold text-indigo-300 transition hover:bg-indigo-500/20 hover:text-white"
            >
              <UploadCloud className="h-4 w-4" />
              Ingest Resume PDF
            </button>

            {/* Save Profile Button */}
            <button
              onClick={() => handleSave()}
              disabled={saving}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/25 transition hover:brightness-110 disabled:opacity-50"
            >
              {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </div>

        {/* Status Alerts */}
        {saveStatus && (
          <div
            className={`mt-4 flex items-center gap-2 rounded-xl p-3.5 text-sm ${
              saveStatus.type === 'success'
                ? 'border border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                : 'border border-rose-500/30 bg-rose-500/10 text-rose-300'
            }`}
          >
            {saveStatus.type === 'success' ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
            <span>{saveStatus.message}</span>
          </div>
        )}
      </div>

      {/* ==================================================== */}
      {/* Completeness Breakdown Modal / Drawer */}
      {/* ==================================================== */}
      {showCompletenessModal && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/95 p-6 shadow-2xl backdrop-blur-md">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-cyan-400" />
              <h3 className="text-lg font-bold text-white">Profile Completeness Rules ({score} / 100)</h3>
            </div>
            <button onClick={() => setShowCompletenessModal(false)} className="text-sm text-slate-400 hover:text-white">
              Close
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Completeness is computed using strictly defined, non-arbitrary rules: 60 points required core signals + 40 points optional enrichment signals.
          </p>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            {(completeness?.details || []).map((crit, idx) => (
              <div
                key={idx}
                className={`flex items-start gap-3 rounded-xl border p-3 ${
                  crit.met ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-slate-800 bg-slate-950/40'
                }`}
              >
                <div className={`mt-0.5 rounded-full p-1 ${crit.met ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                  {crit.met ? <Check className="h-3 w-3" /> : <AlertCircle className="h-3 w-3" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-slate-200">
                      {crit.criterion} {crit.is_required && <span className="text-rose-400">*</span>}
                    </span>
                    <span className="text-xs font-mono text-slate-400">+{crit.weight} pts</span>
                  </div>
                  <p className="text-xs text-slate-400">{crit.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Resume Ingestion Modal */}
      {/* ==================================================== */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-indigo-400" />
                <h3 className="text-lg font-bold text-white">Resume Ingestion Pipeline</h3>
              </div>
              <button onClick={() => setShowIngestModal(false)} className="text-sm text-slate-400 hover:text-white">
                Cancel
              </button>
            </div>

            <div className="mt-4 space-y-4">
              <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4 text-xs text-indigo-200">
                <p className="font-semibold text-indigo-300">Strict Provenance Protocol:</p>
                <ul className="mt-1.5 list-disc space-y-1 pl-4 text-slate-400">
                  <li><strong className="text-emerald-400">CONFIRMED:</strong> Information directly present in the resume PDF text.</li>
                  <li><strong className="text-cyan-400">USER-PROVIDED:</strong> Links, GitHub certifications repo, and career search preferences.</li>
                  <li><strong className="text-amber-400">INFERRED:</strong> Stored with explicit review flags before being finalized.</li>
                </ul>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Option A: Authorized Local Resume</div>
                <p className="mt-1 text-xs text-slate-300">
                  Load directly from: <code className="rounded bg-slate-800 px-1 py-0.5 text-cyan-300">C:\Users\Admin\Downloads\Harsh_Resume.pdf</code>
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Persists isolated copy to <code className="text-slate-300">storage/documents/Harsh_Resume.pdf</code> on F: drive.
                </p>
                <button
                  onClick={() => handleIngestResume()}
                  disabled={ingesting}
                  className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 py-2.5 text-sm font-semibold text-white shadow-lg transition hover:brightness-110 disabled:opacity-50"
                >
                  {ingesting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                  {ingesting ? 'Parsing & Ingesting...' : 'Parse & Ingest Authorized Resume'}
                </button>
              </div>

              <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950/40 p-4 text-center">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">Option B: Upload Alternate PDF</div>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={(e) => {
                    if (e.target.files?.[0]) {
                      handleIngestResume(e.target.files[0]);
                    }
                  }}
                  className="mt-2 text-xs text-slate-400 file:mr-2 file:rounded-lg file:border-0 file:bg-slate-800 file:px-3 file:py-1 file:text-xs file:font-semibold file:text-slate-200"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Navigation Tabs */}
      {/* ==================================================== */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-2">
        {[
          { key: 'personal', label: 'Personal Info', icon: User },
          { key: 'preferences', label: 'Career Preferences', icon: Sliders },
          { key: 'education', label: `Education (${profile.educations?.length || 0})`, icon: GraduationCap },
          { key: 'experience', label: `Experience (${profile.experiences?.length || 0})`, icon: Briefcase },
          { key: 'skills', label: `Skills (${profile.skills?.length || 0})`, icon: Code },
          { key: 'projects', label: `Projects (${profile.projects?.length || 0})`, icon: FolderGit2 },
          { key: 'certifications', label: `Certifications (${profile.certifications?.length || 0})`, icon: Award },
          { key: 'documents', label: `Documents (${profile.documents?.length || 0})`, icon: FileText },
          { key: 'links', label: 'Links', icon: LinkIcon },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                isActive
                  ? 'border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 shadow-sm'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ==================================================== */}
      {/* Tab 1: Personal Info */}
      {/* ==================================================== */}
      {activeTab === 'personal' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <h2 className="text-lg font-bold text-white">Personal Information</h2>
          <p className="text-xs text-slate-400">Core identity and contact details extracted from canonical resume.</p>

          <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Full Name *</label>
              <input
                type="text"
                value={profile.name}
                onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Email Address *</label>
              <input
                type="email"
                value={profile.email}
                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Phone Number</label>
              <input
                type="text"
                value={profile.phone || ''}
                onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Location</label>
              <input
                type="text"
                value={profile.location || ''}
                onChange={(e) => setProfile({ ...profile, location: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Executive Summary</label>
              <textarea
                rows={4}
                value={profile.summary || ''}
                onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
                placeholder="High-level engineering overview..."
              />
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 2: Career Preferences */}
      {/* ==================================================== */}
      {activeTab === 'preferences' && (
        <div className="space-y-6">
          {/* Target Roles with Priority Ordering */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Target Roles (Strict Priority Order)</h3>
                <p className="text-xs text-slate-400">Future matching prioritizes roles based on order position (top = highest priority).</p>
              </div>
            </div>

            <div className="mt-4 flex gap-2">
              <input
                type="text"
                value={newRoleInput}
                onChange={(e) => setNewRoleInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addRole()}
                placeholder="Add new target role (e.g. AI Systems Architect)"
                className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              />
              <button
                onClick={addRole}
                className="flex items-center gap-1 rounded-xl bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500"
              >
                <Plus className="h-4 w-4" /> Add Role
              </button>
            </div>

            <div className="mt-4 space-y-2">
              {(profile.preference_record?.target_roles || []).map((role, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-xl border border-slate-800/80 bg-slate-950/60 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-cyan-500/20 text-xs font-bold text-cyan-300">
                      #{idx + 1}
                    </span>
                    <span className="font-semibold text-slate-200">{role}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => moveRole(idx, 'up')}
                      disabled={idx === 0}
                      className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-30"
                      title="Move Up"
                    >
                      <ArrowUp className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => moveRole(idx, 'down')}
                      disabled={idx === (profile.preference_record?.target_roles?.length || 0) - 1}
                      className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-30"
                      title="Move Down"
                    >
                      <ArrowDown className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => removeRole(idx)}
                      className="rounded p-1 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Locations with Priority Ordering */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
            <h3 className="text-lg font-bold text-white">Preferred Locations (Priority Order)</h3>
            <p className="text-xs text-slate-400">Structured location targets with priority sequencing.</p>

            <div className="mt-4 flex gap-2">
              <input
                type="text"
                value={newLocationInput}
                onChange={(e) => setNewLocationInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addLocation()}
                placeholder="Add location (e.g. Noida, Delhi NCR)"
                className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
              />
              <button
                onClick={addLocation}
                className="flex items-center gap-1 rounded-xl bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500"
              >
                <Plus className="h-4 w-4" /> Add Location
              </button>
            </div>

            <div className="mt-4 space-y-2">
              {(profile.preference_record?.preferred_locations || []).map((loc, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between rounded-xl border border-slate-800/80 bg-slate-950/60 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-500/20 text-xs font-bold text-indigo-300">
                      #{idx + 1}
                    </span>
                    <span className="font-semibold text-slate-200">{loc}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => moveLocation(idx, 'up')}
                      disabled={idx === 0}
                      className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-30"
                    >
                      <ArrowUp className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => moveLocation(idx, 'down')}
                      disabled={idx === (profile.preference_record?.preferred_locations?.length || 0) - 1}
                      className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-30"
                    >
                      <ArrowDown className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => removeLocation(idx)}
                      className="rounded p-1 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Salary, Experience & Modes */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Salary Expectation */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">Compensation Expectation</h3>
                  <p className="text-xs text-slate-400">Preserved minimum baseline. Jobs lacking salary data are never rejected.</p>
                </div>
                <span
                  className={`rounded-full px-2.5 py-1 text-[11px] font-bold border ${
                    (profile.preference_record?.salary_status || 'NEEDS_CONFIRMATION') === 'CONFIRMED'
                      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                      : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                  }`}
                >
                  {(profile.preference_record?.salary_status || 'NEEDS_CONFIRMATION') === 'CONFIRMED'
                    ? 'CONFIRMED'
                    : 'NEEDS CONFIRMATION'}
                </span>
              </div>

              {/* Status & Confirmation Callout */}
              {(profile.preference_record?.salary_status || 'NEEDS_CONFIRMATION') === 'NEEDS_CONFIRMATION' && (
                <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-xs text-amber-200">
                  <div className="font-semibold text-amber-300 flex items-center gap-1.5">
                    <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
                    Salary Requirement Confirmation Needed
                  </div>
                  <p className="mt-1 text-slate-300">
                    Your initial input was: <span className="font-mono text-amber-200">"Salary atleast 3.5 to 4 LPA"</span>.
                    The system has preserved the minimum acceptable baseline: <strong className="text-white">₹3.5 LPA (₹3,50,000 INR)</strong> without assuming a higher floor.
                  </p>
                  {!editingSalary ? (
                    <div className="mt-3 flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => confirmSalary(350000)}
                        className="rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-emerald-500"
                      >
                        Confirm ₹3.5 LPA
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setSalaryInput(profile.preference_record?.minimum_salary ?? 350000);
                          setEditingSalary(true);
                        }}
                        className="rounded-lg border border-slate-700 bg-slate-800 px-3.5 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-700"
                      >
                        Edit Exact Minimum
                      </button>
                    </div>
                  ) : (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <input
                        type="number"
                        value={salaryInput}
                        onChange={(e) => setSalaryInput(parseFloat(e.target.value) || 0)}
                        placeholder="e.g. 400000"
                        className="w-36 rounded-lg border border-slate-700 bg-slate-950 px-3 py-1.5 text-xs text-white"
                      />
                      <button
                        type="button"
                        onClick={() => confirmSalary(salaryInput)}
                        className="rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-cyan-500"
                      >
                        Save & Confirm
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingSalary(false)}
                        className="rounded-lg px-2.5 py-1.5 text-xs text-slate-400 hover:text-white"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              )}

              {(profile.preference_record?.salary_status || 'NEEDS_CONFIRMATION') === 'CONFIRMED' && (
                <div className="mt-4 flex items-center justify-between rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-emerald-300">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    <span>
                      Confirmed Minimum Salary: <strong>₹{((profile.preference_record?.minimum_salary ?? 350000) / 100000).toFixed(1)} LPA</strong> (₹{profile.preference_record?.minimum_salary?.toLocaleString()} {profile.preference_record?.currency || 'INR'})
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSalaryInput(profile.preference_record?.minimum_salary ?? 350000);
                      setEditingSalary(true);
                    }}
                    className="text-[11px] font-semibold text-cyan-400 hover:underline"
                  >
                    Change
                  </button>
                </div>
              )}

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-400">Minimum Annual Salary</label>
                  <input
                    type="number"
                    value={profile.preference_record?.minimum_salary ?? 350000}
                    onChange={(e) =>
                      updatePref((p) => ({ ...p, minimum_salary: e.target.value ? parseFloat(e.target.value) : null }))
                    }
                    className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                  />
                  <span className="text-[11px] text-cyan-400">
                    ₹{((profile.preference_record?.minimum_salary ?? 350000) / 100000).toFixed(1)} LPA baseline
                  </span>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-400">Currency</label>
                  <input
                    type="text"
                    value={profile.preference_record?.currency || 'INR'}
                    onChange={(e) => updatePref((p) => ({ ...p, currency: e.target.value }))}
                    className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="text-xs font-semibold text-slate-400">Target Experience Preference</label>
                <input
                  type="text"
                  value={profile.preference_record?.experience_preference || '0-1 years'}
                  onChange={(e) => updatePref((p) => ({ ...p, experience_preference: e.target.value }))}
                  className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"
                />
                <span className="text-[11px] text-slate-500">
                  Candidate preference (0-1 years); does not overwrite your actual employment history. Flexible matching: jobs with differing requirements will not be auto-rejected.
                </span>
              </div>
            </div>

            {/* Work Modes & Relocation */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
              <h3 className="text-base font-bold text-white">Work Modes & Relocation</h3>
              <p className="text-xs text-slate-400">User specified: YES to all modes & relocation.</p>

              <div className="mt-4 space-y-3">
                <label className="text-xs font-semibold text-slate-400">Accepted Work Modes</label>
                <div className="flex flex-wrap gap-2">
                  {['Remote', 'Hybrid', 'On-site'].map((mode) => {
                    const isSelected = (profile.preference_record?.work_modes || []).includes(mode);
                    return (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => {
                          updatePref((p) => {
                            const modes = p.work_modes || [];
                            const next = isSelected ? modes.filter((m) => m !== mode) : [...modes, mode];
                            return { ...p, work_modes: next };
                          });
                        }}
                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                          isSelected
                            ? 'border-emerald-500/40 bg-emerald-500/20 text-emerald-300'
                            : 'border-slate-800 bg-slate-950 text-slate-400'
                        }`}
                      >
                        {isSelected && <Check className="h-3 w-3" />}
                        {mode}
                      </button>
                    );
                  })}
                </div>

                <div className="pt-2">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={profile.preference_record?.relocation_allowed ?? true}
                      onChange={(e) => updatePref((p) => ({ ...p, relocation_allowed: e.target.checked }))}
                      className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-cyan-500"
                    />
                    <span className="text-sm font-semibold text-slate-200">Willing to Relocate (YES)</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Company & Employment Types */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Company Types */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
              <h3 className="text-base font-bold text-white">Target Company Types</h3>
              <p className="text-xs text-slate-400">YES to all types across scale and sector.</p>
              <div className="mt-4 space-y-2">
                {[
                  { key: 'startup_allowed', label: 'Startups & Scaleups' },
                  { key: 'service_company_allowed', label: 'Service & Consulting Firms' },
                  { key: 'product_company_allowed', label: 'Product Companies' },
                ].map((item) => (
                  <label key={item.key} className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={(profile.preference_record as any)?.[item.key] ?? true}
                      onChange={(e) => updatePref((p) => ({ ...p, [item.key]: e.target.checked }))}
                      className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-cyan-500"
                    />
                    <span className="text-sm text-slate-300">{item.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Employment Types */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
              <h3 className="text-base font-bold text-white">Accepted Employment Types</h3>
              <p className="text-xs text-slate-400">Supported: Full-time, Internship, Contract, etc.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {['Full-time', 'Internship', 'Contract', 'Technical Consultant'].map((type) => {
                  const isSelected = (profile.preference_record?.employment_types || []).includes(type);
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        updatePref((p) => {
                          const types = p.employment_types || [];
                          const next = isSelected ? types.filter((t) => t !== type) : [...types, type];
                          return { ...p, employment_types: next };
                        });
                      }}
                      className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                        isSelected
                          ? 'border-indigo-500/40 bg-indigo-500/20 text-indigo-300'
                          : 'border-slate-800 bg-slate-950 text-slate-400'
                      }`}
                    >
                      {isSelected && <Check className="h-3 w-3" />}
                      {type}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 3: Education */}
      {/* ==================================================== */}
      {activeTab === 'education' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Education History</h2>
              <p className="text-xs text-slate-400">Degrees, institutions, and academic credentials.</p>
            </div>
            <button
              onClick={addEducation}
              className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-cyan-500"
            >
              <Plus className="h-4 w-4" /> Add Education
            </button>
          </div>

          <div className="mt-6 space-y-4">
            {(profile.educations || []).map((edu, idx) => (
              <div key={idx} className="relative rounded-xl border border-slate-800 bg-slate-950 p-5">
                <button
                  onClick={() => removeEducation(idx)}
                  className="absolute right-4 top-4 text-slate-500 hover:text-rose-400"
                  title="Remove Education"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Institution</label>
                    <input
                      type="text"
                      value={edu.institution}
                      onChange={(e) => updateEducation(idx, 'institution', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Degree</label>
                    <input
                      type="text"
                      value={edu.degree}
                      onChange={(e) => updateEducation(idx, 'degree', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Field of Study</label>
                    <input
                      type="text"
                      value={edu.field}
                      onChange={(e) => updateEducation(idx, 'field', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs font-semibold text-slate-400">Start Date</label>
                      <input
                        type="text"
                        value={edu.start_date}
                        onChange={(e) => updateEducation(idx, 'start_date', e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-400">End Date</label>
                      <input
                        type="text"
                        value={edu.end_date || ''}
                        onChange={(e) => updateEducation(idx, 'end_date', e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Location</label>
                    <input
                      type="text"
                      value={edu.location || ''}
                      onChange={(e) => updateEducation(idx, 'location', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Status</label>
                    <select
                      value={edu.status || 'CONFIRMED'}
                      onChange={(e) => updateEducation(idx, 'status', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    >
                      <option value="CONFIRMED">CONFIRMED (In Resume)</option>
                      <option value="USER_PROVIDED">USER_PROVIDED</option>
                      <option value="INFERRED">INFERRED</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 4: Experience */}
      {/* ==================================================== */}
      {activeTab === 'experience' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Work Experience</h2>
              <p className="text-xs text-slate-400">Roles, responsibilities, engineering deliverables, and achievements.</p>
            </div>
            <button
              onClick={addExperience}
              className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-cyan-500"
            >
              <Plus className="h-4 w-4" /> Add Experience
            </button>
          </div>

          <div className="mt-6 space-y-5">
            {(profile.experiences || []).map((exp, idx) => (
              <div key={idx} className="relative rounded-xl border border-slate-800 bg-slate-950 p-5">
                <button
                  onClick={() => removeExperience(idx)}
                  className="absolute right-4 top-4 text-slate-500 hover:text-rose-400"
                  title="Remove Experience"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Company</label>
                    <input
                      type="text"
                      value={exp.company}
                      onChange={(e) => updateExperience(idx, 'company', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Role / Title</label>
                    <input
                      type="text"
                      value={exp.title}
                      onChange={(e) => updateExperience(idx, 'title', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs font-semibold text-slate-400">Start Date</label>
                      <input
                        type="text"
                        value={exp.start_date}
                        onChange={(e) => updateExperience(idx, 'start_date', e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-400">End Date</label>
                      <input
                        type="text"
                        value={exp.end_date || ''}
                        disabled={exp.current}
                        onChange={(e) => updateExperience(idx, 'end_date', e.target.value)}
                        className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-40"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-4 pt-5">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={exp.current}
                        onChange={(e) => updateExperience(idx, 'current', e.target.checked)}
                        className="h-4 w-4 rounded border-slate-700 bg-slate-950 text-cyan-500"
                      />
                      <span className="text-xs font-semibold text-slate-200">Current Role</span>
                    </label>
                    <div className="flex-1">
                      <input
                        type="text"
                        placeholder="Location (e.g. Lucknow, India)"
                        value={exp.location || ''}
                        onChange={(e) => updateExperience(idx, 'location', e.target.value)}
                        className="w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-white"
                      />
                    </div>
                  </div>

                  <div className="md:col-span-2">
                    <label className="text-xs font-semibold text-slate-400">Responsibilities / Accomplishments</label>
                    <textarea
                      rows={3}
                      value={exp.description || ''}
                      onChange={(e) => updateExperience(idx, 'description', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                      placeholder="Bullet points and quantifiable outcomes..."
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 5: Skills */}
      {/* ==================================================== */}
      {activeTab === 'skills' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Skills Inventory</h2>
              <p className="text-xs text-slate-400">
                Categorized skills extracted from resume. No invented skills — 100% verified.
              </p>
            </div>
          </div>

          {/* Category Filter Pills */}
          <div className="mt-4 flex flex-wrap gap-1.5">
            {skillCategories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedSkillCategory(cat)}
                className={`rounded-lg px-3 py-1 text-xs font-semibold transition ${
                  selectedSkillCategory === cat
                    ? 'bg-cyan-500 text-slate-950 shadow'
                    : 'bg-slate-800/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Add Skill Form */}
          <div className="mt-5 grid grid-cols-1 gap-3 rounded-xl border border-slate-800/60 bg-slate-950/60 p-4 sm:grid-cols-4">
            <input
              type="text"
              value={newSkill.name}
              onChange={(e) => setNewSkill({ ...newSkill, name: e.target.value })}
              onKeyDown={(e) => e.key === 'Enter' && addSkill()}
              placeholder="Skill name (e.g. PyTorch)"
              className="rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none sm:col-span-2"
            />
            <select
              value={newSkill.category}
              onChange={(e) => setNewSkill({ ...newSkill, category: e.target.value })}
              className="rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white focus:border-cyan-500 focus:outline-none"
            >
              {skillCategories.filter((c) => c !== 'All').map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <button
              onClick={addSkill}
              className="flex items-center justify-center gap-1 rounded-xl bg-cyan-600 px-4 py-2 text-sm font-semibold text-white hover:bg-cyan-500"
            >
              <Plus className="h-4 w-4" /> Add Skill
            </button>
          </div>

          {/* Skills Grid */}
          <div className="mt-6 flex flex-wrap gap-2">
            {filteredSkills.map((sk, idx) => (
              <div
                key={idx}
                className="group flex items-center gap-2 rounded-xl border border-slate-800/80 bg-slate-950 px-3.5 py-1.5 text-xs text-slate-200 shadow-sm transition hover:border-cyan-500/40"
              >
                <span className="font-semibold text-white">{sk.name}</span>
                <span className="rounded bg-slate-800/60 px-1.5 py-0.5 text-[10px] text-cyan-300">
                  {sk.category || 'General'}
                </span>
                <button
                  onClick={() => removeSkill(idx)}
                  className="text-slate-500 opacity-60 transition hover:text-rose-400 group-hover:opacity-100"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 6: Projects */}
      {/* ==================================================== */}
      {activeTab === 'projects' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Projects Showcase</h2>
              <p className="text-xs text-slate-400">Featured technical implementations, architectures, and deployments.</p>
            </div>
            <button
              onClick={addProject}
              className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-cyan-500"
            >
              <Plus className="h-4 w-4" /> Add Project
            </button>
          </div>

          <div className="mt-6 space-y-4">
            {(profile.projects || []).map((proj, idx) => (
              <div key={idx} className="relative rounded-xl border border-slate-800 bg-slate-950 p-5">
                <button
                  onClick={() => removeProject(idx)}
                  className="absolute right-4 top-4 text-slate-500 hover:text-rose-400"
                  title="Remove Project"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Project Name</label>
                    <input
                      type="text"
                      value={proj.name}
                      onChange={(e) => updateProject(idx, 'name', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Technologies</label>
                    <input
                      type="text"
                      value={proj.technologies || ''}
                      onChange={(e) => updateProject(idx, 'technologies', e.target.value)}
                      placeholder="LangGraph, ChromaDB, FastAPI..."
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Role</label>
                    <input
                      type="text"
                      value={proj.role || ''}
                      onChange={(e) => updateProject(idx, 'role', e.target.value)}
                      placeholder="e.g. Creator / Engineer (Unspecified on resume)"
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-slate-400">Repository or Demo URL</label>
                    <input
                      type="text"
                      value={proj.url || ''}
                      onChange={(e) => updateProject(idx, 'url', e.target.value)}
                      placeholder="https://github.com/..."
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                  <div className="md:col-span-2">
                    <label className="text-xs font-semibold text-slate-400">Description & Highlights</label>
                    <textarea
                      rows={3}
                      value={proj.description || ''}
                      onChange={(e) => updateProject(idx, 'description', e.target.value)}
                      className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-900 px-3.5 py-2 text-sm text-white"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 7: Certifications */}
      {/* ==================================================== */}
      {activeTab === 'certifications' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Verified Certifications</h2>
              <p className="text-xs text-slate-400">
                Sourced from authorized GitHub repository (
                <a
                  href="https://github.com/itripathiharsh/Certifications"
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-400 underline"
                >
                  itripathiharsh/Certifications
                </a>
                ). Zero fabrication.
              </p>
            </div>
          </div>

          {/* Add Certification */}
          <div className="mt-5 rounded-xl border border-slate-800/80 bg-slate-950 p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Add New Certification</h4>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <input
                type="text"
                placeholder="Certification Name *"
                value={newCert.name || ''}
                onChange={(e) => setNewCert({ ...newCert, name: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white"
              />
              <input
                type="text"
                placeholder="Issuing Organization *"
                value={newCert.issuing_organization || ''}
                onChange={(e) => setNewCert({ ...newCert, issuing_organization: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white"
              />
              <input
                type="text"
                placeholder="Issue Date (e.g. 2025-07)"
                value={newCert.issue_date || ''}
                onChange={(e) => setNewCert({ ...newCert, issue_date: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white"
              />
              <input
                type="text"
                placeholder="Credential ID (optional)"
                value={newCert.credential_id || ''}
                onChange={(e) => setNewCert({ ...newCert, credential_id: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white"
              />
              <input
                type="text"
                placeholder="Verification URL (optional)"
                value={newCert.credential_url || ''}
                onChange={(e) => setNewCert({ ...newCert, credential_url: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white"
              />
              <button
                onClick={addCert}
                className="flex items-center justify-center gap-1 rounded-xl bg-cyan-600 px-4 py-2 text-xs font-semibold text-white hover:bg-cyan-500"
              >
                <Plus className="h-4 w-4" /> Save Certification
              </button>
            </div>
          </div>

          {/* Certifications List */}
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {(profile.certifications || []).map((cert, idx) => (
              <div
                key={idx}
                className="relative flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-950 p-4 transition hover:border-cyan-500/30"
              >
                <button
                  onClick={() => removeCert(idx)}
                  className="absolute right-3 top-3 text-slate-500 hover:text-rose-400"
                  title="Remove"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <div>
                  <div className="flex items-center gap-2">
                    <Award className="h-5 w-5 text-amber-400" />
                    <h4 className="font-bold text-white">{cert.name}</h4>
                  </div>
                  <p className="mt-1 text-xs font-medium text-cyan-300">{cert.issuing_organization}</p>
                  {cert.issue_date && <p className="mt-1 text-[11px] text-slate-400">Issued: {cert.issue_date}</p>}
                  {cert.credential_id && (
                    <p className="mt-0.5 text-[11px] text-slate-400">ID: <code className="text-slate-300">{cert.credential_id}</code></p>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-800/80 pt-3">
                  {cert.credential_url && (
                    <a
                      href={cert.credential_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-cyan-400 hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" /> Verify Credential
                    </a>
                  )}
                  {cert.source_url && (
                    <a
                      href={cert.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400 hover:text-white hover:underline"
                    >
                      <FolderGit2 className="h-3 w-3" /> Repository File
                    </a>
                  )}
                  <span
                    className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-semibold border ${
                      cert.status === 'NEEDS_CONFIRMATION'
                        ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                        : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    }`}
                  >
                    {cert.status === 'NEEDS_CONFIRMATION' ? 'NEEDS CONFIRMATION' : (cert.status || 'CONFIRMED')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 8: Documents */}
      {/* ==================================================== */}
      {activeTab === 'documents' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white">Application Documents</h2>
              <p className="text-xs text-slate-400">Resumes, generated cover letter models, and certificate documents.</p>
            </div>
            <button
              onClick={() => setShowIngestModal(true)}
              className="flex items-center gap-1.5 rounded-xl bg-cyan-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-cyan-500"
            >
              <UploadCloud className="h-4 w-4" /> Ingest Resume PDF
            </button>
          </div>

          {/* Quick Register Document */}
          <div className="mt-5 rounded-xl border border-slate-800/80 bg-slate-950 p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Register Document Reference</h4>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
              <input
                type="text"
                placeholder="Document Name (e.g. Resume_2026.pdf)"
                value={newDoc.name || ''}
                onChange={(e) => setNewDoc({ ...newDoc, name: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white sm:col-span-2"
              />
              <select
                value={newDoc.type || 'resume'}
                onChange={(e) => setNewDoc({ ...newDoc, type: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white"
              >
                <option value="resume">Resume</option>
                <option value="cover_letter">Cover Letter</option>
                <option value="certificate">Certificate</option>
                <option value="other">Other</option>
              </select>
              <button
                onClick={addDoc}
                className="flex items-center justify-center gap-1 rounded-xl bg-cyan-600 px-4 py-2 text-xs font-semibold text-white hover:bg-cyan-500"
              >
                <Plus className="h-4 w-4" /> Add Document
              </button>
              <input
                type="text"
                placeholder="File Storage Path (e.g. storage/documents/Harsh_Resume.pdf)"
                value={newDoc.file_path || ''}
                onChange={(e) => setNewDoc({ ...newDoc, file_path: e.target.value })}
                className="rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-xs text-white sm:col-span-4"
              />
            </div>
          </div>

          {/* Documents Grid */}
          <div className="mt-6 space-y-3">
            {(profile.documents || []).map((doc, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950 p-4"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">{doc.name}</h4>
                    <p className="text-xs text-slate-400">
                      Type: <span className="uppercase text-cyan-300">{doc.type}</span> • Path: <code className="text-[11px] text-slate-400">{doc.file_path}</code>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {doc.file_size && (
                    <span className="text-xs text-slate-500">{(doc.file_size / 1024).toFixed(1)} KB</span>
                  )}
                  <button
                    onClick={() => removeDoc(idx)}
                    className="text-slate-500 hover:text-rose-400"
                    title="Remove Document"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}

            {(!profile.documents || profile.documents.length === 0) && (
              <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-slate-500">
                No documents currently attached. Click "Ingest Resume PDF" to register Harsh's resume.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==================================================== */}
      {/* Tab 9: Professional Links */}
      {/* ==================================================== */}
      {activeTab === 'links' && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
          <h2 className="text-lg font-bold text-white">Professional Web Profiles</h2>
          <p className="text-xs text-slate-400">Authoritative URLs stored cleanly as structured profile fields.</p>

          <div className="mt-6 space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">LinkedIn Profile</label>
              <div className="mt-1.5 flex gap-2">
                <input
                  type="url"
                  value={profile.links?.linkedin || ''}
                  onChange={(e) =>
                    setProfile({ ...profile, links: { ...profile.links, linkedin: e.target.value } })
                  }
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white"
                />
                {profile.links?.linkedin && (
                  <a
                    href={profile.links.linkedin}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-cyan-400 hover:bg-slate-800"
                  >
                    <ExternalLink className="h-4 w-4" /> Visit
                  </a>
                )}
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">GitHub Profile</label>
              <div className="mt-1.5 flex gap-2">
                <input
                  type="url"
                  value={profile.links?.github || ''}
                  onChange={(e) =>
                    setProfile({ ...profile, links: { ...profile.links, github: e.target.value } })
                  }
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white"
                />
                {profile.links?.github && (
                  <a
                    href={profile.links.github}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-cyan-400 hover:bg-slate-800"
                  >
                    <ExternalLink className="h-4 w-4" /> Visit
                  </a>
                )}
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">Portfolio Website</label>
              <div className="mt-1.5 flex gap-2">
                <input
                  type="url"
                  value={profile.links?.portfolio || ''}
                  onChange={(e) =>
                    setProfile({ ...profile, links: { ...profile.links, portfolio: e.target.value } })
                  }
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2.5 text-sm text-white"
                />
                {profile.links?.portfolio && (
                  <a
                    href={profile.links.portfolio}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-cyan-400 hover:bg-slate-800"
                  >
                    <ExternalLink className="h-4 w-4" /> Visit
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

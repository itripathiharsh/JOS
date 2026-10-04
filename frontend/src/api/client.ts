const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export interface HealthResponse {
  status: string;
  database: string;
  environment: string;
  version: string;
}

export interface DashboardStats {
  jobs_discovered: number;
  relevant_jobs: number;
  strong_matches: number;
  applications: number;
  needs_attention: number;
}

export interface EducationItem {
  id?: string;
  institution: string;
  degree: string;
  field: string;
  start_date: string;
  end_date?: string | null;
  grade?: string | null;
  location?: string | null;
  details?: string | null;
  status?: string;
}

export interface ExperienceItem {
  id?: string;
  company: string;
  title: string;
  description?: string | null;
  start_date: string;
  end_date?: string | null;
  current: boolean;
  location?: string | null;
  employment_type?: string | null;
  responsibilities?: string[];
  achievements?: string[];
  technologies?: string | null;
  status?: string;
}

export interface SkillItem {
  id?: string;
  name: string;
  category?: string | null;
  proficiency?: string | null;
  status?: string;
}

export interface ProjectItem {
  id?: string;
  name: string;
  description?: string | null;
  technologies?: string | null;
  url?: string | null;
  role?: string | null;
  repo_url?: string | null;
  demo_url?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  status?: string;
}

export interface CertificationItem {
  id?: string;
  name: string;
  issuing_organization: string;
  issue_date?: string | null;
  expiry_date?: string | null;
  credential_id?: string | null;
  credential_url?: string | null;
  source_url?: string | null;
  document_ref?: string | null;
  status?: string;
}

export interface DocumentItem {
  id?: string;
  name: string;
  type: string; // resume, cover_letter, certificate, other
  file_path: string;
  file_size?: number | null;
  mime_type?: string | null;
  source?: string | null;
  created_at?: string;
}

export interface CandidatePreference {
  id?: string;
  target_roles: string[];
  role_priority: string[];
  preferred_locations: string[];
  location_priority: string[];
  work_modes: string[];
  minimum_salary?: number | null;
  currency: string;
  salary_status?: string;
  experience_preference: string;
  employment_types: string[];
  relocation_allowed: boolean;
  startup_allowed: boolean;
  service_company_allowed: boolean;
  product_company_allowed: boolean;
  internship_allowed: boolean;
  contract_allowed: boolean;
}

export interface ProfileCompletenessCriterion {
  criterion: string;
  is_required: boolean;
  weight: number;
  met: boolean;
  detail: string;
}

export interface ProfileCompletenessResponse {
  score: number;
  level: string; // Incomplete, Good, Complete
  missing_required: string[];
  missing_optional: string[];
  details: ProfileCompletenessCriterion[];
}

export interface CandidateProfile {
  id?: string;
  name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  summary?: string | null;
  preferences?: Record<string, any>;
  links?: {
    github?: string;
    linkedin?: string;
    portfolio?: string;
  };
  preference_record?: CandidatePreference | null;
  educations?: EducationItem[];
  experiences?: ExperienceItem[];
  skills?: SkillItem[];
  projects?: ProjectItem[];
  certifications?: CertificationItem[];
  documents?: DocumentItem[];
  completeness?: ProfileCompletenessResponse;
  created_at?: string;
  updated_at?: string;
}

export interface ResumeIngestResponse {
  success: boolean;
  message: string;
  candidate: Record<string, any>;
  provenance_summary: {
    confirmed: number;
    user_provided: number;
    inferred: number;
  };
  educations: EducationItem[];
  experiences: ExperienceItem[];
  skills: SkillItem[];
  projects: ProjectItem[];
  certifications: CertificationItem[];
  preferences: CandidatePreference;
  documents: DocumentItem[];
  completeness: ProfileCompletenessResponse;
}

export interface JobOccurrenceItem {
  job_id: string;
  source: string;
  external_job_id?: string | null;
  application_url?: string | null;
  canonical_url?: string | null;
  discovered_at?: string | null;
  last_seen_at?: string | null;
  is_canonical: boolean;
  duplicate_status: string;
  duplicate_confidence?: string | null;
}

export interface JobDuplicateLinkItem {
  id: string;
  canonical_job_id: string;
  duplicate_job_id: string;
  confidence: string;
  confidence_score: number;
  match_method: string;
  status: string;
  evidence?: Record<string, any> | null;
  created_at: string;
}

export interface BatchDeduplicationResult {
  jobs_evaluated: number;
  duplicates_found: number;
  possible_duplicates_found: number;
  duration_ms: number;
  message: string;
}

export interface JobItem {
  id: string;
  title: string;
  company: string;
  location?: string | null;
  work_mode?: string | null;
  description?: string | null;
  requirements?: string | null;
  responsibilities?: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  currency?: string;
  application_url?: string | null;
  source: string;
  external_job_id?: string | null;
  posted_at?: string | null;
  expires_at?: string | null;
  discovered_at: string;
  status: string;
  match_score?: number | null;
  fit_category?: string | null;
  raw_payload?: string | null;
  canonical_job_id?: string | null;
  is_canonical?: boolean;
  duplicate_status?: string;
  duplicate_confidence?: string | null;
  canonical_url?: string | null;
  occurrences_count?: number;
  sources?: string[];
  occurrences?: JobOccurrenceItem[];
  duplicate_links?: JobDuplicateLinkItem[];

  application_decision?: 'APPLY' | 'REVIEW' | 'SKIP' | string;
  decision_reason?: string;
  decision_risk_level?: string;
  decision_details?: ApplicationDecisionItem;
}

export interface ApplicationDecisionItem {
  id: string;
  job_id: string;
  candidate_id: string;
  decision: 'APPLY' | 'REVIEW' | 'SKIP' | string;
  confidence_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | string;
  reasons: string[];
  supporting_factors: string[];
  disqualifying_factors: string[];
  review_reasons: string[];
  evaluation_metadata: Record<string, any>;
  engine_version: string;
  decided_at: string;
  created_at: string;
  updated_at: string;
}

export interface DecisionBatchResult {
  processed: number;
  reused: number;
  new_or_updated: number;
  apply_count: number;
  review_count: number;
  skip_count: number;
  items: ApplicationDecisionItem[];
}

export interface DecisionListResponse {
  total: number;
  items: ApplicationDecisionItem[];
  apply_count: number;
  review_count: number;
  skip_count: number;
}

// Step 8: Application Preparation Engine Interfaces
export interface CandidateEvidenceItem {
  requirement: string;
  category: string;
  match_type: 'DIRECT' | 'TRANSFERABLE' | 'WEAK' | 'MISSING' | 'UNKNOWN';
  candidate_evidence?: string;
  source?: string;
  notes?: string;
}

export interface ExtractedJobRequirements {
  required_qualifications: string[];
  preferred_qualifications: string[];
  responsibilities: string[];
  keywords: string[];
  min_experience_years?: number;
  max_experience_years?: number;
  required_degree?: string;
  required_location?: string;
  work_mode?: string;
  employment_type?: string;
}

export interface ResumeRecommendation {
  recommended_document_id?: string;
  document_name: string;
  file_path: string;
  why_recommended: string;
  sufficiency_assessment: string;
  gaps_identified: string[];
  keep_points: string[];
  emphasize_points: string[];
  deemphasize_points: string[];
  add_if_true_points: string[];
}

export interface SkillsRecommendation {
  strong_match: string[];
  supporting_skills: string[];
  missing_skills: string[];
  do_not_claim: string[];
}

export interface GeneratedContent {
  application_summary: string;
  cover_letter: string;
  short_message: string;
  claim_safety_audit: {
    passed: boolean;
    violations: string[];
    warnings: string[];
    safety_verdict: string;
    verified_years_used?: string;
    verified_skills_used?: string;
  };
}

export interface ApplicationQuestionAnswer {
  question: string;
  category: string;
  proposed_answer?: string;
  answer_source: string;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  evidence: string;
  requires_human_confirmation: boolean;
  confirmed_answer?: string;
}

export interface ApplicationPreparationItem {
  id: string;
  application_id?: string;
  job_id: string;
  candidate_id: string;
  version: number;
  readiness_status: 'READY' | 'READY_WITH_REVIEW' | 'BLOCKED' | string;
  readiness_score: number;
  readiness_reasons: string[];
  job_snapshot: Record<string, any>;
  decision_snapshot: Record<string, any>;
  resume_recommendation: ResumeRecommendation;
  extracted_requirements: ExtractedJobRequirements;
  evidence_mapping: CandidateEvidenceItem[];
  skills_recommendation: SkillsRecommendation;
  generated_content: GeneratedContent;
  question_answers: ApplicationQuestionAnswer[];
  warnings: string[];
  human_confirmation_required: Array<{
    question: string;
    category: string;
    proposed_answer?: string;
    reason?: string;
  }>;
  user_overrides?: Record<string, any>;
  user_notes?: string;
  engine_version: string;
  prepared_at: string;
  created_at: string;
  updated_at: string;
}

export interface PreparationRequest {
  candidate_id?: string;
  force_regenerate?: boolean;
  allow_skip?: boolean;
  user_overrides?: Record<string, any>;
  user_notes?: string;
}

export interface PreparationUpdateRequest {
  user_overrides: Record<string, any>;
  user_notes?: string;
  candidate_id?: string;
}


export interface DimensionDetail {
  name: string;
  status: string;
  score: number;
  weight: number;
  is_known: boolean;
  explanation: string;
}

export interface MatchResultItem {
  id: string;
  job_id: string;
  candidate_id: string;
  engine_version: string;
  overall_score: number;
  fit_category: string;
  has_hard_mismatch: boolean;
  hard_requirement_status: string;
  hard_requirement_warnings: {
    category: string;
    severity: string;
    message: string;
    details?: Record<string, any>;
  }[];
  role_score: number;
  skill_score: number;
  experience_score: number;
  location_score: number;
  work_mode_score: number;
  salary_score: number;
  education_score: number;
  employment_type_score: number;
  matched_required_skills: { source: string; canonical: string }[];
  missing_required_skills: string[];
  matched_preferred_skills: { source: string; canonical: string }[];
  missing_preferred_skills: string[];
  dimension_details: Record<string, DimensionDetail>;
  concerns: string[];
  explanations: string[];
  data_completeness: number;
  data_completeness_level: string;
  calculated_at: string;
  created_at: string;
  updated_at: string;
}

export interface BulkMatchResult {
  processed: number;
  created: number;
  reused: number;
  results: MatchResultItem[];
}

export interface JobListResponse {
  items: JobItem[];
  total: number;
  skip?: number;
  limit?: number;
  canonical_count?: number;
  duplicate_count?: number;
  possible_duplicate_count?: number;
  apply_count?: number;
  review_count?: number;
  skip_count?: number;
}


export interface FetchJobsParams {
  keyword?: string;
  location?: string | null;
  remote?: boolean;
  limit?: number;
  source?: string;
}

export interface IngestionResult {
  success: boolean;
  source: string;
  query: string;
  jobs_fetched: number;
  jobs_created: number;
  jobs_updated: number;
  jobs_skipped: number;
  errors: string[];
  message: string;
}

export interface SourceStatusItem {
  id: string;
  source: string;
  status: string;
  last_checked?: string | null;
  last_success?: string | null;
  last_failure_at?: string | null;
  jobs_fetched: number;
  jobs_created: number;
  jobs_updated: number;
  error_message?: string | null;
}

export interface SearchStrategyQuery {
  query: string;
  canonical_role: string;
  strategy: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  reason: string;
  location_filter?: string | null;
  remote_filter?: boolean | null;
  limit?: number;
}

export interface DiscoveryConfig {
  max_total_queries?: number;
  max_queries_per_role?: number;
  max_tech_modifiers?: number;
  max_location_modifiers?: number;
  include_aliases?: boolean;
  include_work_mode_modifiers?: boolean;
  include_location_modifiers?: boolean;
  include_tech_modifiers?: boolean;
  min_priority?: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface DiscoveryPreviewResponse {
  candidate_id?: string | null;
  candidate_name: string;
  target_roles: string[];
  total_strategies: number;
  priority_breakdown: Record<string, number>;
  queries: SearchStrategyQuery[];
}

export interface DiscoveryQueryExecution {
  query: string;
  canonical_role: string;
  strategy: string;
  priority: string;
  status: string;
  jobs_fetched: number;
  jobs_created: number;
  jobs_updated: number;
  jobs_skipped: number;
  duration_ms?: number | null;
  error?: string | null;
}

export interface DiscoveryRunSummary {
  id: string;
  source: string;
  status: string;
  queries_generated: number;
  queries_executed: number;
  successful_queries: number;
  failed_queries: number;
  jobs_fetched: number;
  jobs_created: number;
  jobs_updated: number;
  jobs_skipped: number;
  duration_ms?: number | null;
  created_at: string;
  completed_at?: string | null;
  executed_queries: DiscoveryQueryExecution[];
  errors: string[];
}

export interface DiscoveryRunListResponse {
  items: DiscoveryRunSummary[];
  total: number;
}

export interface ApplicationItem {
  id: string;
  job_id?: string | null;
  candidate_id?: string | null;
  status: string;
  lifecycle_stage?: string;
  outcome_category?: string | null;
  outcome_provenance?: string;
  rejection_category?: string | null;
  rejection_reason?: string | null;
  last_outcome_date?: string | null;
  source?: string | null;
  application_url?: string | null;
  resume_used?: string | null;
  notes?: string | null;
  applied_at?: string | null;
  created_at: string;
  updated_at: string;
}


export interface ApplicationListResponse {
  items: ApplicationItem[];
  total: number;
}

export interface SystemSettings {
  app_name: string;
  app_version: string;
  app_env: string;
  database_connected: boolean;
  database_url_masked: string;
  storage_path: string;
  log_level: string;
  automation_status: Record<string, string>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const isFormData = options?.body instanceof FormData;
    const headers: Record<string, string> = {
      ...(options?.headers as Record<string, string> || {}),
    };
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errorMsg = `HTTP Error ${res.status}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) errorMsg = errorJson.detail;
      } catch {
        // Fallback to status text
      }
      throw new ApiError(res.status, errorMsg);
    }

    if (res.status === 204) {
      return null as T;
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    throw new Error(`Connection to backend failed (${endpoint}): ${err.message || 'Check if FastAPI is running'}`);
  }
}

export const api = {
  getHealth: () => request<HealthResponse>('/api/health'),
  getDashboardStats: () => request<DashboardStats>('/api/dashboard/stats'),
  
  // Profile
  getProfile: () => request<CandidateProfile | null>('/api/profile'),
  saveProfile: (profile: CandidateProfile) => request<CandidateProfile>('/api/profile', {
    method: 'POST',
    body: JSON.stringify(profile),
  }),
  patchProfile: (profile: Partial<CandidateProfile>) => request<CandidateProfile>('/api/profile', {
    method: 'PATCH',
    body: JSON.stringify(profile),
  }),
  getProfileCompleteness: () => request<ProfileCompletenessResponse>('/api/profile/completeness'),

  // Preferences
  getPreferences: () => request<CandidatePreference>('/api/profile/preferences'),
  updatePreferences: (prefs: Partial<CandidatePreference>) => request<CandidatePreference>('/api/profile/preferences', {
    method: 'PATCH',
    body: JSON.stringify(prefs),
  }),

  // Resume Ingestion
  ingestResume: (formData?: FormData) => request<ResumeIngestResponse>('/api/profile/resume/ingest', {
    method: 'POST',
    body: formData,
  }),

  // Educations
  getEducations: () => request<EducationItem[]>('/api/profile/educations'),
  addEducation: (item: EducationItem) => request<EducationItem>('/api/profile/educations', {
    method: 'POST',
    body: JSON.stringify(item),
  }),
  updateEducation: (id: string, item: Partial<EducationItem>) => request<EducationItem>(`/api/profile/educations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(item),
  }),
  deleteEducation: (id: string) => request<void>(`/api/profile/educations/${id}`, {
    method: 'DELETE',
  }),

  // Experiences
  getExperiences: () => request<ExperienceItem[]>('/api/profile/experiences'),
  addExperience: (item: ExperienceItem) => request<ExperienceItem>('/api/profile/experiences', {
    method: 'POST',
    body: JSON.stringify(item),
  }),
  updateExperience: (id: string, item: Partial<ExperienceItem>) => request<ExperienceItem>(`/api/profile/experiences/${id}`, {
    method: 'PUT',
    body: JSON.stringify(item),
  }),
  deleteExperience: (id: string) => request<void>(`/api/profile/experiences/${id}`, {
    method: 'DELETE',
  }),

  // Skills
  getSkills: () => request<SkillItem[]>('/api/profile/skills'),
  addSkill: (item: SkillItem) => request<SkillItem>('/api/profile/skills', {
    method: 'POST',
    body: JSON.stringify(item),
  }),
  updateSkill: (id: string, item: Partial<SkillItem>) => request<SkillItem>(`/api/profile/skills/${id}`, {
    method: 'PUT',
    body: JSON.stringify(item),
  }),
  deleteSkill: (id: string) => request<void>(`/api/profile/skills/${id}`, {
    method: 'DELETE',
  }),

  // Projects
  getProjects: () => request<ProjectItem[]>('/api/profile/projects'),
  addProject: (item: ProjectItem) => request<ProjectItem>('/api/profile/projects', {
    method: 'POST',
    body: JSON.stringify(item),
  }),
  updateProject: (id: string, item: Partial<ProjectItem>) => request<ProjectItem>(`/api/profile/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(item),
  }),
  deleteProject: (id: string) => request<void>(`/api/profile/projects/${id}`, {
    method: 'DELETE',
  }),

  // Certifications
  getCertifications: () => request<CertificationItem[]>('/api/profile/certifications'),
  addCertification: (item: CertificationItem) => request<CertificationItem>('/api/profile/certifications', {
    method: 'POST',
    body: JSON.stringify(item),
  }),
  updateCertification: (id: string, item: Partial<CertificationItem>) => request<CertificationItem>(`/api/profile/certifications/${id}`, {
    method: 'PUT',
    body: JSON.stringify(item),
  }),
  deleteCertification: (id: string) => request<void>(`/api/profile/certifications/${id}`, {
    method: 'DELETE',
  }),

  // Documents
  getDocuments: () => request<DocumentItem[]>('/api/profile/documents'),
  addDocument: (item: DocumentItem) => request<DocumentItem>('/api/profile/documents', {
    method: 'POST',
    body: JSON.stringify(item),
  }),
  deleteDocument: (id: string) => request<void>(`/api/profile/documents/${id}`, {
    method: 'DELETE',
  }),

  // Jobs & Applications
  getJobs: (params?: {
    skip?: number;
    limit?: number;
    search?: string;
    work_mode?: string;
    source?: string;
    status?: string;
    duplicate_status?: string;
    decision?: string;
    only_canonical?: boolean;
  }) => {
    const query = new URLSearchParams();
    if (params?.skip !== undefined) query.set('skip', params.skip.toString());
    if (params?.limit !== undefined) query.set('limit', params.limit.toString());
    if (params?.search) query.set('search', params.search);
    if (params?.work_mode && params.work_mode !== 'all') query.set('work_mode', params.work_mode);
    if (params?.source && params.source !== 'all') query.set('source', params.source);
    if (params?.status) query.set('status', params.status);
    if (params?.duplicate_status && params.duplicate_status !== 'all') query.set('duplicate_status', params.duplicate_status);
    if (params?.decision && params.decision !== 'all') query.set('decision', params.decision);
    if (params?.only_canonical) query.set('only_canonical', 'true');
    return request<JobListResponse>(`/api/jobs?${query.toString()}`);
  },
  getJobDetail: (id: string) => request<JobItem>(`/api/jobs/${id}`),
  getJobOccurrences: (id: string) => request<JobOccurrenceItem[]>(`/api/jobs/${id}/occurrences`),
  runBatchDeduplication: (limit = 500, dryRun = false) => request<BatchDeduplicationResult>('/api/jobs/deduplicate/batch', {
    method: 'POST',
    body: JSON.stringify({ limit, dry_run: dryRun }),
  }),
  fetchJobs: (payload: FetchJobsParams) => request<IngestionResult>('/api/jobs/fetch', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getSourcesStatus: () => request<SourceStatusItem[]>('/api/jobs/sources/status'),
  checkSourceHealth: (source: string) => request<any>(`/api/jobs/sources/${source}/health`, {
    method: 'POST',
  }),

  // Phase 4: Job Intelligence & Matching
  matchJob: (jobId: string, force = false) => request<MatchResultItem>(`/api/jobs/${jobId}/match?force=${force}`, {
    method: 'POST',
  }),
  getJobMatch: (jobId: string) => request<MatchResultItem>(`/api/jobs/${jobId}/match`),
  bulkMatchJobs: (limit = 50, force = false) => request<BulkMatchResult>('/api/jobs/match/bulk', {
    method: 'POST',
    body: JSON.stringify({ limit, force_recompute: force }),
  }),

  // Step 4: Search Everything / Search Expansion Engine
  previewDiscovery: (config?: DiscoveryConfig, source = 'remotive') => request<DiscoveryPreviewResponse>(`/api/discovery/preview?source=${source}`, {
    method: 'POST',
    body: config ? JSON.stringify(config) : undefined,
  }),
  runDiscovery: (payload: { source?: string; config?: DiscoveryConfig; dry_run?: boolean }) => request<DiscoveryRunSummary>('/api/discovery/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  getDiscoveryRuns: (skip = 0, limit = 20) => request<DiscoveryRunListResponse>(`/api/discovery/runs?skip=${skip}&limit=${limit}`),
  getDiscoveryRunDetail: (runId: string) => request<DiscoveryRunSummary>(`/api/discovery/runs/${runId}`),

  // Step 7: Application Decision Engine
  evaluateJobDecision: (jobId: string, force = false, candidateId?: string) => request<ApplicationDecisionItem>(
    `/api/jobs/${jobId}/decision?force=${force}${candidateId ? `&candidate_id=${candidateId}` : ''}`,
    { method: 'POST' }
  ),
  getJobDecision: (jobId: string, candidateId?: string) => request<ApplicationDecisionItem>(
    `/api/jobs/${jobId}/decision${candidateId ? `?candidate_id=${candidateId}` : ''}`
  ),
  bulkEvaluateDecisions: (limit = 50, force = false, onlyCanonical = true, candidateId?: string) => request<DecisionBatchResult>(
    `/api/jobs/decisions/bulk${candidateId ? `?candidate_id=${candidateId}` : ''}`,
    {
      method: 'POST',
      body: JSON.stringify({ limit, force_recompute: force, only_canonical: onlyCanonical }),
    }
  ),
  listDecisions: (params?: { decision?: string; risk_level?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.decision && params.decision !== 'all') query.set('decision', params.decision);
    if (params?.risk_level && params.risk_level !== 'all') query.set('risk_level', params.risk_level);
    if (params?.skip !== undefined) query.set('skip', params.skip.toString());
    if (params?.limit !== undefined) query.set('limit', params.limit.toString());
    return request<DecisionListResponse>(`/api/jobs/decisions?${query.toString()}`);
  },

  // Step 8: Application Preparation Engine
  prepareJobApplication: (jobId: string, payload?: PreparationRequest) => request<ApplicationPreparationItem>(
    `/api/jobs/${jobId}/prepare`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  getJobPreparation: (jobId: string, candidateId?: string) => request<ApplicationPreparationItem>(
    `/api/jobs/${jobId}/preparation${candidateId ? `?candidate_id=${candidateId}` : ''}`
  ),
  regenerateJobPreparation: (jobId: string, payload?: PreparationRequest) => request<ApplicationPreparationItem>(
    `/api/jobs/${jobId}/preparation/regenerate`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  updateJobPreparation: (jobId: string, payload: PreparationUpdateRequest) => request<ApplicationPreparationItem>(
    `/api/jobs/${jobId}/preparation`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }
  ),
  prepareApplication: (applicationId: string, payload?: PreparationRequest) => request<ApplicationPreparationItem>(
    `/api/applications/${applicationId}/prepare`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  getApplicationPreparation: (applicationId: string) => request<ApplicationPreparationItem>(
    `/api/applications/${applicationId}/preparation`
  ),
  regenerateApplicationPreparation: (applicationId: string, payload?: PreparationRequest) => request<ApplicationPreparationItem>(
    `/api/applications/${applicationId}/preparation/regenerate`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  updateApplicationPreparation: (applicationId: string, payload: PreparationUpdateRequest) => request<ApplicationPreparationItem>(
    `/api/applications/${applicationId}/preparation`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }
  ),

  getApplications: (skip = 0, limit = 50) => request<ApplicationListResponse>(`/api/applications?skip=${skip}&limit=${limit}`),
  getSettings: () => request<SystemSettings>('/api/settings'),

  // Step 9: Application Execution Layer API Methods
  executeApplication: (applicationId: string, payload?: ExecutionStartPayload) => request<ApplicationExecutionItem>(
    `/api/applications/${applicationId}/execute`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  getApplicationExecution: (applicationId: string) => request<ApplicationExecutionItem>(
    `/api/applications/${applicationId}/execution`
  ),
  getApplicationExecutions: (applicationId: string) => request<ApplicationExecutionListResponse>(
    `/api/applications/${applicationId}/executions`
  ),
  resumeApplicationExecution: (applicationId: string, executionId: string, payload: ExecutionResumePayload) => request<ApplicationExecutionItem>(
    `/api/applications/${applicationId}/execution/${executionId}/resume`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  ),
  approveAndSubmitApplication: (applicationId: string, executionId: string, context?: Record<string, any>) => request<ApplicationExecutionItem>(
    `/api/applications/${applicationId}/execution/${executionId}/approve-submit`,
    {
      method: 'POST',
      body: JSON.stringify({ context }),
    }
  ),
  cancelApplicationExecution: (applicationId: string, executionId: string, reason?: string) => request<ApplicationExecutionItem>(
    `/api/applications/${applicationId}/execution/${executionId}/cancel`,
    {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }
  ),
  retryApplicationExecution: (applicationId: string, executionId: string, payload?: ExecutionStartPayload) => request<ApplicationExecutionItem>(
    `/api/applications/${applicationId}/execution/${executionId}/retry`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  executeJob: (jobId: string, payload?: ExecutionStartPayload, candidateId?: string) => request<ApplicationExecutionItem>(
    `/api/jobs/${jobId}/execute${candidateId ? `?candidate_id=${candidateId}` : ''}`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  getJobExecution: (jobId: string, candidateId?: string) => request<ApplicationExecutionItem>(
    `/api/jobs/${jobId}/execution${candidateId ? `?candidate_id=${candidateId}` : ''}`
  ),

  // Step 10: Application Memory & Feedback Loop API Methods
  getApplicationMemory: (applicationId: string) => request<ApplicationMemoryItem>(
    `/api/applications/${applicationId}/memory`
  ),
  getApplicationTimeline: (applicationId: string) => request<TimelineItem[]>(
    `/api/applications/${applicationId}/timeline`
  ),
  updateApplicationOutcome: (applicationId: string, payload: OutcomeUpdatePayload) => request<ApplicationMemoryItem>(
    `/api/applications/${applicationId}/outcome`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  ),
  addApplicationNote: (applicationId: string, payload: NoteCreatePayload) => request<NoteItem>(
    `/api/applications/${applicationId}/notes`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  ),
  getApplicationNotes: (applicationId: string) => request<NoteItem[]>(
    `/api/applications/${applicationId}/notes`
  ),
  recordApplicationOverride: (applicationId: string, payload: OverrideCreatePayload) => request<OverrideItem>(
    `/api/applications/${applicationId}/override`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  ),
  getApplicationOverrides: (applicationId: string) => request<OverrideItem[]>(
    `/api/applications/${applicationId}/override`
  ),
  getMemoryFeedbackAnalytics: (candidateId?: string) => request<FeedbackReport>(
    `/api/analytics/application-memory${candidateId ? `?candidate_id=${candidateId}` : ''}`
  ),
  getJobOperatingSystem: (params?: { target_role?: string; work_mode?: string; source?: string }) => {
    const query = new URLSearchParams();
    if (params?.target_role) query.set('target_role', params.target_role);
    if (params?.work_mode && params.work_mode !== 'all') query.set('work_mode', params.work_mode);
    if (params?.source && params.source !== 'all') query.set('source', params.source);
    const qs = query.toString();
    return request<JobOperatingSystemResponse>(`/api/dashboard/operating-system${qs ? `?${qs}` : ''}`);
  },

  // Step 12: Controlled Autonomy, Task Queue & Human Approval API Methods
  getAutomationStatus: (candidateId?: string) => request<AutomationStatusResponse>(
    `/api/automation/status${candidateId ? `?candidate_id=${candidateId}` : ''}`
  ),
  getAutomationSettings: (candidateId?: string) => request<AutomationSettingsResponse>(
    `/api/automation/settings${candidateId ? `?candidate_id=${candidateId}` : ''}`
  ),
  updateAutomationSettings: (payload: AutomationSettingsUpdateRequest, candidateId?: string) => request<AutomationSettingsResponse>(
    `/api/automation/settings${candidateId ? `?candidate_id=${candidateId}` : ''}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  ),
  getAutomationTasks: (params?: { status?: string; task_type?: string; skip?: number; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.status && params.status !== 'all') query.set('status', params.status);
    if (params?.task_type && params.task_type !== 'all') query.set('task_type', params.task_type);
    if (params?.skip !== undefined) query.set('skip', params.skip.toString());
    if (params?.limit !== undefined) query.set('limit', params.limit.toString());
    const qs = query.toString();
    return request<AutomationTaskListResponse>(`/api/automation/tasks${qs ? `?${qs}` : ''}`);
  },
  retryAutomationTask: (taskId: string) => request<AutomationTaskResponse>(
    `/api/automation/tasks/${taskId}/retry`,
    { method: 'POST' }
  ),
  cancelAutomationTask: (taskId: string, reason?: string) => request<AutomationTaskResponse>(
    `/api/automation/tasks/${taskId}/cancel${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`,
    { method: 'POST' }
  ),
  triggerWorkerTick: (workerId?: string, maxTasks = 5) => request<WorkerTickResult>(
    `/api/automation/worker/tick?max_tasks=${maxTasks}${workerId ? `&worker_id=${encodeURIComponent(workerId)}` : ''}`,
    { method: 'POST' }
  ),
  triggerSchedulerTick: (candidateId?: string) => request<SchedulerTickResult>(
    `/api/automation/scheduler/tick${candidateId ? `?candidate_id=${candidateId}` : ''}`,
    { method: 'POST' }
  ),
  approveApplicationSubmission: (applicationId: string, payload?: ApplicationApprovalCreateRequest, candidateId?: string) => request<ApplicationApprovalResponse>(
    `/api/applications/${applicationId}/approve${candidateId ? `?candidate_id=${candidateId}` : ''}`,
    {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }
  ),
  revokeApplicationSubmissionApproval: (applicationId: string, reason?: string) => request<ApplicationApprovalResponse>(
    `/api/applications/${applicationId}/revoke-approval${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`,
    { method: 'POST' }
  ),
  getApplicationSubmissionApproval: (applicationId: string) => request<ApplicationApprovalResponse | null>(
    `/api/applications/${applicationId}/approval`
  ),
};

export interface ApplicationExecutionItem {
  id: string;
  application_id: string;
  job_id: string;
  candidate_id: string;
  preparation_id?: string | null;
  attempt_number: number;
  mode: 'MANUAL' | 'ASSISTED' | 'AUTOMATED' | string;
  source: string;
  status: 'NOT_STARTED' | 'READY' | 'AWAITING_APPROVAL' | 'OPENING' | 'NAVIGATING' | 'FILLING' | 'AWAITING_USER' | 'READY_TO_SUBMIT' | 'SUBMITTING' | 'SUBMITTED' | 'FAILED' | 'BLOCKED' | 'CANCELLED' | string;
  current_step?: string | null;
  step_details?: Record<string, any> | null;
  field_mappings?: Array<{
    form_field: {
      field_id: string;
      name: string;
      label: string;
      input_type: string;
      placeholder?: string;
      aria_label?: string;
      autocomplete?: string;
      options?: string[];
      is_required?: boolean;
      is_sensitive?: boolean;
      selector?: string;
    };
    matched_key: string;
    proposed_value: any;
    confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN' | string;
    requires_human_confirmation: boolean;
    confirmed_by_user: boolean;
    status: string;
    reason: string;
  }> | null;
  blocker_reason?: string | null;
  failure_reason?: string | null;
  requires_user_action: boolean;
  user_action_prompt?: string | null;
  submission_confirmed: boolean;
  confirmation_evidence?: Record<string, any> | null;
  browser_metadata?: Record<string, any> | null;
  started_at: string;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationExecutionListResponse {
  items: ApplicationExecutionItem[];
  total: number;
}

export interface ExecutionStartPayload {
  mode?: 'MANUAL' | 'ASSISTED' | 'AUTOMATED' | string;
  source?: string;
  allow_force?: boolean;
  context?: Record<string, any>;
}

export interface ExecutionResumePayload {
  user_inputs: Record<string, any>;
  context?: Record<string, any>;
}

// Step 10: Application Memory & Feedback Interfaces
export interface NoteItem {
  id: string;
  application_id: string;
  author: string;
  category: string;
  content: string;
  created_at: string;
}

export interface NoteCreatePayload {
  content: string;
  category?: string;
  author?: string;
}

export interface OverrideItem {
  id: string;
  application_id: string;
  original_decision: string;
  override_decision: string;
  override_type: string;
  reason?: string | null;
  created_at: string;
}

export interface OverrideCreatePayload {
  override_decision: string;
  original_decision?: string;
  override_type?: string;
  reason?: string;
}

export interface TimelineItem {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  description?: string | null;
  actor: string;
  provenance: string;
  metadata: Record<string, any>;
}

export interface ApplicationMemoryItem {
  id: string;
  job_id?: string | null;
  candidate_id?: string | null;
  lifecycle_stage: string;
  status: string;
  source?: string | null;
  application_url?: string | null;
  outcome_category?: string | null;
  outcome_provenance: string;
  rejection_category?: string | null;
  rejection_reason?: string | null;
  last_outcome_date?: string | null;
  candidate_snapshot?: Record<string, any> | null;
  job_snapshot?: Record<string, any> | null;
  decision_snapshot?: Record<string, any> | null;
  artifacts_snapshot?: Record<string, any> | null;
  notes: NoteItem[];
  overrides: OverrideItem[];
  timeline: TimelineItem[];
  created_at: string;
  updated_at: string;
}

export interface OutcomeUpdatePayload {
  lifecycle_stage: string;
  provenance?: string;
  rejection_category?: string;
  rejection_reason?: string;
  notes?: string;
}

export interface ConversionMetricItem {
  numerator: number;
  denominator: number;
  rate: number;
  is_statistically_significant: boolean;
  warning?: string | null;
}

export interface RolePerformanceItem {
  role: string;
  applications: number;
  interviews: number;
  offers: number;
  rejections: number;
  no_response: number;
  interview_rate: number;
  offer_rate: number;
  is_small_sample: boolean;
}

export interface SourcePerformanceItem {
  source: string;
  applications: number;
  interviews: number;
  offers: number;
  rejections: number;
  no_response: number;
  interview_rate: number;
  rejection_rate: number;
  is_small_sample: boolean;
}

export interface MatchTierItem {
  tier: string;
  label: string;
  applications: number;
  interviews: number;
  offers: number;
  rejections: number;
  interview_rate: number;
}

export interface WorkModeItem {
  work_mode: string;
  applications: number;
  interviews: number;
  offers: number;
  interview_rate: number;
}

export interface ResumePerformanceItem {
  resume_name: string;
  applications: number;
  interviews: number;
  offers: number;
  rejections: number;
  interview_rate: number;
  note: string;
}

export interface RejectionPatternItem {
  category: string;
  count: number;
  percentage: number;
  sample_reasons: string[];
}

export interface DecisionAlignmentData {
  matrix: Record<string, {
    total: number;
    interviews: number;
    offers: number;
    rejections: number;
  }>;
  total_overrides_recorded: number;
}

export interface FeedbackReport {
  total_applications: number;
  lifecycle_counts: Record<string, number>;
  conversions: {
    application_to_interview: ConversionMetricItem;
    application_to_offer: ConversionMetricItem;
    interview_to_offer: ConversionMetricItem;
    submitted_total: number;
  };
  role_performance: RolePerformanceItem[];
  source_performance: SourcePerformanceItem[];
  match_tier_performance: MatchTierItem[];
  work_mode_performance: WorkModeItem[];
  resume_performance: ResumePerformanceItem[];
  rejection_patterns: {
    total_rejections: number;
    breakdown: RejectionPatternItem[];
  };
  decision_alignment: DecisionAlignmentData;
  observations: Array<{
    type: 'INFO' | 'CAUTION' | 'OBSERVATION' | 'SUMMARY' | string;
    message: string;
  }>;
  sample_size_alert?: string | null;
}

// Step 11: Job Operating System Dashboard Types
export interface DashboardHealthKPIs {
  jobs_discovered: number;
  canonical_jobs: number;
  high_relevance_jobs: number;
  ready_to_apply: number;
  review_required: number;
  applications_submitted: number;
  active_interviews: number;
  offers_received: number;
  awaiting_response: number;
}

export interface AttentionQueueItem {
  id: string;
  priority: 'HIGH' | 'MEDIUM' | 'INFO';
  category: 'APPROVAL' | 'BLOCKED' | 'DECISION' | 'PREPARATION' | 'FOLLOW_UP' | 'INTERVIEW' | 'PROFILE';
  title: string;
  description: string;
  job_id?: string | null;
  application_id?: string | null;
  action_label: string;
  action_target: 'jobs' | 'applications' | 'profile';
  action_type: 'open_job' | 'open_execution' | 'open_preparation' | 'open_memory' | 'open_profile';
  metadata?: Record<string, any> | null;
  created_at?: string | null;
}

export interface DashboardFunnelStep {
  stage: string;
  label: string;
  count: number;
  conversion_from_prev?: number | null;
}

export interface DashboardFunnel {
  discovered: number;
  unique_canonical: number;
  career_aligned: number;
  decided_apply_review: number;
  prepared: number;
  submitted: number;
  interviews: number;
  offers: number;
  steps: DashboardFunnelStep[];
}

export interface PipelineStageCount {
  stage: string;
  label: string;
  count: number;
  is_terminal: boolean;
  is_positive: boolean;
  is_active: boolean;
}

export interface MatchQualityDistribution {
  high_relevance: number;
  good_relevance: number;
  partial_relevance: number;
  low_relevance: number;
  hard_mismatches: number;
  insufficient_data: number;
}

export interface TopOpportunityItem {
  id: string;
  title: string;
  company: string;
  source: string;
  location?: string | null;
  work_mode?: string | null;
  salary_display?: string | null;
  match_score?: number | null;
  fit_category?: string | null;
  decision?: string | null;
  decision_reasons: string[];
  hard_requirement_status?: string | null;
  is_canonical: boolean;
  application_id?: string | null;
  preparation_status?: string | null;
  execution_status?: string | null;
  posted_at?: string | null;
}

export interface SourceHealthItem {
  source: string;
  status: string; // active, idle, degraded, error
  last_checked?: string | null;
  last_success?: string | null;
  jobs_fetched: number;
  jobs_created: number;
  jobs_updated: number;
  error_message?: string | null;
}

export interface ProfileHealthSummary {
  completeness_score: number;
  is_ready_for_apply: boolean;
  missing_critical_items: string[];
  pending_confirmations: string[];
  has_resume: boolean;
  target_roles_count: number;
}

export interface RecentActivityItem {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  actor: string;
  job_id?: string | null;
  application_id?: string | null;
  job_title?: string | null;
  company?: string | null;
}

export interface FeedbackSummaryKPIs {
  submitted_count: number;
  app_to_interview_rate: number;
  app_to_interview_fraction: string;
  app_to_offer_rate: number;
  app_to_offer_fraction: string;
  interview_to_offer_rate: number;
  interview_to_offer_fraction: string;
  sample_size_alert?: string | null;
  top_observations: string[];
}

export interface AutomationTelemetrySummary {
  mode: string;
  is_active: boolean;
  pending_tasks: number;
  running_tasks: number;
  failed_tasks: number;
  blocked_tasks: number;
  last_run?: string | null;
}

export interface JobOperatingSystemResponse {
  health_kpis: DashboardHealthKPIs;
  action_queue: AttentionQueueItem[];
  funnel: DashboardFunnel;
  pipeline: PipelineStageCount[];
  match_quality: MatchQualityDistribution;
  top_opportunities: TopOpportunityItem[];
  source_health: SourceHealthItem[];
  profile_health: ProfileHealthSummary;
  recent_activity: RecentActivityItem[];
  feedback_summary: FeedbackSummaryKPIs;
  automation_telemetry?: AutomationTelemetrySummary | null;
  generated_at: string;
}

export interface AutomationSettingsResponse {
  id: string;
  candidate_id: string;
  mode: 'MANUAL' | 'ASSISTED' | 'CONTROLLED_AUTO' | string;
  job_discovery_enabled: boolean;
  matching_enabled: boolean;
  deduplication_enabled: boolean;
  preparation_enabled: boolean;
  submission_requires_approval: boolean;
  discovery_interval_hours: number;
  max_daily_preparations: number;
  stale_job_threshold_days: number;
  created_at: string;
  updated_at: string;
}

export interface AutomationSettingsUpdateRequest {
  mode?: string;
  job_discovery_enabled?: boolean;
  matching_enabled?: boolean;
  deduplication_enabled?: boolean;
  preparation_enabled?: boolean;
  discovery_interval_hours?: number;
  max_daily_preparations?: number;
  stale_job_threshold_days?: number;
}

export interface AutomationTaskResponse {
  id: string;
  task_type: string;
  candidate_id?: string | null;
  application_id?: string | null;
  job_id?: string | null;
  status: 'PENDING' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'RETRY_WAIT' | 'CANCELLED' | 'BLOCKED' | string;
  priority: number;
  attempts: number;
  max_attempts: number;
  available_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  locked_at?: string | null;
  locked_by?: string | null;
  last_error?: string | null;
  error_category?: string | null;
  idempotency_key: string;
  payload?: Record<string, any> | null;
  result?: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface AutomationTaskListResponse {
  items: AutomationTaskResponse[];
  total: number;
}

export interface AutomationStatusResponse {
  mode: string;
  is_active: boolean;
  scheduler_enabled: boolean;
  worker_enabled: boolean;
  pending_tasks: number;
  running_tasks: number;
  failed_tasks: number;
  blocked_tasks: number;
  succeeded_tasks: number;
  last_successful_run?: string | null;
  next_scheduled_run?: string | null;
  settings: AutomationSettingsResponse;
}

export interface ApplicationApprovalResponse {
  id: string;
  application_id: string;
  job_id: string;
  candidate_id: string;
  preparation_id?: string | null;
  preparation_version: number;
  approved_by: string;
  approved_at: string;
  approval_scope: string;
  expires_at?: string | null;
  revoked_at?: string | null;
  approval_status: 'PENDING' | 'APPROVED' | 'REVOKED' | 'EXPIRED' | 'NOT_REQUIRED' | string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationApprovalCreateRequest {
  scope?: string;
  expires_hours?: number;
  notes?: string;
}

export interface WorkerTickResult {
  worker_id: string;
  claimed_count: number;
  succeeded_count: number;
  failed_count: number;
  blocked_count: number;
  recovered_count: number;
  task_ids: string[];
}

export interface SchedulerTickResult {
  enqueued_count: number;
  skipped_count: number;
  task_types_enqueued: string[];
  enqueued_task_ids: string[];
}





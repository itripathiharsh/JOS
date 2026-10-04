import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  Search,
  Filter,
  ExternalLink,
  RefreshCw,
  DownloadCloud,
  CheckCircle2,
  AlertCircle,
  MapPin,
  DollarSign,
  Building2,
  ChevronLeft,
  ChevronRight,
  X,
  Radio,
  FileText,
  Sparkles,
  Target,
  AlertTriangle,
  Layers,
  ShieldCheck,
  Check,
  HelpCircle,
  Clock,
  GraduationCap,
  Compass,
  Play,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  JobItem,
  IngestionResult,
  SourceStatusItem,
  MatchResultItem,
  BulkMatchResult,
  DiscoveryPreviewResponse,
  DiscoveryRunSummary,
  DecisionBatchResult,
} from '../api/client';
import { ApplicationPreparationModal } from '../components/ApplicationPreparationModal';
import { ApplicationExecutionModal } from '../components/ApplicationExecutionModal';


export const JobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination & Filtering state
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');
  const [workModeFilter, setWorkModeFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [duplicateFilter, setDuplicateFilter] = useState('all');
  const [decisionFilter, setDecisionFilter] = useState('all');

  // Step 7 Decision Engine State
  const [evaluatingDecisionJobId, setEvaluatingDecisionJobId] = useState<string | null>(null);
  const [showBulkDecisionModal, setShowBulkDecisionModal] = useState(false);
  const [bulkDecisionLoading, setBulkDecisionLoading] = useState(false);
  const [bulkDecisionLimit, setBulkDecisionLimit] = useState(50);
  const [bulkDecisionForce, setBulkDecisionForce] = useState(false);
  const [bulkDecisionCanonicalOnly, setBulkDecisionCanonicalOnly] = useState(true);
  const [bulkDecisionResult, setBulkDecisionResult] = useState<DecisionBatchResult | null>(null);
  const [bulkDecisionError, setBulkDecisionError] = useState<string | null>(null);

  // Step 8 Application Preparation Modal
  const [prepModalJobId, setPrepModalJobId] = useState<string | null>(null);

  // Step 9 Application Execution Modal
  const [execModalJob, setExecModalJob] = useState<JobItem | null>(null);

  // Source Statuses
  const [sourceStatuses, setSourceStatuses] = useState<SourceStatusItem[]>([]);

  // Selected Job for Details Modal
  const [selectedJob, setSelectedJob] = useState<JobItem | null>(null);


  // Phase 4 Match Analysis Modal state
  const [selectedMatch, setSelectedMatch] = useState<MatchResultItem | null>(null);
  const [selectedMatchJob, setSelectedMatchJob] = useState<JobItem | null>(null);
  const [showMatchModal, setShowMatchModal] = useState(false);
  const [matchingJobId, setMatchingJobId] = useState<string | null>(null);
  const [matchError, setMatchError] = useState<string | null>(null);

  // Phase 4 Bulk Matching Modal state
  const [showBulkMatchModal, setShowBulkMatchModal] = useState(false);
  const [bulkMatching, setBulkMatching] = useState(false);
  const [bulkMatchLimit, setBulkMatchLimit] = useState(25);
  const [bulkMatchForce, setBulkMatchForce] = useState(false);
  const [bulkMatchResult, setBulkMatchResult] = useState<BulkMatchResult | null>(null);
  const [bulkMatchError, setBulkMatchError] = useState<string | null>(null);

  // Ingestion Modal State
  const [showFetchModal, setShowFetchModal] = useState(false);
  const [fetchKeyword, setFetchKeyword] = useState('AI Engineer');
  const [fetchLocation, setFetchLocation] = useState('');
  const [fetchLimit, setFetchLimit] = useState(20);
  const [fetchSource, setFetchSource] = useState('remotive');
  const [fetching, setFetching] = useState(false);
  const [fetchResult, setFetchResult] = useState<IngestionResult | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Step 4 Discovery Engine State
  const [showDiscoveryModal, setShowDiscoveryModal] = useState(false);
  const [discoveryLimit, setDiscoveryLimit] = useState(10);
  const [discoveryRunning, setDiscoveryRunning] = useState(false);
  const [discoveryPreviewing, setDiscoveryPreviewing] = useState(false);
  const [discoveryPreview, setDiscoveryPreview] = useState<DiscoveryPreviewResponse | null>(null);
  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryRunSummary | null>(null);
  const [discoveryError, setDiscoveryError] = useState<string | null>(null);

  // Load jobs from API with backend filtering & pagination
  const loadJobs = async (resetPage = false) => {
    setLoading(true);
    setError(null);
    try {
      const currentPage = resetPage ? 1 : page;
      if (resetPage) setPage(1);

      const skip = (currentPage - 1) * pageSize;
      const data = await api.getJobs({
        skip,
        limit: pageSize,
        search: searchTerm.trim() || undefined,
        work_mode: workModeFilter !== 'all' ? workModeFilter : undefined,
        source: sourceFilter !== 'all' ? sourceFilter : undefined,
        duplicate_status: duplicateFilter !== 'all' ? duplicateFilter : undefined,
        decision: decisionFilter !== 'all' ? decisionFilter : undefined,
      });

      setJobs(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load jobs from backend');
    } finally {
      setLoading(false);
    }
  };

  // Load source operational status
  const loadSourceStatuses = async () => {
    try {
      const statuses = await api.getSourcesStatus();
      setSourceStatuses(statuses);
    } catch {
      // Non-critical, ignore in background
    }
  };

  useEffect(() => {
    loadJobs();
    loadSourceStatuses();
  }, [page, pageSize, workModeFilter, sourceFilter, duplicateFilter, decisionFilter]);


  // Handle Search Submission
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadJobs(true);
  };

  // Open Job Details Modal
  const handleOpenDetails = async (jobId: string) => {
    try {
      const detailed = await api.getJobDetail(jobId);
      setSelectedJob(detailed);
    } catch {
      const local = jobs.find((j) => j.id === jobId) || null;
      setSelectedJob(local);
    }
  };

  // Open Match Analysis Modal
  const handleOpenMatch = async (job: JobItem, force = false) => {
    setMatchingJobId(job.id);
    setMatchError(null);
    setSelectedMatchJob(job);
    setShowMatchModal(true);

    try {
      const match = await api.matchJob(job.id, force);
      setSelectedMatch(match);

      // Update local job state if score changed
      setJobs((prev) =>
        prev.map((j) =>
          j.id === job.id
            ? { ...j, match_score: match.overall_score, fit_category: match.fit_category }
            : j
        )
      );
    } catch (err: any) {
      setMatchError(err.message || 'Failed to analyze job match');
    } finally {
      setMatchingJobId(null);
    }
  };

  // Trigger Bulk Matching
  const handleExecuteBulkMatch = async () => {
    setBulkMatching(true);
    setBulkMatchError(null);
    setBulkMatchResult(null);

    try {
      const result = await api.bulkMatchJobs(bulkMatchLimit, bulkMatchForce);
      setBulkMatchResult(result);
      await loadJobs(false);
    } catch (err: any) {
      setBulkMatchError(err.message || 'Bulk matching execution failed');
    } finally {
      setBulkMatching(false);
    }
  };

  // Trigger Real Manual Ingestion
  const handleExecuteFetch = async () => {
    setFetching(true);
    setFetchError(null);
    setFetchResult(null);

    try {
      const result = await api.fetchJobs({
        keyword: fetchKeyword.trim(),
        location: fetchLocation.trim() || null,
        remote: true,
        limit: fetchLimit,
        source: fetchSource,
      });

      setFetchResult(result);
      await loadJobs(true);
      await loadSourceStatuses();
    } catch (err: any) {
      setFetchError(err.message || 'Failed to execute job fetch');
    } finally {
      setFetching(false);
    }
  };

  // Step 4: Preview Discovery Strategies
  const handlePreviewDiscovery = async (limitOverride?: number) => {
    setDiscoveryPreviewing(true);
    setDiscoveryError(null);
    try {
      const prev = await api.previewDiscovery({ max_total_queries: limitOverride ?? discoveryLimit });
      setDiscoveryPreview(prev);
    } catch (err: any) {
      setDiscoveryError(err.message || 'Failed to generate discovery strategy preview');
    } finally {
      setDiscoveryPreviewing(false);
    }
  };

  // Step 4: Execute Real Discovery Run
  const handleExecuteDiscovery = async () => {
    setDiscoveryRunning(true);
    setDiscoveryError(null);
    try {
      const summary = await api.runDiscovery({
        source: 'remotive',
        config: { max_total_queries: discoveryLimit },
      });
      setDiscoveryResult(summary);
      await loadJobs(true);
      await loadSourceStatuses();
    } catch (err: any) {
      setDiscoveryError(err.message || 'Discovery run execution failed');
    } finally {
      setDiscoveryRunning(false);
    }
  };


  // Step 7: Evaluate Single Job Decision
  const handleEvaluateSingleDecision = async (jobId: string, force = true) => {
    setEvaluatingDecisionJobId(jobId);
    try {
      const decision = await api.evaluateJobDecision(jobId, force);
      if (selectedJob && selectedJob.id === jobId) {
        setSelectedJob({
          ...selectedJob,
          application_decision: decision.decision,
          decision_reason: decision.reasons?.[0],
          decision_risk_level: decision.risk_level,
          decision_details: decision,
        });
      }
      setJobs((prev) =>
        prev.map((j) =>
          j.id === jobId
            ? {
                ...j,
                application_decision: decision.decision,
                decision_reason: decision.reasons?.[0],
                decision_risk_level: decision.risk_level,
                decision_details: decision,
              }
            : j
        )
      );
    } catch (err: any) {
      alert(`Decision evaluation error: ${err.message || 'Unknown error'}`);
    } finally {
      setEvaluatingDecisionJobId(null);
    }
  };

  // Step 7: Bulk Evaluate Decisions
  const handleRunBulkDecisions = async () => {
    setBulkDecisionLoading(true);
    setBulkDecisionError(null);
    try {
      const res = await api.bulkEvaluateDecisions(bulkDecisionLimit, bulkDecisionForce, bulkDecisionCanonicalOnly);
      setBulkDecisionResult(res);
      await loadJobs();
    } catch (err: any) {
      setBulkDecisionError(err.message || 'Failed to run application decision engine');
    } finally {
      setBulkDecisionLoading(false);
    }
  };


  const totalPages = Math.ceil(total / pageSize) || 1;

  const quickQueries = [
    'AI Engineer',
    'Machine Learning',
    'Backend Engineer',
    'Python',
    'Forward Deployed Engineer',
    'Full Stack',
  ];

  const getFitBadgeStyle = (category: string) => {
    switch (category) {
      case 'HIGH_RELEVANCE':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'GOOD_RELEVANCE':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'PARTIAL_RELEVANCE':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'LOW_RELEVANCE':
        return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30';
      case 'INSUFFICIENT_DATA':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getDimensionStatusBadge = (status: string) => {
    const s = status.toUpperCase();
    if (s === 'STRONG' || s === 'FIT') {
      return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">FIT</span>;
    }
    if (s === 'MODERATE' || s === 'PARTIAL') {
      return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">PARTIAL</span>;
    }
    if (s === 'WEAK' || s === 'MISMATCH' || s === 'BELOW_PREFERENCE') {
      return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">GAP</span>;
    }
    return <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">UNKNOWN</span>;
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Job Inventory & Intelligence</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-indigo-400" />
              Phase 4 Matching Active
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic match engine evaluating profiles against stored jobs. Total vacancies: <span className="font-semibold text-slate-200">{total}</span>
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {sourceStatuses.map((s) => (
            <div
              key={s.id}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-300"
              title={`Fetched: ${s.jobs_fetched} | Created: ${s.jobs_created} | Updated: ${s.jobs_updated}`}
            >
              <Radio className={`w-3 h-3 ${s.status === 'active' || s.status === 'healthy' ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
              <span className="uppercase text-slate-400">{s.source}:</span>
              <span className="font-medium text-emerald-300 capitalize">{s.status}</span>
              <span className="text-slate-500">({s.jobs_fetched} fetched)</span>
            </div>
          ))}

          {/* Bulk Match Button */}
          <button
            onClick={() => {
              setBulkMatchResult(null);
              setBulkMatchError(null);
              setShowBulkMatchModal(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white shadow-sm transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Bulk Match Jobs
          </button>

          {/* Step 4 Discovery Engine Button */}
          <button
            onClick={() => {
              setDiscoveryResult(null);
              setDiscoveryError(null);
              setShowDiscoveryModal(true);
              if (!discoveryPreview) {
                handlePreviewDiscovery();
              }
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-xs font-semibold text-white shadow-sm transition"
          >
            <Compass className="w-3.5 h-3.5" />
            Discovery Engine
          </button>

          {/* Step 7 Decision Engine Button */}
          <button
            onClick={() => {
              setBulkDecisionResult(null);
              setBulkDecisionError(null);
              setShowBulkDecisionModal(true);
            }}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-xs font-semibold text-white shadow-sm transition"
          >
            <Target className="w-3.5 h-3.5" />
            Decision Engine
          </button>

          {/* Fetch Real Jobs Button */}
          <button
            onClick={() => {
              setFetchResult(null);
              setFetchError(null);
              setShowFetchModal(true);
            }}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-sm transition"
          >
            <DownloadCloud className="w-4 h-4" />
            Fetch Real Jobs
          </button>

          <button
            onClick={() => loadJobs(false)}
            disabled={loading}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by job title, company, or location (Press Enter)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-20 py-2 bg-[#0e1626] border border-slate-800 rounded-md text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
          />
          <button
            type="submit"
            className="absolute right-2 top-1.5 px-2.5 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={workModeFilter}
            onChange={(e) => setWorkModeFilter(e.target.value)}
            className="bg-[#0e1626] border border-slate-800 text-xs text-slate-300 rounded-md px-3 py-2 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="all">All Work Modes</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">On-site</option>
          </select>

          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="bg-[#0e1626] border border-slate-800 text-xs text-slate-300 rounded-md px-3 py-2 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="all">All Sources</option>
            <option value="remotive">Remotive</option>
            <option value="manual">Manual</option>
          </select>

          <select
            value={duplicateFilter}
            onChange={(e) => setDuplicateFilter(e.target.value)}
            className="bg-[#0e1626] border border-slate-800 text-xs text-slate-300 rounded-md px-3 py-2 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="all">All Vacancies</option>
            <option value="canonical">Canonical Only</option>
            <option value="possible_duplicate">Possible Duplicates</option>
            <option value="duplicate">Duplicates</option>
          </select>

          <select
            value={decisionFilter}
            onChange={(e) => {
              setDecisionFilter(e.target.value);
              setPage(1);
            }}
            className="bg-[#0e1626] border border-slate-800 text-xs text-slate-300 rounded-md px-3 py-2 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="all">All Decisions</option>
            <option value="APPLY">Decision: APPLY</option>
            <option value="REVIEW">Decision: REVIEW</option>
            <option value="SKIP">Decision: SKIP</option>
          </select>
        </div>
      </div>


      {/* Error state */}
      {error && (
        <div className="p-4 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Content Area */}
      {loading ? (
        <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-6 h-6 animate-spin text-indigo-500" />
          <span>Loading normalized jobs from database...</span>
        </div>
      ) : jobs.length === 0 ? (
        /* Empty State */
        <div className="p-16 rounded-xl bg-[#0e1626] border border-slate-800 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <Briefcase className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-200">No jobs found in inventory</h2>
            <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
              Fetch real job listings from Remotive public API to populate your database with verified vacancies.
            </p>
          </div>
          <button
            onClick={() => {
              setFetchResult(null);
              setShowFetchModal(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-sm transition"
          >
            <DownloadCloud className="w-4 h-4" />
            Fetch Jobs from Remotive (₹0)
          </button>
        </div>
      ) : (
        /* Job Table with Match Relevance Column */
        <div className="border border-slate-800 rounded-xl overflow-hidden bg-[#0e1626] shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 font-mono text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3.5">Job Title & Company</th>
                  <th className="px-4 py-3.5">Profile Match</th>
                  <th className="px-4 py-3.5">Decision</th>
                  <th className="px-4 py-3.5">Location</th>
                  <th className="px-4 py-3.5">Work Mode</th>
                  <th className="px-4 py-3.5">Salary Disclosed</th>
                  <th className="px-4 py-3.5">Source</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-slate-200">
                {jobs.map((job) => {
                  const hasMatch = job.match_score !== undefined && job.match_score !== null;
                  const isMatchingThis = matchingJobId === job.id;

                  return (
                    <tr
                      key={job.id}
                      className="hover:bg-slate-900/50 transition cursor-pointer"
                      onClick={() => handleOpenDetails(job.id)}
                    >
                      <td className="px-4 py-3.5 max-w-xs">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-slate-100 hover:text-indigo-300 transition">
                            {job.title}
                          </span>
                          {job.duplicate_status === 'duplicate' && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/30">
                              Duplicate
                            </span>
                          )}
                          {job.duplicate_status === 'possible_duplicate' && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase bg-yellow-500/10 text-yellow-400 border border-yellow-500/30">
                              Possible Dup
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-slate-400 text-[11px] font-medium flex items-center gap-1">
                            <Building2 className="w-3 h-3 text-slate-500" />
                            {job.company}
                          </span>
                          {job.external_job_id && (
                            <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800">
                              #{job.external_job_id}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Match Column */}
                      <td
                        className="px-4 py-3.5 whitespace-nowrap"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenMatch(job);
                        }}
                      >
                        {hasMatch ? (
                          <div className="flex items-center gap-2">
                            <span
                              className={`px-2 py-0.5 rounded text-[11px] font-bold border flex items-center gap-1 ${getFitBadgeStyle(
                                job.fit_category || ''
                              )}`}
                            >
                              <Sparkles className="w-3 h-3" />
                              {job.match_score}/100
                            </span>
                            <span className="text-[10px] font-mono text-slate-400 uppercase">
                              {(job.fit_category || '').replace('_RELEVANCE', '')}
                            </span>
                          </div>
                        ) : (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenMatch(job);
                            }}
                            disabled={isMatchingThis}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-indigo-300 border border-slate-700 transition"
                          >
                            <Target className={`w-3.5 h-3.5 ${isMatchingThis ? 'animate-spin' : 'text-indigo-400'}`} />
                            {isMatchingThis ? 'Matching...' : 'Analyze Match'}
                          </button>
                        )}
                      </td>

                      {/* Step 7 Decision Column */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        {job.application_decision === 'APPLY' ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 w-fit">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            APPLY
                          </span>
                        ) : job.application_decision === 'REVIEW' ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1 w-fit">
                            <AlertTriangle className="w-3 h-3 text-amber-400" />
                            REVIEW
                          </span>
                        ) : job.application_decision === 'SKIP' ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1 w-fit">
                            <X className="w-3 h-3 text-slate-500" />
                            SKIP
                          </span>
                        ) : (
                          <span className="text-[11px] font-mono text-slate-500">--</span>
                        )}
                      </td>


                      {/* Location */}
                      <td className="px-4 py-3.5 text-slate-400 whitespace-nowrap">
                        <span className="flex items-center gap-1 text-[11px]">
                          <MapPin className="w-3 h-3 text-slate-500" />
                          {job.location || 'Not specified'}
                        </span>
                      </td>

                      {/* Work Mode */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider border ${
                            job.work_mode?.toLowerCase() === 'remote'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : job.work_mode?.toLowerCase() === 'hybrid'
                              ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                              : 'bg-slate-800 text-slate-400 border-slate-700'
                          }`}
                        >
                          {job.work_mode || 'unknown'}
                        </span>
                      </td>

                      {/* Salary */}
                      <td className="px-4 py-3.5 text-slate-300 whitespace-nowrap font-mono text-[11px]">
                        {job.salary_min || job.salary_max ? (
                          <span className="text-emerald-400 flex items-center gap-1">
                            <DollarSign className="w-3 h-3" />
                            {job.salary_min?.toLocaleString()} - {job.salary_max?.toLocaleString()} {job.currency}
                          </span>
                        ) : (
                          <span className="text-slate-500">Undisclosed</span>
                        )}
                      </td>

                      {/* Source & Occurrences */}
                      <td className="px-4 py-3.5 text-slate-400 font-mono text-[11px]">
                        <div className="flex flex-col gap-0.5">
                          <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] text-indigo-300 uppercase w-fit">
                            {job.source}
                          </span>
                          {job.occurrences_count && job.occurrences_count > 1 ? (
                            <span className="text-[10px] font-sans text-emerald-400 font-medium">
                              {job.occurrences_count} sources
                            </span>
                          ) : null}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenMatch(job);
                            }}
                            className="px-2.5 py-1 text-[11px] font-medium bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded transition flex items-center gap-1"
                          >
                            <Sparkles className="w-3 h-3" />
                            {hasMatch ? 'View Match' : 'Match'}
                          </button>

                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenDetails(job.id);
                            }}
                            className="px-2.5 py-1 text-[11px] font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 transition"
                          >
                            Details
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="p-3 border-t border-slate-800/80 bg-slate-900/50 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-slate-400">
              <span>Show</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
              <span className="text-slate-500">
                Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} of {total}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 border border-slate-700 transition"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Previous
              </button>
              <span className="font-mono text-slate-300 px-2">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed text-slate-200 border border-slate-700 transition"
              >
                Next
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PHASE 4: Dedicated Match Analysis Modal */}
      {showMatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl bg-[#0e1626] border border-slate-800 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex items-start justify-between gap-4 sticky top-0 bg-[#0e1626]/95 backdrop-blur z-10">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    Deterministic Match Engine
                  </span>
                  {selectedMatch && (
                    <span className="text-[10px] font-mono text-slate-500">
                      v{selectedMatch.engine_version}
                    </span>
                  )}
                </div>
                <h2 className="text-lg font-bold text-slate-100 mt-1">
                  {selectedMatchJob?.title}
                </h2>
                <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                  <span className="flex items-center gap-1 font-medium text-slate-300">
                    <Building2 className="w-3.5 h-3.5 text-slate-500" />
                    {selectedMatchJob?.company}
                  </span>
                  <span>•</span>
                  <span>{selectedMatchJob?.location || 'Location Not Stated'}</span>
                  <span>•</span>
                  <span className="capitalize">{selectedMatchJob?.work_mode || 'Work mode unknown'}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {selectedMatchJob && (
                  <button
                    onClick={() => handleOpenMatch(selectedMatchJob, true)}
                    disabled={matchingJobId !== null}
                    className="flex items-center gap-1 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 transition"
                    title="Force recomputation without using cached result"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${matchingJobId ? 'animate-spin' : ''}`} />
                    Re-evaluate
                  </button>
                )}
                <button
                  onClick={() => setShowMatchModal(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              {matchingJobId ? (
                <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
                  <span>Evaluating candidate profile against job requirements...</span>
                </div>
              ) : matchError ? (
                <div className="p-4 rounded-md bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{matchError}</span>
                </div>
              ) : selectedMatch ? (
                <>
                  {/* Top Score Banner */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Relevance Score */}
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
                          Profile Relevance
                        </span>
                        <div className="text-3xl font-black text-slate-100 mt-1">
                          {selectedMatch.overall_score}
                          <span className="text-sm font-normal text-slate-500"> / 100</span>
                        </div>
                      </div>
                      <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                        <Target className="w-6 h-6" />
                      </div>
                    </div>

                    {/* Fit Category */}
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
                          Fit Category
                        </span>
                        <span
                          className={`inline-block mt-2 px-2.5 py-1 rounded text-xs font-bold border ${getFitBadgeStyle(
                            selectedMatch.fit_category
                          )}`}
                        >
                          {selectedMatch.fit_category}
                        </span>
                      </div>
                      <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                        <ShieldCheck className="w-6 h-6" />
                      </div>
                    </div>

                    {/* Data Completeness */}
                    <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
                          Data Completeness
                        </span>
                        <div className="text-xl font-bold text-slate-200 mt-1 flex items-center gap-1.5">
                          {selectedMatch.data_completeness}%
                          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                            {selectedMatch.data_completeness_level}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 mt-0.5 block">
                          Reliability metric (non-penalizing)
                        </span>
                      </div>
                      <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                        <Layers className="w-6 h-6" />
                      </div>
                    </div>
                  </div>

                  {/* Phase 4.1: HARD REQUIREMENT WARNINGS CALLOUT */}
                  {selectedMatch.hard_requirement_warnings && selectedMatch.hard_requirement_warnings.length > 0 && (
                    <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400 font-mono flex items-center gap-1.5">
                          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                          HARD REQUIREMENT WARNINGS ({selectedMatch.hard_requirement_warnings.length})
                        </h4>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                          {selectedMatch.hard_requirement_status || 'MISMATCH'}
                        </span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                        {selectedMatch.hard_requirement_warnings.map((w, idx) => (
                          <div key={idx} className="p-3 rounded-lg bg-slate-900/80 border border-rose-500/20 space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-semibold text-rose-300 flex items-center gap-1.5 capitalize font-mono">
                                {w.category === 'experience' && <Clock className="w-3.5 h-3.5 text-rose-400" />}
                                {w.category === 'required_skills' && <Target className="w-3.5 h-3.5 text-rose-400" />}
                                {w.category === 'location' && <MapPin className="w-3.5 h-3.5 text-rose-400" />}
                                {w.category === 'education' && <GraduationCap className="w-3.5 h-3.5 text-rose-400" />}
                                ⚠ {w.category.replace('_', ' ')}
                              </span>
                              <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold font-mono uppercase ${
                                w.severity === 'CRITICAL' ? 'bg-rose-500/30 text-rose-200 border border-rose-400' : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              }`}>
                                {w.severity}
                              </span>
                            </div>
                            <p className="text-xs text-slate-300 leading-snug">
                              {w.message}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 8 Dimension Evaluations Breakdown */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-indigo-400" />
                      8 Dimension Fit Analysis
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                      {/* Role Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <Target className="w-3 h-3 text-indigo-400" /> Role
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.role_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.role_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.role_fit?.explanation || 'Evaluated against candidate target roles.'}
                        </p>
                      </div>

                      {/* Skills Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Skills
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.skill_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.skill_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.skill_fit?.explanation || 'Matched technical skills.'}
                        </p>
                      </div>

                      {/* Experience Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <Clock className="w-3 h-3 text-blue-400" /> Experience
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.experience_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.experience_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.experience_fit?.explanation || 'Candidate experience records.'}
                        </p>
                      </div>

                      {/* Location Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-amber-400" /> Location
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.location_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.location_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.location_fit?.explanation || 'Preferences & remote eligibility.'}
                        </p>
                      </div>

                      {/* Work Mode Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <Compass className="w-3 h-3 text-purple-400" /> Work Mode
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.work_mode_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.work_mode_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.work_mode_fit?.explanation || 'Remote/hybrid flexibility.'}
                        </p>
                      </div>

                      {/* Salary Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <DollarSign className="w-3 h-3 text-emerald-400" /> Salary
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.salary_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.salary_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.salary_fit?.explanation || 'Compared against candidate baseline.'}
                        </p>
                      </div>

                      {/* Education Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <GraduationCap className="w-3 h-3 text-indigo-400" /> Education
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.education_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.education_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.education_fit?.explanation || 'B.Tech CSE & BS Data Science.'}
                        </p>
                      </div>

                      {/* Employment Type Fit */}
                      <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1">
                            <Briefcase className="w-3 h-3 text-teal-400" /> Employment
                          </span>
                          {getDimensionStatusBadge(selectedMatch.dimension_details?.employment_type_fit?.status || 'UNKNOWN')}
                        </div>
                        <div className="text-base font-bold text-slate-100">
                          {selectedMatch.employment_type_score.toFixed(0)} <span className="text-[10px] text-slate-500">pts</span>
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight">
                          {selectedMatch.dimension_details?.employment_type_fit?.explanation || 'Full-time, contract, internship.'}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Matched vs Missing Skills */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Matched Skills */}
                    <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          Matched Skills ({selectedMatch.matched_required_skills.length + selectedMatch.matched_preferred_skills.length})
                        </h4>
                      </div>

                      <div className="space-y-2">
                        {selectedMatch.matched_required_skills.length > 0 && (
                          <div>
                            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                              Required:
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedMatch.matched_required_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                                >
                                  <Check className="w-3 h-3 text-emerald-400" />
                                  {s.canonical}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedMatch.matched_preferred_skills.length > 0 && (
                          <div>
                            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                              Preferred (Bonus):
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedMatch.matched_preferred_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-teal-500/10 text-teal-300 border border-teal-500/20"
                                >
                                  <Check className="w-2.5 h-2.5 text-teal-400" />
                                  {s.canonical}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedMatch.matched_required_skills.length === 0 &&
                          selectedMatch.matched_preferred_skills.length === 0 && (
                            <span className="text-xs text-slate-500 italic">No skills matched directly.</span>
                          )}
                      </div>
                    </div>

                    {/* Missing Skills */}
                    <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-400 font-mono flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Missing Skills ({selectedMatch.missing_required_skills.length + selectedMatch.missing_preferred_skills.length})
                        </h4>
                      </div>

                      <div className="space-y-2">
                        {selectedMatch.missing_required_skills.length > 0 && (
                          <div>
                            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                              Required:
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedMatch.missing_required_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20"
                                >
                                  • {s}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedMatch.missing_preferred_skills.length > 0 && (
                          <div>
                            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
                              Preferred (Non-penalizing):
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedMatch.missing_preferred_skills.map((s, idx) => (
                                <span
                                  key={idx}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700"
                                >
                                  • {s}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {selectedMatch.missing_required_skills.length === 0 &&
                          selectedMatch.missing_preferred_skills.length === 0 && (
                            <span className="text-xs text-emerald-400">All identified skills satisfied!</span>
                          )}
                      </div>
                    </div>
                  </div>

                  {/* Concerns Box */}
                  {selectedMatch.concerns.length > 0 && (
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 space-y-2">
                      <h4 className="text-xs font-semibold text-amber-300 flex items-center gap-1.5 uppercase font-mono tracking-wider">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        Identified Gaps & Considerations ({selectedMatch.concerns.length})
                      </h4>
                      <ul className="space-y-1 pl-4 list-disc text-xs text-amber-200/90 leading-relaxed">
                        {selectedMatch.concerns.map((c, idx) => (
                          <li key={idx}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Explanations: Why this result? */}
                  <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 space-y-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono flex items-center gap-1.5">
                      <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
                      Why This Result? Deterministic Explanation
                    </h4>
                    <ul className="space-y-1.5 pl-4 list-disc text-xs text-slate-300 leading-relaxed">
                      {selectedMatch.explanations.map((exp, idx) => (
                        <li key={idx}>{exp}</li>
                      ))}
                    </ul>
                  </div>
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500 font-mono">
                Calculated {selectedMatch?.calculated_at ? new Date(selectedMatch.calculated_at).toLocaleString() : 'Just now'}
              </span>
              <button
                onClick={() => setShowMatchModal(false)}
                className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PHASE 4: Bulk Matching Modal */}
      {showBulkMatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl bg-[#0e1626] border border-slate-800 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-semibold text-slate-100">Bulk Match Stored Jobs</h3>
              </div>
              <button
                onClick={() => setShowBulkMatchModal(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <p className="text-slate-300">
                Run deterministic profile matching across multiple vacancies already stored in PostgreSQL.
                Zero external network calls, zero API costs (₹0).
              </p>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Batch Limit (Jobs to process)</label>
                <select
                  value={bulkMatchLimit}
                  onChange={(e) => setBulkMatchLimit(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value={10}>10 Jobs</option>
                  <option value={25}>25 Jobs</option>
                  <option value={50}>50 Jobs</option>
                  <option value={100}>100 Jobs</option>
                </select>
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="forceRecompute"
                  checked={bulkMatchForce}
                  onChange={(e) => setBulkMatchForce(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-800 text-indigo-600 focus:ring-0 w-4 h-4"
                />
                <label htmlFor="forceRecompute" className="text-slate-300 font-medium cursor-pointer">
                  Force recompute (ignore cached MatchResults)
                </label>
              </div>

              {bulkMatchError && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{bulkMatchError}</span>
                </div>
              )}

              {bulkMatchResult && (
                <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-emerald-400">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Batch Matching Complete!</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">PROCESSED</span>
                      <span className="text-sm font-bold text-slate-100">{bulkMatchResult.processed}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">NEW / UPDATED</span>
                      <span className="text-sm font-bold text-emerald-400">{bulkMatchResult.created}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">REUSED CACHE</span>
                      <span className="text-sm font-bold text-blue-400">{bulkMatchResult.reused}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-4">
              <button
                onClick={() => setShowBulkMatchModal(false)}
                className="px-3.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition"
              >
                Close
              </button>
              <button
                onClick={handleExecuteBulkMatch}
                disabled={bulkMatching}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-xs font-semibold text-white shadow-sm transition"
              >
                <Sparkles className={`w-3.5 h-3.5 ${bulkMatching ? 'animate-spin' : ''}`} />
                {bulkMatching ? 'Analyzing...' : 'Execute Bulk Analysis'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manual Fetch Jobs Modal (From Phase 3) */}
      {showFetchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl bg-[#0e1626] border border-slate-800 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <DownloadCloud className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-semibold text-slate-100">Fetch Real Jobs Pipeline</h3>
              </div>
              <button
                onClick={() => setShowFetchModal(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Ingestion Parameters Form */}
            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Source Connector</label>
                <select
                  value={fetchSource}
                  onChange={(e) => setFetchSource(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="remotive">Remotive (Official Public API — ₹0 Cost)</option>
                </select>
                <p className="text-[11px] text-slate-500 mt-1">
                  100% legal, free public developer API. No scraping or anti-bot bypass.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Search Keyword / Role</label>
                <input
                  type="text"
                  value={fetchKeyword}
                  onChange={(e) => setFetchKeyword(e.target.value)}
                  placeholder="e.g. AI Engineer, Python, Backend..."
                  className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {quickQueries.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => setFetchKeyword(q)}
                      className={`px-2 py-0.5 rounded text-[10px] font-medium border transition ${
                        fetchKeyword === q
                          ? 'bg-indigo-600 text-white border-indigo-500'
                          : 'bg-slate-800/80 text-slate-400 border-slate-700 hover:text-slate-200'
                      }`}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Location Filter (Optional)</label>
                  <input
                    type="text"
                    value={fetchLocation}
                    onChange={(e) => setFetchLocation(e.target.value)}
                    placeholder="e.g. Worldwide, USA"
                    className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Fetch Limit</label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={fetchLimit}
                    onChange={(e) => setFetchLimit(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {fetchError && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{fetchError}</span>
                </div>
              )}

              {fetchResult && (
                <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-emerald-400">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Ingestion Complete</span>
                  </div>
                  <div className="grid grid-cols-4 gap-2 text-center text-xs">
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">FETCHED</span>
                      <span className="text-sm font-bold text-slate-100">{fetchResult.jobs_fetched}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">CREATED</span>
                      <span className="text-sm font-bold text-emerald-400">{fetchResult.jobs_created}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">UPDATED</span>
                      <span className="text-sm font-bold text-blue-400">{fetchResult.jobs_updated}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-900/60 border border-slate-800">
                      <span className="text-slate-400 block text-[10px]">SKIPPED</span>
                      <span className="text-sm font-bold text-slate-400">{fetchResult.jobs_skipped}</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-300 mt-1">{fetchResult.message}</p>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-4">
              <button
                onClick={() => setShowFetchModal(false)}
                className="px-3.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition"
              >
                Close
              </button>
              <button
                onClick={handleExecuteFetch}
                disabled={fetching}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white shadow-sm transition"
              >
                <DownloadCloud className={`w-3.5 h-3.5 ${fetching ? 'animate-spin' : ''}`} />
                {fetching ? 'Fetching Remotive...' : 'Start Ingestion'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 4: Dedicated Search Expansion & Discovery Engine Modal */}
      {showDiscoveryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-xl bg-[#0e1626] border border-slate-800 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex items-start justify-between gap-4 sticky top-0 bg-[#0e1626]/95 backdrop-blur z-10">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded text-[10px] font-mono uppercase bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center gap-1">
                    <Compass className="w-3 h-3 text-purple-400" />
                    Step 4 Discovery Engine
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    Source: Remotive (₹0)
                  </span>
                </div>
                <h2 className="text-lg font-bold text-slate-100 mt-1">
                  Controlled Search Strategy Expansion
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Synthesizes candidate preferences, role synonyms, and verified technical skills into bounded, deduplicated queries.
                </p>
              </div>

              <button
                onClick={() => setShowDiscoveryModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Controls Bar */}
            <div className="p-6 pb-0 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-lg bg-slate-900/60 border border-slate-800">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-300 font-medium">Query Explosion Limit:</span>
                  <select
                    value={discoveryLimit}
                    onChange={(e) => {
                      const newLim = Number(e.target.value);
                      setDiscoveryLimit(newLim);
                      handlePreviewDiscovery(newLim);
                    }}
                    className="bg-slate-800 border border-slate-700 text-xs text-slate-200 rounded px-2.5 py-1 focus:outline-none focus:border-purple-500"
                  >
                    <option value={5}>5 queries (Fast)</option>
                    <option value={10}>10 queries (Recommended)</option>
                    <option value={15}>15 queries (Balanced)</option>
                    <option value={20}>20 queries (Deep)</option>
                    <option value={25}>25 queries (Max)</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handlePreviewDiscovery()}
                    disabled={discoveryPreviewing || discoveryRunning}
                    className="flex items-center gap-1 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs font-medium text-slate-200 border border-slate-700 transition"
                  >
                    <RefreshCw className={`w-3 h-3 ${discoveryPreviewing ? 'animate-spin' : ''}`} />
                    Preview Strategies
                  </button>

                  <button
                    onClick={handleExecuteDiscovery}
                    disabled={discoveryRunning}
                    className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-xs font-semibold text-white shadow-sm transition"
                  >
                    <Compass className={`w-3.5 h-3.5 ${discoveryRunning ? 'animate-spin' : ''}`} />
                    {discoveryRunning ? 'Executing Discovery...' : 'Execute Discovery Run'}
                  </button>
                </div>
              </div>

              {discoveryError && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{discoveryError}</span>
                </div>
              )}
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5 text-xs">
              {discoveryRunning ? (
                <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
                  <Compass className="w-8 h-8 animate-spin text-purple-400" />
                  <span className="font-medium text-slate-200">Executing Discovery Run across Remotive API...</span>
                  <span className="text-[11px] text-slate-500">Querying prioritized strategies, validating payloads, deduplicating records, and recording SearchQuery telemetry.</span>
                </div>
              ) : discoveryResult ? (
                /* Discovery Result Card */
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-semibold text-purple-300">
                        <CheckCircle2 className="w-4 h-4 text-purple-400" />
                        <span>Discovery Run Completed</span>
                      </div>
                      <span className="font-mono text-[11px] text-slate-400">
                        Duration: {discoveryResult.duration_ms ? `${(discoveryResult.duration_ms / 1000).toFixed(1)}s` : 'N/A'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
                      <div className="p-2.5 rounded bg-slate-900/70 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">EXECUTED</span>
                        <span className="text-sm font-bold text-slate-100">{discoveryResult.queries_executed}</span>
                      </div>
                      <div className="p-2.5 rounded bg-slate-900/70 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">SUCCESSFUL</span>
                        <span className="text-sm font-bold text-emerald-400">{discoveryResult.successful_queries}</span>
                      </div>
                      <div className="p-2.5 rounded bg-slate-900/70 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">FETCHED</span>
                        <span className="text-sm font-bold text-slate-100">{discoveryResult.jobs_fetched}</span>
                      </div>
                      <div className="p-2.5 rounded bg-slate-900/70 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">CREATED</span>
                        <span className="text-sm font-bold text-emerald-400">+{discoveryResult.jobs_created}</span>
                      </div>
                      <div className="p-2.5 rounded bg-slate-900/70 border border-slate-800">
                        <span className="text-slate-400 block text-[10px]">UPDATED</span>
                        <span className="text-sm font-bold text-blue-400">{discoveryResult.jobs_updated}</span>
                      </div>
                    </div>
                  </div>

                  {/* Executed Queries List */}
                  <div>
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 font-mono">
                      Executed Query Strategies & Results ({discoveryResult.executed_queries.length})
                    </h3>
                    <div className="border border-slate-800 rounded-lg overflow-hidden max-h-72 overflow-y-auto">
                      <table className="w-full text-left text-[11px]">
                        <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 sticky top-0 font-mono">
                          <tr>
                            <th className="px-3 py-2">Query</th>
                            <th className="px-3 py-2">Canonical Role</th>
                            <th className="px-3 py-2">Strategy</th>
                            <th className="px-3 py-2">Priority</th>
                            <th className="px-3 py-2">Status</th>
                            <th className="px-3 py-2 text-right">Yield</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {discoveryResult.executed_queries.map((q, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/40">
                              <td className="px-3 py-2 font-semibold text-slate-200 font-sans">{q.query}</td>
                              <td className="px-3 py-2 text-slate-400">{q.canonical_role}</td>
                              <td className="px-3 py-2 text-slate-400">
                                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300">
                                  {q.strategy.replace('_', ' ')}
                                </span>
                              </td>
                              <td className="px-3 py-2">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                  q.priority === 'HIGH' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                  q.priority === 'MEDIUM' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                                  'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                }`}>
                                  {q.priority}
                                </span>
                              </td>
                              <td className="px-3 py-2">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                  q.status === 'completed' ? 'text-emerald-400' : 'text-rose-400'
                                }`}>
                                  {q.status}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-right text-slate-300">
                                {q.jobs_fetched} fetched (+{q.jobs_created} new)
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ) : discoveryPreview ? (
                /* Discovery Preview Card */
                <div className="space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-mono">Profile Context</span>
                      <span className="text-slate-200 font-semibold">{discoveryPreview.candidate_name}</span>
                      <span className="text-slate-500 ml-2">({discoveryPreview.target_roles.join(', ')})</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                        HIGH: {discoveryPreview.priority_breakdown['HIGH'] || 0}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] font-mono">
                        MEDIUM: {discoveryPreview.priority_breakdown['MEDIUM'] || 0}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[10px] font-mono">
                        LOW: {discoveryPreview.priority_breakdown['LOW'] || 0}
                      </span>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 font-mono">
                      Planned Search Strategies ({discoveryPreview.queries.length} queries)
                    </h3>
                    <div className="border border-slate-800 rounded-lg overflow-hidden max-h-80 overflow-y-auto">
                      <table className="w-full text-left text-[11px]">
                        <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 sticky top-0 font-mono">
                          <tr>
                            <th className="px-3 py-2">#</th>
                            <th className="px-3 py-2">Query String</th>
                            <th className="px-3 py-2">Canonical Role</th>
                            <th className="px-3 py-2">Strategy Type</th>
                            <th className="px-3 py-2">Priority</th>
                            <th className="px-3 py-2">Rationale</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60 font-mono">
                          {discoveryPreview.queries.map((q, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/40">
                              <td className="px-3 py-2 text-slate-500">{idx + 1}</td>
                              <td className="px-3 py-2 font-semibold text-slate-200 font-sans">{q.query}</td>
                              <td className="px-3 py-2 text-slate-400">{q.canonical_role}</td>
                              <td className="px-3 py-2 text-slate-400">
                                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300">
                                  {q.strategy.replace('_', ' ')}
                                </span>
                              </td>
                              <td className="px-3 py-2">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                  q.priority === 'HIGH' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                  q.priority === 'MEDIUM' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                                  'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                }`}>
                                  {q.priority}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-slate-400 font-sans text-[11px] truncate max-w-xs" title={q.reason}>
                                {q.reason}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500 font-mono">
                Controlled Discovery: strictly bounded query expansion, ₹0 cost.
              </span>
              <button
                onClick={() => setShowDiscoveryModal(false)}
                className="px-3.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Single Job Details Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-xl bg-[#0e1626] border border-slate-800 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="p-6 border-b border-slate-800 flex items-start justify-between gap-4 sticky top-0 bg-[#0e1626]/95 backdrop-blur z-10">
              <div>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                  {selectedJob.source} • #{selectedJob.external_job_id || selectedJob.id.slice(0, 8)}
                </span>
                <h2 className="text-lg font-bold text-slate-100 mt-2">
                  {selectedJob.title}
                </h2>
                <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                  <span className="flex items-center gap-1 font-medium text-slate-200">
                    <Building2 className="w-3.5 h-3.5 text-slate-500" />
                    {selectedJob.company}
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5 text-slate-500" />
                    {selectedJob.location || 'Location Not Specified'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    const j = selectedJob;
                    setSelectedJob(null);
                    handleOpenMatch(j);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-sm transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  View Match Analysis
                </button>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-5 text-xs">
              {/* Badges Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-mono text-slate-500 block">Work Mode</span>
                  <span className="text-xs font-semibold text-slate-200 capitalize">
                    {selectedJob.work_mode || 'Unknown'}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-mono text-slate-500 block">Compensation</span>
                  <span className="text-xs font-semibold text-emerald-400">
                    {selectedJob.salary_min || selectedJob.salary_max
                      ? `${selectedJob.salary_min?.toLocaleString()} - ${selectedJob.salary_max?.toLocaleString()} ${selectedJob.currency}`
                      : 'Undisclosed'}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-mono text-slate-500 block">Match Score</span>
                  <span className="text-xs font-semibold text-indigo-300">
                    {selectedJob.match_score !== undefined && selectedJob.match_score !== null
                      ? `${selectedJob.match_score}/100 (${selectedJob.fit_category?.replace('_RELEVANCE', '')})`
                      : 'Not Analyzed'}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-mono text-slate-500 block">Discovered At</span>
                  <span className="text-xs font-semibold text-slate-200">
                    {new Date(selectedJob.discovered_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Cross-Source Occurrences & Identity */}
              <div className="space-y-3 p-4 rounded-lg bg-slate-900/60 border border-slate-800">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 font-mono flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    Cross-Source Identity & Traceability
                  </h3>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase border ${
                    selectedJob.is_canonical !== false && selectedJob.duplicate_status !== 'possible_duplicate'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : selectedJob.duplicate_status === 'possible_duplicate'
                      ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                  }`}>
                    {selectedJob.is_canonical !== false && selectedJob.duplicate_status !== 'possible_duplicate'
                      ? 'Canonical Vacancy'
                      : selectedJob.duplicate_status === 'possible_duplicate'
                      ? 'Possible Duplicate'
                      : 'Duplicate Record'}
                  </span>
                </div>

                {/* Occurrences list */}
                {selectedJob.occurrences && selectedJob.occurrences.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="text-[11px] text-slate-400 font-medium">
                      Found across {selectedJob.occurrences.length} source occurrence{selectedJob.occurrences.length > 1 ? 's' : ''}:
                    </span>
                    <div className="rounded border border-slate-800 divide-y divide-slate-800/80 overflow-hidden">
                      {selectedJob.occurrences.map((occ) => (
                        <div key={occ.job_id} className="p-2.5 bg-slate-950/40 flex items-center justify-between text-[11px]">
                          <div className="flex items-center gap-2">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-mono uppercase text-indigo-300">
                              {occ.source}
                            </span>
                            <span className="text-slate-300 font-mono">#{occ.external_job_id || occ.job_id.slice(0, 8)}</span>
                            {occ.is_canonical && (
                              <span className="text-[9px] text-emerald-400 font-bold uppercase">(Canonical)</span>
                            )}
                          </div>
                          <div className="flex items-center gap-3">
                            {occ.discovered_at && (
                              <span className="text-slate-500 text-[10px]">
                                Seen: {new Date(occ.discovered_at).toLocaleDateString()}
                              </span>
                            )}
                            {occ.application_url && (
                              <a
                                href={occ.application_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5 text-[10px]"
                              >
                                Link <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Duplicate link evidence if duplicate or possible duplicate */}
                {selectedJob.duplicate_links && selectedJob.duplicate_links.length > 0 && (
                  <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800/60 text-[11px] text-slate-400 space-y-1.5">
                    <span className="font-semibold text-slate-300 block">Deduplication Evidence:</span>
                    {selectedJob.duplicate_links.map((link) => (
                      <div key={link.id} className="flex flex-col gap-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-indigo-300 font-medium">Method:</span> {link.match_method}
                          <span className="text-slate-500">•</span>
                          <span className="text-indigo-300 font-medium">Confidence:</span> {link.confidence} ({Math.round(link.confidence_score * 100)}%)
                        </div>
                        {link.evidence?.matched_signals && (
                          <div className="text-[10px] text-slate-400">
                            Signals: {link.evidence.matched_signals.join(', ')}
                          </div>
                        )}
                        {link.evidence?.contradictions && link.evidence.contradictions.length > 0 && (
                          <div className="text-[10px] text-amber-400">
                            Contradictions checked: {link.evidence.contradictions.join('; ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Step 7 Application Decision Engine Card */}
              <div className="space-y-3 p-4 rounded-lg bg-slate-900/60 border border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Target className="w-3.5 h-3.5 text-indigo-400" />
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 font-mono">
                      Application Decision Engine (Step 7)
                    </h3>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleEvaluateSingleDecision(selectedJob.id, true)}
                      disabled={evaluatingDecisionJobId === selectedJob.id}
                      className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-[11px] font-medium text-slate-300 border border-slate-700 transition"
                      title="Recompute decision using multi-dimensional rules"
                    >
                      <RefreshCw className={`w-3 h-3 ${evaluatingDecisionJobId === selectedJob.id ? 'animate-spin' : ''}`} />
                      {evaluatingDecisionJobId === selectedJob.id ? 'Evaluating...' : 'Evaluate Decision'}
                    </button>

                    <span className={`px-2.5 py-0.5 rounded text-[10px] font-bold uppercase border ${
                      selectedJob.application_decision === 'APPLY'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : selectedJob.application_decision === 'REVIEW'
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        : selectedJob.application_decision === 'SKIP'
                        ? 'bg-slate-800 text-slate-400 border-slate-700'
                        : 'bg-slate-900 text-slate-500 border-slate-800'
                    }`}>
                      {selectedJob.application_decision || 'Pending Evaluation'}
                    </span>

                    {(selectedJob.application_decision === 'APPLY' || selectedJob.application_decision === 'REVIEW') && (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setPrepModalJobId(selectedJob.id)}
                          className="flex items-center gap-1.5 px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] font-semibold text-slate-200 border border-slate-700 transition"
                        >
                          <FileText className="w-3.5 h-3.5 text-indigo-400" />
                          Prepare Package
                        </button>
                        <button
                          onClick={() => setExecModalJob(selectedJob)}
                          className="flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-[11px] font-semibold text-white shadow-sm shadow-emerald-600/20 transition"
                        >
                          <Play className="w-3.5 h-3.5" />
                          Execute
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {selectedJob.decision_details ? (
                  <div className="space-y-2.5 text-[11px]">
                    <div className="grid grid-cols-3 gap-2">
                      <div className="p-2 rounded bg-slate-950/40 border border-slate-800">
                        <span className="text-[10px] uppercase font-mono text-slate-500 block">Confidence</span>
                        <span className="font-semibold text-slate-200">{Math.round((selectedJob.decision_details.confidence_score || 0) * 100)}%</span>
                      </div>
                      <div className="p-2 rounded bg-slate-950/40 border border-slate-800">
                        <span className="text-[10px] uppercase font-mono text-slate-500 block">Risk Level</span>
                        <span className={`font-semibold capitalize ${
                          selectedJob.decision_details.risk_level === 'LOW'
                            ? 'text-emerald-400'
                            : selectedJob.decision_details.risk_level === 'MEDIUM'
                            ? 'text-amber-400'
                            : 'text-rose-400'
                        }`}>
                          {selectedJob.decision_details.risk_level || 'Low'}
                        </span>
                      </div>
                      <div className="p-2 rounded bg-slate-950/40 border border-slate-800">
                        <span className="text-[10px] uppercase font-mono text-slate-500 block">Evaluated On</span>
                        <span className="font-semibold text-slate-200">
                          {selectedJob.decision_details.decided_at ? new Date(selectedJob.decision_details.decided_at).toLocaleDateString() : 'Today'}
                        </span>
                      </div>
                    </div>

                    {/* Step 7.1 Role Relevance Detail */}
                    {selectedJob.decision_details.evaluation_metadata?.role_relevance_tier && (
                      <div className="p-2.5 rounded bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Compass className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                          <div>
                            <span className="text-[10px] uppercase font-mono text-slate-400 font-semibold block">Role Career Relevance</span>
                            <span className="text-[11px] text-slate-300">
                              {selectedJob.decision_details.evaluation_metadata?.role_concept || selectedJob.title}
                              {selectedJob.decision_details.evaluation_metadata?.role_family && (
                                <span className="text-slate-500 text-[10px] ml-1.5 font-mono">({selectedJob.decision_details.evaluation_metadata.role_family})</span>
                              )}
                            </span>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                          selectedJob.decision_details.evaluation_metadata.role_relevance_tier === 'DIRECT'
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : selectedJob.decision_details.evaluation_metadata.role_relevance_tier === 'ADJACENT'
                            ? 'bg-sky-500/10 text-sky-400 border-sky-500/30'
                            : selectedJob.decision_details.evaluation_metadata.role_relevance_tier === 'TRANSFERABLE'
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                        }`}>
                          {selectedJob.decision_details.evaluation_metadata.role_relevance_tier === 'DIRECT'
                            ? 'Direct Match'
                            : selectedJob.decision_details.evaluation_metadata.role_relevance_tier === 'ADJACENT'
                            ? 'Adjacent Role'
                            : selectedJob.decision_details.evaluation_metadata.role_relevance_tier === 'TRANSFERABLE'
                            ? 'Transferable Role'
                            : 'Unrelated Role'}
                        </span>
                      </div>
                    )}

                    {/* Primary Reasons */}
                    {selectedJob.decision_details.reasons && selectedJob.decision_details.reasons.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-mono text-slate-400 block font-semibold">Primary Decision Reasons:</span>
                        <ul className="space-y-1 text-slate-300">
                          {selectedJob.decision_details.reasons.map((r, i) => (
                            <li key={i} className="flex items-start gap-1.5">
                              <span className="text-indigo-400">•</span>
                              <span>{r}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Supporting Factors */}
                    {selectedJob.decision_details.supporting_factors && selectedJob.decision_details.supporting_factors.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-mono text-emerald-400 block font-semibold">Supporting Signals:</span>
                        <ul className="space-y-1 text-slate-300">
                          {selectedJob.decision_details.supporting_factors.map((sf, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-emerald-300/90">
                              <Check className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />
                              <span>{sf}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Disqualifying Factors */}
                    {selectedJob.decision_details.disqualifying_factors && selectedJob.decision_details.disqualifying_factors.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-mono text-rose-400 block font-semibold">Disqualifying Factors:</span>
                        <ul className="space-y-1 text-slate-300">
                          {selectedJob.decision_details.disqualifying_factors.map((df, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-rose-300/90">
                              <X className="w-3 h-3 text-rose-400 shrink-0 mt-0.5" />
                              <span>{df}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Review Reasons */}
                    {selectedJob.decision_details.review_reasons && selectedJob.decision_details.review_reasons.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase font-mono text-amber-400 block font-semibold">Attention / Review Items:</span>
                        <ul className="space-y-1 text-slate-300">
                          {selectedJob.decision_details.review_reasons.map((rr, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-amber-300/90">
                              <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0 mt-0.5" />
                              <span>{rr}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-between text-slate-400 text-[11px] p-2 rounded bg-slate-950/40">
                    <span>No decision recorded yet for this job.</span>
                    <button
                      onClick={() => handleEvaluateSingleDecision(selectedJob.id, false)}
                      disabled={evaluatingDecisionJobId === selectedJob.id}
                      className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition"
                    >
                      Run Evaluation
                    </button>
                  </div>
                )}
              </div>

              {/* Requirements */}
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
                  Key Requirements & Qualifications
                </h3>
                <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {selectedJob.requirements || 'Not provided'}
                </div>
              </div>

              {/* Responsibilities */}
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                  <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
                  Responsibilities & Role Scope
                </h3>
                <div className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800 text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {selectedJob.responsibilities || 'Not provided'}
                </div>
              </div>

              {/* Full Description */}
              <div className="space-y-2">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-indigo-400" />
                  Full Position Description
                </h3>
                <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 text-slate-300 leading-relaxed whitespace-pre-wrap max-h-80 overflow-y-auto">
                  {selectedJob.description || 'Not provided'}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 bg-slate-900/60 flex items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500 font-mono">
                {selectedJob.match_score !== undefined && selectedJob.match_score !== null
                  ? `Relevance: ${selectedJob.match_score}/100 (${selectedJob.fit_category})`
                  : 'Ready for deterministic match analysis'}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSelectedJob(null)}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition"
                >
                  Close
                </button>
                {selectedJob.application_url && (
                  <a
                    href={selectedJob.application_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition shadow-sm"
                  >
                    Open Original Posting <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Step 7: Bulk Application Decision Engine Modal */}
      {showBulkDecisionModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl bg-[#0e1626] border border-slate-800 shadow-2xl p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <Target className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-100">
                    Application Decision Engine
                  </h2>
                  <p className="text-xs text-slate-400">
                    Evaluates candidate fit, preferences, hard requirements, and history to categorize jobs into APPLY, REVIEW, or SKIP.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowBulkDecisionModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="text-slate-300 font-medium block mb-1">
                  Batch Evaluation Limit:
                </label>
                <select
                  value={bulkDecisionLimit}
                  onChange={(e) => setBulkDecisionLimit(Number(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-800 rounded-md p-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value={25}>25 Jobs</option>
                  <option value={50}>50 Jobs (Recommended)</option>
                  <option value={100}>100 Jobs</option>
                  <option value={200}>200 Jobs (Max)</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={bulkDecisionCanonicalOnly}
                    onChange={(e) => setBulkDecisionCanonicalOnly(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                  />
                  <span>Evaluate only canonical jobs (Exclude duplicates)</span>
                </label>

                <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={bulkDecisionForce}
                    onChange={(e) => setBulkDecisionForce(e.target.checked)}
                    className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                  />
                  <span>Force recomputation (Bypass decision cache)</span>
                </label>
              </div>

              {bulkDecisionError && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400">
                  {bulkDecisionError}
                </div>
              )}

              {bulkDecisionResult && (
                <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2.5">
                  <span className="font-semibold text-slate-200 block text-xs">Decision Results:</span>
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">PROCESSED</span>
                      <span className="text-sm font-bold text-slate-100">{bulkDecisionResult.processed}</span>
                    </div>
                    <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/20">
                      <span className="text-[10px] text-emerald-400 block font-semibold">APPLY</span>
                      <span className="text-sm font-bold text-emerald-400">{bulkDecisionResult.apply_count}</span>
                    </div>
                    <div className="p-2 rounded bg-amber-500/10 border border-amber-500/20">
                      <span className="text-[10px] text-amber-400 block font-semibold">REVIEW</span>
                      <span className="text-sm font-bold text-amber-400">{bulkDecisionResult.review_count}</span>
                    </div>
                    <div className="p-2 rounded bg-slate-800/80 border border-slate-700">
                      <span className="text-[10px] text-slate-400 block font-semibold">SKIP</span>
                      <span className="text-sm font-bold text-slate-400">{bulkDecisionResult.skip_count}</span>
                    </div>
                  </div>
                  <span className="text-[10px] text-slate-400 block text-center">
                    ({bulkDecisionResult.reused} reused from fresh cache, {bulkDecisionResult.new_or_updated} newly evaluated)
                  </span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-4">
              <button
                onClick={() => setShowBulkDecisionModal(false)}
                className="px-3.5 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition"
              >
                Close
              </button>
              <button
                onClick={handleRunBulkDecisions}
                disabled={bulkDecisionLoading}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white shadow-sm transition"
              >
                <Target className={`w-3.5 h-3.5 ${bulkDecisionLoading ? 'animate-spin' : ''}`} />
                {bulkDecisionLoading ? 'Evaluating...' : 'Run Decision Engine'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 8 Application Preparation Modal */}
      {prepModalJobId && (
        <ApplicationPreparationModal
          jobId={prepModalJobId}
          isOpen={!!prepModalJobId}
          onClose={() => setPrepModalJobId(null)}
          onSuccess={loadJobs}
        />
      )}

      {/* Step 9 Application Execution Modal */}
      {execModalJob && (
        <ApplicationExecutionModal
          jobId={execModalJob.id}
          jobTitle={execModalJob.title}
          company={execModalJob.company}
          jobUrl={execModalJob.application_url || undefined}
          isOpen={!!execModalJob}
          onClose={() => setExecModalJob(null)}
          onExecutionCompleted={loadJobs}
        />
      )}

    </div>
  );
};

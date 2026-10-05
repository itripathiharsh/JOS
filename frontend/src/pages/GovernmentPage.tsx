import React, { useState, useEffect } from 'react';
import {
  Globe,
  FileText,
  RefreshCw,
  Search,
  ExternalLink,
  CheckCircle2,
  Clock,
  Layers,
  MapPin,
  Sparkles,
  AlertCircle,
  Activity,
  History,
  Timer,
  Calendar,
  Check,
  ShieldCheck,
  Target,
  Compass,
  FolderTree,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  GovernmentCoverageResponse,
  GovernmentSourceItem,
  GovernmentVacancyItem,
  GovernmentMonitoringStatsResponse,
  GovernmentChangeEventItem,
  GovernmentUniverseStatsResponse,
  GovernmentUniverseMissionResponse,
  GovernmentUnresolvedTargetItem,
} from '../api/client';

export const GovernmentPage: React.FC = () => {
  const [coverage, setCoverage] = useState<GovernmentCoverageResponse | null>(null);
  const [sources, setSources] = useState<GovernmentSourceItem[]>([]);
  const [vacancies, setVacancies] = useState<GovernmentVacancyItem[]>([]);
  const [monitoringStats, setMonitoringStats] = useState<GovernmentMonitoringStatsResponse | null>(null);
  const [changeEvents, setChangeEvents] = useState<GovernmentChangeEventItem[]>([]);
  const [universeStats, setUniverseStats] = useState<GovernmentUniverseStatsResponse | null>(null);
  const [unresolvedTargets, setUnresolvedTargets] = useState<GovernmentUnresolvedTargetItem[]>([]);
  const [hierarchy, setHierarchy] = useState<any[]>([]);
  const [missionResult, setMissionResult] = useState<GovernmentUniverseMissionResponse | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Active view tab
  const [activeTab, setActiveTab] = useState<
    'monitoring' | 'vacancies' | 'registry' | 'changes' | 'matrix' | 'sectors' | 'universe' | 'unresolved' | 'hierarchy'
  >('monitoring');

  // Filters
  const [selectedState, setSelectedState] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [contractOnly, setContractOnly] = useState<boolean>(false);
  const [deadlineFilter, setDeadlineFilter] = useState<string>('all');
  const [changeTypeFilter, setChangeTypeFilter] = useState<string>('all');

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [covData, srcData, vacData, monData, chgData, uniData, unresData, hierData] = await Promise.all([
        api.getGovernmentCoverage(),
        api.getGovernmentSources({ limit: 100 }),
        api.getGovernmentVacancies({ limit: 100 }),
        api.getGovernmentMonitoringStats(),
        api.getGovernmentChanges({ limit: 50 }),
        api.getGovernmentUniverseStats().catch(() => null),
        api.getGovernmentUnresolvedTargets({ limit: 100 }).catch(() => ({ total: 0, items: [] })),
        api.getGovernmentSourcesHierarchy().catch(() => ({ total_parents: 0, hierarchy: [] })),
      ]);
      setCoverage(covData);
      setSources(srcData.items || []);
      setVacancies(vacData.items || []);
      setMonitoringStats(monData);
      setChangeEvents(chgData || []);
      if (uniData) setUniverseStats(uniData);
      if (unresData) setUnresolvedTargets(unresData.items || []);
      if (hierData) setHierarchy(hierData.hierarchy || []);
    } catch (err: any) {
      console.error('Failed to load government discovery and monitoring data', err);
      setError(err.message || 'Could not connect to government continuous monitoring API');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSeedRegistry = async () => {
    setActionLoading('seed');
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await api.seedGovernmentSources();
      setSuccessMsg(`Seeded core registry: ${res.seeded_count || 'Initial'} organisations checked/registered.`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to seed government sources');
    } finally {
      setActionLoading(null);
    }
  };

  const handleTriggerDiscovery = async () => {
    setActionLoading('discover');
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await api.triggerGovernmentDiscovery({
        scope: selectedState !== 'all' ? 'STATE' : 'ALL',
        state_filter: selectedState !== 'all' ? selectedState : undefined,
        max_search_queries: 15,
      });
      setSuccessMsg(`Autonomous Discovery Run Complete: Found ${res.sources_discovered} new government portals across public networks.`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Discovery run failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleTriggerCrawl = async () => {
    setActionLoading('crawl');
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await api.triggerGovernmentCrawl({
        batch_size: 20,
        force_recheck: false,
        state_filter: selectedState !== 'all' ? selectedState : undefined,
      });
      setSuccessMsg(`Continuous Crawl Batch Complete: Processed ${res.sources_processed} sources. Created ${res.vacancies_created} new vacancies, updated ${res.vacancies_updated}.`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Crawl failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleTriggerMonitoringTick = async () => {
    setActionLoading('tick');
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await api.triggerGovernmentMonitoringTick(20);
      setSuccessMsg(`Continuous Scheduler Tick: Identified ${res.due_sources_count} due sources, enqueued ${res.enqueued_crawls} crawl tasks.`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Monitoring tick failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleRecheckDeadlines = async () => {
    setActionLoading('recheck');
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await api.recheckGovernmentDeadlines();
      setSuccessMsg(`Deadline Revalidation Complete: Revalidated ${res.revalidated || 0} vacancies. Open: ${res.open || 0}, Approaching: ${res.deadline_approaching || 0}, Expired: ${res.expired || 0}.`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Deadline recheck failed');
    } finally {
      setActionLoading(null);
    }
  };

  const handleTriggerUniverseMission = async () => {
    setActionLoading('universe');
    setSuccessMsg(null);
    setError(null);
    try {
      const res = await api.triggerGovernmentUniverseMission({
        max_passes: 10,
        run_search: true,
        batch_size: 50,
      });
      setMissionResult(res);
      setSuccessMsg(`10-Pass Universe Discovery Complete: Parsed ${res.total_deduplicated_targets} targets, resolved & verified ${res.verified_sources} authoritative sources, found ${res.metrics?.vacancies_created ?? 0} vacancies!`);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Universe mission failed');
    } finally {
      setActionLoading(null);
    }
  };

  // Filtered lists
  const filteredSources = sources.filter((s) => {
    if (selectedState !== 'all' && s.state !== selectedState) return false;
    if (statusFilter !== 'all' && s.source_status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchName = s.organisation_name.toLowerCase().includes(q);
      const matchDomain = s.official_domain.toLowerCase().includes(q);
      const matchType = s.organisation_type.toLowerCase().includes(q);
      if (!matchName && !matchDomain && !matchType) return false;
    }
    return true;
  });

  const filteredVacancies = vacancies.filter((v) => {
    if (selectedState !== 'all' && v.state !== selectedState) return false;
    if (contractOnly && v.employment_type?.toLowerCase() !== 'contract') return false;
    if (deadlineFilter !== 'all' && v.deadline_status !== deadlineFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTitle = (v.title || v.job_title || '').toLowerCase().includes(q);
      const matchOrg = (v.organisation_name || v.job_company || '').toLowerCase().includes(q);
      const matchDept = (v.department || '').toLowerCase().includes(q);
      if (!matchTitle && !matchOrg && !matchDept) return false;
    }
    return true;
  });

  const filteredChanges = changeEvents.filter((c) => {
    if (changeTypeFilter !== 'all' && c.change_type !== changeTypeFilter) return false;
    return true;
  });

  const getDeadlineBadge = (status?: string, deadline?: string | null) => {
    switch (status) {
      case 'DEADLINE_TODAY':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-mono bg-red-500/20 text-red-300 border border-red-500/40 animate-pulse">
            <Timer className="w-3 h-3 text-red-400" /> Deadline Today
          </span>
        );
      case 'DEADLINE_APPROACHING':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40">
            <Clock className="w-3 h-3 text-amber-400" /> &lt;3 Days Left
          </span>
        );
      case 'EXTENDED':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-mono bg-purple-500/20 text-purple-300 border border-purple-500/40">
            <Calendar className="w-3 h-3 text-purple-400" /> Deadline Extended
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-mono bg-slate-800 text-slate-400 border border-slate-700">
            Expired
          </span>
        );
      case 'OPEN':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
            <Check className="w-3 h-3 text-emerald-400" /> Active
          </span>
        );
      default:
        return deadline ? (
          <span className="text-[10px] text-slate-400 font-mono">Deadline: {deadline.slice(0, 10)}</span>
        ) : null;
    }
  };

  const getChangeTypeBadge = (changeType: string) => {
    switch (changeType) {
      case 'NEW':
        return <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-emerald-500/15 border border-emerald-500/30 text-emerald-300">NEW</span>;
      case 'UPDATED':
        return <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-blue-500/15 border border-blue-500/30 text-blue-300">UPDATED</span>;
      case 'EXTENDED':
        return <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-purple-500/15 border border-purple-500/30 text-purple-300">EXTENDED</span>;
      case 'CORRIGENDUM':
        return <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-amber-500/15 border border-amber-500/30 text-amber-300">CORRIGENDUM</span>;
      case 'CLOSED':
        return <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-red-500/15 border border-red-500/30 text-red-300">CLOSED</span>;
      default:
        return <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-400">{changeType}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <Activity className="w-5 h-5" />
            </span>
            <h1 className="text-xl font-bold text-white tracking-tight">Government Continuous Monitoring & Freshness</h1>
            <span className="text-[11px] px-2 py-0.5 rounded-full font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-300">
              Living Queue • ₹0 Cost
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Autonomous rediscovery, continuous per-source adaptive crawl cycles, PDF hash change detection, and deadline-aware vacancy protection.
          </p>
        </div>

        {/* Global Control Actions */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleTriggerUniverseMission}
            disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white shadow-md shadow-indigo-900/30 transition transform hover:-translate-y-0.5"
            title="Executes the full 10-Pass Indian Government Source Discovery Mission across MD universe, State/UT, District, Endpoints & PDFs"
          >
            {actionLoading === 'universe' ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Target className="w-3.5 h-3.5 text-blue-200" />
            )}
            <span>Run 10-Pass Mission</span>
          </button>

          <button
            onClick={handleSeedRegistry}
            disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
            title="Seeds authoritative government ministries, states, and PSUs"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
            <span>Seed Registry</span>
          </button>

          <button
            onClick={handleTriggerMonitoringTick}
            disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition"
            title="Runs living queue scheduler tick to enqueue due sources"
          >
            {actionLoading === 'tick' ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Timer className="w-3.5 h-3.5" />
            )}
            <span>Monitoring Tick</span>
          </button>

          <button
            onClick={handleRecheckDeadlines}
            disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-purple-600 hover:bg-purple-500 text-white shadow-sm transition"
            title="Revalidates approaching vacancy deadlines"
          >
            {actionLoading === 'recheck' ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Calendar className="w-3.5 h-3.5" />
            )}
            <span>Recheck Deadlines</span>
          </button>

          <button
            onClick={handleTriggerDiscovery}
            disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition"
          >
            {actionLoading === 'discover' ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>Discover New</span>
          </button>

          <button
            onClick={handleTriggerCrawl}
            disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            {actionLoading === 'crawl' ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span>Crawl Due Batch</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-white">✕</button>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-lg bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-indigo-950/20 border border-indigo-500/20 text-indigo-300 text-xs">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-indigo-400" />
          <span>Synchronizing continuous monitoring telemetry and freshness matrices...</span>
        </div>
      )}

      {/* Primary KPI Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Registered Sources</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {monitoringStats?.total_registered_sources ?? sources.length}
          </div>
          <div className="text-[10px] text-emerald-400 mt-1">
            {monitoringStats?.sources_with_scheduled_crawl ?? 0} scheduled living
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider">Freshness SLA</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            {monitoringStats?.sources_within_freshness_sla ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {monitoringStats?.sources_outside_freshness_sla ?? 0} outside SLA window
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[11px] font-medium text-amber-400 uppercase tracking-wider">Due / Overdue</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            {monitoringStats?.sources_currently_due ?? 0}
          </div>
          <div className="text-[10px] text-slate-500 mt-1">
            {monitoringStats?.sources_never_crawled ?? 0} never crawled
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[11px] font-medium text-cyan-400 uppercase tracking-wider">Crawled Today</div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {monitoringStats?.sources_successfully_crawled_today ?? 0}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {monitoringStats?.sources_failed_today ?? 0} failed / backed off
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[11px] font-medium text-purple-400 uppercase tracking-wider">Changes & Notices</div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-1">
            {changeEvents.length}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {monitoringStats?.corrigenda_count ?? 0} corrigenda / updates
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[11px] font-medium text-red-400 uppercase tracking-wider">Deadline Alert</div>
          <div className="text-2xl font-bold font-mono text-red-400 mt-1">
            {(monitoringStats?.deadline_lt_24h_count ?? 0) + (monitoringStats?.deadline_lt_3d_count ?? 0)}
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {monitoringStats?.expired_vacancies_count ?? 0} expired verified
          </div>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="flex items-center justify-between border-b border-slate-800">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setActiveTab('monitoring')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'monitoring'
                ? 'border-emerald-500 text-emerald-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Monitoring Queue & SLA</span>
          </button>

          <button
            onClick={() => setActiveTab('vacancies')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'vacancies'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Vacancies & Deadlines ({vacancies.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('registry')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'registry'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            <span>Living Registry ({sources.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('changes')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'changes'
                ? 'border-purple-500 text-purple-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Change Audit Trail ({changeEvents.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('matrix')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'matrix'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            <span>State / UT Matrix</span>
          </button>

          <button
            onClick={() => setActiveTab('sectors')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'sectors'
                ? 'border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Sectors</span>
          </button>

          <button
            onClick={() => setActiveTab('universe')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'universe'
                ? 'border-blue-500 text-blue-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            <span>Universe Discovery</span>
          </button>

          <button
            onClick={() => setActiveTab('hierarchy')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'hierarchy'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FolderTree className="w-3.5 h-3.5" />
            <span>Hierarchy Tree ({hierarchy.length})</span>
          </button>

          <button
            onClick={() => setActiveTab('unresolved')}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition ${
              activeTab === 'unresolved'
                ? 'border-amber-500 text-amber-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Unresolved Backlog ({universeStats?.unresolved_backlog_targets ?? unresolvedTargets.length})</span>
          </button>
        </div>

        {selectedState !== 'all' && (
          <div className="flex items-center gap-2 text-xs text-indigo-300 bg-indigo-500/10 px-2.5 py-1 rounded-md border border-indigo-500/20">
            <span>Filtered: <strong>{selectedState}</strong></span>
            <button onClick={() => setSelectedState('all')} className="hover:text-white font-bold ml-1">✕</button>
          </div>
        )}
      </div>

      {/* TAB 1: Monitoring Queue & Freshness SLA */}
      {activeTab === 'monitoring' && (
        <div className="space-y-4">
          {/* SLA Overview & Target Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300">Continuous Freshness SLA</span>
                <span className="text-xs font-mono text-emerald-400">
                  {monitoringStats?.total_registered_sources
                    ? Math.round(
                        ((monitoringStats.sources_within_freshness_sla || 0) /
                          monitoringStats.total_registered_sources) *
                          100
                      )
                    : 100}
                  % Compliant
                </span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${
                      monitoringStats?.total_registered_sources
                        ? Math.min(
                            100,
                            Math.round(
                              ((monitoringStats.sources_within_freshness_sla || 0) /
                                monitoringStats.total_registered_sources) *
                                100
                            )
                          )
                        : 100
                    }%`,
                  }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-slate-800 text-[11px] text-slate-400">
                <div>Within SLA: <strong className="text-emerald-400">{monitoringStats?.sources_within_freshness_sla ?? 0}</strong></div>
                <div>Overdue: <strong className="text-amber-400">{monitoringStats?.sources_outside_freshness_sla ?? 0}</strong></div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800">
              <div className="text-xs font-semibold text-slate-300">Adaptive Crawl SLA Windows</div>
              <div className="grid grid-cols-2 gap-2 mt-2 text-[11px] text-slate-400">
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-800/60">
                  <span>High Activity:</span>
                  <span className="font-mono text-emerald-400">≤ 3 hours</span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-800/60">
                  <span>Normal Recruitment:</span>
                  <span className="font-mono text-blue-400">≤ 12 hours</span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-800/60">
                  <span>Low / Static:</span>
                  <span className="font-mono text-slate-300">≤ 72 hours</span>
                </div>
                <div className="flex items-center justify-between p-1.5 rounded bg-slate-800/60">
                  <span>Imminent Deadline:</span>
                  <span className="font-mono text-amber-400">≤ 3 hours</span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-900/90 border border-slate-800">
              <div className="text-xs font-semibold text-slate-300">Queue & Recovery Telemetry</div>
              <div className="space-y-1.5 mt-2 text-[11px] text-slate-400 font-mono">
                <div className="flex justify-between">
                  <span>Oldest Due:</span>
                  <span className="text-slate-200 truncate max-w-[150px]" title={monitoringStats?.oldest_overdue_source || ''}>
                    {monitoringStats?.oldest_overdue_source || 'None'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Next Scheduled:</span>
                  <span className="text-emerald-400">
                    {monitoringStats?.next_scheduled_crawl
                      ? new Date(monitoringStats.next_scheduled_crawl).toLocaleTimeString()
                      : 'Immediate'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Last Global Crawl:</span>
                  <span className="text-slate-300">
                    {monitoringStats?.last_global_crawl
                      ? new Date(monitoringStats.last_global_crawl).toLocaleTimeString()
                      : 'Never'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Next Discovery:</span>
                  <span className="text-indigo-400">
                    {monitoringStats?.next_global_discovery
                      ? new Date(monitoringStats.next_global_discovery).toLocaleDateString()
                      : 'Scheduled'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Living Monitoring Queue Table */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-emerald-400" />
                <span>Living Monitoring Queue (Ordered by Next Crawl Due)</span>
              </div>
              <span className="text-[11px] text-slate-500">Every eligible source participates in continuous rotation</span>
            </div>

            <div className="border border-slate-800 rounded-lg overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                  <tr>
                    <th className="p-3">Source & Domain</th>
                    <th className="p-3">Category</th>
                    <th className="p-3">Interval</th>
                    <th className="p-3">Next Crawl</th>
                    <th className="p-3">Last Crawl</th>
                    <th className="p-3">Failures</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                  {sources.slice(0, 25).map((s) => {
                    const isDue = s.next_crawl_at ? new Date(s.next_crawl_at) <= new Date() : true;
                    return (
                      <tr key={s.id} className="hover:bg-slate-900/40">
                        <td className="p-3 font-sans">
                          <div className="font-semibold text-white">{s.organisation_name}</div>
                          <div className="font-mono text-[11px] text-slate-400">{s.official_domain}</div>
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono ${
                            s.change_frequency_category === 'high'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : s.change_frequency_category === 'medium'
                              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                              : 'bg-slate-800 text-slate-400'
                          }`}>
                            {s.change_frequency_category || 'low'}
                          </span>
                        </td>
                        <td className="p-3 text-slate-300">
                          {s.crawl_interval_minutes ? `${Math.round(s.crawl_interval_minutes / 60)}h (${s.crawl_interval_minutes}m)` : '24h'}
                        </td>
                        <td className="p-3">
                          {isDue ? (
                            <span className="text-amber-400 font-bold flex items-center gap-1">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                              Due Now
                            </span>
                          ) : (
                            <span className="text-slate-400">
                              {s.next_crawl_at ? new Date(s.next_crawl_at).toLocaleTimeString() : 'Due'}
                            </span>
                          )}
                        </td>
                        <td className="p-3 text-slate-400">
                          {s.last_crawled_at ? new Date(s.last_crawled_at).toLocaleDateString() : 'Never'}
                        </td>
                        <td className="p-3">
                          {s.consecutive_failures && s.consecutive_failures > 0 ? (
                            <span className="text-red-400 font-bold">{s.consecutive_failures} (Backoff)</span>
                          ) : (
                            <span className="text-emerald-400">0</span>
                          )}
                        </td>
                        <td className="p-3">
                          <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                            s.source_status === 'ACTIVE'
                              ? 'bg-emerald-500/15 text-emerald-300'
                              : s.source_status === 'TEMPORARILY_UNAVAILABLE'
                              ? 'bg-amber-500/15 text-amber-300'
                              : s.source_status === 'BLOCKED'
                              ? 'bg-red-500/15 text-red-300'
                              : 'bg-slate-800 text-slate-400'
                          }`}>
                            {s.source_status}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <button
                            onClick={async () => {
                              try {
                                await api.triggerGovernmentCrawl({ batch_size: 1 });
                                await fetchData();
                              } catch (e: any) {
                                setError(e.message);
                              }
                            }}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 hover:text-white text-[10px]"
                          >
                            Crawl
                          </button>
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

      {/* TAB 2: Vacancies & Deadlines */}
      {activeTab === 'vacancies' && (
        <div className="space-y-3">
          {/* Vacancies Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <div className="flex items-center gap-2 flex-1 max-w-sm">
              <Search className="w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search vacancies, designations, departments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-none text-slate-200 placeholder-slate-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={deadlineFilter}
                onChange={(e) => setDeadlineFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-slate-200"
              >
                <option value="all">All Deadlines</option>
                <option value="DEADLINE_TODAY">Deadline Today</option>
                <option value="DEADLINE_APPROACHING">Approaching (&lt;3 Days)</option>
                <option value="EXTENDED">Deadline Extended</option>
                <option value="OPEN">Open</option>
                <option value="EXPIRED">Expired</option>
              </select>

              <button
                onClick={() => setContractOnly(!contractOnly)}
                className={`px-2.5 py-1 rounded border transition ${
                  contractOnly
                    ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                Contractual Only
              </button>
            </div>
          </div>

          {filteredVacancies.length === 0 ? (
            <div className="p-8 text-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
              No government vacancies matched the current query or deadline filter.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredVacancies.map((v) => (
                <div
                  key={v.id}
                  className="p-4 rounded-lg bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition flex flex-col justify-between space-y-3"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-semibold text-white leading-snug">
                        {v.title || v.job_title}
                      </h3>
                      {getDeadlineBadge(v.deadline_status, v.application_deadline)}
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                      <span className="font-medium text-slate-300">
                        {v.organisation_name || v.job_company}
                      </span>
                      <span>•</span>
                      <span>{v.state || 'Central'}</span>
                      {v.department && (
                        <>
                          <span>•</span>
                          <span className="text-slate-400">{v.department}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Attributes Grid */}
                  <div className="grid grid-cols-2 gap-2 text-xs py-2 border-y border-slate-800/60">
                    <div>
                      <span className="text-slate-500">Employment:</span>{' '}
                      <span className="text-slate-300 font-medium">{v.employment_type}</span>
                    </div>
                    {v.contract_duration && (
                      <div>
                        <span className="text-slate-500">Duration:</span>{' '}
                        <span className="text-slate-300">{v.contract_duration}</span>
                      </div>
                    )}
                    {v.pay_scale && (
                      <div className="col-span-2">
                        <span className="text-slate-500">Remuneration:</span>{' '}
                        <span className="text-emerald-400 font-mono">{v.pay_scale}</span>
                      </div>
                    )}
                    {v.application_deadline && (
                      <div className="col-span-2 text-amber-300/90 font-mono text-[11px]">
                        Closing Deadline: {new Date(v.application_deadline).toLocaleDateString()}
                      </div>
                    )}
                  </div>

                  {/* Actions & Links */}
                  <div className="flex items-center justify-between pt-1 text-xs">
                    <div className="text-[11px] text-slate-500">
                      Mode: <span className="text-slate-400 uppercase font-mono">{v.application_mode}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      {v.pdf_url && (
                        <a
                          href={v.pdf_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>Official PDF</span>
                        </a>
                      )}
                      {(v.official_application_url || v.official_notification_url) && (
                        <a
                          href={v.official_application_url || v.official_notification_url || '#'}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 text-slate-400 hover:text-white"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Portal</span>
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Change Audit Trail */}
      {activeTab === 'changes' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <div className="text-slate-300 flex items-center gap-2">
              <History className="w-4 h-4 text-purple-400" />
              <span>Real-Time Change Detection & Corrigendum Audit Trail</span>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={changeTypeFilter}
                onChange={(e) => setChangeTypeFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-slate-200"
              >
                <option value="all">All Change Types</option>
                <option value="NEW">NEW</option>
                <option value="UPDATED">UPDATED</option>
                <option value="CORRIGENDUM">CORRIGENDUM</option>
                <option value="EXTENDED">EXTENDED</option>
                <option value="CLOSED">CLOSED</option>
              </select>
            </div>
          </div>

          {filteredChanges.length === 0 ? (
            <div className="p-8 text-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
              No change events recorded yet. Crawl active sources to populate document revision history.
            </div>
          ) : (
            <div className="border border-slate-800 rounded-lg overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                  <tr>
                    <th className="p-3">Detected At</th>
                    <th className="p-3">Change Type</th>
                    <th className="p-3">Document / Notice</th>
                    <th className="p-3">Summary</th>
                    <th className="p-3">Hash Difference</th>
                    <th className="p-3 text-right">Link</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                  {filteredChanges.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-900/40">
                      <td className="p-3 text-slate-400 whitespace-nowrap">
                        {new Date(c.detected_at).toLocaleString()}
                      </td>
                      <td className="p-3">
                        {getChangeTypeBadge(c.change_type)}
                      </td>
                      <td className="p-3 uppercase text-slate-400 text-[10px]">
                        {c.document_type}
                      </td>
                      <td className="p-3 font-sans text-slate-200 max-w-sm">
                        {c.change_summary || 'Document content update detected'}
                      </td>
                      <td className="p-3 text-[10px] text-slate-500 font-mono">
                        {c.previous_hash ? (
                          <span>{c.previous_hash.slice(0, 8)}... → {c.new_hash?.slice(0, 8)}...</span>
                        ) : (
                          <span>SHA: {c.new_hash?.slice(0, 10)}...</span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Living Registry */}
      {activeTab === 'registry' && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <div className="flex items-center gap-2 flex-1 max-w-sm">
              <Search className="w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                placeholder="Filter by domain or organisation..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-none text-slate-200 placeholder-slate-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-slate-200"
              >
                <option value="all">All Statuses</option>
                <option value="ACTIVE">ACTIVE</option>
                <option value="VERIFIED">VERIFIED</option>
                <option value="DISCOVERED">DISCOVERED</option>
                <option value="REQUIRES_MANUAL_ACCESS">MANUAL ACCESS</option>
                <option value="BLOCKED">BLOCKED</option>
              </select>
            </div>
          </div>

          <div className="border border-slate-800 rounded-lg overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 uppercase font-mono text-[10px]">
                <tr>
                  <th className="p-3">Organisation & Domain</th>
                  <th className="p-3">Level / Type</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Interval</th>
                  <th className="p-3">Jobs</th>
                  <th className="p-3">Next Crawl</th>
                  <th className="p-3 text-right">Links</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredSources.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-900/40">
                    <td className="p-3">
                      <div className="font-semibold text-white">{s.organisation_name}</div>
                      <div className="font-mono text-[11px] text-slate-400">{s.official_domain}</div>
                    </td>
                    <td className="p-3">
                      <div className="capitalize">{s.government_level}</div>
                      <div className="text-[10px] text-slate-500 uppercase font-mono">{s.organisation_type}</div>
                    </td>
                    <td className="p-3">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-medium ${
                        s.source_status === 'ACTIVE' ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30' :
                        s.source_status === 'VERIFIED' ? 'bg-blue-500/15 text-blue-300 border border-blue-500/30' :
                        s.source_status === 'REQUIRES_MANUAL_ACCESS' ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30' :
                        'bg-slate-800 text-slate-400'
                      }`}>
                        {s.source_status}
                      </span>
                    </td>
                    <td className="p-3 font-mono text-[11px] text-slate-300">
                      {s.crawl_interval_minutes ? `${Math.round(s.crawl_interval_minutes / 60)}h` : '24h'}
                    </td>
                    <td className="p-3 font-mono font-semibold text-slate-200">
                      {s.vacancies_found}
                    </td>
                    <td className="p-3 text-[11px] text-slate-400 font-mono">
                      {s.next_crawl_at ? new Date(s.next_crawl_at).toLocaleTimeString() : 'Immediate'}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {s.career_url && (
                          <a
                            href={s.career_url}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1 text-indigo-400 hover:text-indigo-300"
                            title="Recruitment Portal"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                        <a
                          href={`https://${s.official_domain}`}
                          target="_blank"
                          rel="noreferrer"
                          className="p-1 text-slate-400 hover:text-white"
                          title="Official Site"
                        >
                          <Globe className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: State / UT Matrix */}
      {activeTab === 'matrix' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <div>Coverage matrix across Central Ministries, 28 States and 8 Union Territories:</div>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400"></span> Covered</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-400"></span> Minimal</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-slate-600"></span> Unexplored</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {coverage?.states_coverage?.map((st) => {
              const isSelected = selectedState === st.state;
              const statusColor =
                st.status === 'COVERED'
                  ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300'
                  : st.status === 'MINIMAL'
                  ? 'border-amber-500/30 bg-amber-950/20 text-amber-300'
                  : 'border-slate-800 bg-slate-900/40 text-slate-400';

              return (
                <div
                  key={st.state}
                  onClick={() => setSelectedState(isSelected ? 'all' : st.state)}
                  className={`p-3 rounded-lg border cursor-pointer transition ${statusColor} ${
                    isSelected ? 'ring-2 ring-indigo-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold truncate">{st.state}</span>
                    {st.is_ut && <span className="text-[9px] uppercase px-1 rounded bg-slate-800 text-slate-400 font-mono">UT</span>}
                  </div>
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/60 font-mono text-[11px]">
                    <span>{st.sources_count} sources</span>
                    <span className="text-indigo-400 font-bold">{st.vacancies_count} vac</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 6: Sector Breakdown */}
      {activeTab === 'sectors' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {coverage?.sectors_coverage?.map((sec) => (
            <div
              key={sec.sector}
              className="p-4 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between"
            >
              <div>
                <div className="text-sm font-semibold text-white">{sec.sector}</div>
                <div className="text-xs text-slate-400 mt-1">
                  Autonomous hiring boards & research institutes
                </div>
              </div>
              <div className="text-right font-mono">
                <div className="text-xl font-bold text-indigo-400">{sec.sources_count}</div>
                <div className="text-[10px] text-slate-500">{sec.vacancies_count} vacancies</div>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* TAB 7: Universe Discovery Universe & 10-Pass Engine */}
      {activeTab === 'universe' && (
        <div className="space-y-4">
          {/* Mission Hero Banner */}
          <div className="p-5 rounded-xl bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-purple-950/40 border border-blue-500/30 shadow-lg">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-blue-500/20 text-blue-300 border border-blue-500/40">
                    Phase 1–24 Full Execution
                  </span>
                  <span className="text-xs text-slate-400">12,000+ Target Universe Engine</span>
                </div>
                <h3 className="text-lg font-bold text-white mt-1">
                  Indian Government Employment Source Discovery Universe
                </h3>
                <p className="text-xs text-slate-300 mt-1 max-w-2xl leading-relaxed">
                  Autonomous 10-pass discovery engine operating over 15,636 raw items in the universe specification:
                  resolves official domains, links Parent → Child hierarchies, expands all 28 States, 8 UTs, districts & local bodies,
                  discovers recruitment endpoints & PDFs, and registers continuous monitoring.
                </p>
              </div>

              <button
                onClick={handleTriggerUniverseMission}
                disabled={!!actionLoading}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white shadow-lg shadow-indigo-950 transition transform hover:-translate-y-0.5 shrink-0"
              >
                {actionLoading === 'universe' ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Target className="w-4 h-4 text-blue-200" />
                )}
                <span>Execute 10-Pass Mission</span>
              </button>
            </div>

            {/* Target Breakdown Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3 mt-4 pt-4 border-t border-slate-800">
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-[10px] uppercase font-mono text-slate-400">MD Targets Parsed</div>
                <div className="text-xl font-bold font-mono text-white mt-0.5">
                  {universeStats?.total_deduplicated_targets || 2846}
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5">15,636 raw lines deduped</div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-[10px] uppercase font-mono text-emerald-400">Resolved Sources</div>
                <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">
                  {universeStats?.verified_registered_sources || 0}
                </div>
                <div className="text-[9px] text-slate-400 mt-0.5">Official portals matched</div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-[10px] uppercase font-mono text-cyan-400">Authoritative / Verified</div>
                <div className="text-xl font-bold font-mono text-cyan-400 mt-0.5">
                  {universeStats?.verified_registered_sources || 0}
                </div>
                <div className="text-[9px] text-cyan-500/80 mt-0.5">.gov.in / .nic.in / apex</div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-[10px] uppercase font-mono text-amber-400">Unresolved Backlog</div>
                <div className="text-xl font-bold font-mono text-amber-400 mt-0.5">
                  {universeStats?.unresolved_backlog_targets || unresolvedTargets.length}
                </div>
                <div className="text-[9px] text-slate-400 mt-0.5">Stored for retry review</div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-[10px] uppercase font-mono text-purple-400">Hierarchical Links</div>
                <div className="text-xl font-bold font-mono text-purple-400 mt-0.5">
                  {hierarchy.reduce((acc, p) => acc + (p.children?.length || 0), 0)}
                </div>
                <div className="text-[9px] text-slate-400 mt-0.5">Ministry → Lab / Office</div>
              </div>

              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
                <div className="text-[10px] uppercase font-mono text-blue-400">Scheduled Living</div>
                <div className="text-xl font-bold font-mono text-blue-400 mt-0.5">
                  {monitoringStats?.sources_with_scheduled_crawl || 0}
                </div>
                <div className="text-[9px] text-emerald-400 mt-0.5">Continuous monitoring</div>
              </div>
            </div>
          </div>

          {/* Mission Execution Report if run */}
          {missionResult && (
            <div className="p-4 rounded-xl bg-slate-900/90 border border-emerald-500/30">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-bold text-white">Latest 10-Pass Mission Execution Run</span>
                </div>
                <span className="text-xs font-mono text-emerald-400">Status: {missionResult.status}</span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-[10px] uppercase text-slate-400">Targets Parsed</div>
                  <div className="text-lg font-bold font-mono text-white mt-1">{missionResult.total_deduplicated_targets}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-[10px] uppercase text-emerald-400">Verified Sources</div>
                  <div className="text-lg font-bold font-mono text-emerald-400 mt-1">{missionResult.verified_sources}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-[10px] uppercase text-cyan-400">PDF Sources Found</div>
                  <div className="text-lg font-bold font-mono text-cyan-400 mt-1">{missionResult.metrics?.pdf_sources_found ?? 0}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800">
                  <div className="text-[10px] uppercase text-indigo-400">Vacancies Discovered</div>
                  <div className="text-lg font-bold font-mono text-indigo-400 mt-1">{missionResult.metrics?.vacancies_created ?? 0}</div>
                </div>
              </div>

              {/* Breakdown by Sector / Classification */}
              <div className="mt-4 pt-3 border-t border-slate-800">
                <div className="text-xs font-semibold text-slate-300 mb-2">Breakdown by Classification & Sector</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(missionResult.metrics?.breakdown || {}).map(([key, val]) => (
                    <span
                      key={key}
                      className="px-2.5 py-1 rounded bg-slate-800/80 border border-slate-700/60 text-xs font-mono text-slate-300 flex items-center gap-1.5"
                    >
                      <span className="text-slate-400">{key}:</span>
                      <strong className="text-emerald-400">{String(val)}</strong>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 10-Pass Pipeline Architecture Cards */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
              10-Pass Recursive Discovery Pipeline
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2.5">
              {[
                { pass: 'Pass 1', name: 'MD Universe Parse', desc: '15,636 raw items parsed & classified into 2,846 unique targets' },
                { pass: 'Pass 2', name: 'Parent → Child Expansion', desc: 'Ministries linked to 100+ attached labs, centers & boards' },
                { pass: 'Pass 3', name: 'State & UT Expansion', desc: 'All 28 States & 8 UTs directorates, commissions & secretariats' },
                { pass: 'Pass 4', name: 'District & Local Bodies', desc: 'Collectorates, DRDAs, Health Societies & Smart Cities' },
                { pass: 'Pass 5', name: 'Endpoint Discovery', desc: '26+ hiring term path families crawled for careers/notices' },
                { pass: 'Pass 6', name: 'PDF Discovery & Hashing', desc: 'Advs, corrigenda, walk-ins, and extensions parsed via pypdf' },
                { pass: 'Pass 7', name: 'Search Query Rotation', desc: 'Autonomous queries across nic.in, gov.in, res.in, ac.in' },
                { pass: 'Pass 8', name: 'Child Feedback Loop', desc: 'New discovered child organisations fed back into crawler' },
                { pass: 'Pass 9', name: 'Anti-Duplicate Engine', desc: 'Cross-source URL and title hash deduplication before ingestion' },
                { pass: 'Pass 10', name: 'Continuous Monitoring', desc: 'Adaptive intervals, SLA freshness & deadline acceleration' },
              ].map((p, idx) => (
                <div key={idx} className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase text-indigo-400 font-bold">{p.pass}</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <div className="text-xs font-semibold text-white mt-1">{p.name}</div>
                  <div className="text-[10px] text-slate-400 mt-1 leading-snug">{p.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 8: Hierarchy Tree (Phase 4 & Phase 16) */}
      {activeTab === 'hierarchy' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-xs text-slate-300">
            <div>
              <strong>Parent → Child Organization Discovery Graph</strong>
              <div className="text-[11px] text-slate-400 mt-0.5">
                Displays ministries and apex councils linked recursively to attached labs, subordinate offices, and institutes.
              </div>
            </div>
            <div className="font-mono text-cyan-400 text-xs shrink-0">
              {hierarchy.length} Parents | {hierarchy.reduce((acc, p) => acc + (p.children?.length || 0), 0)} Linked Children
            </div>
          </div>

          <div className="space-y-3">
            {hierarchy.map((parent) => (
              <div key={parent.parent_id} className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                        {parent.parent_type || 'CENTRAL_MINISTRY'}
                      </span>
                      <h4 className="text-sm font-bold text-white">{parent.parent_name}</h4>
                    </div>
                    <div className="text-xs text-slate-400 font-mono mt-1 flex items-center gap-2">
                      <span>{parent.parent_domain}</span>
                      {parent.state && <span className="text-slate-500">• {parent.state}</span>}
                    </div>
                  </div>

                  <span className="px-2.5 py-1 rounded-full text-xs font-mono bg-cyan-950/60 text-cyan-300 border border-cyan-500/30">
                    {parent.children?.length || 0} Attached Child Bodies
                  </span>
                </div>

                {/* Children grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5 mt-3">
                  {parent.children?.map((child: any) => (
                    <div
                      key={child.id}
                      className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono text-indigo-400 uppercase">
                          {child.organisation_type || 'LABORATORY'}
                        </span>
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${
                            child.confidence_category === 'AUTHORITATIVE'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                              : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                          }`}
                        >
                          {child.confidence_category || 'AUTHORITATIVE'}
                        </span>
                      </div>
                      <div className="text-xs font-medium text-slate-200 mt-1 line-clamp-1">
                        {child.organisation_name}
                      </div>
                      <div className="text-[10px] font-mono text-slate-500 mt-1 truncate">
                        {child.official_domain}
                      </div>
                      <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/60 text-[10px]">
                        <span className="text-slate-400">{child.state || 'All-India'}</span>
                        {child.recruitment_endpoint && (
                          <a
                            href={child.recruitment_endpoint}
                            target="_blank"
                            rel="noreferrer"
                            className="text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5"
                          >
                            <span>Careers</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 9: Unresolved Target Backlog (Phase 15) */}
      {activeTab === 'unresolved' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 text-xs text-amber-200">
            <div className="flex items-center gap-2 font-semibold text-sm text-amber-300">
              <Compass className="w-4 h-4 text-amber-400" />
              <span>Persistent Unresolved Source Backlog (Mandatory Phase 15)</span>
            </div>
            <p className="mt-1 text-slate-300 leading-relaxed">
              In accordance with Phase 15 rules, targets from the 12,000+ universe specification that cannot currently
              be resolved to an authoritative public domain are <strong>never discarded</strong>. They remain in this
              persistent audit queue with exact query logs, failure reasons, and automatic retry intervals.
            </p>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Showing up to {unresolvedTargets.length} backlog targets</span>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>Pending Recursive Resolution</span>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/60">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Target Name</th>
                  <th className="py-2.5 px-3">Target Type</th>
                  <th className="py-2.5 px-3">State / District</th>
                  <th className="py-2.5 px-3">Reason Unresolved</th>
                  <th className="py-2.5 px-3">Attempted Queries</th>
                  <th className="py-2.5 px-3 text-center">Retries</th>
                  <th className="py-2.5 px-3">Next Retry</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {unresolvedTargets.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-2.5 px-3 font-medium text-white max-w-xs truncate">
                      {item.target_name}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700">
                        {item.target_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                      {item.state || 'National'} {item.district ? `(${item.district})` : ''}
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-amber-300/90 max-w-xs truncate">
                      {item.reason || 'Pending verification'}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-slate-400 max-w-xs truncate">
                      {typeof item.attempted_queries === 'string' && item.attempted_queries.length > 0
                        ? item.attempted_queries
                        : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-center font-mono text-slate-400">
                      {item.attempts_count}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[10px] text-slate-400">
                      {item.retry_at ? item.retry_at.slice(0, 10) : 'Scheduled'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default GovernmentPage;

import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  Star,
  FileText,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  Layers,
  Activity,
  Award,
  Sparkles,
  UserCheck,
  Send,
  Clock,
  Radio,
  Filter,
  Check,
  ChevronRight,
  FileCheck,
  Bot,
  Landmark,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  JobOperatingSystemResponse,
  AttentionQueueItem,
  TopOpportunityItem,
  PipelineStageCount,
} from '../api/client';
import type { PageId } from '../components/Navigation';

interface DashboardPageProps {
  onNavigate: (page: PageId, filter?: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [data, setData] = useState<JobOperatingSystemResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [targetRoleFilter, setTargetRoleFilter] = useState<string>('');
  const [workModeFilter, setWorkModeFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [actionQueueFilter, setActionQueueFilter] = useState<'ALL' | 'HIGH' | 'MEDIUM' | 'INFO'>('ALL');

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getJobOperatingSystem({
        target_role: targetRoleFilter || undefined,
        work_mode: workModeFilter !== 'all' ? workModeFilter : undefined,
        source: sourceFilter !== 'all' ? sourceFilter : undefined,
      });
      setData(res);
    } catch (err: any) {
      setError(err?.message || 'Failed to load Job Operating System dashboard.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, [targetRoleFilter, workModeFilter, sourceFilter]);

  const handleActionClick = (item: AttentionQueueItem) => {
    if (item.action_target === 'jobs') {
      onNavigate('jobs');
    } else if (item.action_target === 'applications') {
      onNavigate('applications');
    } else if (item.action_target === 'profile') {
      onNavigate('profile');
    }
  };

  const handlePipelineClick = (_stage: PipelineStageCount) => {
    onNavigate('applications');
  };

  const filteredActionQueue = (data?.action_queue || []).filter((item) => {
    if (actionQueueFilter === 'ALL') return true;
    return item.priority === actionQueueFilter;
  });

  return (
    <div className="space-y-7 pb-12">
      {/* Top Header & Global Command Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">Job Operating System</h1>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Control Center
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time decision intelligence, application execution queue, and lifecycle memory telemetry.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Action Buttons */}
          <button
            onClick={() => onNavigate('jobs')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
          >
            <Briefcase className="w-3.5 h-3.5 text-blue-400" />
            Browse Jobs
          </button>
          <button
            onClick={() => onNavigate('government')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
          >
            <Landmark className="w-3.5 h-3.5 text-emerald-400" />
            Gov Discovery
          </button>
          <button
            onClick={() => onNavigate('applications')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition"
          >
            <FileText className="w-3.5 h-3.5 text-emerald-400" />
            Pipeline & Memory
          </button>
          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-medium text-white shadow-sm transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Sync Dashboard
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-3 rounded-lg bg-[#0e1626] border border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-400">
          <Filter className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-semibold text-slate-300">View Filters:</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Work Mode */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Work Mode:</span>
            <select
              value={workModeFilter}
              onChange={(e) => setWorkModeFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Modes</option>
              <option value="remote">Remote</option>
              <option value="hybrid">Hybrid</option>
              <option value="onsite">Onsite</option>
            </select>
          </div>

          {/* Source */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Source:</span>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Sources</option>
              <option value="government">Government & PSUs</option>
              <option value="remotive">Remotive</option>
              <option value="manual">Manual</option>
            </select>
          </div>

          {/* Role Keyword */}
          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Role:</span>
            <input
              type="text"
              placeholder="e.g. AI Engineer..."
              value={targetRoleFilter}
              onChange={(e) => setTargetRoleFilter(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 w-36 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {(workModeFilter !== 'all' || sourceFilter !== 'all' || targetRoleFilter) && (
            <button
              onClick={() => {
                setWorkModeFilter('all');
                setSourceFilter('all');
                setTargetRoleFilter('');
              }}
              className="text-indigo-400 hover:text-indigo-300 font-medium ml-1"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-between text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchDashboardData}
            className="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* 1. Job Search Health KPI Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        {[
          {
            title: 'Discovered',
            val: data?.health_kpis.jobs_discovered ?? (loading ? '...' : 0),
            sub: `${data?.health_kpis.canonical_jobs ?? 0} unique`,
            icon: Briefcase,
            color: 'text-blue-400',
            bg: 'bg-blue-500/10',
            border: 'border-blue-500/20',
          },
          {
            title: 'High Relevance',
            val: data?.health_kpis.high_relevance_jobs ?? (loading ? '...' : 0),
            sub: 'Score >= 80%',
            icon: Star,
            color: 'text-amber-400',
            bg: 'bg-amber-500/10',
            border: 'border-amber-500/20',
          },
          {
            title: 'Ready to Apply',
            val: data?.health_kpis.ready_to_apply ?? (loading ? '...' : 0),
            sub: 'Decision=APPLY',
            icon: Send,
            color: 'text-emerald-400',
            bg: 'bg-emerald-500/10',
            border: 'border-emerald-500/20',
          },
          {
            title: 'Review Needed',
            val: data?.health_kpis.review_required ?? (loading ? '...' : 0),
            sub: 'Action required',
            icon: AlertTriangle,
            color: 'text-orange-400',
            bg: 'bg-orange-500/10',
            border: 'border-orange-500/20',
          },
          {
            title: 'Submitted',
            val: data?.health_kpis.applications_submitted ?? (loading ? '...' : 0),
            sub: `${data?.health_kpis.awaiting_response ?? 0} pending`,
            icon: FileCheck,
            color: 'text-indigo-400',
            bg: 'bg-indigo-500/10',
            border: 'border-indigo-500/20',
          },
          {
            title: 'Interviews',
            val: data?.health_kpis.active_interviews ?? (loading ? '...' : 0),
            sub: 'Screening/Calls',
            icon: UserCheck,
            color: 'text-cyan-400',
            bg: 'bg-cyan-500/10',
            border: 'border-cyan-500/20',
          },
          {
            title: 'Offers',
            val: data?.health_kpis.offers_received ?? (loading ? '...' : 0),
            sub: 'Final offers',
            icon: Award,
            color: 'text-purple-400',
            bg: 'bg-purple-500/10',
            border: 'border-purple-500/20',
          },
        ].map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.title}
              className={`p-3.5 rounded-lg bg-[#0e1626] border ${card.border} flex flex-col justify-between`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-medium text-slate-400 truncate">{card.title}</span>
                <div className={`p-1 rounded ${card.bg}`}>
                  <Icon className={`w-3.5 h-3.5 ${card.color}`} />
                </div>
              </div>
              <div>
                <div className="text-xl font-bold font-mono text-slate-100 mb-0.5">
                  {card.val}
                </div>
                <div className="text-[10px] text-slate-400 font-mono truncate">{card.sub}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 2. Today's Action Queue (Prioritized Next Actions) */}
      <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <h2 className="text-sm font-semibold text-slate-200">Today's Action Queue</h2>
              <span className="px-2 py-0.2 text-[10px] font-mono rounded bg-slate-800 text-slate-300">
                {filteredActionQueue.length} items
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Prioritized tasks requiring your explicit decision, review, or approval.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 text-xs bg-slate-900 p-1 rounded-md border border-slate-800 self-start sm:self-auto">
            {(['ALL', 'HIGH', 'MEDIUM', 'INFO'] as const).map((filterVal) => (
              <button
                key={filterVal}
                onClick={() => setActionQueueFilter(filterVal)}
                className={`px-2.5 py-1 rounded text-[11px] font-medium transition ${
                  actionQueueFilter === filterVal
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {filterVal}
              </button>
            ))}
          </div>
        </div>

        {/* Action Queue List */}
        {filteredActionQueue.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            <Check className="w-6 h-6 mx-auto mb-2 text-emerald-400/80" />
            <p className="text-slate-300 font-medium">All caught up!</p>
            <p className="text-slate-400 text-[11px] mt-0.5">
              No pending tasks require immediate human attention.
            </p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {filteredActionQueue.map((item) => {
              const isHigh = item.priority === 'HIGH';
              const isMedium = item.priority === 'MEDIUM';

              const badgeColor = isHigh
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                : isMedium
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                : 'bg-blue-500/10 text-blue-400 border-blue-500/20';

              const borderHighlight = isHigh ? 'border-l-4 border-l-rose-500' : isMedium ? 'border-l-4 border-l-amber-500' : 'border-l-4 border-l-blue-500';

              return (
                <div
                  key={item.id}
                  className={`p-3.5 rounded-r-lg bg-slate-900/60 border border-slate-800/80 ${borderHighlight} flex flex-col md:flex-row md:items-center justify-between gap-3 hover:bg-slate-900 transition`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 text-[9px] font-bold font-mono rounded border uppercase ${badgeColor}`}>
                        {item.priority}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                        {item.category}
                      </span>
                      <h3 className="text-xs font-semibold text-slate-200">{item.title}</h3>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed">{item.description}</p>
                  </div>

                  <button
                    onClick={() => handleActionClick(item)}
                    className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition self-start md:self-auto"
                  >
                    <span>{item.action_label}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 3. Job Search Funnel & 14-Stage Application Pipeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Full Funnel */}
        <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-slate-200">Job Search Funnel</h2>
            </div>
            <span className="text-[11px] font-mono text-slate-400">Step-to-Step Yield</span>
          </div>

          <div className="space-y-2 pt-1">
            {(data?.funnel.steps || []).map((step, idx) => (
              <div key={step.stage} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-4 text-[10px] font-mono text-slate-400">{idx + 1}.</span>
                  <span className="text-slate-300 font-medium">{step.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  {step.conversion_from_prev !== null && step.conversion_from_prev !== undefined && (
                    <span className="text-[10px] font-mono text-slate-400">
                      {step.conversion_from_prev.toFixed(1)}% yield
                    </span>
                  )}
                  <span className="w-12 text-right font-mono font-bold text-slate-100">
                    {step.count}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 14-Stage Pipeline */}
        <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-slate-200">Application Pipeline</h2>
            </div>
            <button
              onClick={() => onNavigate('applications')}
              className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
            >
              Open Applications <ChevronRight className="w-3 h-3" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
            {(data?.pipeline || []).map((p) => {
              const isZero = p.count === 0;
              const badgeBg = p.is_positive
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : p.is_terminal
                ? 'bg-slate-800/40 text-slate-400 border-slate-700/50'
                : 'bg-indigo-500/10 text-indigo-300 border-indigo-500/20';

              return (
                <div
                  key={p.stage}
                  onClick={() => handlePipelineClick(p)}
                  className={`p-2.5 rounded bg-slate-900/60 border border-slate-800 hover:border-slate-700 cursor-pointer transition flex items-center justify-between ${
                    isZero ? 'opacity-60' : ''
                  }`}
                >
                  <div className="truncate pr-1">
                    <div className="text-[11px] text-slate-300 font-medium truncate">{p.label}</div>
                    <div className="text-[9px] font-mono text-slate-400 uppercase tracking-wider">{p.stage}</div>
                  </div>
                  <span className={`px-2 py-0.5 text-xs font-bold font-mono rounded border ${badgeBg}`}>
                    {p.count}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 4. Curated Top Opportunities (Ready for Action) */}
      <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-200">High-Affinity Opportunities</h2>
            <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-slate-300">
              Top Canonical Postings
            </span>
          </div>
          <button
            onClick={() => onNavigate('jobs')}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
          >
            View All Jobs <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {(data?.top_opportunities || []).length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            <p>No matching opportunities available in the current filter.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {data?.top_opportunities.map((job: TopOpportunityItem) => {
              const isApply = job.decision === 'APPLY';
              const isReview = job.decision === 'REVIEW';
              const decColor = isApply
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : isReview
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/20';

              return (
                <div
                  key={job.id}
                  className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition space-y-3"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="truncate">
                        <h3 className="text-xs font-semibold text-slate-100 truncate">{job.title}</h3>
                        <div className="text-[11px] text-slate-400 truncate">{job.company}</div>
                      </div>
                      <span className={`px-1.5 py-0.5 text-[10px] font-mono font-bold rounded border uppercase shrink-0 ${decColor}`}>
                        {job.decision || 'UNDECIDED'}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                      {job.match_score !== null && job.match_score !== undefined && (
                        <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                          {job.match_score.toFixed(0)}% Match
                        </span>
                      )}
                      {job.work_mode && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          {job.work_mode}
                        </span>
                      )}
                      {job.salary_display && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-emerald-400">
                          {job.salary_display}
                        </span>
                      )}
                    </div>

                    {job.decision_reasons && job.decision_reasons.length > 0 && (
                      <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed pt-1">
                        {job.decision_reasons[0]}
                      </p>
                    )}
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-[10px] font-mono text-slate-400">
                      via {job.source}
                    </span>
                    <button
                      onClick={() => onNavigate('jobs')}
                      className="text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
                    >
                      View in Jobs <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

        {/* 5. Telemetry Grid: Match Quality, Profile Health, Source Status, Outcome Yields, Controlled Autonomy */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {/* Match Quality Distribution */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <span className="text-xs font-semibold text-slate-200">Match Distribution</span>
            <Star className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-emerald-400">High Relevance (&gt;=80%)</span>
              <span className="font-mono font-bold text-slate-200">{data?.match_quality.high_relevance}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-indigo-300">Good Relevance (70-79%)</span>
              <span className="font-mono font-bold text-slate-200">{data?.match_quality.good_relevance}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-amber-400">Partial Relevance (60-69%)</span>
              <span className="font-mono font-bold text-slate-200">{data?.match_quality.partial_relevance}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Low Relevance (&lt;60%)</span>
              <span className="font-mono font-bold text-slate-200">{data?.match_quality.low_relevance}</span>
            </div>
            <div className="flex items-center justify-between border-t border-slate-800 pt-1.5 text-rose-400">
              <span>Hard Requirement Fails</span>
              <span className="font-mono font-bold">{data?.match_quality.hard_mismatches}</span>
            </div>
          </div>
        </div>

        {/* Profile Health */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <span className="text-xs font-semibold text-slate-200">Profile Health</span>
            <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Completeness:</span>
              <span className="font-mono font-bold text-indigo-400">
                {data?.profile_health.completeness_score}%
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Application Ready:</span>
              <span className={`font-mono text-[11px] font-bold ${data?.profile_health.is_ready_for_apply ? 'text-emerald-400' : 'text-amber-400'}`}>
                {data?.profile_health.is_ready_for_apply ? 'READY' : 'INCOMPLETE'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Master Resume:</span>
              <span className="font-mono text-[11px] text-slate-300">
                {data?.profile_health.has_resume ? 'Available (v1.0)' : 'Missing'}
              </span>
            </div>
            <div className="pt-2 border-t border-slate-800">
              <button
                onClick={() => onNavigate('profile')}
                className="w-full py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium transition text-center"
              >
                Inspect Profile
              </button>
            </div>
          </div>
        </div>

        {/* Source Health */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <span className="text-xs font-semibold text-slate-200">Source Health</span>
            <Radio className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="space-y-2 text-xs">
            {(data?.source_health || []).map((s) => (
              <div key={s.source} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${s.status === 'active' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                  <span className="text-slate-300 font-medium capitalize">{s.source}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">
                  {s.jobs_fetched} fetched
                </span>
              </div>
            ))}
            <div className="pt-2 border-t border-slate-800">
              <button
                onClick={() => onNavigate('jobs')}
                className="w-full py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium transition text-center"
              >
                Manage Connectors
              </button>
            </div>
          </div>
        </div>

        {/* Feedback & Memory Summary */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <span className="text-xs font-semibold text-slate-200">Outcome Yields</span>
            <Award className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">App -&gt; Interview:</span>
              <span className="font-mono text-slate-200">
                {data?.feedback_summary.app_to_interview_rate.toFixed(1)}% ({data?.feedback_summary.app_to_interview_fraction})
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">App -&gt; Offer:</span>
              <span className="font-mono text-slate-200">
                {data?.feedback_summary.app_to_offer_rate.toFixed(1)}% ({data?.feedback_summary.app_to_offer_fraction})
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Interview -&gt; Offer:</span>
              <span className="font-mono text-slate-200">
                {data?.feedback_summary.interview_to_offer_rate.toFixed(1)}% ({data?.feedback_summary.interview_to_offer_fraction})
              </span>
            </div>
            {data?.feedback_summary.sample_size_alert && (
              <p className="text-[10px] text-amber-400/90 leading-tight pt-1">
                * {data.feedback_summary.sample_size_alert}
              </p>
            )}
            <div className="pt-2 border-t border-slate-800">
              <button
                onClick={() => onNavigate('applications')}
                className="w-full py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-medium transition text-center"
              >
                View Feedback
              </button>
            </div>
          </div>
        </div>

        {/* Step 12: Controlled Autonomy Card */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
            <span className="text-xs font-semibold text-slate-200">Controlled Autonomy</span>
            <Bot className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Mode:</span>
              <span className="font-mono text-cyan-400 font-bold uppercase text-[11px]">
                {data?.automation_telemetry?.mode || 'ASSISTED'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Task Queue:</span>
              <span className="font-mono text-slate-200">
                {data?.automation_telemetry?.pending_tasks || 0} pending, {data?.automation_telemetry?.running_tasks || 0} active
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Safety Blocked:</span>
              <span className={`font-mono font-bold ${(data?.automation_telemetry?.blocked_tasks || 0) > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                {data?.automation_telemetry?.blocked_tasks || 0} halted
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400">Approval Gate:</span>
              <span className="font-mono text-emerald-400 font-semibold">ENFORCED</span>
            </div>
            <div className="pt-2 border-t border-slate-800">
              <button
                onClick={() => onNavigate('settings')}
                className="w-full py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-400 text-[11px] font-medium transition text-center"
              >
                Autonomy Settings
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Recent Activity Chronological Feed */}
      <div className="p-5 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-slate-200">Recent System Activity</h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Append-only Audit Stream
          </span>
        </div>

        {(data?.recent_activity || []).length === 0 ? (
          <div className="py-6 text-center text-slate-500 text-xs">
            <p>No recent activity recorded yet.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {data?.recent_activity.map((act) => (
              <div key={act.id} className="py-2.5 flex items-start justify-between gap-4 text-xs">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-200">{act.title}</span>
                    <span className="px-1.5 py-0.2 text-[10px] font-mono rounded bg-slate-800 text-slate-400">
                      {act.actor}
                    </span>
                    {act.company && (
                      <span className="text-[11px] text-indigo-400 font-medium">
                        @ {act.company}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">{act.description}</p>
                </div>
                <span className="text-[10px] font-mono text-slate-400 shrink-0">
                  {new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

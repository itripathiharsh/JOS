import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Award,
  AlertTriangle,
  Briefcase,
  XCircle,
  RefreshCw,
  BarChart3,
  Lightbulb,
  Globe,
} from 'lucide-react';
import { api } from '../api/client';
import type { FeedbackReport } from '../api/client';

export const ApplicationFeedbackDashboard: React.FC = () => {
  const [report, setReport] = useState<FeedbackReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [perfView, setPerfView] = useState<'role' | 'source'>('role');


  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMemoryFeedbackAnalytics();
      setReport(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load feedback analytics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, []);

  if (loading) {
    return (
      <div className="p-8 rounded-xl bg-[#0e1626] border border-slate-800 text-center space-y-2">
        <RefreshCw className="w-5 h-5 animate-spin mx-auto text-indigo-400" />
        <span className="text-xs text-slate-400">Loading career feedback analytics...</span>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center justify-between">
        <span>{error || 'Unable to compute application feedback.'}</span>
        <button
          onClick={fetchReport}
          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs"
        >
          Retry
        </button>
      </div>
    );
  }

  const { conversions, lifecycle_counts, role_performance, source_performance, match_tier_performance, rejection_patterns, decision_alignment, observations, sample_size_alert } = report;

  return (
    <div className="space-y-6">
      {/* Header & Refresh */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-slate-100">Application Memory & Feedback Loop</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic career outcomes, conversion rates, role performance, and rejection pattern analysis.
          </p>
        </div>
        <button
          onClick={fetchReport}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Metrics
        </button>
      </div>

      {/* Sample Size Warning Banner */}
      {sample_size_alert && (
        <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <strong className="font-semibold">Directional Observations:</strong> {sample_size_alert}
          </div>
        </div>
      )}

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg bg-[#0e1626] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400">Total Tracked</span>
          <div className="text-xl font-bold text-slate-100 mt-1">{report.total_applications}</div>
          <span className="text-[10px] text-slate-500">all pipeline states</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0e1626] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400">Submitted</span>
          <div className="text-xl font-bold text-indigo-400 mt-1">{conversions.submitted_total}</div>
          <span className="text-[10px] text-indigo-300/70">active & completed</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0e1626] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400">Interviews</span>
          <div className="text-xl font-bold text-blue-400 mt-1">
            {conversions.application_to_interview.numerator}
          </div>
          <span className="text-[10px] text-blue-300/70">screenings & rounds</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0e1626] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400">Offers</span>
          <div className="text-xl font-bold text-emerald-400 mt-1">
            {conversions.application_to_offer.numerator}
          </div>
          <span className="text-[10px] text-emerald-300/70">received & accepted</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0e1626] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400">Rejections</span>
          <div className="text-xl font-bold text-rose-400 mt-1">
            {rejection_patterns.total_rejections}
          </div>
          <span className="text-[10px] text-rose-300/70">classified reasons</span>
        </div>

        <div className="p-3 rounded-lg bg-[#0e1626] border border-slate-800">
          <span className="text-[11px] font-mono text-slate-400">Awaiting Reply</span>
          <div className="text-xl font-bold text-amber-400 mt-1">
            {lifecycle_counts['NO_RESPONSE'] || 0}
          </div>
          <span className="text-[10px] text-amber-300/70">no response yet</span>
        </div>
      </div>

      {/* Conversion Funnels (Explicit Denominators) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* App -> Interview */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-200">Application → Interview</span>
            <span className="text-[10px] font-mono text-slate-400">
              {conversions.application_to_interview.numerator}/{conversions.application_to_interview.denominator}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-blue-400">
              {conversions.application_to_interview.rate}%
            </span>
            <span className="text-[11px] text-slate-400">conversion rate</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(conversions.application_to_interview.rate, 100)}%` }}
            />
          </div>
          {conversions.application_to_interview.warning && (
            <p className="text-[10px] text-slate-500 italic">{conversions.application_to_interview.warning}</p>
          )}
        </div>

        {/* Interview -> Offer */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-200">Interview → Offer</span>
            <span className="text-[10px] font-mono text-slate-400">
              {conversions.interview_to_offer.numerator}/{conversions.interview_to_offer.denominator}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-emerald-400">
              {conversions.interview_to_offer.rate}%
            </span>
            <span className="text-[11px] text-slate-400">interview close rate</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(conversions.interview_to_offer.rate, 100)}%` }}
            />
          </div>
          {conversions.interview_to_offer.warning && (
            <p className="text-[10px] text-slate-500 italic">{conversions.interview_to_offer.warning}</p>
          )}
        </div>

        {/* Application -> Offer */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-200">Application → Offer</span>
            <span className="text-[10px] font-mono text-slate-400">
              {conversions.application_to_offer.numerator}/{conversions.application_to_offer.denominator}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-indigo-400">
              {conversions.application_to_offer.rate}%
            </span>
            <span className="text-[11px] text-slate-400">overall yield</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min(conversions.application_to_offer.rate, 100)}%` }}
            />
          </div>
          {conversions.application_to_offer.warning && (
            <p className="text-[10px] text-slate-500 italic">{conversions.application_to_offer.warning}</p>
          )}
        </div>
      </div>

      {/* Two Column Section: Role Performance & Rejection Patterns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Target Role & Source Performance */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              {perfView === 'role' ? <Briefcase className="w-4 h-4 text-indigo-400" /> : <Globe className="w-4 h-4 text-indigo-400" />}
              <div className="flex items-center gap-1.5 bg-slate-900 p-0.5 rounded border border-slate-800 text-[10px]">
                <button
                  onClick={() => setPerfView('role')}
                  className={`px-2 py-0.5 rounded font-medium transition ${perfView === 'role' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  By Role
                </button>
                <button
                  onClick={() => setPerfView('source')}
                  className={`px-2 py-0.5 rounded font-medium transition ${perfView === 'source' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  By Source
                </button>
              </div>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Interview Yield</span>
          </div>

          {perfView === 'role' ? (
            role_performance.length === 0 ? (
              <p className="text-slate-500 text-xs italic">No role data available yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800/80">
                    <tr>
                      <th className="pb-2">Role</th>
                      <th className="pb-2 text-center">Apps</th>
                      <th className="pb-2 text-center">Int.</th>
                      <th className="pb-2 text-right">Int. Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {role_performance.slice(0, 6).map((rp, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40">
                        <td className="py-2 pr-2">
                          <span className="font-medium text-slate-200 block truncate max-w-[180px]">{rp.role}</span>
                          {rp.is_small_sample && (
                            <span className="text-[9px] text-amber-400/80 font-mono">Small N</span>
                          )}
                        </td>
                        <td className="py-2 text-center font-mono text-slate-300">{rp.applications}</td>
                        <td className="py-2 text-center font-mono text-blue-400">{rp.interviews}</td>
                        <td className="py-2 text-right font-mono font-semibold text-slate-100">
                          {rp.interview_rate}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            source_performance.length === 0 ? (
              <p className="text-slate-500 text-xs italic">No source data available yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] font-mono text-slate-400 uppercase border-b border-slate-800/80">
                    <tr>
                      <th className="pb-2">Source</th>
                      <th className="pb-2 text-center">Apps</th>
                      <th className="pb-2 text-center">Int.</th>
                      <th className="pb-2 text-right">Int. Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {source_performance.map((sp, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40">
                        <td className="py-2 pr-2">
                          <span className="font-medium text-slate-200 block capitalize">{sp.source}</span>
                          {sp.is_small_sample && (
                            <span className="text-[9px] text-amber-400/80 font-mono">Small N</span>
                          )}
                        </td>
                        <td className="py-2 text-center font-mono text-slate-300">{sp.applications}</td>
                        <td className="py-2 text-center font-mono text-blue-400">{sp.interviews}</td>
                        <td className="py-2 text-right font-mono font-semibold text-slate-100">
                          {sp.interview_rate}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </div>


        {/* Rejection Pattern Analysis */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-rose-400" />
              <h3 className="font-semibold text-slate-200 text-xs">Rejection Pattern Analysis</h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">Categorized</span>
          </div>

          {rejection_patterns.breakdown.length === 0 ? (
            <p className="text-slate-500 text-xs italic">No rejections recorded.</p>
          ) : (
            <div className="space-y-2.5">
              {rejection_patterns.breakdown.map((item, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="capitalize text-slate-300 font-medium">
                      {item.category.replace('_', ' ')}
                    </span>
                    <span className="font-mono text-slate-400 text-[11px]">
                      {item.count} ({item.percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-rose-500/80 h-full rounded-full"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                  {item.sample_reasons.length > 0 && (
                    <p className="text-[10px] text-slate-400 italic truncate pl-1">
                      "{item.sample_reasons[0]}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Match Score Tiers & Decision Alignment Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Match Score Tier Breakdown */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <BarChart3 className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-slate-200 text-xs">Outcomes by Match Score Tier</h3>
          </div>
          <div className="space-y-2">
            {match_tier_performance.map((tier) => (
              <div key={tier.tier} className="p-2.5 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs">
                <div>
                  <span className="font-semibold text-slate-200">{tier.label}</span>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                    {tier.applications} apps • {tier.interviews} interviews • {tier.offers} offers
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-indigo-300 font-mono">{tier.interview_rate}%</span>
                  <span className="text-[10px] text-slate-500 block">interview rate</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Decision Alignment Matrix */}
        <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-400" />
              <h3 className="font-semibold text-slate-200 text-xs">System Decision vs User Action Matrix</h3>
            </div>
            <span className="text-[10px] font-mono text-slate-400">
              {decision_alignment.total_overrides_recorded} Overrides
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="font-semibold text-emerald-400">APPLY Followed</span>
                <span className="text-[10px] text-slate-400 block font-mono">System recommended APPLY</span>
              </div>
              <div className="text-right font-mono">
                <span className="text-slate-200">{decision_alignment.matrix.APPLY_followed.total} apps</span>
                <span className="text-[10px] text-blue-400 block">{decision_alignment.matrix.APPLY_followed.interviews} interviews</span>
              </div>
            </div>

            <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="font-semibold text-amber-300">SKIP Overridden to APPLY</span>
                <span className="text-[10px] text-slate-400 block font-mono">User applied despite system SKIP</span>
              </div>
              <div className="text-right font-mono">
                <span className="text-slate-200">{decision_alignment.matrix.SKIP_overridden_to_APPLY.total} apps</span>
                <span className="text-[10px] text-rose-400 block">{decision_alignment.matrix.SKIP_overridden_to_APPLY.rejections} rejected</span>
              </div>
            </div>

            <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="font-semibold text-blue-300">REVIEW Approved</span>
                <span className="text-[10px] text-slate-400 block font-mono">Candidate confirmed human review</span>
              </div>
              <div className="text-right font-mono">
                <span className="text-slate-200">{decision_alignment.matrix.REVIEW_approved.total} apps</span>
                <span className="text-[10px] text-blue-400 block">{decision_alignment.matrix.REVIEW_approved.interviews} interviews</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Purely Descriptive Observations */}
      <div className="p-4 rounded-lg bg-[#0e1626] border border-slate-800 space-y-3">
        <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
          <Lightbulb className="w-4 h-4 text-amber-400" />
          <h3 className="font-semibold text-slate-200 text-xs">Deterministic Feedback Observations</h3>
        </div>
        <div className="space-y-2">
          {observations.map((obs, idx) => (
            <div key={idx} className="p-2.5 rounded bg-slate-900/70 border border-slate-800/80 flex items-start gap-2.5 text-xs">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono shrink-0 font-bold ${
                obs.type === 'CAUTION'
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                  : obs.type === 'SUMMARY'
                  ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                  : 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
              }`}>
                {obs.type}
              </span>
              <p className="text-slate-300 leading-relaxed">{obs.message}</p>
            </div>
          ))}
        </div>
        <p className="text-[10px] text-slate-500 italic pt-1">
          * Safeguard: Feedback observations are strictly descriptive. The system does not automatically modify your candidate profile, target roles, or decision scoring rules.
        </p>
      </div>
    </div>
  );
};

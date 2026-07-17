'use client'

import { useSession } from '@/components/SessionContext'
import { useQuery } from '@tanstack/react-query'
import { getAnalytics } from '@/lib/api'
import { ATSScoreGauge } from '@/components/ATSScoreGauge'
import { AgentLog } from '@/components/AgentLog'
import {
  BarChart3, Briefcase, Zap, CheckCircle2, FileText, Mic2, TrendingUp, Loader2
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend
} from 'recharts'
import { cn } from '@/lib/utils'

const COLORS = ['#22c55e', '#eab308', '#f97316', '#ef4444', '#6366f1']

export default function AnalyticsPage() {
  const { sessionId, status } = useSession()

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['analytics', sessionId],
    queryFn: () => getAnalytics(sessionId!),
    enabled: !!sessionId && !!status?.jobs_discovered,
    refetchInterval: status?.status === 'running' ? 5000 : false,
  })

  const metricCards = [
    {
      label: 'Jobs Discovered',
      value: analytics?.jobs_discovered ?? status?.jobs_discovered ?? 0,
      icon: Briefcase,
      color: 'text-indigo-400',
      bg: 'bg-indigo-500/10',
    },
    {
      label: 'Avg ATS Score',
      value: analytics ? `${Math.round(analytics.avg_ats_score)}` : '—',
      icon: Zap,
      color: 'text-yellow-400',
      bg: 'bg-yellow-500/10',
      suffix: '/100',
    },
    {
      label: 'Ready to Apply',
      value: analytics?.applications_ready ?? status?.applications_ready ?? 0,
      icon: CheckCircle2,
      color: 'text-green-400',
      bg: 'bg-green-500/10',
    },
    {
      label: 'Resume Versions',
      value: analytics?.resume_versions ?? status?.resume_versions ?? 0,
      icon: FileText,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10',
    },
    {
      label: 'Interview Preps',
      value: analytics?.interviews_prepared ?? Object.keys(status?.interview_preps || {}).length,
      icon: Mic2,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    {
      label: 'Avg Match Score',
      value: analytics ? `${Math.round(analytics.avg_match_score)}` : '—',
      icon: TrendingUp,
      color: 'text-orange-400',
      bg: 'bg-orange-500/10',
      suffix: '%',
    },
  ]

  // Build score distribution for bar chart
  const scoreDistData = analytics?.score_distribution
    ? Object.entries(analytics.score_distribution).map(([range, count]) => ({
        range,
        count,
      }))
    : []

  // Decision breakdown pie
  const appStatuses = status?.application_statuses || {}
  const decisions = { apply: 0, improve: 0, skip: 0 }
  Object.values(appStatuses).forEach((s) => {
    if (s.decision in decisions) decisions[s.decision as keyof typeof decisions]++
  })
  const decisionData = [
    { name: 'Ready to Apply', value: decisions.apply, color: '#22c55e' },
    { name: 'Need Improvement', value: decisions.improve, color: '#eab308' },
    { name: 'Skip', value: decisions.skip, color: '#ef4444' },
  ].filter((d) => d.value > 0)

  return (
    <div className="p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-[#f0f0f8] flex items-center gap-2">
            <BarChart3 size={22} className="text-indigo-400" />
            Analytics Dashboard
          </h1>
          <p className="text-[#9090a8] mt-1">
            Real-time overview of your job search pipeline performance.
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={28} className="animate-spin text-indigo-400" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* KPI grid */}
            <div className="grid grid-cols-3 gap-4">
              {metricCards.map((card) => {
                const Icon = card.icon
                return (
                  <div key={card.label} className="card p-4">
                    <div className="flex items-center gap-3">
                      <div className={cn('p-2.5 rounded-xl', card.bg)}>
                        <Icon size={18} className={card.color} />
                      </div>
                      <div>
                        <div className="text-[#9090a8] text-xs">{card.label}</div>
                        <div className="text-xl font-bold text-[#f0f0f8]">
                          {card.value}
                          {card.suffix && (
                            <span className="text-sm text-[#5a5a70] ml-0.5">{card.suffix}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-2 gap-4">
              {/* Score distribution */}
              {scoreDistData.length > 0 && (
                <div className="card p-5">
                  <h3 className="section-title text-base">ATS Score Distribution</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={scoreDistData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                      <XAxis dataKey="range" tick={{ fontSize: 11, fill: '#9090a8' }} />
                      <YAxis tick={{ fontSize: 11, fill: '#9090a8' }} />
                      <Tooltip
                        contentStyle={{
                          background: '#1e1e28',
                          border: '1px solid #2a2a38',
                          borderRadius: 8,
                          color: '#f0f0f8',
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {scoreDistData.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Decision breakdown */}
              {decisionData.length > 0 && (
                <div className="card p-5">
                  <h3 className="section-title text-base">Application Decisions</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={decisionData}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {decisionData.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: '#1e1e28',
                          border: '1px solid #2a2a38',
                          borderRadius: 8,
                          color: '#f0f0f8',
                          fontSize: 12,
                        }}
                      />
                      <Legend
                        formatter={(value) => (
                          <span style={{ color: '#9090a8', fontSize: 12 }}>{value}</span>
                        )}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Top missing keywords */}
            {analytics?.top_missing_keywords && analytics.top_missing_keywords.length > 0 && (
              <div className="card p-5">
                <h3 className="section-title">Top Missing Keywords Across All Jobs</h3>
                <div className="flex flex-wrap gap-2">
                  {analytics.top_missing_keywords.slice(0, 20).map((kw, i) => (
                    <span
                      key={kw}
                      className="badge bg-red-500/10 text-red-400 border-red-500/20 text-xs"
                      style={{ opacity: 1 - i * 0.03 }}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-[#5a5a70] mt-2">
                  Add these to your resume to improve ATS compatibility across all matched jobs.
                </p>
              </div>
            )}

            {/* Per-job ATS summary */}
            {Object.keys(status?.ats_scores || {}).length > 0 && (
              <div className="card p-5">
                <h3 className="section-title">Per-Job ATS Breakdown</h3>
                <div className="flex flex-wrap gap-4">
                  {Object.entries(status?.ats_scores || {}).map(([jobId, ats]) => {
                    const job = status?.filtered_jobs?.find(j => j.job_id === jobId)
                    const opt = status?.optimized_resumes?.[jobId]
                    const finalScore = opt?.optimized_score ?? ats.total_score
                    return (
                      <div key={jobId} className="text-center">
                        <ATSScoreGauge score={finalScore} size="sm" showLabel={false} />
                        <div className="text-[10px] text-[#9090a8] mt-1 max-w-[80px] truncate mx-auto">
                          {job?.company || jobId.slice(0, 8)}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Agent activity log */}
            {status?.agent_messages && status.agent_messages.length > 0 && (
              <div className="card p-5">
                <h3 className="section-title">Full Pipeline Log</h3>
                <AgentLog messages={status.agent_messages} maxItems={30} />
              </div>
            )}

            {/* Empty state */}
            {!analytics && Object.keys(status?.ats_scores || {}).length === 0 && (
              <div className="card p-10 text-center text-[#5a5a70]">
                No analytics data yet. Upload a resume and start the pipeline.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

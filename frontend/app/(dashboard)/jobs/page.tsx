'use client'

import { useState } from 'react'
import { useSession } from '@/components/SessionContext'
import { JobCard } from '@/components/JobCard'
import { AgentLog } from '@/components/AgentLog'
import { approveJobs } from '@/lib/api'
import { toast } from 'sonner'
import { Loader2, Filter, CheckSquare, Briefcase } from 'lucide-react'
import { cn } from '@/lib/utils'

type FilterType = 'all' | 'apply' | 'improve' | 'skip'

export default function JobsPage() {
  const { status, sessionId, refreshStatus } = useSession()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [filter, setFilter] = useState<FilterType>('all')
  const [approving, setApproving] = useState(false)

  const jobs = status?.filtered_jobs || []
  const appStatuses = status?.application_statuses || {}
  const atsScores = status?.ats_scores || {}
  const optimized = status?.optimized_resumes || {}
  const isRunning = status?.status === 'running'

  const filtered = jobs.filter((job) => {
    if (filter === 'all') return true
    return appStatuses[job.job_id]?.decision === filter
  })

  const toggleSelect = (jobId: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(jobId)) next.delete(jobId)
      else next.add(jobId)
      return next
    })
  }

  const handleApprove = async () => {
    if (!sessionId || selected.size === 0) return
    setApproving(true)
    try {
      await approveJobs(sessionId, Array.from(selected))
      toast.success(`${selected.size} job(s) approved for interview prep!`)
      await refreshStatus()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Approval failed')
    } finally {
      setApproving(false)
    }
  }

  const filterCounts: Record<FilterType, number> = {
    all: jobs.length,
    apply: jobs.filter(j => appStatuses[j.job_id]?.decision === 'apply').length,
    improve: jobs.filter(j => appStatuses[j.job_id]?.decision === 'improve').length,
    skip: jobs.filter(j => appStatuses[j.job_id]?.decision === 'skip').length,
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[#f0f0f8] flex items-center gap-2">
              <Briefcase size={22} className="text-indigo-400" />
              Job Matches
            </h1>
            <p className="text-[#9090a8] mt-1">
              {jobs.length > 0
                ? `${jobs.length} jobs matched · sorted by ATS compatibility`
                : 'Waiting for job discovery to complete...'}
            </p>
          </div>

          {/* Approve button */}
          {status?.pending_approval && selected.size > 0 && (
            <button
              className="btn-primary flex items-center gap-2"
              onClick={handleApprove}
              disabled={approving}
            >
              {approving ? (
                <Loader2 size={15} className="animate-spin" />
              ) : (
                <CheckSquare size={15} />
              )}
              Approve {selected.size} Job{selected.size !== 1 ? 's' : ''}
            </button>
          )}
        </div>

        {/* Filters */}
        {jobs.length > 0 && (
          <div className="flex gap-2 mb-4">
            <Filter size={15} className="text-[#5a5a70] mt-2" />
            {(['all', 'apply', 'improve', 'skip'] as FilterType[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  'px-3 py-1 rounded-full text-xs font-medium transition-colors border',
                  filter === f
                    ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300'
                    : 'border-[#2a2a38] text-[#9090a8] hover:text-[#f0f0f8] hover:border-[#3a3a50]'
                )}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                <span className="ml-1.5 text-[10px] opacity-70">({filterCounts[f]})</span>
              </button>
            ))}
          </div>
        )}

        {/* Running state */}
        {isRunning && jobs.length === 0 && (
          <div className="card p-8 text-center">
            <Loader2 size={32} className="animate-spin text-indigo-400 mx-auto mb-3" />
            <div className="text-[#f0f0f8] font-medium">Discovering and scoring jobs...</div>
            <div className="text-sm text-[#9090a8] mt-1">
              Current agent: {status?.current_agent?.replace(/_/g, ' ')}
            </div>
          </div>
        )}

        {/* Pending approval banner */}
        {status?.pending_approval && (
          <div className="mb-4 p-4 bg-indigo-500/10 border border-indigo-500/30 rounded-xl">
            <div className="flex items-center gap-2">
              <CheckSquare size={16} className="text-indigo-400" />
              <span className="text-indigo-300 font-medium text-sm">Human Approval Required</span>
            </div>
            <p className="text-xs text-[#9090a8] mt-1">
              Select the jobs you want to proceed with for interview preparation, then click Approve.
            </p>
          </div>
        )}

        {/* Job grid */}
        {filtered.length > 0 && (
          <div className="space-y-3">
            {filtered.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                atsScore={atsScores[job.job_id]}
                optimized={optimized[job.job_id]}
                appStatus={appStatuses[job.job_id]}
                selected={selected.has(job.job_id)}
                onSelect={status?.pending_approval ? toggleSelect : undefined}
                showCheckbox={!!status?.pending_approval}
              />
            ))}
          </div>
        )}

        {/* Agent log */}
        {status?.agent_messages && status.agent_messages.length > 0 && (
          <div className="card p-4 mt-6">
            <h3 className="section-title">Pipeline Activity</h3>
            <AgentLog messages={status.agent_messages} compact maxItems={15} />
          </div>
        )}
      </div>
    </div>
  )
}

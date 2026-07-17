'use client'

import { useState } from 'react'
import { cn, formatSalary, decisionColor, decisionLabel, timeAgo } from '@/lib/utils'
import { ATSScoreGauge } from './ATSScoreGauge'
import type { JobListing, ApplicationStatus, ATSBreakdown, OptimizedResume } from '@/lib/types'
import {
  MapPin,
  Briefcase,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Wifi,
  Check,
} from 'lucide-react'

interface JobCardProps {
  job: JobListing
  atsScore?: ATSBreakdown
  optimized?: OptimizedResume
  appStatus?: ApplicationStatus
  selected?: boolean
  onSelect?: (jobId: string) => void
  showCheckbox?: boolean
}

export function JobCard({
  job,
  atsScore,
  optimized,
  appStatus,
  selected,
  onSelect,
  showCheckbox = false,
}: JobCardProps) {
  const [expanded, setExpanded] = useState(false)

  const score = optimized?.optimized_score ?? atsScore?.total_score ?? job.match_score

  return (
    <div
      className={cn(
        'card-hover p-4 cursor-pointer select-none',
        selected && 'border-indigo-500/60 bg-indigo-500/5'
      )}
      onClick={() => onSelect?.(job.job_id)}
    >
      {/* Header row */}
      <div className="flex items-start gap-3">
        {showCheckbox && (
          <div
            className={cn(
              'mt-0.5 w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 transition-colors',
              selected
                ? 'bg-indigo-600 border-indigo-600'
                : 'border-[#3a3a50] bg-[#1e1e28]'
            )}
          >
            {selected && <Check size={12} className="text-white" />}
          </div>
        )}

        {/* Score gauge */}
        <ATSScoreGauge score={score} size="sm" showLabel={false} className="flex-shrink-0" />

        {/* Job info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold text-[#f0f0f8] text-sm leading-tight">
                {job.title}
              </h3>
              <div className="text-sm text-indigo-400 mt-0.5">{job.company}</div>
            </div>
            {appStatus && (
              <span
                className={cn(
                  'badge text-[10px] flex-shrink-0',
                  decisionColor(appStatus.decision)
                )}
              >
                {decisionLabel(appStatus.decision)}
              </span>
            )}
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5 text-xs text-[#9090a8]">
            {job.location && (
              <span className="flex items-center gap-1">
                <MapPin size={10} />
                {job.location}
              </span>
            )}
            {job.employment_type && (
              <span className="flex items-center gap-1">
                <Briefcase size={10} />
                {job.employment_type}
              </span>
            )}
            {job.remote_friendly && (
              <span className="flex items-center gap-1 text-green-400">
                <Wifi size={10} />
                Remote
              </span>
            )}
            {job.posted_date && (
              <span className="flex items-center gap-1">
                <Clock size={10} />
                {timeAgo(job.posted_date)}
              </span>
            )}
          </div>

          {/* Salary */}
          {(job.salary_min || job.salary_max) && (
            <div className="mt-1 text-xs font-medium text-green-400">
              {formatSalary(job.salary_min, job.salary_max, job.salary_currency)}
            </div>
          )}
        </div>

        {/* Match score badge */}
        <div className="text-right flex-shrink-0">
          <div className="text-[10px] text-[#5a5a70]">Match</div>
          <div className="text-sm font-bold text-indigo-400">
            {Math.round(job.match_score)}%
          </div>
        </div>
      </div>

      {/* Score breakdown */}
      {atsScore && (
        <div className="mt-3 pt-3 border-t border-[#2a2a38]">
          <div className="flex gap-4 text-xs">
            <ScorePill label="Keywords" value={atsScore.keyword_score} />
            <ScorePill label="Skills" value={atsScore.skills_coverage_score} />
            <ScorePill label="Exp" value={atsScore.experience_alignment_score} />
            <ScorePill label="Edu" value={atsScore.education_match_score} />
          </div>

          {/* Keywords */}
          {atsScore.matched_keywords.length > 0 && (
            <div className="mt-2">
              <button
                className="flex items-center gap-1 text-[10px] text-[#5a5a70] hover:text-[#9090a8]"
                onClick={(e) => {
                  e.stopPropagation()
                  setExpanded((p) => !p)
                }}
              >
                {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                {expanded ? 'Hide' : 'Show'} keyword details
              </button>

              {expanded && (
                <div className="mt-2 space-y-1.5 animate-fade-in">
                  <div>
                    <div className="text-[10px] text-green-400 mb-1">
                      Matched ({atsScore.matched_keywords.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {atsScore.matched_keywords.slice(0, 12).map((kw) => (
                        <span
                          key={kw}
                          className="text-[10px] px-1.5 py-0.5 bg-green-500/10 text-green-400 rounded border border-green-500/20"
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                  {atsScore.missing_keywords.length > 0 && (
                    <div>
                      <div className="text-[10px] text-red-400 mb-1">
                        Missing ({atsScore.missing_keywords.length})
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {atsScore.missing_keywords.slice(0, 12).map((kw) => (
                          <span
                            key={kw}
                            className="text-[10px] px-1.5 py-0.5 bg-red-500/10 text-red-400 rounded border border-red-500/20"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
        {job.application_url && (
          <a
            href={job.application_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <ExternalLink size={11} />
            Apply
          </a>
        )}
        <span className="text-[10px] text-[#5a5a70] ml-auto">
          via {job.source}
        </span>
      </div>
    </div>
  )
}

function ScorePill({ label, value }: { label: string; value: number }) {
  const getColor = (v: number) => {
    if (v >= 80) return 'text-green-400'
    if (v >= 60) return 'text-yellow-400'
    return 'text-red-400'
  }

  return (
    <div className="text-center">
      <div className={cn('font-medium', getColor(value))}>{Math.round(value)}</div>
      <div className="text-[#5a5a70] text-[10px]">{label}</div>
    </div>
  )
}

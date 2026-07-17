'use client'

import { useState } from 'react'
import { useSession } from '@/components/SessionContext'
import { ATSScoreGauge, ATSScoreBar } from '@/components/ATSScoreGauge'
import { reoptimizeResume } from '@/lib/api'
import { toast } from 'sonner'
import { Loader2, Zap, ArrowUp, FileText, Copy, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'

export default function OptimizePage() {
  const { status, sessionId, refreshStatus } = useSession()
  const [selectedJob, setSelectedJob] = useState<string | null>(null)
  const [reoptimizing, setReoptimizing] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'resume' | 'cover'>('resume')

  const jobs = status?.filtered_jobs || []
  const optimized = status?.optimized_resumes || {}
  const atsScores = status?.ats_scores || {}

  const selectedJobData = jobs.find(j => j.job_id === selectedJob)
  const selectedOpt = selectedJob ? optimized[selectedJob] : null
  const selectedAts = selectedJob ? atsScores[selectedJob] : null

  const handleReoptimize = async (jobId: string) => {
    if (!sessionId) return
    setReoptimizing(jobId)
    try {
      await reoptimizeResume(sessionId, jobId)
      await refreshStatus()
      toast.success('Resume re-optimized!')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Re-optimization failed')
    } finally {
      setReoptimizing(null)
    }
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(id)
    setTimeout(() => setCopied(null), 2000)
    toast.success('Copied to clipboard')
  }

  return (
    <div className="p-8 h-full">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-[#f0f0f8] flex items-center gap-2">
            <Zap size={22} className="text-indigo-400" />
            ATS Optimization
          </h1>
          <p className="text-[#9090a8] mt-1">
            View AI-optimized resumes and cover letters tailored to each job.
          </p>
        </div>

        {jobs.length === 0 ? (
          <div className="card p-8 text-center text-[#5a5a70]">
            No optimized resumes yet. Run the pipeline from the Upload page first.
          </div>
        ) : (
          <div className="flex gap-5">
            {/* Job list */}
            <div className="w-72 flex-shrink-0 space-y-2">
              {jobs.map((job) => {
                const opt = optimized[job.job_id]
                const ats = atsScores[job.job_id]
                const originalScore = ats?.total_score ?? job.match_score
                const finalScore = opt?.optimized_score ?? originalScore
                const improved = opt && opt.optimized_score > opt.original_score

                return (
                  <button
                    key={job.job_id}
                    className={cn(
                      'w-full text-left p-3 rounded-xl border transition-all',
                      selectedJob === job.job_id
                        ? 'border-indigo-500/50 bg-indigo-500/10'
                        : 'border-[#2a2a38] bg-[#16161d] hover:border-[#3a3a50]'
                    )}
                    onClick={() => setSelectedJob(job.job_id)}
                  >
                    <div className="flex items-center gap-2">
                      <ATSScoreGauge score={finalScore} size="sm" showLabel={false} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-[#f0f0f8] truncate">
                          {job.title}
                        </div>
                        <div className="text-xs text-indigo-400 truncate">{job.company}</div>
                        {improved && (
                          <div className="flex items-center gap-1 text-green-400 text-[10px] mt-0.5">
                            <ArrowUp size={9} />
                            +{Math.round(opt.optimized_score - opt.original_score)} pts
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>

            {/* Detail panel */}
            <div className="flex-1 min-w-0">
              {!selectedJob ? (
                <div className="card p-8 text-center text-[#5a5a70]">
                  Select a job to view optimization details
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Score comparison */}
                  {selectedOpt && (
                    <div className="card p-5">
                      <div className="flex items-center justify-between mb-4">
                        <h2 className="font-semibold text-[#f0f0f8]">
                          {selectedJobData?.title} @ {selectedJobData?.company}
                        </h2>
                        <button
                          className="btn-secondary text-xs flex items-center gap-1.5"
                          onClick={() => handleReoptimize(selectedJob)}
                          disabled={!!reoptimizing}
                        >
                          {reoptimizing === selectedJob ? (
                            <Loader2 size={12} className="animate-spin" />
                          ) : (
                            <Zap size={12} />
                          )}
                          Re-optimize
                        </button>
                      </div>

                      <div className="flex items-center gap-8">
                        <div className="text-center">
                          <div className="text-sm text-[#9090a8] mb-2">Original</div>
                          <ATSScoreGauge score={selectedOpt.original_score} size="md" label="Score" />
                        </div>
                        <div className="text-2xl text-[#5a5a70]">→</div>
                        <div className="text-center">
                          <div className="text-sm text-green-400 mb-2">Optimized</div>
                          <ATSScoreGauge score={selectedOpt.optimized_score} size="md" label="Score" />
                        </div>
                        <div className="flex-1">
                          {selectedAts && (
                            <div className="space-y-2">
                              <ATSScoreBar label="Keywords" score={selectedAts.keyword_score} />
                              <ATSScoreBar label="Skills" score={selectedAts.skills_coverage_score} />
                              <ATSScoreBar label="Experience" score={selectedAts.experience_alignment_score} />
                              <ATSScoreBar label="Education" score={selectedAts.education_match_score} />
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Added keywords */}
                      {selectedOpt.added_keywords.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-[#2a2a38]">
                          <div className="text-xs text-[#9090a8] mb-2">Keywords Added</div>
                          <div className="flex flex-wrap gap-1">
                            {selectedOpt.added_keywords.map((kw) => (
                              <span key={kw} className="badge bg-indigo-500/10 text-indigo-300 border-indigo-500/20 text-[10px]">
                                +{kw}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Optimization notes */}
                      {selectedOpt.optimization_notes.length > 0 && (
                        <div className="mt-3">
                          <div className="text-xs text-[#9090a8] mb-2">Optimization Notes</div>
                          <ul className="space-y-1">
                            {selectedOpt.optimization_notes.map((note, i) => (
                              <li key={i} className="text-xs text-[#9090a8] flex gap-2">
                                <span className="text-indigo-400 flex-shrink-0">•</span>
                                {note}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Resume / Cover letter tabs */}
                  {selectedOpt && (
                    <div className="card overflow-hidden">
                      <div className="flex border-b border-[#2a2a38]">
                        <button
                          className={cn(
                            'flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors',
                            activeTab === 'resume'
                              ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5'
                              : 'text-[#9090a8] hover:text-[#f0f0f8]'
                          )}
                          onClick={() => setActiveTab('resume')}
                        >
                          <FileText size={14} />
                          Optimized Resume
                        </button>
                        <button
                          className={cn(
                            'flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium transition-colors',
                            activeTab === 'cover'
                              ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5'
                              : 'text-[#9090a8] hover:text-[#f0f0f8]'
                          )}
                          onClick={() => setActiveTab('cover')}
                        >
                          <FileText size={14} />
                          Cover Letter
                        </button>
                      </div>

                      <div className="p-5 relative">
                        <button
                          className="absolute top-4 right-4 btn-ghost text-xs flex items-center gap-1"
                          onClick={() => copyToClipboard(
                            activeTab === 'resume'
                              ? `${selectedOpt.optimized_summary}\n\n${Object.entries(selectedOpt.optimized_bullets).map(([role, bullets]) => `${role}:\n${bullets.map(b => `• ${b}`).join('\n')}`).join('\n\n')}`
                              : selectedOpt.cover_letter,
                            activeTab
                          )}
                        >
                          {copied === activeTab ? (
                            <Check size={12} className="text-green-400" />
                          ) : (
                            <Copy size={12} />
                          )}
                          {copied === activeTab ? 'Copied!' : 'Copy'}
                        </button>

                        {activeTab === 'resume' ? (
                          <div className="space-y-4 pr-16">
                            <div>
                              <div className="label mb-2">Professional Summary</div>
                              <p className="text-sm text-[#f0f0f8] leading-relaxed">
                                {selectedOpt.optimized_summary}
                              </p>
                            </div>
                            {Object.entries(selectedOpt.optimized_bullets).map(([role, bullets]) => (
                              <div key={role}>
                                <div className="label mb-2">{role}</div>
                                <ul className="space-y-1.5">
                                  {bullets.map((bullet, i) => (
                                    <li key={i} className="text-sm text-[#9090a8] flex gap-2">
                                      <span className="text-indigo-400 flex-shrink-0">•</span>
                                      {bullet}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="prose prose-invert prose-sm max-w-none pr-16">
                            <ReactMarkdown>{selectedOpt.cover_letter}</ReactMarkdown>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {!selectedOpt && (
                    <div className="card p-6 text-center text-[#5a5a70] text-sm">
                      {status?.status === 'running'
                        ? 'ATS optimization in progress...'
                        : 'No optimization data for this job yet.'}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

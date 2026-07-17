'use client'

import { useState } from 'react'
import { useSession } from '@/components/SessionContext'
import { cn, difficultyColor } from '@/lib/utils'
import { Brain, ChevronDown, ChevronUp, Building2, DollarSign, HelpCircle } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

export default function InterviewPage() {
  const { status } = useSession()
  const [selectedJob, setSelectedJob] = useState<string | null>(null)
  const [expandedQ, setExpandedQ] = useState<number | null>(null)

  const preps = status?.interview_preps || {}
  const jobs = status?.filtered_jobs || []
  const approvedIds = status?.approved_job_ids || []

  const prepJobs = jobs.filter(
    (j) => preps[j.job_id] || approvedIds.includes(j.job_id)
  )

  const selectedPrep = selectedJob ? preps[selectedJob] : null

  return (
    <div className="p-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-[#f0f0f8] flex items-center gap-2">
            <Brain size={22} className="text-indigo-400" />
            Interview Intelligence
          </h1>
          <p className="text-[#9090a8] mt-1">
            AI-generated top 20 questions with model answers, salary tips, and company research.
          </p>
        </div>

        {prepJobs.length === 0 ? (
          <div className="card p-8 text-center text-[#5a5a70]">
            No interview prep yet. Approve jobs and complete the pipeline first.
          </div>
        ) : (
          <div className="flex gap-5">
            {/* Job selector */}
            <div className="w-64 flex-shrink-0 space-y-2">
              {prepJobs.map((job) => {
                const prep = preps[job.job_id]
                return (
                  <button
                    key={job.job_id}
                    className={cn(
                      'w-full text-left p-3 rounded-xl border transition-all',
                      selectedJob === job.job_id
                        ? 'border-indigo-500/50 bg-indigo-500/10'
                        : 'border-[#2a2a38] bg-[#16161d] hover:border-[#3a3a50]'
                    )}
                    onClick={() => { setSelectedJob(job.job_id); setExpandedQ(null) }}
                  >
                    <div className="font-medium text-sm text-[#f0f0f8] truncate">{job.title}</div>
                    <div className="text-xs text-indigo-400 truncate mt-0.5">{job.company}</div>
                    {prep && (
                      <div className="text-[10px] text-[#5a5a70] mt-1">
                        {prep.top_questions.length} questions ready
                      </div>
                    )}
                  </button>
                )
              })}
            </div>

            {/* Detail */}
            <div className="flex-1 min-w-0">
              {!selectedJob ? (
                <div className="card p-8 text-center text-[#5a5a70]">Select a job to view interview prep</div>
              ) : !selectedPrep ? (
                <div className="card p-8 text-center text-[#5a5a70]">Interview prep loading...</div>
              ) : (
                <div className="space-y-4">
                  {/* Company research */}
                  <div className="card p-5">
                    <h3 className="flex items-center gap-2 font-semibold text-[#f0f0f8] mb-3">
                      <Building2 size={15} className="text-indigo-400" />
                      Company Research
                    </h3>
                    <pre className="text-xs text-[#9090a8] whitespace-pre-wrap leading-relaxed font-sans">
                      {selectedPrep.company_research}
                    </pre>
                  </div>

                  {/* Salary tips */}
                  <div className="card p-4">
                    <h3 className="flex items-center gap-2 font-semibold text-[#f0f0f8] mb-2 text-sm">
                      <DollarSign size={14} className="text-green-400" />
                      Salary Negotiation
                    </h3>
                    <p className="text-xs text-[#9090a8]">{selectedPrep.salary_negotiation_tips}</p>
                  </div>

                  {/* Questions to ask */}
                  {selectedPrep.questions_to_ask.length > 0 && (
                    <div className="card p-4">
                      <h3 className="flex items-center gap-2 font-semibold text-[#f0f0f8] mb-2 text-sm">
                        <HelpCircle size={14} className="text-yellow-400" />
                        Questions to Ask the Interviewer
                      </h3>
                      <ul className="space-y-1">
                        {selectedPrep.questions_to_ask.map((q, i) => (
                          <li key={i} className="text-xs text-[#9090a8] flex gap-2">
                            <span className="text-yellow-400 flex-shrink-0">{i + 1}.</span>
                            {q}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Top 20 Questions */}
                  <div>
                    <h3 className="section-title">Top {selectedPrep.top_questions.length} Interview Questions</h3>
                    <div className="space-y-2">
                      {selectedPrep.top_questions.map((q, i) => (
                        <div key={i} className="card overflow-hidden">
                          <button
                            className="w-full flex items-start gap-3 p-4 text-left"
                            onClick={() => setExpandedQ(expandedQ === i ? null : i)}
                          >
                            <span className="text-xs text-[#5a5a70] font-mono w-5 flex-shrink-0 mt-0.5">
                              {String(i + 1).padStart(2, '0')}
                            </span>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm text-[#f0f0f8]">{q.question}</div>
                              <div className="flex gap-2 mt-1.5">
                                <span className="badge border-[#2a2a38] text-[#9090a8] text-[10px]">
                                  {q.category}
                                </span>
                                <span className={cn('badge text-[10px]', difficultyColor(q.difficulty))}>
                                  {q.difficulty}
                                </span>
                              </div>
                            </div>
                            {expandedQ === i ? (
                              <ChevronUp size={15} className="text-[#5a5a70] flex-shrink-0 mt-0.5" />
                            ) : (
                              <ChevronDown size={15} className="text-[#5a5a70] flex-shrink-0 mt-0.5" />
                            )}
                          </button>

                          {expandedQ === i && (
                            <div className="px-4 pb-4 border-t border-[#2a2a38] pt-3 animate-fade-in">
                              <div className="label mb-2">Model Answer</div>
                              <div className="text-sm text-[#9090a8] leading-relaxed prose prose-invert prose-sm max-w-none">
                                <ReactMarkdown>{q.model_answer}</ReactMarkdown>
                              </div>

                              {q.star_framework && (
                                <div className="mt-3 p-3 bg-indigo-500/5 border border-indigo-500/20 rounded-lg">
                                  <div className="label mb-1 text-indigo-400">STAR Framework</div>
                                  <p className="text-xs text-[#9090a8]">{q.star_framework}</p>
                                </div>
                              )}

                              {q.follow_up_questions.length > 0 && (
                                <div className="mt-3">
                                  <div className="label mb-1">Likely Follow-ups</div>
                                  <ul className="space-y-1">
                                    {q.follow_up_questions.map((fq, fi) => (
                                      <li key={fi} className="text-xs text-[#5a5a70]">→ {fq}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

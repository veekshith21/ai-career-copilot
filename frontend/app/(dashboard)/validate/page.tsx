'use client'

import { useSession } from '@/components/SessionContext'
import { ATSScoreGauge } from '@/components/ATSScoreGauge'
import { cn } from '@/lib/utils'
import { ClipboardCheck, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'

export default function ValidatePage() {
  const { status } = useSession()

  const jobs = status?.filtered_jobs || []
  const validations = status?.validation_results || {}
  const atsScores = status?.ats_scores || {}

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-[#f0f0f8] flex items-center gap-2">
            <ClipboardCheck size={22} className="text-indigo-400" />
            Resume Validation
          </h1>
          <p className="text-[#9090a8] mt-1">
            Post-optimization validation: keyword coverage, formatting, and gap analysis.
          </p>
        </div>

        {jobs.length === 0 ? (
          <div className="card p-8 text-center text-[#5a5a70]">
            No validation results yet. Complete the pipeline first.
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => {
              const val = validations[job.job_id]
              const ats = atsScores[job.job_id]
              if (!val && !ats) return null

              const score = val?.recalculated_score ?? ats?.total_score ?? 0
              const passed = val?.passed ?? score >= 80

              return (
                <div key={job.job_id} className="card p-5">
                  <div className="flex items-start gap-4">
                    <ATSScoreGauge score={score} size="md" label="Final Score" />

                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-[#f0f0f8]">{job.title}</h3>
                        <span className="text-[#9090a8]">@</span>
                        <span className="text-indigo-400">{job.company}</span>
                        {passed ? (
                          <span className="badge bg-green-500/10 text-green-400 border-green-500/20 text-[10px]">
                            <CheckCircle2 size={10} className="mr-1" />
                            Passed
                          </span>
                        ) : (
                          <span className="badge bg-yellow-500/10 text-yellow-400 border-yellow-500/20 text-[10px]">
                            <AlertCircle size={10} className="mr-1" />
                            Needs Work
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-4 mt-3">
                        {/* Missing skills */}
                        {(val?.missing_skills || ats?.missing_skills || []).length > 0 && (
                          <div>
                            <div className="label mb-2 flex items-center gap-1 text-red-400">
                              <XCircle size={10} />
                              Missing Skills
                            </div>
                            <div className="flex flex-wrap gap-1">
                              {(val?.missing_skills || ats?.missing_skills || []).slice(0, 8).map((skill) => (
                                <span key={skill} className="badge bg-red-500/10 text-red-400 border-red-500/20 text-[10px]">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Formatting issues */}
                        {(val?.formatting_issues || []).length > 0 && (
                          <div>
                            <div className="label mb-2 flex items-center gap-1 text-yellow-400">
                              <AlertCircle size={10} />
                              Formatting Issues
                            </div>
                            <ul className="space-y-1">
                              {val.formatting_issues.slice(0, 5).map((issue, i) => (
                                <li key={i} className="text-xs text-yellow-400">• {issue}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      {/* Recommendations */}
                      {(val?.recommendations || ats?.recommendations || []).length > 0 && (
                        <div className="mt-3 pt-3 border-t border-[#2a2a38]">
                          <div className="label mb-2">Recommendations</div>
                          <ul className="space-y-1">
                            {(val?.recommendations || ats?.recommendations || []).slice(0, 4).map((rec, i) => (
                              <li key={i} className="text-xs text-[#9090a8] flex gap-2">
                                <span className="text-indigo-400 flex-shrink-0">→</span>
                                {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

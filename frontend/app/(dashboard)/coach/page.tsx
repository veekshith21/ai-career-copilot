'use client'

import { useState, useRef, useEffect } from 'react'
import { useSession } from '@/components/SessionContext'
import { startMockInterview, sendInterviewAnswer } from '@/lib/api'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { Mic2, Send, Loader2, RotateCcw, Star } from 'lucide-react'

interface Turn {
  role: 'interviewer' | 'candidate'
  content: string
  feedback?: string
  scores?: Record<string, number>
  isComplete?: boolean
}

export default function CoachPage() {
  const { status, sessionId } = useSession()
  const [selectedJob, setSelectedJob] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [answer, setAnswer] = useState('')
  const [started, setStarted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [completed, setCompleted] = useState(false)
  const [sessionScores, setSessionScores] = useState<Record<string, number> | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const jobs = status?.filtered_jobs || []
  const approvedIds = status?.approved_job_ids || []
  const preps = status?.interview_preps || {}

  const eligibleJobs = jobs.filter(j => approvedIds.includes(j.job_id) || preps[j.job_id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  const handleStart = async () => {
    if (!sessionId || !selectedJob) return
    setLoading(true)
    try {
      const res = await startMockInterview(sessionId, selectedJob)
      setTurns([{ role: 'interviewer', content: res.first_question }])
      setStarted(true)
      setCompleted(false)
      setSessionScores(null)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to start interview')
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async () => {
    if (!sessionId || !selectedJob || !answer.trim()) return
    const userAnswer = answer.trim()
    setAnswer('')
    setTurns(prev => [...prev, { role: 'candidate', content: userAnswer }])
    setLoading(true)
    try {
      const res = await sendInterviewAnswer(sessionId, selectedJob, userAnswer)
      const feedbackTurn: Turn = {
        role: 'interviewer',
        content: res.next_question || res.overall_impression || "Great interview! We're done.",
        feedback: res.feedback,
        scores: res.scores,
        isComplete: res.is_complete,
      }
      setTurns(prev => [...prev, feedbackTurn])
      if (res.is_complete) {
        setCompleted(true)
        if (res.session_scores) setSessionScores(res.session_scores)
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to send answer')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setTurns([])
    setStarted(false)
    setCompleted(false)
    setSessionScores(null)
    setAnswer('')
  }

  const selectedJobData = jobs.find(j => j.job_id === selectedJob)

  return (
    <div className="p-8 h-[calc(100vh-0px)]">
      <div className="max-w-4xl mx-auto h-full flex flex-col">
        <div className="mb-4 flex-shrink-0">
          <h1 className="text-2xl font-bold text-[#f0f0f8] flex items-center gap-2">
            <Mic2 size={22} className="text-indigo-400" />
            Mock Interview Coach
          </h1>
          <p className="text-[#9090a8] mt-1 text-sm">
            AI-powered mock interviews with STAR evaluation and real-time feedback.
          </p>
        </div>

        {eligibleJobs.length === 0 ? (
          <div className="card p-8 text-center text-[#5a5a70]">
            No approved jobs yet. Approve jobs in the Jobs tab first.
          </div>
        ) : !started ? (
          /* Job selection */
          <div className="card p-6 flex-shrink-0">
            <h2 className="font-semibold text-[#f0f0f8] mb-4">Select a Role to Practice</h2>
            <div className="grid grid-cols-2 gap-3 mb-5">
              {eligibleJobs.map((job) => (
                <button
                  key={job.job_id}
                  className={cn(
                    'p-4 rounded-xl border text-left transition-all',
                    selectedJob === job.job_id
                      ? 'border-indigo-500/60 bg-indigo-500/10'
                      : 'border-[#2a2a38] hover:border-[#3a3a50]'
                  )}
                  onClick={() => setSelectedJob(job.job_id)}
                >
                  <div className="font-medium text-[#f0f0f8] text-sm">{job.title}</div>
                  <div className="text-xs text-indigo-400 mt-0.5">{job.company}</div>
                  <div className="text-[10px] text-[#5a5a70] mt-1">
                    {preps[job.job_id]?.top_questions.length || 0} questions prepared
                  </div>
                </button>
              ))}
            </div>
            <button
              className="btn-primary w-full flex items-center justify-center gap-2"
              onClick={handleStart}
              disabled={!selectedJob || loading}
            >
              {loading ? (
                <><Loader2 size={16} className="animate-spin" /> Starting interview...</>
              ) : (
                <><Mic2 size={16} /> Start Mock Interview</>
              )}
            </button>
          </div>
        ) : (
          /* Interview UI */
          <div className="flex flex-col flex-1 min-h-0">
            {/* Header */}
            <div className="flex items-center justify-between mb-3 flex-shrink-0">
              <div className="text-sm text-[#9090a8]">
                Interviewing for <span className="text-indigo-400">{selectedJobData?.title}</span> @ {selectedJobData?.company}
              </div>
              <button onClick={handleReset} className="btn-ghost text-xs flex items-center gap-1">
                <RotateCcw size={12} />
                Reset
              </button>
            </div>

            {/* Chat window */}
            <div className="flex-1 overflow-y-auto space-y-3 min-h-0 pb-3">
              {turns.map((turn, i) => (
                <div key={i} className={cn('flex flex-col gap-1', turn.role === 'candidate' && 'items-end')}>
                  <div
                    className={cn(
                      'max-w-[80%] rounded-xl px-4 py-3 text-sm',
                      turn.role === 'interviewer'
                        ? 'bg-[#1e1e28] border border-[#2a2a38] text-[#f0f0f8]'
                        : 'bg-indigo-600/20 border border-indigo-500/30 text-indigo-100'
                    )}
                  >
                    {turn.content}
                  </div>

                  {/* Feedback block */}
                  {turn.feedback && (
                    <div className="max-w-[80%] bg-green-500/5 border border-green-500/20 rounded-xl px-4 py-3 text-xs text-[#9090a8]">
                      <div className="text-green-400 font-medium mb-1">Feedback</div>
                      <p>{turn.feedback}</p>
                      {turn.scores && (
                        <div className="flex gap-4 mt-2">
                          {Object.entries(turn.scores).map(([k, v]) => (
                            <div key={k} className="text-center">
                              <div className="flex gap-0.5">
                                {[1,2,3,4,5].map(star => (
                                  <Star
                                    key={star}
                                    size={9}
                                    className={star <= Math.round(Number(v) / 2) ? 'text-yellow-400 fill-yellow-400' : 'text-[#3a3a50]'}
                                  />
                                ))}
                              </div>
                              <div className="text-[10px] text-[#5a5a70] mt-0.5 capitalize">
                                {k.replace(/_/g, ' ')}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-2 text-sm text-[#9090a8]">
                  <Loader2 size={14} className="animate-spin text-indigo-400" />
                  Evaluating your answer...
                </div>
              )}

              {/* Completion card */}
              {completed && sessionScores && (
                <div className="card p-5 border-green-500/30 bg-green-500/5">
                  <div className="font-semibold text-green-400 mb-3">Interview Complete! 🎉</div>
                  <div className="grid grid-cols-4 gap-3">
                    {Object.entries(sessionScores).map(([k, v]) => (
                      <div key={k} className="text-center">
                        <div className="text-xl font-bold text-[#f0f0f8]">{Math.round(Number(v))}</div>
                        <div className="text-[10px] text-[#9090a8] capitalize">{k.replace(/_/g, ' ')}</div>
                      </div>
                    ))}
                  </div>
                  <button className="btn-primary mt-4 w-full text-sm" onClick={handleReset}>
                    Practice Again
                  </button>
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            {/* Input */}
            {!completed && (
              <div className="flex gap-2 pt-3 border-t border-[#2a2a38] flex-shrink-0">
                <textarea
                  className="input resize-none text-sm flex-1"
                  rows={3}
                  placeholder="Type your answer... (Ctrl+Enter to send)"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.ctrlKey) handleSend()
                  }}
                  disabled={loading}
                />
                <button
                  className="btn-primary flex-shrink-0 self-end flex items-center gap-1.5"
                  onClick={handleSend}
                  disabled={loading || !answer.trim()}
                >
                  {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
                  Send
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

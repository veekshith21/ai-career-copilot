import type {
  PipelineStatus,
  Analytics,
  InterviewPrep,
  MockInterviewSession,
} from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API error')
  }
  return res.json()
}

export async function createSession(): Promise<{ session_id: string }> {
  return apiFetch('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

export async function uploadResume(sessionId: string, file: File) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/resume`, {
    method: 'POST', body: form,
  })
  if (!res.ok) throw new Error((await res.json().catch(() => ({detail: res.statusText}))).detail)
  return res.json()
}

export async function startPipeline(sessionId: string, jobQuery: string, location: string) {
  return apiFetch(`/api/sessions/${sessionId}/run`, {
    method: 'POST',
    body: JSON.stringify({ job_query: jobQuery, location }),
  })
}

export async function getStatus(sessionId: string): Promise<PipelineStatus> {
  return apiFetch(`/api/sessions/${sessionId}/status`)
}

export async function approveJobs(sessionId: string, jobIds: string[]) {
  return apiFetch(`/api/sessions/${sessionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approved_job_ids: jobIds }),
  })
}

export async function reoptimizeResume(sessionId: string, jobId: string) {
  return apiFetch(`/api/sessions/${sessionId}/optimize/${jobId}`, { method: 'POST' })
}

export async function getInterviewPrep(sessionId: string, jobId: string): Promise<InterviewPrep> {
  return apiFetch(`/api/sessions/${sessionId}/interview/${jobId}`)
}

export async function startMockInterview(sessionId: string, jobId: string): Promise<{ message: string; first_question: string }> {
  return apiFetch(`/api/sessions/${sessionId}/interview/${jobId}/start`, { method: 'POST' })
}

export async function sendInterviewAnswer(sessionId: string, jobId: string, answer: string): Promise<{ feedback: string; scores: Record<string, number>; next_question: string | null; is_complete: boolean; overall_impression?: string; session_scores?: Record<string, number> }> {
  return apiFetch(`/api/sessions/${sessionId}/interview/${jobId}/answer`, {
    method: 'POST',
    body: JSON.stringify({ answer }),
  })
}

export async function getMockSession(sessionId: string, jobId: string): Promise<MockInterviewSession> {
  return apiFetch(`/api/sessions/${sessionId}/interview/${jobId}/session`)
}

export async function getAnalytics(sessionId: string): Promise<Analytics> {
  return apiFetch(`/api/sessions/${sessionId}/analytics`)
}

export async function healthCheck() {
  return apiFetch('/health')
}

export function createWebSocket(sessionId: string, onMessage: (e: MessageEvent) => void, onClose?: () => void): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/${sessionId}`)
  ws.onmessage = onMessage
  ws.onclose = onClose || (() => {})
  ws.onerror = (e) => console.error('[WS Error]', e)
  return ws
}
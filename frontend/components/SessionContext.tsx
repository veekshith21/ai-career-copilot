'use client'

import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { createSession, getStatus, createWebSocket } from '@/lib/api'
import type { PipelineStatus, WSEvent } from '@/lib/types'

interface SessionContextValue {
  sessionId: string | null
  status: PipelineStatus | null
  isConnected: boolean
  wsEvents: WSEvent[]
  refreshStatus: () => Promise<void>
  clearSession: () => void
}

const SessionContext = createContext<SessionContextValue>({
  sessionId: null,
  status: null,
  isConnected: false,
  wsEvents: [],
  refreshStatus: async () => {},
  clearSession: () => {},
})

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [wsEvents, setWsEvents] = useState<WSEvent[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Initialize session on mount
  useEffect(() => {
    const stored = typeof window !== 'undefined'
      ? localStorage.getItem('career_copilot_session')
      : null

    if (stored) {
      setSessionId(stored)
    } else {
      createSession().then(({ session_id }) => {
        setSessionId(session_id)
        localStorage.setItem('career_copilot_session', session_id)
      })
    }
  }, [])

  // Connect WebSocket when session available
  useEffect(() => {
    if (!sessionId) return

    // Initial status fetch
    refreshStatus()

    // WebSocket connection
    const ws = createWebSocket(
      sessionId,
      (event) => {
        try {
          const data: WSEvent = JSON.parse(event.data)
          setWsEvents((prev) => [...prev.slice(-49), data])

          // Refresh status on significant events
          if (
            data.type === 'agent_complete' ||
            data.type === 'pipeline_complete' ||
            data.type === 'human_approval_needed' ||
            data.type === 'status_update'
          ) {
            refreshStatus()
          }
        } catch {
          /* ignore parse errors */
        }
      },
      () => {
        setIsConnected(false)
        // Reconnect after 3s
        setTimeout(() => {
          if (sessionId) {
            const newWs = createWebSocket(sessionId, wsRef.current?.onmessage as EventListener)
            wsRef.current = newWs
          }
        }, 3000)
      }
    )

    ws.onopen = () => setIsConnected(true)
    wsRef.current = ws

    // Polling fallback (every 5s — always poll so stale closure doesn't block updates)
    pollRef.current = setInterval(() => {
      refreshStatus()
    }, 5000)

    return () => {
      ws.close()
      if (pollRef.current) clearInterval(pollRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  const refreshStatus = async () => {
    if (!sessionId) return
    try {
      const s = await getStatus(sessionId)
      setStatus(s)
    } catch {
      /* ignore */
    }
  }

  const clearSession = () => {
    localStorage.removeItem('career_copilot_session')
    setSessionId(null)
    setStatus(null)
    setWsEvents([])
    wsRef.current?.close()
    createSession().then(({ session_id }) => {
      setSessionId(session_id)
      localStorage.setItem('career_copilot_session', session_id)
    })
  }

  return (
    <SessionContext.Provider
      value={{ sessionId, status, isConnected, wsEvents, refreshStatus, clearSession }}
    >
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  return useContext(SessionContext)
}

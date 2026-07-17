'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useSession } from './SessionContext'
import {
  Upload,
  Briefcase,
  Zap,
  ClipboardCheck,
  Brain,
  Mic2,
  BarChart3,
  Wifi,
  WifiOff,
  RefreshCw,
} from 'lucide-react'

const navItems = [
  { href: '/upload', label: 'Upload Resume', icon: Upload, step: 1 },
  { href: '/jobs', label: 'Job Matches', icon: Briefcase, step: 2 },
  { href: '/optimize', label: 'ATS Optimize', icon: Zap, step: 3 },
  { href: '/validate', label: 'Validate', icon: ClipboardCheck, step: 4 },
  { href: '/interview', label: 'Interview Prep', icon: Brain, step: 5 },
  { href: '/coach', label: 'Mock Interview', icon: Mic2, step: 6 },
  { href: '/analytics', label: 'Analytics', icon: BarChart3, step: 7 },
]

function AgentActivity({ agent }: { agent: string }) {
  if (!agent || agent === 'idle') return null
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg mx-3 mb-2">
      <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
      <span className="text-xs text-indigo-300 truncate">
        {agent.replace(/_/g, ' ')}
      </span>
    </div>
  )
}

export function Sidebar() {
  const pathname = usePathname()
  const { status, isConnected, clearSession } = useSession()

  const isRunning = status?.status === 'running'
  const currentAgent = status?.current_agent || ''

  // Determine which steps are "done" based on pipeline progress
  const completedAgents = new Set(
    (status?.agent_messages || [])
      .filter((m) => m.level === 'success')
      .map((m) => m.agent)
  )

  const stepStatus = (step: number): 'done' | 'active' | 'pending' => {
    const agentForStep: Record<number, string> = {
      1: 'resume_parser',
      2: 'job_discovery',
      3: 'ats_optimizer',
      4: 'resume_validator',
      5: 'interview_intel',
      6: 'interview_coach',
      7: 'analytics',
    }
    const agent = agentForStep[step]
    if (completedAgents.has(agent)) return 'done'
    if (currentAgent === agent) return 'active'
    return 'pending'
  }

  return (
    <aside className="w-60 flex-shrink-0 bg-[#12121a] border-r border-[#2a2a38] flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-[#2a2a38]">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
            AI
          </div>
          <div>
            <div className="text-sm font-semibold text-[#f0f0f8]">Career Copilot</div>
            <div className="text-[10px] text-[#9090a8]">Multi-Agent AI Platform</div>
          </div>
        </div>
      </div>

      {/* Connection indicator */}
      <div className="px-4 py-2 border-b border-[#2a2a38]">
        <div className="flex items-center gap-2 text-xs">
          {isConnected ? (
            <>
              <Wifi size={12} className="text-green-400" />
              <span className="text-green-400">Live</span>
            </>
          ) : (
            <>
              <WifiOff size={12} className="text-red-400" />
              <span className="text-red-400">Disconnected</span>
            </>
          )}
          {status?.session_id && (
            <span className="text-[#5a5a70] ml-auto truncate font-mono text-[10px]">
              {status.session_id.slice(0, 8)}
            </span>
          )}
        </div>
      </div>

      {/* Active agent indicator */}
      {isRunning && (
        <div className="pt-2">
          <AgentActivity agent={currentAgent} />
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = pathname === item.href || pathname.startsWith(item.href + '/')
          const stepState = stepStatus(item.step)

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg transition-all duration-150 group',
                active
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'text-[#9090a8] hover:text-[#f0f0f8] hover:bg-[#1e1e28]'
              )}
            >
              <Icon size={17} className={active ? 'text-indigo-400' : 'text-current'} />
              <span className="text-sm flex-1">{item.label}</span>
              {stepState === 'done' && (
                <span className="w-4 h-4 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center text-[10px]">
                  ✓
                </span>
              )}
              {stepState === 'active' && (
                <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Progress summary */}
      {status && status.status !== 'idle' && (
        <div className="px-4 py-3 border-t border-[#2a2a38]">
          <div className="text-[10px] text-[#5a5a70] uppercase tracking-wider mb-2">
            Pipeline
          </div>
          <div className="space-y-1 text-xs text-[#9090a8]">
            <div className="flex justify-between">
              <span>Jobs found</span>
              <span className="text-[#f0f0f8]">{status.jobs_discovered}</span>
            </div>
            <div className="flex justify-between">
              <span>Ready to apply</span>
              <span className="text-green-400">{status.applications_ready}</span>
            </div>
            <div className="flex justify-between">
              <span>Resume versions</span>
              <span className="text-[#f0f0f8]">{status.resume_versions}</span>
            </div>
          </div>
          <div className="mt-3">
            <div className="h-1 bg-[#2a2a38] rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 transition-all duration-500"
                style={{ width: `${status.progress || 0}%` }}
              />
            </div>
            <div className="text-[10px] text-[#5a5a70] mt-1 text-right">
              {status.progress || 0}%
            </div>
          </div>
        </div>
      )}

      {/* Reset */}
      <div className="px-4 py-3 border-t border-[#2a2a38]">
        <button
          onClick={clearSession}
          className="flex items-center gap-2 text-xs text-[#5a5a70] hover:text-[#9090a8] transition-colors"
        >
          <RefreshCw size={12} />
          New Session
        </button>
      </div>
    </aside>
  )
}

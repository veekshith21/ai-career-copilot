'use client'

import { agentDisplayName, agentIcon } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { AgentMessage } from '@/lib/types'

interface AgentLogProps {
  messages: AgentMessage[]
  maxItems?: number
  compact?: boolean
}

const levelStyles: Record<string, string> = {
  info: 'text-[#9090a8] border-[#2a2a38]',
  success: 'text-green-400 border-green-500/20',
  warning: 'text-yellow-400 border-yellow-500/20',
  error: 'text-red-400 border-red-500/20',
}

const levelDot: Record<string, string> = {
  info: 'bg-[#5a5a70]',
  success: 'bg-green-500',
  warning: 'bg-yellow-500',
  error: 'bg-red-500',
}

export function AgentLog({ messages, maxItems = 20, compact = false }: AgentLogProps) {
  const displayed = messages.slice(-maxItems).reverse()

  if (displayed.length === 0) {
    return (
      <div className="text-center py-8 text-[#5a5a70] text-sm">
        No agent activity yet. Start the pipeline to see live updates.
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      {displayed.map((msg, i) => (
        <div
          key={i}
          className={cn(
            'flex items-start gap-2.5 px-3 py-2 rounded-lg border',
            levelStyles[msg.level] || levelStyles.info,
            compact ? 'text-xs' : 'text-sm'
          )}
        >
          <div
            className={cn(
              'w-2 h-2 rounded-full flex-shrink-0 mt-1.5',
              levelDot[msg.level] || levelDot.info
            )}
          />
          <div className="flex-1 min-w-0">
            <span className="font-medium mr-1.5">
              {agentIcon(msg.agent)} {agentDisplayName(msg.agent)}
            </span>
            <span>{msg.message}</span>
          </div>
          <span className="text-[10px] text-[#5a5a70] flex-shrink-0 mt-0.5">
            {new Date(msg.timestamp).toLocaleTimeString()}
          </span>
        </div>
      ))}
    </div>
  )
}

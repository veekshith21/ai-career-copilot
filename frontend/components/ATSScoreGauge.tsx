'use client'

import { cn } from '@/lib/utils'

interface ATSScoreGaugeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  label?: string
  showLabel?: boolean
  className?: string
}

export function ATSScoreGauge({
  score,
  size = 'md',
  label = 'ATS Score',
  showLabel = true,
  className,
}: ATSScoreGaugeProps) {
  const clampedScore = Math.min(100, Math.max(0, score))

  const sizes = {
    sm: { outer: 64, strokeW: 5, textSize: 'text-sm', labelSize: 'text-[10px]' },
    md: { outer: 96, strokeW: 7, textSize: 'text-xl', labelSize: 'text-[11px]' },
    lg: { outer: 128, strokeW: 9, textSize: 'text-3xl', labelSize: 'text-xs' },
  }

  const { outer, strokeW, textSize, labelSize } = sizes[size]
  const radius = (outer - strokeW * 2) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clampedScore / 100) * circumference

  const getColor = (s: number) => {
    if (s >= 85) return { stroke: '#22c55e', text: 'text-green-400', bg: '#22c55e20' }
    if (s >= 70) return { stroke: '#eab308', text: 'text-yellow-400', bg: '#eab30820' }
    if (s >= 50) return { stroke: '#f97316', text: 'text-orange-400', bg: '#f9731620' }
    return { stroke: '#ef4444', text: 'text-red-400', bg: '#ef444420' }
  }

  const colors = getColor(clampedScore)

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <div className="relative" style={{ width: outer, height: outer }}>
        <svg
          width={outer}
          height={outer}
          viewBox={`0 0 ${outer} ${outer}`}
          className="-rotate-90"
        >
          {/* Background ring */}
          <circle
            cx={outer / 2}
            cy={outer / 2}
            r={radius}
            fill="none"
            stroke="#2a2a38"
            strokeWidth={strokeW}
          />
          {/* Score ring */}
          <circle
            cx={outer / 2}
            cy={outer / 2}
            r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth={strokeW}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="score-ring"
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('font-bold leading-none', textSize, colors.text)}>
            {Math.round(clampedScore)}
          </span>
          {showLabel && size !== 'sm' && (
            <span className={cn('text-[#9090a8] mt-0.5', labelSize)}>/ 100</span>
          )}
        </div>
      </div>
      {showLabel && (
        <span className={cn('text-[#9090a8]', labelSize)}>{label}</span>
      )}
    </div>
  )
}

// Mini bar version for compact displays
export function ATSScoreBar({
  score,
  label,
}: {
  score: number
  label: string
}) {
  const getColor = (s: number) => {
    if (s >= 85) return 'bg-green-500'
    if (s >= 70) return 'bg-yellow-500'
    if (s >= 50) return 'bg-orange-500'
    return 'bg-red-500'
  }

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-[#9090a8]">{label}</span>
        <span className="text-[#f0f0f8] font-medium">{Math.round(score)}</span>
      </div>
      <div className="h-1.5 bg-[#2a2a38] rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-700', getColor(score))}
          style={{ width: `${Math.min(100, score)}%` }}
        />
      </div>
    </div>
  )
}

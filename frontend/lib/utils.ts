import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatScore(score: number): string {
  return Math.round(score).toString()
}

export function scoreColor(score: number): string {
  if (score >= 85) return 'text-green-400'
  if (score >= 70) return 'text-yellow-400'
  if (score >= 50) return 'text-orange-400'
  return 'text-red-400'
}

export function scoreBg(score: number): string {
  if (score >= 85) return 'bg-green-500'
  if (score >= 70) return 'bg-yellow-500'
  if (score >= 50) return 'bg-orange-500'
  return 'bg-red-500'
}

export function scoreLabel(score: number): string {
  if (score >= 85) return 'Excellent'
  if (score >= 70) return 'Good'
  if (score >= 50) return 'Fair'
  return 'Poor'
}

export function decisionColor(decision: string): string {
  switch (decision) {
    case 'apply':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 'improve':
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    case 'skip':
      return 'bg-red-500/20 text-red-400 border-red-500/30'
    default:
      return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }
}

export function decisionLabel(decision: string): string {
  switch (decision) {
    case 'apply':
      return '✓ Ready to Apply'
    case 'improve':
      return '⚠ Needs Improvement'
    case 'skip':
      return '✕ Skip'
    default:
      return decision
  }
}

export function formatSalary(min: number | null, max: number | null, currency = 'USD'): string {
  if (!min && !max) return 'Not specified'
  const fmt = (n: number) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(n)
  if (min && max) return `${fmt(min)} – ${fmt(max)}`
  if (min) return `From ${fmt(min)}`
  return `Up to ${fmt(max!)}`
}

export function timeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = (now.getTime() - date.getTime()) / 1000

  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
  return date.toLocaleDateString()
}

export function difficultyColor(difficulty: string): string {
  switch (difficulty) {
    case 'easy':
      return 'text-green-400 bg-green-500/10'
    case 'medium':
      return 'text-yellow-400 bg-yellow-500/10'
    case 'hard':
      return 'text-red-400 bg-red-500/10'
    default:
      return 'text-gray-400 bg-gray-500/10'
  }
}

export function agentDisplayName(agent: string): string {
  const map: Record<string, string> = {
    resume_parser: 'Resume Parser',
    job_discovery: 'Job Discovery',
    ats_optimizer: 'ATS Optimizer',
    resume_validator: 'Resume Validator',
    application_readiness: 'Application Readiness',
    human_approval: 'Human Approval',
    interview_intel: 'Interview Intelligence',
    interview_coach: 'Interview Coach',
  }
  return map[agent] || agent
}

export function agentIcon(agent: string): string {
  const map: Record<string, string> = {
    resume_parser: '📄',
    job_discovery: '🔍',
    ats_optimizer: '⚡',
    resume_validator: '✅',
    application_readiness: '📊',
    human_approval: '👤',
    interview_intel: '🧠',
    interview_coach: '🎤',
  }
  return map[agent] || '🤖'
}

// ─── Candidate Profile ─────────────────────────────────────────────────────

export interface EducationItem {
  institution: string
  degree: string
  field_of_study: string
  graduation_year: number | null
  gpa: number | null
}

export interface ExperienceItem {
  company: string
  title: string
  start_date: string
  end_date: string | null
  is_current: boolean
  responsibilities: string[]
  achievements: string[]
  technologies: string[]
}

export interface ProjectItem {
  name: string
  description: string
  technologies: string[]
  url: string | null
}

export interface CandidateProfile {
  full_name: string
  email: string
  phone: string
  location: string
  linkedin_url: string
  github_url: string
  portfolio_url: string
  summary: string
  technical_skills: string[]
  soft_skills: string[]
  languages: string[]
  certifications: string[]
  education: EducationItem[]
  experience: ExperienceItem[]
  projects: ProjectItem[]
  total_years_experience: number
  seniority_level: string
  target_roles: string[]
  industries: string[]
}

// ─── Job Listings ──────────────────────────────────────────────────────────

export interface JobListing {
  job_id: string
  title: string
  company: string
  location: string
  employment_type: string
  experience_level: string
  description: string
  requirements: string[]
  preferred_qualifications: string[]
  technical_skills_required: string[]
  salary_min: number | null
  salary_max: number | null
  salary_currency: string
  remote_friendly: boolean
  posted_date: string
  application_url: string
  source: string
  match_score: number
}

// ─── ATS ───────────────────────────────────────────────────────────────────

export interface ATSBreakdown {
  total_score: number
  keyword_score: number
  skills_coverage_score: number
  experience_alignment_score: number
  education_match_score: number
  formatting_score: number
  matched_keywords: string[]
  missing_keywords: string[]
  matched_skills: string[]
  missing_skills: string[]
  experience_years_required: number | null
  experience_years_candidate: number
  recommendations: string[]
}

export interface OptimizedResume {
  job_id: string
  original_score: number
  optimized_score: number
  optimized_summary: string
  optimized_bullets: Record<string, string[]>
  added_keywords: string[]
  cover_letter: string
  optimization_notes: string[]
}

export interface ValidationResult {
  job_id: string
  passed: boolean
  recalculated_score: number
  keyword_coverage: number
  formatting_issues: string[]
  missing_skills: string[]
  recommendations: string[]
  llm_validation_score: number | null
}

// ─── Application ──────────────────────────────────────────────────────────

export type ApplicationDecision = 'apply' | 'improve' | 'skip'

export interface ApplicationStatus {
  job_id: string
  decision: ApplicationDecision
  ats_score: number
  reasoning: string
  common_app_answers: Record<string, string>
  outreach_message: string
  outreach_subject: string
}

// ─── Interview ────────────────────────────────────────────────────────────

export interface InterviewQuestion {
  question: string
  category: string
  difficulty: 'easy' | 'medium' | 'hard'
  model_answer: string
  star_framework: string | null
  follow_up_questions: string[]
}

export interface InterviewPrep {
  job_id: string
  company: string
  role: string
  top_questions: InterviewQuestion[]
  company_research: string
  salary_negotiation_tips: string
  questions_to_ask: string[]
}

export interface MockInterviewTurn {
  turn_number: number
  question: string
  answer: string
  evaluation: {
    feedback: string
    scores: {
      clarity: number
      technical_depth: number
      communication: number
    }
    improvement_tips: string[]
    next_question: string | null
  } | null
  timestamp: string
}

export interface MockInterviewSession {
  job_id: string
  turns: MockInterviewTurn[]
  current_question_idx: number
  scores: {
    clarity: number
    technical_depth: number
    communication: number
    confidence: number
  }
  overall_score: number
  feedback_summary: string
  completed: boolean
}

// ─── Agent Messages & Session State ──────────────────────────────────────

export interface AgentMessage {
  agent: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface PipelineStatus {
  session_id: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed'
  current_agent: string
  progress: number
  candidate_profile: CandidateProfile | null
  discovered_jobs: JobListing[]
  filtered_jobs: JobListing[]
  ats_scores: Record<string, ATSBreakdown>
  optimized_resumes: Record<string, OptimizedResume>
  validation_results: Record<string, ValidationResult>
  application_statuses: Record<string, ApplicationStatus>
  interview_preps: Record<string, InterviewPrep>
  mock_sessions: Record<string, MockInterviewSession>
  agent_messages: AgentMessage[]
  pending_approval: boolean
  approved_job_ids: string[]
  jobs_discovered: number
  applications_ready: number
  interviews_completed: number
  resume_versions: number
  error: string | null
}

// ─── Analytics ────────────────────────────────────────────────────────────

export interface Analytics {
  jobs_discovered: number
  jobs_matched: number
  avg_ats_score: number
  avg_match_score: number
  applications_ready: number
  interviews_prepared: number
  resume_versions: number
  score_distribution: Record<string, number>
  top_missing_keywords: string[]
}

// ─── WebSocket Events ─────────────────────────────────────────────────────

export type WSEventType =
  | 'agent_start'
  | 'agent_complete'
  | 'agent_error'
  | 'pipeline_complete'
  | 'human_approval_needed'
  | 'status_update'
  | 'interview_update'

export interface WSEvent {
  type: WSEventType
  agent?: string
  message?: string
  data?: unknown
  timestamp: string
}

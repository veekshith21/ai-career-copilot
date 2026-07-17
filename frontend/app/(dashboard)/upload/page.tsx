'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { useSession } from '@/components/SessionContext'
import { AgentLog } from '@/components/AgentLog'
import { uploadResume, startPipeline } from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  Upload,
  FileText,
  MapPin,
  Search,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react'

export default function UploadPage() {
  const router = useRouter()
  const { sessionId, status, refreshStatus } = useSession()

  const [file, setFile] = useState<File | null>(null)
  const [jobQuery, setJobQuery] = useState('')
  const [location, setLocation] = useState('')
  const [uploading, setUploading] = useState(false)
  const [starting, setStarting] = useState(false)
  const [uploaded, setUploaded] = useState(false)

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) {
      setFile(accepted[0])
      setUploaded(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  })

  const handleUpload = async () => {
    if (!file || !sessionId) return
    setUploading(true)
    try {
      await uploadResume(sessionId, file)
      setUploaded(true)
      toast.success('Resume uploaded and parsed successfully!')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleStart = async () => {
    if (!sessionId || !uploaded) return
    if (!jobQuery.trim()) {
      toast.error('Please enter a job title or keywords')
      return
    }
    setStarting(true)
    try {
      await startPipeline(sessionId, jobQuery, location)
      toast.success('Pipeline started! Discovering jobs...')
      await refreshStatus()
      router.push('/jobs')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to start pipeline')
    } finally {
      setStarting(false)
    }
  }

  const profile = status?.candidate_profile
  const isRunning = status?.status === 'running'

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[#f0f0f8]">Upload Your Resume</h1>
        <p className="text-[#9090a8] mt-1">
          AI agents will parse, optimize, and match your resume to jobs automatically.
        </p>
      </div>

      <div className="space-y-6">
        {/* Drop zone */}
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all',
            isDragActive
              ? 'border-indigo-500 bg-indigo-500/10'
              : file
              ? 'border-green-500/40 bg-green-500/5'
              : 'border-[#2a2a38] hover:border-indigo-500/50 hover:bg-[#1a1a24]'
          )}
        >
          <input {...getInputProps()} />
          {file ? (
            <div className="flex flex-col items-center gap-3">
              <FileText size={40} className="text-green-400" />
              <div>
                <div className="font-medium text-[#f0f0f8]">{file.name}</div>
                <div className="text-sm text-[#9090a8] mt-0.5">
                  {(file.size / 1024).toFixed(0)} KB · Click to replace
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <Upload size={40} className={isDragActive ? 'text-indigo-400' : 'text-[#5a5a70]'} />
              <div>
                <div className="font-medium text-[#f0f0f8]">
                  {isDragActive ? 'Drop your resume here' : 'Drag & drop your resume'}
                </div>
                <div className="text-sm text-[#9090a8] mt-0.5">
                  PDF, DOCX, or TXT · Max 10 MB
                </div>
              </div>
              <button className="btn-secondary text-sm mt-2">Browse files</button>
            </div>
          )}
        </div>

        {/* Upload button */}
        {file && !uploaded && (
          <button
            className="btn-primary w-full flex items-center justify-center gap-2"
            onClick={handleUpload}
            disabled={uploading}
          >
            {uploading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Parsing resume...
              </>
            ) : (
              <>
                <Upload size={16} />
                Upload & Parse Resume
              </>
            )}
          </button>
        )}

        {/* Parsed profile preview */}
        {profile && (
          <div className="card p-4 animate-fade-in">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 size={16} className="text-green-400" />
              <span className="text-sm font-medium text-green-400">Resume Parsed Successfully</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="label">Name</div>
                <div className="text-[#f0f0f8]">{profile.full_name || 'N/A'}</div>
              </div>
              <div>
                <div className="label">Experience</div>
                <div className="text-[#f0f0f8]">{profile.total_years_experience} years · {profile.seniority_level}</div>
              </div>
              <div>
                <div className="label">Top Skills</div>
                <div className="text-[#f0f0f8]">{profile.technical_skills.slice(0, 5).join(', ')}</div>
              </div>
              <div>
                <div className="label">Target Roles</div>
                <div className="text-[#f0f0f8]">{(profile.target_roles || []).slice(0, 3).join(', ') || 'Auto-detected'}</div>
              </div>
            </div>
          </div>
        )}

        {/* Job search config */}
        {uploaded && (
          <div className="card p-5 animate-slide-up space-y-4">
            <h2 className="font-semibold text-[#f0f0f8]">Configure Job Search</h2>
            <div className="space-y-3">
              <div>
                <label className="label mb-1.5 block">Job Title / Keywords *</label>
                <div className="relative">
                  <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5a5a70]" />
                  <input
                    className="input pl-9"
                    placeholder="e.g. Senior Software Engineer, ML Engineer, Product Manager"
                    value={jobQuery}
                    onChange={(e) => setJobQuery(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="label mb-1.5 block">Location (optional)</label>
                <div className="relative">
                  <MapPin size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5a5a70]" />
                  <input
                    className="input pl-9"
                    placeholder="e.g. San Francisco, CA or Remote"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <button
              className="btn-primary w-full flex items-center justify-center gap-2"
              onClick={handleStart}
              disabled={starting || isRunning}
            >
              {starting || isRunning ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Running AI Pipeline...
                </>
              ) : (
                <>
                  <Search size={16} />
                  Start AI Career Analysis
                </>
              )}
            </button>

            {isRunning && (
              <div className="flex items-center gap-2 text-xs text-indigo-400">
                <AlertCircle size={12} />
                Pipeline is running. You can navigate to other pages to see live results.
              </div>
            )}
          </div>
        )}

        {/* Agent log */}
        {status?.agent_messages && status.agent_messages.length > 0 && (
          <div className="card p-4">
            <h3 className="section-title">Agent Activity</h3>
            <AgentLog messages={status.agent_messages} compact />
          </div>
        )}
      </div>
    </div>
  )
}

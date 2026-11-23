export type VideoStatus =
  | 'uploaded'
  | 'transcribing'
  | 'finding_moments'
  | 'ready'
  | 'error'

export type JobStatus = 'pending' | 'running' | 'done' | 'error'

export interface Video {
  id: number
  filename: string
  path: string
  status: VideoStatus
  progress: number
  duration?: number | null
  width?: number | null
  height?: number | null
  fps?: number | null
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface Moment {
  id: number
  video_id: number
  start: number
  end: number
  title: string
  reason: string
  score: number
  rendered: boolean
  created_at: string
}

export interface Job {
  id: number
  video_id: number
  status: JobStatus
  stage: string
  progress: number
  error_message?: string | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
}

export interface Word {
  text: string
  start: number
  end: number
  prob: number
}

export interface Transcript {
  language: string
  words: Word[]
  segments: Array<{
    id: number
    start: number
    end: number
    text: string
    words: Word[]
  }>
}

export interface RenderOptions {
  captions_style?: 'clasico' | 'resaltado' | 'minimal' | null
  framing_mode?: 'single' | 'auto' | 'split' | null
  remove_silence?: boolean | null
}

export interface EditorState {
  playhead: number
  selection: { start: number; end: number } | null
  style: 'clasico' | 'resaltado' | 'minimal'
  reframeMode: 'single' | 'auto' | 'split'
  removeSilence: boolean
}

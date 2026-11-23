import * as React from 'react'
import { formatTime } from '../../lib/format'
import { Chip } from '../../components/ui/Chip'
import { PipelineStages } from './PipelineStages'
import type { ChipProps } from '../../components/ui/Chip'

export interface VideoCardProps {
  video: import('../../lib/types').Video
  onSelect: (id: number) => void
}

export function VideoCard({ video, onSelect }: VideoCardProps) {
  const STATUS_CONFIG: Record<string, { label: string; variant: ChipProps['variant'] }> = {
    uploaded: { label: 'Subido', variant: 'default' },
    transcribing: { label: 'Transcribiendo', variant: 'plasma' },
    finding_moments: { label: 'Buscando momentos', variant: 'plasma' },
    ready: { label: 'Listo', variant: 'ok' },
    error: { label: 'Error', variant: 'flare' },
  }

  const status = STATUS_CONFIG[video.status] || STATUS_CONFIG.uploaded
  const duration = video.duration !== undefined && video.duration !== null

  return (
    <article
      className="surface p-3 md:p-4 rounded-panel border border-line cursor-pointer group transition-all duration-200 hover:border-plasma/50 hover:shadow-md"
      onClick={() => onSelect(video.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onSelect(video.id) }}
    >
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-2 md:gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-sora font-semibold text-sm md:text-base text-ink line-clamp-1 leading-tight">
            {video.filename}
          </h3>
          {duration && (
            <div className="flex items-center gap-1.5 text-xs text-ink-muted mt-1">
              <span className="font-mono">{formatTime(video.duration)}</span>
              {video.width && video.height && (
                <>
                  <span>·</span>
                  <span>{video.width}×{video.height}</span>
                </>
              )}
            </div>
          )}
        </div>
        <Chip variant={status.variant} size="sm">{status.label}</Chip>
      </div>

      <PipelineStages
        stages={{
          ingest: video.status === 'uploaded' ? { status: 'done', progress: 100 } : { status: 'pending', progress: 0 },
          transcribe: video.status === 'transcribing' ? { status: 'running', progress: video.progress } : video.status === 'ready' ? { status: 'done', progress: 100 } : { status: 'pending', progress: 0 },
          moments: video.status === 'finding_moments' ? { status: 'running', progress: video.progress } : video.status === 'ready' ? { status: 'done', progress: 100 } : { status: 'pending', progress: 0 },
          render: video.status === 'ready' ? { status: 'done', progress: 100 } : { status: 'pending', progress: 0 },
        }}
      />

      {video.error_message && (
        <div className="mt-3 flex items-center gap-1.5 text-[10px] md:text-xs text-flare">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="line-clamp-1">{video.error_message}</span>
        </div>
      )}
    </article>
  )
}

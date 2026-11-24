import * as React from 'react'
import { StageTracker } from './StageTracker'
import { deriveStages, type VideoLike } from './stages'

export interface PipelineStagesProps {
  stages: Partial<Record<'ingest' | 'transcribe' | 'moments' | 'render', { status: 'pending' | 'running' | 'done' | 'error'; progress?: number; error?: string }}>
  onRetry?: (stage: string) => void
}

export function PipelineStages({ stages, onRetry }: PipelineStagesProps) {
  const stageOrder = ['ingest', 'transcribe', 'moments', 'render'] as const
  const stageLabels: Record<string, string> = {
    ingest: 'Subida',
    transcribe: 'Transcripción',
    moments: 'Momentos',
    render: 'Listo',
  }
  const stageDetails: Record<string, string> = {
    ingest: 'Subiendo el archivo',
    transcribe: 'Transcribiendo audio con Whisper',
    moments: 'Buscando los mejores momentos con IA',
    render: 'Exportando clips finales',
  }

  const videoLike = {
    status: 'transcribing',
    progress: 0,
    ...stages,
  } as any

  const trackerStages = deriveStages(videoLike)

  return (
    <section className="surface p-3 md:p-4 rounded-panel border border-line">
      <h3 className="font-sans font-semibold text-xs md:text-sm mb-3 md:mb-4 flex items-center gap-2 text-texto-muted uppercase tracking-tight">
        <span className="w-px h-3 bg-accent rounded-full"></span>
        Procesamiento
      </h3>
      <StageTracker stages={trackerStages} />
    </section>
  )
}

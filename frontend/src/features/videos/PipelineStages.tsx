import * as React from 'react'
import { Mic, Search, ClipboardList, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import { Chip } from '../../components/ui/Chip'

type Stage = 'ingest' | 'transcribe' | 'moments' | 'render'

interface StageStatus {
  status: 'pending' | 'running' | 'done' | 'error'
  progress?: number
  error?: string
}

const STAGE_LABELS: Record<Stage, string> = {
  ingest: 'Subida',
  transcribe: 'Transcripción',
  moments: 'Búsqueda de momentos',
  render: 'Listo',
}

const STAGE_ICONS: Record<Stage, React.ElementType> = {
  ingest: Mic,
  transcribe: Search,
  moments: ClipboardList,
  render: CheckCircle2,
}

const STAGE_KEYS: Stage[] = ['ingest', 'transcribe', 'moments', 'render']

export interface PipelineStagesProps {
  stages: Partial<Record<Stage, StageStatus>>
  onRetry?: (stage: Stage) => void
}

export function PipelineStages({ stages, onRetry }: PipelineStagesProps) {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768

  return (
    <section className="surface p-4 md:p-6 rounded-panel border border-line">
      <h3 className="font-sora font-semibold text-sm mb-4 flex items-center gap-2 text-ink-muted uppercase tracking-wider">
        <span className="w-px h-3 bg-plasma rounded-full"></span>
        Procesamiento
      </h3>
      <div
        className={[
          'flex flex-col md:flex-row gap-3',
          isMobile ? 'flex-col' : 'flex-row',
        ].join(' ')}
      >
        {STAGE_KEYS.map((key) => {
          const stage = stages[key]
          const isDone = stage?.status === 'done'
          const isRunning = stage?.status === 'running'
          const isError = stage?.status === 'error'
          const Icon = STAGE_ICONS[key]

          return (
            <div
              key={key}
              className={[
                'flex-1 flex flex-col items-center gap-2 p-3 rounded-panel border',
                isDone ? 'border-ok bg-ok/5' : '',
                isRunning ? 'border-ion bg-ion/5' : '',
                isError ? 'border-flare bg-flare/5' : '',
                'transition-all duration-200',
              ].join(' ')}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isDone ? 'bg-ok text-void' : isRunning ? 'bg-ion text-void' : isError ? 'bg-flare text-void' : 'bg-panel-2 text-ink-muted border border-line'}`}>
                {isDone || isRunning || isError ? (
                  <Icon size={16} strokeWidth={2.5} />
                ) : (
                  <div className="w-3 h-3 rounded-full bg-line" />
                )}
              </div>
              <span className="text-[11px] font-medium text-center leading-tight">{STAGE_LABELS[key]}</span>
              {stage?.progress !== undefined && (
                <div className="w-full h-1 bg-panel-2 rounded-full overflow-hidden mt-1">
                  <div
                    className={`h-full ${isDone ? 'bg-ok' : isRunning ? 'bg-ion' : 'bg-line'}`}
                    style={{ width: `${stage.progress}%` }}
                  />
                </div>
              )}
              {isError && (
                <div className="mt-1 flex items-center gap-1 text-[10px] text-flare">
                  <AlertCircle size={12} strokeWidth={2} />
                  <span>{stage.error}</span>
                </div>
              )}
              {isError && onRetry && (
                <button
                  onClick={() => onRetry(key)}
                  className="mt-2 text-[10px] text-plasma underline underline-offset-2 hover:text-plasma-soft"
                  aria-label={`Reintentar ${STAGE_LABELS[key]}`}
                >
                  Reintentar
                </button>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}

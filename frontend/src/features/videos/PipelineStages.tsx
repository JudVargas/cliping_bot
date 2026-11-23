import * as React from 'react'
import { Mic, Search, ClipboardList, CheckCircle2, AlertCircle } from 'lucide-react'
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
  moments: 'Momentos',
  render: 'Listo',
}

const STAGE_DESCRIPTIONS: Record<Stage, string> = {
  ingest: 'Subiendo el archivo',
  transcribe: 'Transcribiendo audio con Whisper',
  moments: 'Buscando los mejores momentos con IA',
  render: 'Exportando clips finales',
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
  return (
    <section className="surface p-3 md:p-4 rounded-panel border border-line overflow-hidden">
      <h3 className="font-sora font-semibold text-xs md:text-sm mb-3 md:mb-4 flex items-center gap-2 text-ink-muted uppercase tracking-wider">
        <span className="w-px h-3 bg-plasma rounded-full"></span>
        Procesamiento
      </h3>
      <div className="flex flex-col sm:flex-row gap-2 md:gap-3 overflow-hidden">
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
                'flex-1 flex flex-col items-center gap-1.5 p-2 md:p-3 rounded-panel border',
                isDone ? 'border-ok bg-ok/5' : '',
                isRunning ? 'border-ion bg-ion/5' : '',
                isError ? 'border-flare bg-flare/5' : '',
                'transition-all duration-200 max-w-fit',
              ].join(' ')}
            >
              <div className={`w-7 h-7 md:w-8 md:h-8 rounded-full flex items-center justify-center shrink-0 ${isDone ? 'bg-ok text-void' : isRunning ? 'bg-ion text-void' : isError ? 'bg-flare text-void' : 'bg-panel-2 text-ink-muted border border-line'}`}>
                {isDone || isRunning || isError ? (
                  <Icon size={12} strokeWidth={2} />
                ) : (
                  <div className="w-2.5 h-2.5 rounded-full bg-line" />
                )}
              </div>
              <span className="text-[10px] md:text-[11px] font-medium text-center leading-tight shrink-0">
                {STAGE_LABELS[key]}
              </span>
              <span className="text-[9px] md:text-[10px] text-ink-muted text-center leading-none shrink-0 max-w-[120px]">
                {STAGE_DESCRIPTIONS[key]}
              </span>
              {stage?.progress !== undefined && (
                <div className="w-full h-[3px] md:h-1 bg-panel-2 rounded-full overflow-hidden mt-1 shrink-0">
                  <div
                    className={`h-full ${isDone ? 'bg-ok' : isRunning ? 'bg-ion' : 'bg-line'}`}
                    style={{ width: `${stage.progress}%` }}
                  />
                </div>
              )}
              {isError && (
                <div className="mt-1.5 flex items-center gap-1 text-[9px] md:text-[10px] text-flare shrink-0 max-w-fit">
                  <AlertCircle size={10} strokeWidth={2} />
                  <span className="line-clamp-1">{stage.error}</span>
                </div>
              )}
              {isError && onRetry && (
                <button
                  onClick={() => onRetry(key)}
                  className="mt-1 text-[9px] md:text-xs text-plasma underline underline-offset-2 hover:text-plasma-soft px-2 py-1 shrink-0 max-w-fit"
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

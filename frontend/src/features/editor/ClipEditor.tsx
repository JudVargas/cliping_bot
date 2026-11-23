import * as React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMoment, useRenderMoment } from '../../lib/hooks'
import { ClipFrame } from './ClipFrame'
import { Waveform } from './Waveform'
import { TranscriptPicker } from './TranscriptPicker'
import { StylePanel } from './StylePanel'
import { TrimControls } from './TrimControls'
import { ExportBar } from './ExportBar'
import { Skeleton } from '../../components/ui/Skeleton'
import { Button } from '../../components/ui/Button'

export function EditorPage() {
  const { momentId } = useParams()
  const { data: moment, isLoading } = useMoment(Number(momentId))
  const renderMutation = useRenderMoment()
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="p-4 flex flex-col items-center justify-center h-full">
        <div className="flex flex-col gap-4">
          <Skeleton width="60%" height="8" radius="4px" />
          <Skeleton width="80%" height="16" radius="4px" className="mt-4" />
          <Skeleton width="100%" height="200" radius="16px" />
        </div>
      </div>
    )
  }

  if (!moment) {
    return <div className="p-4 text-center py-20">Momento no encontrado</div>
  }

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto h-[dvh] flex flex-col">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="font-sora font-semibold text-xl text-ink">Editor de clip</h1>
          <p className="text-ink-muted text-sm">{moment.title}</p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => navigate(-1)}
          leftIcon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>}
        >
          Volver
        </Button>
      </header>

      <div className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
        {/* Panel izquierdo: Transcripción */}
        <div className="lg:w-1/4 flex flex-col gap-4 min-w-0">
          <TranscriptPicker
            moment={moment}
            onSelectRange={(start, end) => {
              // Se conectará con el Zustand del editor
            }}
          />
        </div>

        {/* Panel central: Vista previa + forma de onda + controles */}
        <div className="flex-1 flex flex-col gap-4 min-w-0">
          <ClipFrame moment={moment} isBusy={renderMutation.isPending} />
          <Waveform moment={moment} />
          <TrimControls moment={moment} />
        </div>

        {/* Panel derecho: Estilos y exportación */}
        <div className="lg:w-1/4 flex flex-col gap-4 min-w-0">
          <StylePanel moment={moment} />
          <ExportBar
            moment={moment}
            isRendering={renderMutation.isPending}
            onExport={() => {
              renderMutation.mutate({
                id: moment.id,
                options: {
                  captions_style: 'clasico',
                  framing_mode: 'single',
                  remove_silence: false,
                },
              })
            }}
          />
        </div>
      </div>

      {renderMutation.isSuccess && (
        <div className="mt-4 p-3 bg-ok/10 border border-ok/20 rounded-field text-ok text-sm flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>Clip exportado correctamente</span>
          <a
            href={renderMutation.data?.download_url ?? ''}
            download
            className="ml-auto text-plasma underline underline-offset-2 hover:text-plasma-soft text-sm font-medium"
          >
            Descargar
          </a>
        </div>
      )}
    </div>
  )
}

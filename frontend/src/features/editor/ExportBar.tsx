import * as React from 'react'
import { Download, Play, Loader2 } from 'lucide-react'
import { Button } from '../../components/ui/Button'

export interface ExportBarProps {
  moment: import('../../lib/types').Moment
  isRendering: boolean
  onExport: () => void
}

export function ExportBar({ moment, isRendering, onExport }: ExportBarProps) {
  return (
    <div className="surface-glass p-3 rounded-panel border border-line backdrop-blur-sm sticky top-4 z-10">
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between text-xs text-ink-muted font-mono">
          <span>{moment.start.toFixed(2)}s – {moment.end.toFixed(2)}s</span>
          <span>{(moment.end - moment.start).toFixed(1)}s</span>
        </div>
        <Button
          variant="primary"
          size="lg"
          onClick={onExport}
          isLoading={isRendering}
          disabled={isRendering}
          leftIcon={isRendering ? <Loader2 size={18} strokeWidth={2} className="animate-spin" /> : <Play size={18} strokeWidth={2} />}
          className="w-full"
        >
          {isRendering ? 'Exportando…' : 'Exportar clip'}
        </Button>
        {!isRendering && (
          <button
            onClick={() => {
              const url = `/api/clips/${moment.id}/download`
              const a = document.createElement('a')
              a.href = url
              a.download = `clip_${moment.id}.mp4`
              a.click()
            }}
            className="w-full text-xs text-plasma underline underline-offset-4 hover:text-plasma-soft flex items-center justify-center gap-1"
          >
            <Download size={16} strokeWidth={2} /> Descargar ahora
          </button>
        )}
      </div>
    </div>
  )
}

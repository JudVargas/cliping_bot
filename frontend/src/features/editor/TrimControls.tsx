import * as React from 'react'
import { ArrowLeft, ArrowRight, RotateCcw, RotateCw } from 'lucide-react'
import { Button } from '../../components/ui/Button'

export interface TrimControlsProps {
  moment: import('../../lib/types').Moment
}

export function TrimControls({ moment }: TrimControlsProps) {
  const [start, setStart] = React.useState(moment.start)
  const [end, setEnd] = React.useState(moment.end)

  const adjustStart = (delta: number) => {
    setStart((s) => Math.max(0, s + delta))
  }
  const adjustEnd = (delta: number) => {
    setEnd((e) => e + delta)
  }

  return (
    <div className="surface p-3 rounded-panel border border-line flex flex-col gap-3">
      <div className="flex items-center justify-between text-xs text-ink-muted">
        <span>Recorte</span>
        <span className="font-mono">{start.toFixed(2)}s – {end.toFixed(2)}s ({(end - start).toFixed(1)}s)</span>
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        <Button variant="secondary" size="sm" onClick={() => adjustStart(-0.1)} leftIcon={<ArrowLeft size={14} strokeWidth={2} />}>
          Inicio −0.1s
        </Button>
        <Button variant="secondary" size="sm" onClick={() => adjustStart(0.1)} leftIcon={<ArrowRight size={14} strokeWidth={2} />}>
          Inicio +0.1s
        </Button>
        <Button variant="secondary" size="sm" onClick={() => adjustEnd(-0.1)} leftIcon={<ArrowLeft size={14} strokeWidth={2} />}>
          Fin −0.1s
        </Button>
        <Button variant="secondary" size="sm" onClick={() => adjustEnd(0.1)} leftIcon={<ArrowRight size={14} strokeWidth={2} />}>
          Fin +0.1s
        </Button>
      </div>

      <div className="flex gap-1.5 pt-1 border-t border-line/50">
        <Button variant="ghost" size="sm" onClick={() => { setStart(moment.start); setEnd(moment.end) }} leftIcon={<RotateCcw size={14} strokeWidth={2} />}>
          Restablecer
        </Button>
      </div>

      <div className="pt-1 border-t border-line/50">
        <p className="text-[10px] text-ink-muted">
          Atajos: ← → mueven el cabezal · [ y ] fijan inicio y fin
        </p>
      </div>
    </div>
  )
}

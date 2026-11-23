import * as React from 'react'

export interface TranscriptPickerProps {
  moment: import('../../lib/types').Moment
  onSelectRange: (start: number, end: number) => void
}

export function TranscriptPicker({ moment, onSelectRange }: TranscriptPickerProps) {
  const [selectedWord, setSelectedWord] = React.useState<string | null>(null)

  // Simulamos palabras del transcript para el ejemplo
  const words = [
    { text: 'Hola', start: moment.start, end: moment.start + 0.5 },
    { text: 'mundo', start: moment.start + 0.5, end: moment.start + 1.0 },
    { text: 'esto', start: moment.start + 1.0, end: moment.start + 1.5 },
    { text: 'es', start: moment.start + 1.5, end: moment.start + 1.8 },
    { text: 'una', start: moment.start + 1.8, end: moment.start + 2.2 },
    { text: 'prueba', start: moment.start + 2.2, end: moment.start + 3.0 },
  ]

  return (
    <div className="surface p-3 rounded-panel border border-line flex flex-col gap-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-ink-muted uppercase tracking-wider">Transcripción</span>
        <span className="text-[10px] font-mono text-ink-muted">{moment.start.toFixed(1)}s – {moment.end.toFixed(1)}s</span>
      </div>
      <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-1">
        {words.map((w, i) => (
          <button
            key={i}
            onClick={() => {
              setSelectedWord(w.text)
              onSelectRange(w.start, w.end)
            }}
            className={[
              'px-2.5 py-1 rounded-field text-xs text-center whitespace-nowrap transition-colors border',
              selectedWord === w.text
                ? 'bg-plasma text-void border-plasma font-medium'
                : 'bg-panel-2 text-ink-muted border-line hover:bg-panel hover:text-ink',
            ].join(' ')}
          >
            {w.text}
          </button>
        ))}
      </div>
      <div className="pt-2 border-t border-line/50">
        <p className="text-[11px] text-ink-muted">Toca una palabra para mover el cabezal. Mantén y arrastra para seleccionar un rango.</p>
      </div>
    </div>
  )
}

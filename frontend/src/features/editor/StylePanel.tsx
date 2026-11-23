import * as React from 'react'

export interface StylePanelProps {
  moment: import('../../lib/types').Moment
}

const STYLES: Array<{ id: 'clasico' | 'resaltado' | 'minimal'; name: string; preview: string }> = [
  { id: 'clasico', name: 'Clásico', preview: 'Blanco con borde negro' },
  { id: 'resaltado', name: 'Resaltado', preview: 'Amarillo fuerte, más grande' },
  { id: 'minimal', name: 'Minimal', preview: 'Gris claro, discreto' },
]

export function StylePanel({ moment }: StylePanelProps) {
  const [style, setStyle] = React.useState<'clasico' | 'resaltado' | 'minimal'>('clasico')
  const [framingMode, setFramingMode] = React.useState<'single' | 'auto' | 'split'>('auto')
  const [removeSilence, setRemoveSilence] = React.useState(false)

  return (
    <div className="surface p-3 rounded-panel border border-line flex flex-col gap-3">
      <h3 className="text-xs font-semibold text-ink-muted uppercase tracking-wider">Estilo de subtítulos</h3>
      <div className="grid grid-cols-3 gap-1.5">
        {STYLES.map((s) => (
          <button
            key={s.id}
            onClick={() => setStyle(s.id)}
            className={[
              'p-2 rounded-field border flex flex-col items-center gap-1 transition-colors',
              style === s.id
                ? 'bg-plasma/10 border-plasma text-plasma'
                : 'bg-panel-2 border-line text-ink-muted hover:border-line/50',
            ].join(' ')}
          >
            <span className="text-[10px] font-medium">{s.name}</span>
            <span className="text-[10px]">{s.preview}</span>
          </button>
        ))}
      </div>

      <h3 className="text-xs font-semibold text-ink-muted uppercase tracking-wider mt-2">Encuadre</h3>
      <div className="flex gap-1.5">
        {(['single', 'auto', 'split'] as const).map((mode) => {
          const labels: Record<string, string> = { single: 'Una persona', auto: 'Automático', split: 'Dividido' }
          return (
            <button
              key={mode}
              onClick={() => setFramingMode(mode)}
              className={[
                'flex-1 py-1.5 rounded-field text-xs font-medium transition-colors border',
                framingMode === mode
                  ? 'bg-plasma text-void border-plasma'
                  : 'bg-panel-2 text-ink-muted border-line hover:border-line/50',
              ].join(' ')}
            >
              {labels[mode]}
            </button>
          )
        })}
      </div>

      <div className="flex items-center justify-between pt-1 border-t border-line/50">
        <label className="flex items-center gap-2 text-xs cursor-pointer select-none">
          <input
            type="checkbox"
            checked={removeSilence}
            onChange={(e) => setRemoveSilence(e.target.checked)}
            className="w-4 h-4 rounded border-line text-plasma bg-panel-2 focus:ring-ion"
          />
          <span>Quitar silencios y muletillas</span>
        </label>
        <Chip variant={removeSilence ? 'ok' : 'default'} size="sm">
          {removeSilence ? 'Activado' : 'Desactivado'}
        </Chip>
      </div>
    </div>
  )
}

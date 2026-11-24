import { Check, AlertTriangle, Loader2 } from 'lucide-react'
import type { Stage } from './stages'

const STATUS_TEXT: Record<string, string> = { pending: 'Pendiente', active: 'En curso', done: 'Completada', error: 'Con error' }

function Dot({ status }: { status: string }) {
  if (status === 'done') return <Check size={14} strokeWidth={2.5} />
  if (status === 'error') return <AlertTriangle size={14} strokeWidth={2} />
  if (status === 'active') return <Loader2 size={14} strokeWidth={2} className="spin" />
  return null
}

export function StageTracker({ stages }: { stages: Stage[] }) {
  const focus = stages.find((s) => s.status === 'error') ?? stages.find((s) => s.status === 'active')
  return (
    <div className="tracker">
      <ol className="stepper" aria-label="Progreso del procesamiento">
        {stages.map((s) => (
          <li key={s.key} className="step" data-status={s.status} aria-current={s.status === 'active' ? 'step' : undefined}>
            <span className="step__dot" aria-hidden="true"><Dot status={s.status} /></span>
            <span className="step__label" title={s.label}>{s.label}</span>
          </li>
        ))}
      </ol>

      {focus?.detail && (
        <div className="tracker__note" data-status={focus.status} role={focus.status === 'error' ? 'alert' : undefined}>
          <p className="tracker__text">{focus.detail}</p>
          {focus.status === 'active' && (
            <div className="bar" role="progressbar" aria-label={focus.label} aria-valuemin={0} aria-valuemax={100}
                 aria-valuenow={focus.progress} data-indeterminate={focus.progress == null || undefined}>
              <span style={focus.progress != null ? { width: `${focus.progress}%` } : undefined} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}

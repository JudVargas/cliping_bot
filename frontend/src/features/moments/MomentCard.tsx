import * as React from 'react'
import { formatTime, formatDuration } from '../../lib/format'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { Chip } from '../../components/ui/Chip'
import { Button } from '../../components/ui/Button'

export interface MomentCardProps {
  moment: import('../../lib/types').Moment
  isBest?: boolean
  onSelect: () => void
}

export function MomentCard({ moment, isBest = false, onSelect }: MomentCardProps) {
  const duration = moment.end - moment.start

  return (
    <article
      className={[
        'surface p-4 rounded-panel border border-line cursor-pointer group transition-all duration-200',
        isBest ? 'border-accent/50 shadow-[0_0_24px_-4px_color-mix(in_oklab,var(--accent)40%,transparent)]' : 'hover:border-accent/50',
      ].join(' ')}
      onClick={onSelect}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') onSelect() }}
    >
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-shrink-0">
          <ScoreRing score={moment.score} size={isBest ? 56 : 40} />
        </div>
        <div className="flex-1">
          <div className="flex items-start gap-2 mb-1">
            <h3 className="font-sans font-semibold text-base text-texto group-hover:text-accent transition-colors line-clamp-1">
              {moment.title}
            </h3>
            {isBest && (
              <Chip variant="accent" size="sm">Mejor puntuado</Chip>
            )}
          </div>
          <p className="text-texto-secundario text-xs line-clamp-2">{moment.reason}</p>
          <div className="mt-3 flex items-center gap-3 text-xs text-texto-secundario">
            <span className="font-mono">{formatTime(moment.start)} – {formatTime(moment.end)}</span>
            <span className="mx-1">·</span>
            <span className="font-mono">{formatDuration(duration)}</span>
            <span className="mx-1">·</span>
            <span>{moment.score}/10</span>
          </div>
        </div>
      </div>
      <div className="mt-4 flex justify-end">
        <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); onSelect() }}>
          Editar
        </Button>
      </div>
    </article>
  )
}

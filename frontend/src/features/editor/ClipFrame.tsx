import * as React from 'react'

export interface ClipFrameProps {
  moment: import('../../lib/types').Moment
  isBusy?: boolean
}

export function ClipFrame({ moment, isBusy = false }: ClipFrameProps) {
  const [isPlaying, setIsPlaying] = React.useState(false)
  const videoRef = React.useRef<HTMLVideoElement>(null)

  const duration = moment.end - moment.start

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`clip-frame ${isBusy ? '[data-busy=true]' : ''}`}
        style={{ maxHeight: 'min(70dvh, 40rem)' }}
      >
        <div className="inner relative">
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            playsInline
            preload="metadata"
            poster={`/api/clips/${moment.id}/download`}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={() => setIsPlaying(false)}
          >
            <source src={`/api/clips/${moment.id}/download`} type="video/mp4" />
            Tu navegador no soporta la reproducción de video.
          </video>
          {isBusy && (
            <div className="absolute inset-0 bg-void/40 flex items-center justify-center rounded-[18px]">
              <span className="text-plasma-soft font-mono text-sm animate-pulse">Procesando…</span>
            </div>
          )}
          {!isPlaying && !isBusy && (
            <button
              onClick={() => {
                const v = videoRef.current
                if (v) {
                  v.currentTime = 0
                  v.play().catch(() => {})
                }
              }}
              className="absolute inset-0 flex items-center justify-center bg-void/60 hover:bg-void/40 transition-colors"
              aria-label="Reproducir vista previa"
            >
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className="text-white drop-shadow-lg">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </button>
          )}
          <div className="absolute bottom-3 left-3 right-3 flex justify-between text-[11px] font-mono text-ink-muted bg-void/60 px-2 py-1 rounded-field backdrop-blur">
            <span>{formatTime(moment.start)}</span>
            <span>{formatTime(moment.end)}</span>
            <span className="font-sora font-bold">{moment.score}/10</span>
          </div>
        </div>
      </div>
      <div className="w-full text-center">
        <span className="text-ink-muted text-xs">{duration.toFixed(1)} s</span>
      </div>
    </div>
  )
}

import { formatTime } from '../../lib/format'
import type { ChipProps } from '../../components/ui/Chip'

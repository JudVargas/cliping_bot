import * as React from 'react'
import { formatDuration } from '../lib/format'

export interface ScoreRingProps {
  score: number
  size?: number
  thickness?: number
}

export function ScoreRing({ score, size = 48, thickness = 6 }: ScoreRingProps) {
  const pct = Math.max(0, Math.min(10, score)) / 10
  const circumference = 2 * Math.PI * ((size - thickness) / 2)
  const offset = circumference * (1 - pct)

  const color =
    score >= 7 ? 'ok' : score >= 4 ? 'warn' : 'plasma'

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={(size - thickness) / 2}
          fill="none"
          stroke="var(--color-line)"
          strokeWidth={thickness}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={(size - thickness) / 2}
          fill="none"
          stroke={`var(--color-${color})`}
          strokeWidth={thickness}
          strokeLinecap="round"
          style={{ strokeDasharray: circumference, strokeDashoffset: offset, transition: 'stroke-dashoffset 0.5s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="font-sora font-bold text-xs">{score}</span>
        <span className="text-[10px] text-ink-muted">/10</span>
      </div>
    </div>
  )
}

import * as React from 'react'

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'ok' | 'warn' | 'flare' | 'plasma'
  size?: 'sm' | 'md'
}

const VARIANT_CLASSES: Record<string, string> = {
  default: 'bg-panel-2 text-ink-muted border border-line',
  ok: 'bg-ok/10 text-ok border border-ok/30',
  warn: 'bg-warn/10 text-warn border border-warn/30',
  flare: 'bg-flare/10 text-flare border border-flare/30',
  plasma: 'bg-plasma/10 text-plasma-soft border border-plasma/30',
}

const SIZE_CLASSES: Record<string, string> = {
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-3 py-1 text-sm',
}

export function Chip({
  variant = 'default',
  size = 'md',
  className,
  ...props
}: ChipProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-pill border',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      ].filter(Boolean).join('')}
      {...props}
    />
  )
}

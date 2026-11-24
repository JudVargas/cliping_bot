import * as React from 'react'

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'accent' | 'exito' | 'alerta' | 'error'
  size?: 'sm' | 'md'
  className?: string
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
        `badge`,
        `badge[data-tone="${variant}"]`,
        SIZE_CLASSES[size],
        className,
      ].filter(Boolean).join('')}
      {...props}
    />
  )
}

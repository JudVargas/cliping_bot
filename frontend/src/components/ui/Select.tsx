import * as React from 'react'

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  helper?: string
}

export function Select({ label, error, helper, className, ...props }: SelectProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-xs font-semibold text-texto-muted">
          {label}
        </label>
      )}
      <select
        className={[
          'input w-full',
          error ? 'border-error' : '',
          className,
        ].filter(Boolean).join('')}
        {...props}
      />
      {error && <span className="text-xs text-error">{error}</span>}
      {helper && !error && <span className="text-xs text-texto-muted">{helper}</span>}
    </div>
  )
}

import * as React from 'react'

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: string | number
  height?: string | number
  radius?: string
}

export function Skeleton({
  width = '100%',
  height = '1rem',
  radius = '8px',
  className,
  ...props
}: SkeletonProps) {
  return (
    <div
      className={[
        'skeleton h-full w-full',
        `h-[${typeof height === 'number' ? height + 'px' : height}]`,
        `w-[${typeof width === 'number' ? width + 'px' : width}]`,
        `rounded-[${radius}]`,
        className,
      ].filter(Boolean).join('')}
      {...props}
    />
  )
}

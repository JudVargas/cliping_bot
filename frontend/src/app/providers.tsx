import * as React from 'react'
import { createClient } from 'wavesurfer.js'

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <React.Fragment>
      {children}
    </React.Fragment>
  )
}

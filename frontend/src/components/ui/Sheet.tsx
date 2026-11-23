import * as React from 'react'
import { X } from 'lucide-react'
import { Button } from './Button'

export interface SheetProps {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
}

export function Sheet({ open, onClose, title, children }: SheetProps) {
  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-void/60 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Panel */}
      <div className="fixed inset-x-0 bottom-0 z-50 w-full surface-glass p-4 md:p-6 lg:hidden max-h-[75dvh] overflow-y-auto animate-in slide-in-from-bottom duration-220 ease-out">
        {title && (
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-ink">{title}</h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              aria-label="Cerrar"
            >
              <X size={18} strokeWidth={2} />
            </Button>
          </div>
        )}
        {children}
      </div>
    </>
  )
}

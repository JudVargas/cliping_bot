import * as React from 'react'
import { Upload, Plus } from 'lucide-react'
import { Button } from '../../components/ui/Button'

export interface UploadZoneProps {
  onFiles: (files: FileList) => void
  isDropzone?: boolean
  accept?: string
}

export function UploadZone({ onFiles, isDropzone = true, accept = 'video/*' }: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = React.useState(false)
  const [isLoading, setIsLoading] = React.useState(false)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length) {
      onFiles(e.dataTransfer.files)
    }
  }

  const handleClick = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = accept
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files
      if (files) onFiles(files)
    }
    input.click()
  }

  return (
    <section className={`surface p-3 md:p-4 rounded-panel border border-line cursor-pointer transition-all duration-200 hover:border-accent/50 hover:shadow-md ${isDragOver ? 'border-accent bg-accent/5' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
      onDragLeave={(e) => { e.preventDefault(); setIsDragOver(false) }}
      onDrop={handleDrop}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter') handleClick() }}
      onClick={handleClick}
      aria-label="Zona de subida de video. Arrastra un archivo o haz clic para elegir."
    >
      <div className="flex flex-col items-center gap-4 text-center">
        {isDragOver && (
          <div className="flex items-center gap-2 px-3 py-1 rounded-pill bg-accent/10 text-accent border border-accent/30 text-xs font-medium">
            Soltar archivos aquí
          </div>
        )}
        <div className="w-12 h-12 rounded-panel bg-surface-2 flex items-center justify-center border border-border">
          <Upload size={24} strokeWidth={2} />
        </div>
        <h3 className="font-sans font-semibold text-lg text-texto">Subir video</h3>
        <p className="text-texto-muted text-sm max-w-md">
          Arrastra un archivo de video o haz clic para buscar en tu computadora.
          Soporta MP4, MOV, MKV, AVI.
        </p>
        <Button variant="primary" size="lg" onClick={handleClick} disabled={isLoading} leftIcon={<Plus size={18} strokeWidth={2} />}>
          {isLoading ? 'Subiendo...' : 'Elegir video'}
        </Button>
      </div>
    </section>
  )
}

export function UploadProgress({ progress, filename, onCancel }: { progress: number; filename: string; onCancel: () => void }) {
  return (
    <section className="surface p-3 rounded-panel border border-line">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-texto">{filename}</span>
        <span className="text-[10px] font-mono text-texto-muted">{Math.round(progress)}%</span>
      </div>
      <div className="w-full bg-surface-2 rounded-pill h-2 overflow-hidden">
        <div className="h-full bg-accent transition-all duration-300" style={{ width: `${Math.min(100, progress)}%` }} />
      </div>
      <button
        onClick={onCancel}
        className="mt-2 text-[10px] text-accent hover:text-accent-hover flex items-center gap-1"
        aria-label="Cancelar subida"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
        Cancelar
      </button>
    </section>
  )
}

import * as React from 'react'
import { Trash2, AlertTriangle } from 'lucide-react'
import { useDeleteVideo, useToast } from '../../lib/hooks'
import { formatTime } from '../../lib/format'
import { StageTracker } from './StageTracker'
import { deriveStages, type VideoLike } from './stages'

export interface VideoCardProps {
  video: VideoLike & { id: number; filename: string; duration?: number; width?: number; height?: number }
  onSelect: (id: number) => void
  onDelete?: (id: number) => void
}

export function VideoCard({ video, onSelect, onDelete }: VideoCardProps) {
  const stages = deriveStages(video)
  const duration = video.duration !== undefined && video.duration !== null
  const deleteMutation = useDeleteVideo()
  const { deleteSuccess, deleteError } = useToast()
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false)

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    setShowDeleteConfirm(true)
  }

  const handleConfirmDelete = () => {
    setShowDeleteConfirm(false)
    deleteMutation.mutate(video.id, {
      onSuccess: () => {
        deleteSuccess(video.filename)
      },
      onError: (err: Error) => {
        deleteError(err.message)
      },
    })
  }

  const handleCancelDelete = () => {
    setShowDeleteConfirm(false)
  }

  const statusMap: Record<string, 'neutral' | 'accent' | 'success' | 'danger'> = {
    uploaded: 'neutral',
    transcribing: 'accent',
    finding_moments: 'accent',
    ready: 'success',
    error: 'danger',
  }

  return (
    <>
      <article
        className="vcard"
        onClick={() => onSelect(video.id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter') onSelect(video.id) }}
      >
        <header className="vcard__head">
          <h3 className="vcard__title" title={video.filename}>{video.filename}</h3>
          <span className="badge" data-tone={statusMap[video.status] ?? 'neutral'}>{badgeForStatus(video.status)}</span>
          <button type="button" className="icon-btn" aria-label={`Eliminar ${video.filename}`} onClick={handleDeleteClick}>
            <Trash2 size={16} strokeWidth={1.75} />
          </button>
        </header>
        <p className="vcard__meta mono">{duration ? formatTime(video.duration) : '-'} · {video.width && video.height ? `${video.width}×${video.height}` : '-'}</p>
        <StageTracker stages={stages} />
      </article>

      {showDeleteConfirm && (
        <div className="modal-overlay" onClick={handleCancelDelete}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <AlertTriangle size={24} strokeWidth={2} className="modal-icon" />
              <h2 className="modal-title">¿Eliminar este video?</h2>
            </div>
            <p className="modal-text">
              Se eliminará <strong>"{video.filename}"</strong> y todos sus datos asociados. Esta acción no se puede deshacer.
            </p>
            <div className="modal-actions">
              <button type="button" className="modal-btn modal-btn-cancel" onClick={handleCancelDelete}>
                Cancelar
              </button>
              <button type="button" className="modal-btn modal-btn-delete" onClick={handleConfirmDelete}>
                Eliminar video
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

function badgeForStatus(status: string) {
  switch (status) {
    case 'uploaded': return 'En cola'
    case 'transcribing': return 'Transcribiendo'
    case 'finding_moments': return 'Buscando momentos'
    case 'ready': return 'Listo'
    case 'error': return 'Error'
    default: return 'Desconocido'
  }
}

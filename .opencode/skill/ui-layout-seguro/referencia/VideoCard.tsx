import { Trash2 } from 'lucide-react'
import { StageTracker } from './StageTracker'
import { StatusBadge } from './StatusBadge'
import { deriveStages, type VideoLike } from './stages'
import './VideoGrid.css'

// Adapta estos campos a tu modelo real de Video.
export interface Video extends VideoLike { id: string; name: string; duration: string; resolution: string }

export function VideoCard({ video, onDelete }: { video: Video; onDelete?: (id: string) => void }) {
  return (
    <article className="vcard">
      <header className="vcard__head">
        <h3 className="vcard__title" title={video.name}>{video.name}</h3>
        <StatusBadge status={video.status} />
        <button type="button" className="icon-btn" aria-label={`Eliminar ${video.name}`} onClick={() => onDelete?.(video.id)}>
          <Trash2 size={16} strokeWidth={1.75} />
        </button>
      </header>
      <p className="vcard__meta mono">{video.duration} · {video.resolution}</p>
      <StageTracker stages={deriveStages(video)} />
    </article>
  )
}

export function VideoGrid({ videos, onDelete }: { videos: Video[]; onDelete?: (id: string) => void }) {
  return <div className="video-grid">{videos.map((v) => <VideoCard key={v.id} video={v} onDelete={onDelete} />)}</div>
}

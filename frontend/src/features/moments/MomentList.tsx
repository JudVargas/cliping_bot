import * as React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useMoments, useVideo } from '../../lib/hooks'
import { MomentCard } from './MomentCard'
import { Skeleton } from '../../components/ui/Skeleton'
import { formatDuration } from '../../lib/format'

export function MomentsPage() {
  const { videoId } = useParams()
  const { data: video, isLoading: videoLoading } = useVideo(Number(videoId))
  const { data: moments, isLoading } = useMoments(Number(videoId))
  const navigate = useNavigate()

  if (videoLoading || isLoading) {
    return (
      <div className="p-4 md:p-6 flex flex-col gap-4">
        {[1, 2, 3].map((i) => (
          <MomentCardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (!video) {
    return <div className="p-4 text-center py-20">Video no encontrado</div>
  }

  const sorted = [...(moments ?? [])].sort((a, b) => b.score - a.score)

  return (
    <div className="p-4 md:p-6 max-w-4xl mx-auto">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="font-sora font-semibold text-xl text-ink">{video.filename}</h1>
          <p className="text-ink-muted text-sm">
            {video.duration !== undefined ? formatDuration(video.duration) : ''} · {sorted.length} momento{sorted.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {sorted.map((moment) => (
          <MomentCard
            key={moment.id}
            moment={moment}
            isBest={moment.id === sorted[0]?.id}
            onSelect={() => navigate(`/clips/${moment.id}`)}
          />
        ))}
      </div>
    </div>
  )
}

function MomentCardSkeleton() {
  return (
    <div className="surface p-4 rounded-panel border border-line animate-pulse">
      <div className="flex gap-4">
        <Skeleton width="40%" height="80" radius="12px" />
        <div className="flex-1">
          <Skeleton width="60%" height="16" radius="4px" className="mb-2" />
          <Skeleton width="80%" height="16" radius="4px" />
          <Skeleton width="100%" height="8" radius="4px" className="mt-3" />
        </div>
      </div>
    </div>
  )
}

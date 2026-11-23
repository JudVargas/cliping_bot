import * as React from 'react'
import { useVideos, useUploadVideo } from '../../lib/hooks'
import { UploadZone, UploadProgress } from '../upload/UploadZone'
import { VideoCard } from './VideoCard'
import { Skeleton } from '../../components/ui/Skeleton'
import { useNavigate } from 'react-router-dom'

export function VideosPage() {
  const { data: videos, isLoading, error } = useVideos()
  const uploadMutation = useUploadVideo()
  const navigate = useNavigate()
  const [files, setFiles] = React.useState<FileList | null>(null)

  const handleFiles = (fileList: FileList) => {
    setFiles(fileList)
    if (fileList.length > 0) {
      uploadMutation.mutate(fileList[0], {
        onSuccess: (video) => {
          setFiles(null)
          navigate(`/videos/${video.id}`)
        },
      })
    }
  }

  if (isLoading) {
    return (
      <div className="p-3 md:p-6">
        <div className="flex flex-col gap-3 md:gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} width="100%" height="200" radius="16px" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-3 md:p-6 text-center py-12">
        <p className="text-flare text-sm">{error.message}</p>
      </div>
    )
  }

  return (
    <div className="p-3 md:p-6 mx-auto w-full max-w-5xl">
      <div className="mb-4 md:mb-6">
        <UploadZone onFiles={handleFiles} isDropzone={true} />
      </div>

      {files && (
        <div className="mb-4 md:mb-6">
          <UploadProgress
            progress={uploadMutation.isPending ? 50 : 0}
            filename={files[0]?.name ?? ''}
            onCancel={() => { setFiles(null); uploadMutation.reset() }}
          />
        </div>
      )}

      {!videos || videos.length === 0 ? (
        <div className="text-center py-12 surface p-4 md:p-8 rounded-panel border border-line">
          <h3 className="font-sora font-semibold text-sm md:text-lg mb-2">No hay videos aún</h3>
          <p className="text-ink-muted text-xs md:text-sm mb-4">Sube tu primer video para empezar a crear clips.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
          {videos.map((video) => (
            <VideoCard key={video.id} video={video} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  )

  function onSelect(id: number) {
    navigate(`/videos/${id}`)
  }
}

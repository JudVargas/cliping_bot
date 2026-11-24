import * as React from 'react'
import { useVideos, useUploadVideo, useToast } from '../../lib/hooks'
import { UploadProgress } from '../upload/UploadZone'
import { VideoCard } from './VideoCard'
import { Skeleton } from '../../components/ui/Skeleton'
import { useNavigate } from 'react-router-dom'

export function VideosPage() {
  const { data: videos, isLoading, error } = useVideos()
  const uploadMutation = useUploadVideo()
  const { success, error: showError } = useToast()
  const navigate = useNavigate()
  const [files, setFiles] = React.useState<FileList | null>(null)
  const [uploadError, setUploadError] = React.useState<string | null>(null)
  const [isUploading, setIsUploading] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const handleFiles = (fileList: FileList) => {
    setFiles(fileList)
    setUploadError(null)
    if (fileList.length === 0) return

    if (fileList.length > 1) {
      console.warn(
        `Se seleccionaron ${fileList.length} archivos, solo se subirá el primero: ${fileList[0].name}`
      )
    }

    const file = fileList[0]
    uploadMutation.mutate(file, {
      onSuccess: (video) => {
        setFiles(null)
        setIsUploading(false)
        setUploadError(null)
        success('Video subido correctamente', { description: video.filename })
        navigate(`/videos/${video.id}`)
      },
      onError: (err: Error) => {
        setFiles(null)
        setIsUploading(false)
        setUploadError(err.message || 'Error al subir el video')
        showError('Error al subir el video', { description: err.message || 'Intenta de nuevo' })
        console.error('Upload error:', err)
      },
    })
  }

  const handleRetry = () => {
    if (files?.[0]) {
      uploadMutation.mutate(files[0], {
        onSuccess: (video) => {
          setFiles(null)
          setIsUploading(false)
          setUploadError(null)
          success('Video subido correctamente', { description: video.filename })
          navigate(`/videos/${video.id}`)
        },
        onError: (err: Error) => {
          setFiles(null)
          setIsUploading(false)
          setUploadError(err.message || 'Error al subir el video')
          showError('Error al subir el video', { description: err.message || 'Intenta de nuevo' })
        },
      })
    }
  }

  const handleClickUpload = () => {
    fileInputRef.current?.click()
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files
    if (selectedFiles) {
      setIsUploading(true)
      handleFiles(selectedFiles)
    }
  }

  if (isLoading) {
    return (
      <div className="p-3 md:p-6">
        <div className="flex flex-col gap-3 md:gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} width="100%" height="200" radius="12px" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-3 md:p-6 text-center py-12">
        <p className="text-danger text-sm">{error.message}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 text-xs text-accent underline"
        >
          Recargar página
        </button>
      </div>
    )
  }

  return (
    <div className="shell__content">
      <h1>Videos</h1>
      <section className="upload">
        <h2>Subir video</h2>
        <p>Arrastra un archivo de video o haz clic para buscar en tu computadora. Soporta MP4, MOV, MKV, AVI.</p>
        <button className="btn" onClick={handleClickUpload} disabled={isUploading}>
          {isUploading ? 'Subiendo...' : 'Elegir video'}
        </button>
        <input
          type="file"
          accept="video/*"
          style={{ display: 'none' }}
          ref={fileInputRef}
          onChange={handleFileInputChange}
        />
      </section>

      {uploadError && (
        <div className="mb-4 p-3 rounded-panel border border-danger bg-danger/5 text-sm text-danger flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{uploadError}</span>
          <button
            onClick={handleRetry}
            className="ml-auto text-xs text-accent underline underline-offset-2"
          >
            Reintentar
          </button>
        </div>
      )}

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
        <div className="text-center py-12 surface p-4 rounded-panel border border-line">
          <h3 className="font-semibold text-sm mb-2">No hay videos aún</h3>
          <p className="text-texto-muted text-xs mb-4">
            Sube tu primer video para empezar a crear clips.
          </p>
        </div>
      ) : (
        <div className="video-grid">
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

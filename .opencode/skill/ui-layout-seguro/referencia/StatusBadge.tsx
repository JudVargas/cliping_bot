import type { VideoStatus } from './stages'

const MAP: Record<VideoStatus, { label: string; tone: 'neutral' | 'accent' | 'success' | 'danger' }> = {
  uploading:       { label: 'Subiendo',          tone: 'accent' },
  uploaded:        { label: 'En cola',           tone: 'neutral' },
  transcribing:    { label: 'Transcribiendo',    tone: 'accent' },
  finding_moments: { label: 'Buscando momentos', tone: 'accent' },
  rendering:       { label: 'Exportando',        tone: 'accent' },
  ready:           { label: 'Listo',             tone: 'success' },
  error:           { label: 'Error',             tone: 'danger' },
}

export function StatusBadge({ status }: { status: VideoStatus }) {
  const { label, tone } = MAP[status]
  return <span className="badge" data-tone={tone}>{label}</span>
}

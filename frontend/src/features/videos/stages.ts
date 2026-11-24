export type StageKey = 'upload' | 'transcribe' | 'moments' | 'export'
export type StageStatus = 'pending' | 'active' | 'done' | 'error'
export type VideoStatus = 'uploading' | 'uploaded' | 'transcribing' | 'finding_moments' | 'rendering' | 'ready' | 'error'

export interface Stage { key: StageKey; label: string; status: StageStatus; detail?: string; progress?: number }

export interface VideoLike {
  status: VideoStatus
  progress?: number
  error?: string
  error_stage?: StageKey
}

const ORDER: { key: StageKey; label: string; detail: string }[] = [
  { key: 'upload',     label: 'Subida',        detail: 'Subiendo el archivo' },
  { key: 'transcribe', label: 'Transcripción', detail: 'Transcribiendo audio con Whisper' },
  { key: 'moments',    label: 'Momentos',      detail: 'Buscando los mejores momentos con IA' },
  { key: 'export',     label: 'Listo',         detail: 'Exportando clips finales' },
]

const ACTIVE_INDEX: Partial<Record<VideoStatus, number>> = {
  uploading: 0, transcribing: 1, finding_moments: 2, rendering: 3,
}

/** ÚNICA fuente de verdad: de aquí salen las etapas, para que badge y pasos no se contradigan. */
export function deriveStages(v: VideoLike): Stage[] {
  let doneCount = 0, activeIdx = -1, errorIdx = -1

  if (v.status === 'ready') doneCount = ORDER.length
  else if (v.status === 'uploaded') doneCount = 1
  else if (v.status === 'error') {
    const i = ORDER.findIndex((s) => s.key === v.error_stage)
    errorIdx = i >= 0 ? i : ORDER.length - 1
    doneCount = errorIdx
  } else {
    activeIdx = ACTIVE_INDEX[v.status] ?? 0
    doneCount = activeIdx
  }

  return ORDER.map((s, i): Stage => {
    const status: StageStatus = i === errorIdx ? 'error' : i < doneCount ? 'done' : i === activeIdx ? 'active' : 'pending'
    return {
      key: s.key, label: s.label, status,
      detail: status === 'error' ? (v.error ?? 'Ocurrió un error en esta etapa') : status === 'active' ? s.detail : undefined,
      progress: status === 'active' ? v.progress : undefined,
    }
  })
}
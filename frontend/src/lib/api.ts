const BASE = import.meta.env.VITE_API_BASE ?? ''

const LONG_NAME = 'a'.repeat(80)
const LONG_ERROR = 'E'.repeat(200)

const MOCK_VIDEOS = [
  {
    id: 1,
    filename: 'creacion de demandas.wmv',
    path: '/data/creacion_de_demandas.wmv',
    status: 'transcribing',
    progress: 45,
    duration: 1245,
    width: 1920,
    height: 1080,
    fps: 30,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T10:00:00Z',
    updated_at: '2026-11-23T10:15:00Z',
  },
  {
    id: 2,
    filename: 'entrevista_tecnica.mp4',
    path: '/data/entrevista_tecnica.mp4',
    status: 'ready',
    progress: 100,
    duration: 3600,
    width: 1280,
    height: 720,
    fps: 25,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-22T14:30:00Z',
    updated_at: '2026-11-22T15:45:00Z',
  },
  {
    id: 3,
    filename: 'clase_introduccion.mov',
    path: '/data/clase_introduccion.mov',
    status: 'error',
    progress: 0,
    duration: 1800,
    width: 1920,
    height: 1080,
    fps: 24,
    error_message: LONG_ERROR,
    error_stage: 'render',
    created_at: '2026-11-21T09:00:00Z',
    updated_at: '2026-11-21T09:30:00Z',
  },
  {
    id: 4,
    filename: LONG_NAME,
    path: '/data/nombre_muy_largo.mp4',
    status: 'uploaded',
    progress: 0,
    duration: 300,
    width: 1920,
    height: 1080,
    fps: 30,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T08:00:00Z',
    updated_at: '2026-11-23T08:05:00Z',
  },
  {
    id: 5,
    filename: 'video_05.mp4',
    path: '/data/video_05.mp4',
    status: 'uploaded',
    progress: 0,
    duration: 600,
    width: 1920,
    height: 1080,
    fps: 30,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T08:10:00Z',
    updated_at: '2026-11-23T08:10:00Z',
  },
  {
    id: 6,
    filename: 'video_06.mp4',
    path: '/data/video_06.mp4',
    status: 'transcribing',
    progress: 25,
    duration: 900,
    width: 1280,
    height: 720,
    fps: 25,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T08:15:00Z',
    updated_at: '2026-11-23T08:20:00Z',
  },
  {
    id: 7,
    filename: 'video_07.mp4',
    path: '/data/video_07.mp4',
    status: 'finding_moments',
    progress: 60,
    duration: 1500,
    width: 1920,
    height: 1080,
    fps: 30,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T08:25:00Z',
    updated_at: '2026-11-23T08:35:00Z',
  },
  {
    id: 8,
    filename: 'video_08.mp4',
    path: '/data/video_08.mp4',
    status: 'rendering',
    progress: 80,
    duration: 700,
    width: 1920,
    height: 1080,
    fps: 24,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T08:40:00Z',
    updated_at: '2026-11-23T08:50:00Z',
  },
  {
    id: 9,
    filename: 'video_09.mp4',
    path: '/data/video_09.mp4',
    status: 'ready',
    progress: 100,
    duration: 450,
    width: 1280,
    height: 720,
    fps: 25,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T08:55:00Z',
    updated_at: '2026-11-23T09:05:00Z',
  },
  {
    id: 10,
    filename: 'video_10.mp4',
    path: '/data/video_10.mp4',
    status: 'error',
    progress: 0,
    duration: 600,
    width: 1920,
    height: 1080,
    fps: 30,
    error_message: 'Error de transcoding',
    error_stage: 'transcribe',
    created_at: '2026-11-23T09:10:00Z',
    updated_at: '2026-11-23T09:15:00Z',
  },
  {
    id: 11,
    filename: 'video_11.mp4',
    path: '/data/video_11.mp4',
    status: 'uploaded',
    progress: 0,
    duration: 120,
    width: 640,
    height: 480,
    fps: 30,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T09:20:00Z',
    updated_at: '2026-11-23T09:20:00Z',
  },
  {
    id: 12,
    filename: 'video_12.mp4',
    path: '/data/video_12.mp4',
    status: 'ready',
    progress: 100,
    duration: 900,
    width: 1920,
    height: 1080,
    fps: 24,
    error_message: null,
    error_stage: null,
    created_at: '2026-11-23T09:25:00Z',
    updated_at: '2026-11-23T09:35:00Z',
  },
]

async function request<T>(
  input: string,
  init?: RequestInit,
): Promise<T> {
  const url = input.startsWith('http') ? input : `${BASE}${input}`

  // Modo de prueba: devolver datos simulados sin llamar al backend
  if (url.includes('mock=extremos')) {
    if (init?.method === 'POST' && url.includes('/videos')) {
      const newVideo = {
        ...MOCK_VIDEOS[0],
        id: Date.now(),
        filename: 'video_nuevo.mp4',
        status: 'uploaded',
        progress: 0,
      }
      return newVideo as T
    }
    return MOCK_VIDEOS as T
  }

  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Error ${res.status} en ${url}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  listVideos: () => {
    const isMock =
      typeof window !== 'undefined' &&
      window.location.search.includes('mock=extremos')
    if (isMock) {
      return Promise.resolve(MOCK_VIDEOS as unknown[])
    }
    return request<Video[]>(`/api/videos`)
  },
  getVideo: (id: number) => request<Video>(`/api/videos/${id}`),
  uploadVideo: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Video>(`/api/videos`, {
      method: 'POST',
      body: form,
    })
  },

  listMoments: (videoId: number) =>
    request<Moment[]>(`/api/videos/${videoId}/moments`),
  patchMoment: (id: number, body: Partial<Pick<Moment, 'start' | 'end' | 'title'>>) =>
    request<Moment>(`/api/moments/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  renderMoment: (id: number, options: RenderOptions) =>
    request<{ moment_id: number; clip_path: string; download_url: string }>(
      `/api/moments/${id}/render`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(options),
      },
    ),
  downloadClip: (momentId: number) => `/api/clips/${momentId}/download`,

  getJob: (id: number) => request<Job>(`/api/jobs/${id}`),
  deleteVideo: (id: number) =>
    request<{ deleted: boolean }>(`/api/videos/${id}`, {
      method: 'DELETE',
    }),
}

export type Video = import('./types').Video
export type Moment = import('./types').Moment
export type Job = import('./types').Job
export type RenderOptions = import('./types').RenderOptions

export { MOCK_VIDEOS }

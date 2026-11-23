const BASE = import.meta.env.VITE_API_BASE ?? ''

async function request<T>(
  input: string,
  init?: RequestInit,
): Promise<T> {
  const url = input.startsWith('http') ? input : `${BASE}${input}`
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `Error ${res.status} en ${url}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  // Videos
  listVideos: () => request<Video[]>(`/api/videos`),
  getVideo: (id: number) => request<Video>(`/api/videos/${id}`),
  uploadVideo: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<Video>(`/api/videos`, {
      method: 'POST',
      body: form,
    })
  },

  // Momentos
  listMoments: (videoId: number) =>
    request<Moment[]>(`/api/videos/${videoId}/moments`),
  patchMoment: (id: number, body: Partial<Pick<Moment, 'start' | 'end' | 'title'>>) =>
    request<Moment>(`/api/moments/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  // Render
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

  // Jobs
  getJob: (id: number) => request<Job>(`/api/jobs/${id}`),
}

export type Video = import('./types').Video
export type Moment = import('./types').Moment
export type Job = import('./types').Job
export type RenderOptions = import('./types').RenderOptions

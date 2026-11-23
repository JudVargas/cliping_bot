import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './api'

export function useVideos() {
  return useQuery({
    queryKey: ['videos'],
    queryFn: api.listVideos,
  })
}

export function useVideo(videoId: number) {
  return useQuery({
    queryKey: ['video', videoId],
    queryFn: () => api.getVideo(videoId),
    enabled: !!videoId,
  })
}

export function useUploadVideo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.uploadVideo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['videos'] })
    },
  })
}

export function useMoments(videoId: number) {
  return useQuery({
    queryKey: ['moments', videoId],
    queryFn: () => api.listMoments(videoId),
    enabled: !!videoId,
  })
}

export function useMoment(momentId: number) {
  return useQuery({
    queryKey: ['moment', momentId],
    queryFn: async () => {
      const moments = await api.listMoments(0) // placeholder; el endpoint individual no existe aún
      return moments.find((m) => m.id === momentId) ?? null
    },
    enabled: !!momentId,
  })
}

export function usePatchMoment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Pick<import('./types').Moment, 'start' | 'end' | 'title'>> }) =>
      api.patchMoment(id, body),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['moments', vars.id] })
    },
  })
}

export function useRenderMoment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, options }: { id: number; options: import('./types').RenderOptions }) =>
      api.renderMoment(id, options),
    onSuccess: (_, vars) => {
      queryClient.invalidateQueries({ queryKey: ['moments', vars.id] })
    },
  })
}

export function useJob(jobId: number) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId),
    enabled: !!jobId,
    refetchInterval: (data) => {
      const job = data as import('./types').Job | undefined
      if (!job || job.status === 'done' || job.status === 'error') return false
      return 2000
    },
  })
}

/// <reference types="vite/client" />
import axios from 'axios'

export const API_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  timeout: 30000,
})

api.interceptors.request.use(config => {
  const csrf = document.cookie.split('; ').find(row => row.startsWith('srs_csrf='))?.split('=')[1]
  if (csrf) config.headers['X-CSRF-Token'] = decodeURIComponent(csrf)
  return config
})

api.interceptors.response.use(response => response, error => {
  if (error.response?.status === 401 && !['/auth/login', '/auth/register'].includes(error.config?.url)) {
    window.dispatchEvent(new Event('session-expired'))
  }
  return Promise.reject(error)
})

export function apiError(error: any, fallback = 'The request failed. Please try again.'): string {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(item => item.msg).join('. ')
  return fallback
}

export const authApi = {
  login: (data: any) => api.post('/auth/login', data),
  register: (data: any) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  forgotPassword: (email: string) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token: string, password: string) => api.post('/auth/reset-password', { token, password }),
  verifyEmail: (token: string) => api.post('/auth/verify-email', { token }),
  requestVerification: () => api.post('/auth/request-verification'),
}

export const projectsApi = {
  list: () => api.get('/projects/'),
  get: (id: number) => api.get(`/projects/${id}`),
  create: (data: { name: string; description?: string; analysis_profile?: 'srs_only' | 'architecture'; analysis_mode?: 'deterministic' | 'ai' }) => api.post('/projects/', data),
  extraction: (id: number) => api.get(`/projects/${id}/extraction`),
  uploadSRS: (id: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/projects/${id}/upload-srs`, fd)
  },
  uploadUML: (id: number, type: string, file: File) => {
    const fd = new FormData()
    fd.append('uml_type', type)
    fd.append('file', file)
    return api.post(`/projects/${id}/upload-uml`, fd)
  },
  analyze: (id: number) => api.post(`/projects/${id}/analyze`),
  reanalyze: (id: number) => api.post(`/projects/${id}/reanalyze`),
  compare: (id: number, version: number) => api.get(`/projects/${id}/compare?with_version=${version}`)
}

export const findingsApi = {
  getByProject: (id: number) => api.get(`/findings/project/${id}`)
}

export const traceabilityApi = {
  getByProject: (id: number) => api.get(`/traceability/project/${id}`),
  update: (id: number, status: string) => api.patch(`/traceability/${id}`, { status }),
  export: (id: number) => api.get(`/traceability/project/${id}/export`, { responseType: 'blob' }),
}

export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats')
}

export interface Revision {
  id: number; project_id: number; number: number; parent_id: number | null; state: 'draft' | 'sealed'; edit_version: number
  analysis_profile: 'srs_only' | 'architecture'; analysis_mode: 'deterministic' | 'ai'; extraction_confirmed: boolean
  artifacts: { id: number; type: string; filename: string; sha256: string | null; size_bytes: number | null }[]
}
export interface RunSummary {
  id: string; project_id: number; revision_id: number; status: string; stage: string; created_at: string; error_message?: string; has_report: boolean
  attempt_count: number; cancel_requested: boolean
}
export const historyApi = {
  create: (data: unknown, key: string) => api.post('/v1/projects', data, { headers: { 'Idempotency-Key': key } }),
  revision: (pid: number, rid: number) => api.get<Revision>(`/v1/projects/${pid}/revisions/${rid}`),
  draft: (pid: number, parentId?: number) => api.post<Revision>(`/v1/projects/${pid}/drafts`, { parent_revision_id: parentId }),
  edit: (pid: number, revision: Revision, data: unknown) => api.patch<Revision>(`/v1/projects/${pid}/revisions/${revision.id}`, data, { headers: { 'If-Match': revision.edit_version } }),
  upload: (pid: number, revision: Revision, kind: string, file: File, key: string, replaceId?: number) => {
    const data = new FormData(); data.append('kind', kind); data.append('file', file)
    if (replaceId) data.append('replace_artifact_id', String(replaceId))
    return api.post<{ artifact_id: number; revision: Revision }>(`/v1/projects/${pid}/revisions/${revision.id}/artifacts`, data,
      { headers: { 'If-Match': revision.edit_version, 'Idempotency-Key': key }, timeout: 90000 })
  },
  remove: (pid: number, revision: Revision, aid: number) => api.delete(`/v1/projects/${pid}/revisions/${revision.id}/artifacts/${aid}`, { headers: { 'If-Match': revision.edit_version } }),
  extract: (pid: number, revision: Revision) => api.post(`/v1/projects/${pid}/revisions/${revision.id}/extraction`, {}, { headers: { 'If-Match': revision.edit_version }, timeout: 120000 }),
  extraction: (pid: number, rid: number) => api.get(`/v1/projects/${pid}/revisions/${rid}/extraction`),
  correct: (pid: number, revision: Revision, element: string, data: unknown) => api.patch(`/v1/projects/${pid}/revisions/${revision.id}/requirements/${encodeURIComponent(element)}`, data, { headers: { 'If-Match': revision.edit_version } }),
  start: (pid: number, revision: Revision, key: string) => api.post<RunSummary>(`/v1/projects/${pid}/revisions/${revision.id}/runs`, {}, { headers: { 'If-Match': revision.edit_version, 'Idempotency-Key': key } }),
  runs: (pid: number) => api.get<{ items: RunSummary[]; total: number }>(`/v1/projects/${pid}/runs?limit=100`),
  report: (runId: string) => api.get(`/v1/runs/${encodeURIComponent(runId)}/report`),
  run: (runId: string) => api.get<RunSummary>(`/v1/runs/${encodeURIComponent(runId)}`),
  cancel: (runId: string) => api.post<RunSummary>(`/v1/runs/${encodeURIComponent(runId)}/cancel`),
  compare: (runId: string, previous: string) => api.get(`/v1/runs/${encodeURIComponent(runId)}/compare/${encodeURIComponent(previous)}`),
  decision: (runId: string, data: unknown) => api.post(`/v1/runs/${encodeURIComponent(runId)}/decisions`, data),
  suggestion: (runId: string, findingId: number, data: unknown, key: string, version?: number) => api.post(`/v1/runs/${encodeURIComponent(runId)}/suggestions/${findingId}/decisions`, data, { headers: { 'Idempotency-Key': key, ...(version ? { 'If-Match': String(version) } : {}) } }),
  exportTrace: (runId: string) => api.get(`/v1/runs/${encodeURIComponent(runId)}/traceability.csv`, { responseType: 'blob' }),
  source: (pid: number, aid: number) => `${API_URL}/v1/projects/${pid}/artifacts/${aid}/source`,
}


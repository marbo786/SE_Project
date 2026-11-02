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
  create: (data: { name: string; description?: string }) => api.post('/projects/', data),
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


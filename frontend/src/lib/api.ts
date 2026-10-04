/// <reference types="vite/client" />
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

const api = axios.create({
  baseURL: API_URL
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const authApi = {
  login: (data: any) => api.post('/auth/login', data),
  register: (data: any) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me')
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
  getByProject: (id: number) => api.get(`/traceability/project/${id}`)
}

export const dashboardApi = {
  getStats: () => api.get('/dashboard/stats')
}


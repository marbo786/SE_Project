import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' }
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 - redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// Auth
export const authApi = {
  register: (data: { name: string; email: string; password: string; role: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

// Assignments
export const assignmentsApi = {
  list: () => api.get('/assignments'),
  get: (id: number) => api.get(`/assignments/${id}`),
  create: (data: { title: string; course_code: string; due_date?: string }) =>
    api.post('/assignments', data),
}

// Submissions
export const submissionsApi = {
  list: (assignmentId?: number) =>
    api.get('/submissions', { params: assignmentId ? { assignment_id: assignmentId } : {} }),
  get: (id: number) => api.get(`/submissions/${id}`),
  create: (formData: FormData) =>
    api.post('/submissions', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  uploadSRS: (id: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/submissions/${id}/upload-srs`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  uploadUML: (id: number, diagramType: string, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('diagram_type', diagramType)
    return api.post(`/submissions/${id}/upload-uml`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  analyze: (id: number) => api.post(`/submissions/${id}/analyze`),
}

// Reports
export const reportsApi = {
  findings: (submissionId: number) => api.get(`/reports/${submissionId}/findings`),
  scores: (submissionId: number) => api.get(`/reports/${submissionId}/scores`),
  traceability: (submissionId: number) => api.get(`/reports/${submissionId}/traceability`),
  exportCSV: (submissionId: number) =>
    api.get(`/reports/${submissionId}/traceability/csv`, { responseType: 'blob' }),
  makeDecision: (submissionId: number, findingId: number, data: { status: string; comment?: string }) =>
    api.post(`/reports/${submissionId}/findings/${findingId}/decision`, data),
  updateTraceLink: (submissionId: number, linkId: number, status: string) =>
    api.put(`/reports/${submissionId}/trace-links/${linkId}`, null, { params: { status } }),
  createTraceLink: (submissionId: number, data: { source_type: string; source_id: string; target_type: string; target_id: string }) =>
    api.post(`/reports/${submissionId}/trace-links`, null, { params: data }),
}

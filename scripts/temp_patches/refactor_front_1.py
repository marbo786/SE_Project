import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)

# --- API ---
write_file('frontend/src/lib/api.ts', """
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
""")

# --- LAYOUT ---
write_file('frontend/src/components/Layout.tsx', """
import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { LayoutDashboard, FileText, LogOut, FileCode } from 'lucide-react'
import { Button } from './ui/button'

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    const u = localStorage.getItem('user')
    if (u) setUser(JSON.parse(u))
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  const links = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/projects', icon: FileText, label: 'My Projects' }
  ]

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-200">
          <FileCode className="h-6 w-6 text-blue-600 mr-2" />
          <span className="font-bold text-lg text-slate-900">SRS Reviewer</span>
        </div>
        <nav className="flex-1 px-4 py-6 space-y-2">
          {links.map(l => (
            <Link key={l.to} to={l.to}
              className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                location.pathname === l.to ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}>
              <l.icon className="h-4 w-4 mr-3" />
              {l.label}
            </Link>
          ))}
        </nav>
        {user && (
          <div className="p-4 border-t border-slate-200">
            <div className="mb-4">
              <p className="text-sm font-medium text-slate-900">{user.name}</p>
              <p className="text-xs text-slate-500">Developer</p>
            </div>
            <Button variant="outline" className="w-full justify-start" onClick={handleLogout}>
              <LogOut className="h-4 w-4 mr-2" /> Logout
            </Button>
          </div>
        )}
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
""")

# --- APP.TSX ---
write_file('frontend/src/App.tsx', """
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import ProjectsPage from '@/pages/ProjectsPage'
import NewProjectPage from '@/pages/NewProjectPage'
import ReportPage from '@/pages/ReportPage'
import Layout from '@/components/Layout'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        <Route path="/" element={
          <ProtectedRoute>
            <Layout><DashboardPage /></Layout>
          </ProtectedRoute>
        } />
        
        <Route path="/projects" element={
          <ProtectedRoute>
            <Layout><ProjectsPage /></Layout>
          </ProtectedRoute>
        } />

        <Route path="/projects/new" element={
          <ProtectedRoute>
            <Layout><NewProjectPage /></Layout>
          </ProtectedRoute>
        } />
        
        <Route path="/projects/:id" element={
          <ProtectedRoute>
            <Layout><ReportPage /></Layout>
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  )
}
""")

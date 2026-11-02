import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import ProjectsPage from '@/pages/ProjectsPage'
import NewProjectPage from '@/pages/NewProjectPage'
import ReportPage from '@/pages/ReportPage'
import Layout from '@/components/Layout'
import { useAuth } from '@/lib/auth'
import RecoveryPage from '@/pages/RecoveryPage'
import AccountPage from '@/pages/AccountPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading, error, refresh } = useAuth()
  if (loading) return <main className="p-8" role="status">Checking your session…</main>
  if (error) return <main className="p-8" role="alert">{error} <button onClick={refresh}>Try again</button></main>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<RecoveryPage mode="request" />} />
      <Route path="/reset-password" element={<RecoveryPage mode="reset" />} />
      <Route path="/verify-email" element={<RecoveryPage mode="verify" />} />
      <Route path="/account" element={<ProtectedRoute><Layout><AccountPage /></Layout></ProtectedRoute>} />
      
      <Route path="/" element={
        <ProtectedRoute>
          <Layout><DashboardPage /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/dashboard" element={<Navigate to="/" replace />} />
      
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

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

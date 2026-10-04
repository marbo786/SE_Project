import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/lib/auth'
import Layout from '@/components/Layout'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import AssignmentsPage from '@/pages/AssignmentsPage'
import AssignmentDetailPage from '@/pages/AssignmentDetailPage'
import SubmitPage from '@/pages/SubmitPage'
import SubmissionsPage from '@/pages/SubmissionsPage'
import ReportPage from '@/pages/ReportPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function AppRoutes() {
  const { isAuthenticated } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />} />

      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Layout><DashboardPage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/assignments" element={
        <ProtectedRoute>
          <Layout><AssignmentsPage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/assignments/:id" element={
        <ProtectedRoute>
          <Layout><AssignmentDetailPage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/assignments/:id/submit" element={
        <ProtectedRoute>
          <Layout><SubmitPage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/submissions" element={
        <ProtectedRoute>
          <Layout><SubmissionsPage /></Layout>
        </ProtectedRoute>
      } />
      <Route path="/submissions/:id" element={
        <ProtectedRoute>
          <Layout><ReportPage /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

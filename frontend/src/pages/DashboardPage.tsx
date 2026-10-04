import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { assignmentsApi, submissionsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { BookOpen, ClipboardList, AlertTriangle, CheckCircle } from 'lucide-react'

export default function DashboardPage() {
  const { user } = useAuth()
  const { data: assignmentsRes } = useQuery({
    queryKey: ['assignments'],
    queryFn: () => assignmentsApi.list()
  })
  const { data: submissionsRes } = useQuery({
    queryKey: ['submissions'],
    queryFn: () => submissionsApi.list()
  })

  const assignments = assignmentsRes?.data || []
  const submissions = submissionsRes?.data || []
  const doneSubmissions = submissions.filter((s: any) => s.status === 'done').length
  const pendingSubmissions = submissions.filter((s: any) => s.status === 'analyzing').length

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Welcome back, {user?.name}!</h1>
        <p className="text-gray-500 mt-1">Here's your overview for CS325 SRS Reviewer</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <BookOpen className="h-6 w-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{assignments.length}</p>
                <p className="text-gray-500 text-sm">Assignments</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{doneSubmissions}</p>
                <p className="text-gray-500 text-sm">Analyzed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-yellow-100 rounded-lg">
                <AlertTriangle className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{pendingSubmissions}</p>
                <p className="text-gray-500 text-sm">Analyzing</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Assignments</CardTitle>
        </CardHeader>
        <CardContent>
          {assignments.length === 0 ? (
            <p className="text-gray-500 text-sm">No assignments yet.</p>
          ) : (
            <div className="space-y-3">
              {assignments.slice(0, 5).map((a: any) => (
                <div key={a.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="font-medium">{a.title}</p>
                    <p className="text-sm text-gray-500">{a.course_code}</p>
                  </div>
                  <Link to={`/assignments/${a.id}`}>
                    <Button variant="outline" size="sm">View</Button>
                  </Link>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

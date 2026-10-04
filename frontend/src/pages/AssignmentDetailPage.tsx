import React from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/lib/auth'
import { assignmentsApi, submissionsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, ArrowLeft } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const statusVariant: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  done: 'default',
  analyzing: 'secondary',
  pending: 'outline',
  error: 'destructive'
}

export default function AssignmentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { isInstructor } = useAuth()

  const { data: aRes } = useQuery({
    queryKey: ['assignment', id],
    queryFn: () => assignmentsApi.get(Number(id))
  })

  const { data: sRes } = useQuery({
    queryKey: ['submissions', id],
    queryFn: () => submissionsApi.list(Number(id))
  })

  const assignment = aRes?.data
  const submissions = sRes?.data || []

  return (
    <div className="p-8">
      <Link to="/assignments" className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back to Assignments
      </Link>

      {assignment && (
        <div className="mb-8">
          <h1 className="text-3xl font-bold">{assignment.title}</h1>
          <p className="text-gray-500">{assignment.course_code}</p>
          {assignment.due_date && <p className="text-sm text-gray-400">Due: {formatDate(assignment.due_date)}</p>}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold">Submissions ({submissions.length})</h2>
        {!isInstructor && (
          <Link to={`/assignments/${id}/submit`}>
            <Button><Plus className="h-4 w-4 mr-2" />New Submission</Button>
          </Link>
        )}
      </div>

      <div className="space-y-4">
        {submissions.map((s: any) => (
          <Card key={s.id}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{s.team_name}</h3>
                  <p className="text-sm text-gray-500">Version {s.version} • {formatDate(s.created_at)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={statusVariant[s.status] || 'outline'}>
                    {s.status}
                  </Badge>
                  <Link to={`/submissions/${s.id}`}>
                    <Button variant="outline" size="sm">View Report</Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {submissions.length === 0 && (
          <p className="text-gray-500 text-center py-8">No submissions yet.</p>
        )}
      </div>
    </div>
  )
}

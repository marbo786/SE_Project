import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { submissionsApi } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ClipboardList } from 'lucide-react'
import { formatDate } from '@/lib/utils'

const statusVariant: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  done: 'default',
  analyzing: 'secondary',
  pending: 'outline',
  error: 'destructive'
}

export default function SubmissionsPage() {
  const { data: res, isLoading } = useQuery({
    queryKey: ['submissions'],
    queryFn: () => submissionsApi.list()
  })

  const submissions = res?.data || []

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Submissions</h1>
        <p className="text-gray-500 mt-1">All submissions across assignments</p>
      </div>

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : submissions.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <ClipboardList className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>No submissions yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {submissions.map((s: any) => (
            <Card key={s.id}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{s.team_name}</h3>
                    <p className="text-sm text-gray-500">
                      Assignment #{s.assignment_id} • Version {s.version} • {formatDate(s.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={statusVariant[s.status] || 'outline'}>
                      {s.status}
                    </Badge>
                    {s.status === 'done' && (
                      <Link to={`/submissions/${s.id}`}>
                        <Button variant="outline" size="sm">View Report</Button>
                      </Link>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

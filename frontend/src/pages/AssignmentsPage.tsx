import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { assignmentsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Plus, BookOpen } from 'lucide-react'
import { formatDate } from '@/lib/utils'

export default function AssignmentsPage() {
  const { isInstructor } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', course_code: '', due_date: '' })

  const { data: res, isLoading } = useQuery({
    queryKey: ['assignments'],
    queryFn: () => assignmentsApi.list()
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => assignmentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] })
      setShowForm(false)
      setForm({ title: '', course_code: '', due_date: '' })
    }
  })

  const assignments = res?.data || []

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Assignments</h1>
          <p className="text-gray-500 mt-1">Manage course assignments</p>
        </div>
        {isInstructor && (
          <Button onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4 mr-2" />
            New Assignment
          </Button>
        )}
      </div>

      {showForm && isInstructor && (
        <Card className="mb-6">
          <CardHeader><CardTitle>Create Assignment</CardTitle></CardHeader>
          <CardContent>
            <form
              className="space-y-4"
              onSubmit={e => {
                e.preventDefault()
                createMutation.mutate(form)
              }}
            >
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input placeholder="SRS Document Submission"
                    value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
                </div>
                <div className="space-y-2">
                  <Label>Course Code</Label>
                  <Input placeholder="CS325"
                    value={form.course_code} onChange={e => setForm(f => ({ ...f, course_code: e.target.value }))} required />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Due Date (optional)</Label>
                <Input type="datetime-local"
                  value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))} />
              </div>
              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : assignments.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-30" />
          <p>No assignments yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {assignments.map((a: any) => (
            <Card key={a.id}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-lg">{a.title}</h3>
                    <p className="text-sm text-gray-500">{a.course_code}</p>
                    {a.due_date && (
                      <p className="text-sm text-gray-400 mt-1">Due: {formatDate(a.due_date)}</p>
                    )}
                  </div>
                  <Link to={`/assignments/${a.id}`}>
                    <Button variant="outline">View Submissions</Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

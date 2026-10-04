import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { dashboardApi, projectsApi } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { BookOpen, CheckCircle, Clock, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function DashboardPage() {
  const [stats, setStats] = useState<any>(null)
  const [projects, setProjects] = useState<any[]>([])
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  useEffect(() => {
    dashboardApi.getStats().then(res => setStats(res.data))
    projectsApi.list().then(res => setProjects(res.data.slice(0, 5)))
  }, [])

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Welcome back, {user.name}!</h1>
          <p className="text-slate-500">Ready to analyze a new specification document?</p>
        </div>
        <Link to="/projects/new">
          <Button size="lg"><Plus className="mr-2 h-5 w-5" /> Analyze New SRS</Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card className="bg-blue-50 border-blue-100">
          <CardContent className="p-6 flex items-center">
            <div className="p-3 bg-blue-100 text-blue-600 rounded-lg mr-4">
              <BookOpen className="h-6 w-6" />
            </div>
            <div>
              <p className="text-2xl font-bold text-blue-900">{stats?.total_projects || 0}</p>
              <p className="text-sm font-medium text-blue-600">Total Projects</p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-green-50 border-green-100">
          <CardContent className="p-6 flex items-center">
            <div className="p-3 bg-green-100 text-green-600 rounded-lg mr-4">
              <CheckCircle className="h-6 w-6" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-900">{stats?.analyzed_projects || 0}</p>
              <p className="text-sm font-medium text-green-600">Analyzed</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-amber-50 border-amber-100">
          <CardContent className="p-6 flex items-center">
            <div className="p-3 bg-amber-100 text-amber-600 rounded-lg mr-4">
              <Clock className="h-6 w-6" />
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-900">{stats?.analyzing_projects || 0}</p>
              <p className="text-sm font-medium text-amber-600">Analyzing</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Projects</h2>
          {projects.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-gray-200 rounded-lg">
              <p className="text-gray-500 mb-4">No projects yet.</p>
              <Link to="/projects/new">
                <Button variant="outline">Create your first project</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {projects.map(p => (
                <div key={p.id} className="flex items-center justify-between p-4 border rounded-lg hover:bg-slate-50 transition-colors">
                  <div>
                    <h3 className="font-medium text-lg text-slate-900">{p.name}</h3>
                    <p className="text-sm text-slate-500">Version {p.version} • Status: {p.status}</p>
                  </div>
                  <Link to={`/projects/${p.id}`}>
                    <Button variant="secondary">View Report</Button>
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

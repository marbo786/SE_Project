import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { projectsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Plus, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([])
  
  useEffect(() => {
    projectsApi.list().then(res => setProjects(res.data))
  }, [])

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-slate-900">My Projects</h1>
        <Link to="/projects/new">
          <Button><Plus className="mr-2 h-4 w-4" /> New Project</Button>
        </Link>
      </div>

      <div className="bg-white border rounded-lg shadow-sm">
        <div className="p-4 border-b border-gray-200 flex items-center">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input className="pl-9" placeholder="Search projects..." />
          </div>
        </div>
        
        {projects.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No projects found. Create one to get started!
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {projects.map(p => (
              <div key={p.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                <div>
                  <Link to={`/projects/${p.id}`} className="font-semibold text-lg text-blue-600 hover:underline">
                    {p.name}
                  </Link>
                  <p className="text-sm text-gray-500 mt-1">{p.description || "No description provided."}</p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-gray-500">v{p.version}</span>
                  <Badge variant={p.status === 'done' ? 'default' : p.status === 'error' ? 'destructive' : 'outline'}>
                    {p.status}
                  </Badge>
                  <Link to={`/projects/${p.id}`}>
                    <Button variant="outline" size="sm">View Report</Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

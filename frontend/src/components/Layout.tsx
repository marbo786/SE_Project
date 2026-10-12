import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  FileCode2,
  LogOut,
  Plus,
  ChevronLeft,
  ChevronRight,
  User,
  Menu,
  X,
  Terminal,
} from 'lucide-react'
import { Button } from './ui/button'
import { cn } from '@/lib/utils'

interface UserData {
  id: number
  name: string
  email: string
  role?: string
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState<UserData | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const u = localStorage.getItem('user')
    if (u) {
      try {
        setUser(JSON.parse(u))
      } catch {
        setUser(null)
      }
    }
  }, [])

  useEffect(() => {
    setMobileOpen(false)
  }, [location.pathname])

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  const navLinks = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/projects', icon: FileCode2, label: 'Specifications' },
  ]

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#17181B] text-[#E7E7E9]">
      {/* Brand Header */}
      <div className={cn(
        "h-12 flex items-center border-b border-[#303136] px-3.5 shrink-0 select-none",
        collapsed ? "justify-center px-2" : "justify-between"
      )}>
        <Link to="/" className="flex items-center gap-2 min-w-0">
          <div className="flex items-center justify-center w-5 h-5 rounded-sm bg-[#1D1E22] border border-[#303136] text-[#7895B5] shrink-0">
            <Terminal className="h-3 w-3" />
          </div>
          {!collapsed && (
            <div className="flex items-center gap-1.5 truncate">
              <span className="font-mono text-xs font-semibold tracking-wider text-[#E7E7E9]">
                SRS_REVIEWER
              </span>
              <span className="text-[10px] font-mono text-[#777981] border border-[#303136] rounded-sm px-1 py-0.2">
                SYS
              </span>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <div className="flex-1 px-2 py-3 space-y-4 overflow-y-auto scrollbar-technical">
        <div>
          {!collapsed && (
            <p className="px-2 mb-1.5 text-[10px] font-mono font-medium uppercase tracking-wider text-[#777981]">
              Navigation
            </p>
          )}
          <nav className="space-y-0.5">
            {navLinks.map(link => {
              const active = isActive(link.to)
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  title={collapsed ? link.label : undefined}
                  className={cn(
                    "flex items-center gap-2.5 px-2.5 py-1.5 text-xs font-medium rounded transition-none group",
                    collapsed && "justify-center px-1.5",
                    active
                      ? "bg-[#1D1E22] text-[#E7E7E9] border-l-2 border-l-[#7895B5] font-semibold"
                      : "text-[#A1A1AA] hover:bg-[#1D1E22]/60 hover:text-[#E7E7E9]"
                  )}
                >
                  <link.icon className={cn("h-3.5 w-3.5 shrink-0", active ? "text-[#7895B5]" : "text-[#777981] group-hover:text-[#A1A1AA]")} />
                  {!collapsed && <span className="truncate">{link.label}</span>}
                </Link>
              )
            })}
          </nav>
        </div>

        <div>
          {!collapsed && (
            <p className="px-2 mb-1.5 text-[10px] font-mono font-medium uppercase tracking-wider text-[#777981]">
              Actions
            </p>
          )}
          <Link to="/projects/new" title={collapsed ? "New Analysis" : undefined}>
            <button
              className={cn(
                "w-full flex items-center gap-2 px-2.5 py-1.5 text-xs rounded border border-[#303136] bg-[#111214] text-[#A1A1AA] hover:text-[#E7E7E9] hover:border-[#7895B5]/50 transition-none",
                collapsed && "justify-center px-1.5"
              )}
            >
              <Plus className="h-3.5 w-3.5 text-[#7895B5] shrink-0" />
              {!collapsed && <span className="font-mono text-[11px]">New Specification</span>}
            </button>
          </Link>
        </div>
      </div>

      {/* User Section & Collapser */}
      <div className="border-t border-[#303136] p-2 shrink-0 bg-[#141518]">
        {user && (
          <div className={cn(
            "flex items-center gap-2 mb-2 p-1.5 rounded bg-[#1D1E22]/70 border border-[#303136]/50",
            collapsed && "justify-center p-1"
          )}>
            <div className="flex items-center justify-center w-6 h-6 rounded-sm bg-[#17181B] border border-[#303136] text-[10px] font-mono text-[#7895B5] shrink-0 font-medium">
              {user.name?.charAt(0)?.toUpperCase() || <User className="h-3 w-3" />}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-[#E7E7E9] truncate leading-tight">{user.name}</p>
                <p className="text-[10px] font-mono text-[#777981] truncate">{user.email}</p>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-1">
          <button
            onClick={handleLogout}
            title={collapsed ? "Logout" : undefined}
            className={cn(
              "flex items-center gap-2 flex-1 px-2 py-1 text-xs text-[#777981] hover:text-[#E06C6C] hover:bg-[#1D1E22] rounded transition-none",
              collapsed && "justify-center"
            )}
          >
            <LogOut className="h-3.5 w-3.5 shrink-0" />
            {!collapsed && <span className="text-[11px]">Disconnect</span>}
          </button>

          <button
            onClick={() => setCollapsed(!collapsed)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="hidden lg:flex items-center justify-center h-6 w-6 rounded text-[#777981] hover:text-[#E7E7E9] hover:bg-[#1D1E22] transition-none"
          >
            {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-[#111214] text-[#E7E7E9] flex font-sans">
      {/* Mobile Menu Toggle Button */}
      <button
        className="lg:hidden fixed top-2.5 left-2.5 z-50 p-1.5 rounded bg-[#17181B] border border-[#303136] text-[#E7E7E9]"
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle navigation"
      >
        {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
      </button>

      {/* Mobile Overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/70 z-30"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed lg:sticky top-0 left-0 z-40 h-screen border-r border-[#303136] transition-none shrink-0",
          collapsed ? "w-14" : "w-52",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {sidebarContent}
      </aside>

      {/* Main Content Viewport */}
      <main className="flex-1 min-w-0 overflow-auto bg-[#111214]">
        <div className="p-5 lg:p-6 max-w-6xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}

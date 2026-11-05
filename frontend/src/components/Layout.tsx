import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import * as Dialog from '@radix-ui/react-dialog'
import { Menu, X, FileCheck2 } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { apiError } from '@/lib/api'

function preference(key: string, fallback: string) {
  try { return localStorage.getItem(key) || fallback } catch { return fallback }
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const location = useLocation(), navigate = useNavigate()
  const [open, setOpen] = useState(false), [error, setError] = useState('')
  const [theme, setTheme] = useState(() => preference('srs-theme', 'dark'))
  const [density, setDensity] = useState(() => preference('srs-density', 'comfortable'))
  useEffect(() => { setOpen(false) }, [location.pathname])
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.classList.toggle('dark', theme === 'dark')
    document.documentElement.dataset.density = density
    try { localStorage.setItem('srs-theme', theme); localStorage.setItem('srs-density', density) } catch { /* Preferences work without storage. */ }
  }, [theme, density])
  const navigation = <div className="flex flex-col h-full p-5 gap-6 bg-secondary">
    <Link to="/" className="flex items-center gap-2 font-semibold text-lg"><FileCheck2 aria-hidden="true" /> SRS Reviewer</Link>
    <nav aria-label="Main navigation" className="grid gap-2">
      {[['/', 'Dashboard'], ['/projects', 'Projects'], ['/projects/new', 'New project'], ['/account', 'Account']].map(([to, label]) => <Link key={to} to={to}
        aria-current={location.pathname === to ? 'page' : undefined}
        className="rounded px-3 py-3 hover:bg-accent aria-[current=page]:bg-accent aria-[current=page]:font-semibold">{label}</Link>)}
    </nav>
    <div className="mt-auto space-y-4">
      <label className="block text-sm">Appearance<select className="block w-full border rounded p-2 mt-1 bg-background" value={theme} onChange={e => setTheme(e.target.value)}><option value="dark">Dark</option><option value="light">Light</option></select></label>
      <label className="block text-sm">Spacing<select className="block w-full border rounded p-2 mt-1 bg-background" value={density} onChange={e => setDensity(e.target.value)}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></select></label>
      <p className="text-sm break-words text-muted-foreground">{user?.name}<br />{user?.email}</p>
      <button className="border rounded px-3 py-2 w-full" onClick={async () => { try { await logout(); navigate('/login') } catch (err) { setError(apiError(err, 'Sign out failed. Try again.')) } }}>Sign out</button>
    </div>
  </div>
  return <div className="min-h-screen bg-background text-foreground lg:flex">
    <a href="#main-content" className="skip-link">Skip to content</a>
    <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between border-b bg-secondary px-4 h-16 print:hidden">
      <Link to="/" className="font-semibold">SRS Reviewer</Link>
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger asChild><button aria-label="Open navigation" className="p-3"><Menu /></button></Dialog.Trigger>
        <Dialog.Portal><Dialog.Overlay className="fixed inset-0 bg-black/60 z-40" /><Dialog.Content className="fixed inset-y-0 left-0 w-80 max-w-[90vw] z-50 bg-secondary overflow-auto">
          <Dialog.Title className="sr-only">Navigation</Dialog.Title><Dialog.Description className="sr-only">Projects and workspace preferences</Dialog.Description>
          <Dialog.Close asChild><button aria-label="Close navigation" className="absolute right-2 top-2 p-3"><X /></button></Dialog.Close>
          <div className="pt-10 h-full">{navigation}</div>
        </Dialog.Content></Dialog.Portal>
      </Dialog.Root>
    </header>
    <aside className="hidden lg:block sticky top-0 h-screen w-60 shrink-0 border-r print:hidden">{navigation}</aside>
    <main id="main-content" tabIndex={-1} className="flex-1 min-w-0">
      <div className="workspace-content p-4 md:p-6 lg:p-8 max-w-7xl mx-auto">
        {error && <p role="alert">{error}</p>}{children}
      </div>
    </main>
  </div>
}

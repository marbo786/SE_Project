import { Component, type ReactNode } from 'react'

export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <main className="max-w-xl mx-auto p-8 space-y-4" role="alert">
      <h1 className="text-2xl font-semibold">This view could not be displayed</h1>
      <p>Your saved projects and reports are still available. Reload to try again.</p>
      <button className="border rounded px-4 py-2" onClick={() => window.location.reload()}>Reload workspace</button>
    </main>
    return this.props.children
  }
}

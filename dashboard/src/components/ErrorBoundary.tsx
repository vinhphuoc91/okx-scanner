import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Dashboard error:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[#0d1117] p-8">
          <div className="max-w-md rounded-xl border border-[#30363d] bg-[#161b22] p-8 text-center">
            <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-[#f85149]" />
            <h1 className="mb-2 text-xl font-semibold text-[#e6edf3]">Something went wrong</h1>
            <p className="mb-6 text-sm text-[#8b949e]">{this.state.message}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="inline-flex items-center gap-2 rounded-lg bg-[#388bfd] px-4 py-2 text-sm font-medium text-white hover:bg-[#4493f8]"
            >
              <RefreshCw className="h-4 w-4" />
              Reload Dashboard
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

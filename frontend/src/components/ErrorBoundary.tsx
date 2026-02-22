import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("React error boundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center p-8">
          <div className="max-w-xl bg-red-900/50 border border-red-700 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-400 mb-2">Something went wrong</h2>
            <pre className="text-sm text-red-200 whitespace-pre-wrap break-words mb-4">
              {this.state.error.message}
            </pre>
            <pre className="text-xs text-red-300/60 whitespace-pre-wrap break-words max-h-40 overflow-auto">
              {this.state.error.stack}
            </pre>
            <button
              onClick={() => this.setState({ error: null })}
              className="mt-4 px-4 py-2 bg-red-700 hover:bg-red-600 rounded text-sm"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

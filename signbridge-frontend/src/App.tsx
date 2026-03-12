import { useEffect } from 'react'
import { Hand, WifiOff } from 'lucide-react'
import './App.css'
import SignBridgeInterface from './components/SignBridgeInterface'
import { useWebSocket } from './hooks/useWebSocket'

function App() {
  const { connect, disconnect, isConnected } = useWebSocket()

  useEffect(() => {
    connect().catch((error) => {
      console.error('Failed to connect to WebSocket:', error)
    })

    // Keep the singleton socket alive across StrictMode dev remounts.
    return undefined
  }, [connect])

  useEffect(() => {
    const handleBeforeUnload = () => {
      disconnect()
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [disconnect])

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand-block">
          <div className="brand-icon" aria-hidden="true">
            <Hand size={18} />
          </div>
          <div className="brand-copy">
            <h1>SignBridge Live</h1>
            <p>Real-time sign language bridge</p>
          </div>
        </div>

        <div className={`status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? <span className="status-dot" aria-hidden="true"></span> : <WifiOff size={14} />}
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </header>
      <main className="app-main">
        {isConnected ? (
          <SignBridgeInterface />
        ) : (
          <div className="loading">
            <p>Connecting to server...</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App

import { useState, useCallback, useEffect } from 'react'
import { WebSocketClientMessage, WebSocketServerMessage } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/signbridge'

class WebSocketManager {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private readonly maxReconnectAttempts = 5
  private readonly messageListeners = new Set<(message: WebSocketServerMessage) => void>()
  private readonly statusListeners = new Set<(connected: boolean) => void>()
  private shouldReconnect = true
  private connectPromise: Promise<void> | null = null
  private readonly pendingMessages: WebSocketClientMessage[] = []

  isConnected() {
    return Boolean(this.ws && this.ws.readyState === WebSocket.OPEN)
  }

  connect(): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return this.connectPromise ?? Promise.resolve()
    }

    if (this.connectPromise) {
      return this.connectPromise
    }

    this.shouldReconnect = true

    this.connectPromise = new Promise<void>((resolve, reject) => {
      let settled = false

      try {
        const ws = new WebSocket(WS_URL)
        this.ws = ws

        ws.onopen = () => {
          settled = true
          this.reconnectAttempts = 0
          this.notifyStatus(true)
          this.flushPending()
          resolve()
        }

        ws.onerror = (event) => {
          console.error('WebSocket error:', event)
          if (!settled) {
            settled = true
            reject(new Error('WebSocket connection failed'))
          }
        }

        ws.onclose = () => {
          this.ws = null
          this.notifyStatus(false)

          if (!settled) {
            settled = true
            reject(new Error('WebSocket closed before opening'))
          }

          if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts += 1
            const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000)
            setTimeout(() => {
              this.connect().catch((error) => console.error('Reconnection failed', error))
            }, delay)
          }
        }

        ws.onmessage = (event: MessageEvent<string>) => {
          this.handleMessage(event)
        }
      } catch (error) {
        console.error('Failed to create WebSocket:', error)
        if (!settled) {
          settled = true
          reject(error)
        }
      }
    }).finally(() => {
      this.connectPromise = null
    })

    return this.connectPromise
  }

  disconnect() {
    this.shouldReconnect = false
    this.reconnectAttempts = 0
    this.pendingMessages.length = 0
    this.connectPromise = null

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.notifyStatus(false)
  }

  send(message: WebSocketClientMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      return
    }

    this.pendingMessages.push(message)
  }

  subscribe(callback: (message: WebSocketServerMessage) => void) {
    this.messageListeners.add(callback)
    return () => {
      this.messageListeners.delete(callback)
    }
  }

  onStatusChange(callback: (connected: boolean) => void) {
    this.statusListeners.add(callback)
    callback(this.isConnected())
    return () => {
      this.statusListeners.delete(callback)
    }
  }

  private notifyStatus(connected: boolean) {
    this.statusListeners.forEach((listener) => listener(connected))
  }

  private handleMessage(event: MessageEvent<string>) {
    try {
      const parsed = JSON.parse(event.data) as WebSocketServerMessage
      this.messageListeners.forEach((listener) => listener(parsed))
    } catch (error) {
      console.error('Failed to parse WebSocket payload', error)
    }
  }

  private flushPending() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    while (this.pendingMessages.length > 0) {
      const message = this.pendingMessages.shift()
      if (!message) {
        continue
      }
      this.ws.send(JSON.stringify(message))
    }
  }
}

const manager = new WebSocketManager()

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(manager.isConnected())

  useEffect(() => {
    return manager.onStatusChange(setIsConnected)
  }, [])

  const connect = useCallback(() => manager.connect(), [])
  const disconnect = useCallback(() => manager.disconnect(), [])
  const send = useCallback((message: WebSocketClientMessage) => manager.send(message), [])
  const subscribe = useCallback(
    (callback: (message: WebSocketServerMessage) => void) => manager.subscribe(callback),
    []
  )

  return {
    isConnected,
    connect,
    disconnect,
    send,
    subscribe
  }
}

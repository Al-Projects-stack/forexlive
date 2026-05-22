import { useState, useEffect, useRef, useCallback } from 'react'
import { WSMessage, Pair } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const RECONNECT_DELAY_MS = 3000

export interface UseWebSocketResult {
  isConnected: boolean
  lastMessage: WSMessage | null
  connectionError: string | null
}

export const useWebSocket = (pair: Pair): UseWebSocketResult => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    const encodedPair = pair.replace('/', '%2F')
    const url = `${WS_URL}/ws/${encodedPair}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      if (!mountedRef.current) return
      setIsConnected(true)
      setConnectionError(null)
    }

    ws.onclose = () => {
      if (!mountedRef.current) return
      setIsConnected(false)
      // Reconnect after delay
      reconnectTimer.current = setTimeout(() => {
        if (mountedRef.current) connect()
      }, RECONNECT_DELAY_MS)
    }

    ws.onerror = () => {
      if (!mountedRef.current) return
      setConnectionError('Connection error')
    }

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return
      try {
        const msg = JSON.parse(event.data as string) as WSMessage
        if (msg.type === 'PING') {
          ws.send('ping')
          return
        }
        setLastMessage(msg)
      } catch {
        // Ignore malformed messages
      }
    }
  }, [pair])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { isConnected, lastMessage, connectionError }
}

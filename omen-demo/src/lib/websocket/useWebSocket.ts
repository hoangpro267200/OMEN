/**
 * WebSocket hook for real-time updates.
 *
 * Features:
 * - Auto-reconnect with exponential backoff
 * - Heartbeat/ping-pong
 * - Message type routing
 * - Query cache invalidation
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '../api/queryKeys'

// ═══════════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════════

export interface WebSocketMessage {
  type: string
  data: Record<string, unknown>
  timestamp: string
}

export interface UseWebSocketOptions {
  url?: string
  autoConnect?: boolean
  onMessage?: (message: WebSocketMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export interface UseWebSocketReturn {
  isConnected: boolean
  lastMessage: WebSocketMessage | null
  send: (data: unknown) => void
  connect: () => void
  disconnect: () => void
}

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

function getWebSocketUrl(): string {
  if (typeof window === 'undefined') return 'ws://localhost/ws'
  const envUrl = (import.meta.env as { VITE_WS_URL?: string }).VITE_WS_URL
  if (envUrl) return envUrl
  const apiBase = (import.meta.env as { VITE_API_BASE?: string }).VITE_API_BASE
  if (apiBase) {
    const base = apiBase.replace(/^http/, 'ws')
    return base.endsWith('/') ? `${base}ws` : `${base}/ws`
  }
  try {
    const stored = localStorage.getItem('omen.apiBase')
    if (stored) {
      const base = stored.replace(/^http/, 'ws')
      return base.endsWith('/') ? `${base}ws` : `${base}/ws`
    }
  } catch {
    // ignore
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = (import.meta.env as { VITE_API_HOST?: string }).VITE_API_HOST ?? window.location.host
  return `${protocol}//${host}/ws`
}

// ═══════════════════════════════════════════════════════════════════════════════
// Hook
// ═══════════════════════════════════════════════════════════════════════════════

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = getWebSocketUrl(),
    autoConnect = true,
    onMessage,
    onConnect,
    onDisconnect,
  } = options

  const ws = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)

  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ─────────────────────────────────────────────────────────────────────────────
  // Message Handler
  // ─────────────────────────────────────────────────────────────────────────────

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        setLastMessage(message)
        onMessage?.(message)

        switch (message.type) {
          case 'signal_emitted':
            queryClient.invalidateQueries({ queryKey: queryKeys.overview })
            queryClient.invalidateQueries({ queryKey: queryKeys.signals() })
            queryClient.invalidateQueries({ queryKey: ['omen', 'activity'] })
            break
          case 'signal_ingested':
            queryClient.invalidateQueries({ queryKey: queryKeys.overview })
            break
          case 'reconcile_started':
            queryClient.invalidateQueries({
              queryKey: queryKeys.partitionDetail(
                (message.data.partition_date as string) ?? ''
              ),
            })
            break
          case 'reconcile_completed':
            queryClient.invalidateQueries({ queryKey: queryKeys.overview })
            queryClient.invalidateQueries({ queryKey: queryKeys.partitions() })
            queryClient.invalidateQueries({
              queryKey: queryKeys.partitionDetail(
                (message.data.partition_date as string) ?? ''
              ),
            })
            queryClient.invalidateQueries({
              queryKey: queryKeys.partitionDiff(
                (message.data.partition_date as string) ?? ''
              ),
            })
            break
          case 'partition_sealed':
            queryClient.invalidateQueries({ queryKey: queryKeys.partitions() })
            break
          case 'stats_update':
            queryClient.invalidateQueries({ queryKey: queryKeys.overview })
            break
          case 'heartbeat':
          case 'pong':
            break
          default:
            break
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    },
    [queryClient, onMessage]
  )

  // ─────────────────────────────────────────────────────────────────────────────
  // Connection Management
  // ─────────────────────────────────────────────────────────────────────────────

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return

    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        setIsConnected(true)
        reconnectAttempts.current = 0
        onConnect?.()
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'ping' }))
          }
        }, 25000)
      }

      ws.current.onmessage = handleMessage

      ws.current.onclose = () => {
        setIsConnected(false)
        onDisconnect?.()
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current)
        }
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            30000
          )
          reconnectAttempts.current += 1
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        }
      }

      ws.current.onerror = () => {
        // Error details are in onclose
      }
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
    }
  }, [url, handleMessage, onConnect, onDisconnect])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
    }
    reconnectAttempts.current = maxReconnectAttempts
    ws.current?.close()
    ws.current = null
  }, [])

  const send = useCallback((data: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  // ─────────────────────────────────────────────────────────────────────────────
  // Lifecycle
  // ─────────────────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (autoConnect) connect()
    return () => {
      disconnect()
    }
  }, [autoConnect, connect, disconnect])

  return {
    isConnected,
    lastMessage,
    send,
    connect,
    disconnect,
  }
}

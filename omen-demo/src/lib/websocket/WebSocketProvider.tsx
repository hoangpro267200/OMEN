/**
 * WebSocket Provider
 *
 * Provides WebSocket connection to entire app.
 * Shows connection status indicator when using useWebSocketContext().
 */

import { createContext, useContext, type ReactNode } from 'react'
import {
  useWebSocket,
  type UseWebSocketReturn,
  type WebSocketMessage,
} from './useWebSocket'

const WebSocketContext = createContext<UseWebSocketReturn | null>(null)

interface WebSocketProviderProps {
  children: ReactNode
  onMessage?: (message: WebSocketMessage) => void
}

export function WebSocketProvider({ children, onMessage }: WebSocketProviderProps) {
  const ws = useWebSocket({
    autoConnect: true,
    onMessage,
  })

  return (
    <WebSocketContext.Provider value={ws}>{children}</WebSocketContext.Provider>
  )
}

export function useWebSocketContext(): UseWebSocketReturn {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return context
}

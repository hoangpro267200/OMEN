/**
 * WebSocket Provider
 *
 * Provides WebSocket connection to entire app.
 * Shows connection status indicator when using useWebSocketContext().
 * 
 * NOTE: Only connects in LIVE mode. In DEMO mode, WebSocket is disabled.
 */

import { createContext, useContext, type ReactNode } from 'react'
import {
  useWebSocket,
  type UseWebSocketReturn,
  type WebSocketMessage,
} from './useWebSocket'
import { useDataSourceMode } from '../mode/store'

const WebSocketContext = createContext<UseWebSocketReturn | null>(null)

// Dummy return for demo mode
const demoWebSocket: UseWebSocketReturn = {
  isConnected: false,
  lastMessage: null,
  send: () => {},
  connect: () => {},
  disconnect: () => {},
}

interface WebSocketProviderProps {
  children: ReactNode
  onMessage?: (message: WebSocketMessage) => void
}

export function WebSocketProvider({ children, onMessage }: WebSocketProviderProps) {
  const [mode] = useDataSourceMode()
  const isLive = mode === 'live'
  
  // Only connect WebSocket in live mode
  const ws = useWebSocket({
    autoConnect: isLive, // Only auto-connect in live mode
    onMessage,
  })

  // In demo mode, provide a dummy WebSocket context
  const value = isLive ? ws : demoWebSocket

  return (
    <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
  )
}

export function useWebSocketContext(): UseWebSocketReturn {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return context
}

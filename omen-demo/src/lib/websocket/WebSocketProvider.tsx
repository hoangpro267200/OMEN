/**
 * WebSocket Provider
 *
 * Provides WebSocket connection to entire app.
 * Shows connection status indicator when using useWebSocketContext().
 * 
 * NOTE: Only connects in LIVE mode. In DEMO mode, WebSocket is disabled.
 * Uses DataModeContext for consistent mode state across the app.
 */

import { createContext, useContext, type ReactNode } from 'react'
import {
  useWebSocket,
  type UseWebSocketReturn,
  type WebSocketMessage,
} from './useWebSocket'
import { useDataModeSafe } from '../../context/DataModeContext'

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
  // Use safe version to handle edge cases during error recovery
  const { isLive, canUseLiveData } = useDataModeSafe()
  
  // Only connect WebSocket in live mode AND when API is available
  const ws = useWebSocket({
    autoConnect: isLive && canUseLiveData,
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

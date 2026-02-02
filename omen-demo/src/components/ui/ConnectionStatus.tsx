/**
 * Connection Status Indicator
 *
 * Shows WebSocket connection status in header.
 */

import { motion } from 'framer-motion'
import { useWebSocketContext } from '../../lib/websocket'
import { StatusDot } from './StatusDot'

export function ConnectionStatus() {
  const { isConnected } = useWebSocketContext()

  return (
    <motion.div
      className="flex items-center gap-1.5"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <StatusDot variant={isConnected ? 'success' : 'error'} />
      <span className="text-xs text-[var(--text-muted)]">
        {isConnected ? 'Live' : 'Offline'}
      </span>
    </motion.div>
  )
}

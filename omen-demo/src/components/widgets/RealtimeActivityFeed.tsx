/**
 * Real-time Activity Feed
 *
 * Shows live updates as they happen via WebSocket.
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useWebSocketContext } from '../../lib/websocket'
import { Badge } from '../ui/Badge'
import { Card } from '../ui/Card'
import { StatusDot } from '../ui/StatusDot'

interface ActivityEvent {
  id: string
  type: string
  signal_id?: string
  title?: string
  category?: string
  status?: string
  status_code?: number
  timestamp: string
}

const MAX_EVENTS = 50

const SHOW_TYPES = ['signal_emitted', 'signal_ingested', 'reconcile_completed']

function EventBadge({ event }: { event: ActivityEvent }) {
  switch (event.type) {
    case 'signal_emitted':
      return (
        <Badge variant={event.status === 'delivered' ? 'delivered' : 'warning'}>
          {event.status ?? '—'}
        </Badge>
      )
    case 'signal_ingested':
      return (
        <Badge variant={event.status_code === 409 ? '409' : '200'}>
          {event.status_code === 409 ? 'Duplicate' : 'Ingested'}
        </Badge>
      )
    case 'reconcile_completed':
      return (
        <Badge variant="COMPLETED">
          Reconciled
        </Badge>
      )
    default:
      return null
  }
}

export function RealtimeActivityFeed() {
  const { isConnected, lastMessage } = useWebSocketContext()
  const [events, setEvents] = useState<ActivityEvent[]>([])

  useEffect(() => {
    if (!lastMessage) return
    if (!SHOW_TYPES.includes(lastMessage.type)) return

    const newEvent: ActivityEvent = {
      id: `${lastMessage.timestamp}-${Math.random()}`,
      type: lastMessage.type,
      timestamp: lastMessage.timestamp,
      ...(lastMessage.data as Omit<ActivityEvent, 'id' | 'type' | 'timestamp'>),
    }
    setEvents((prev) => [newEvent, ...prev].slice(0, MAX_EVENTS))
  }, [lastMessage])

  return (
    <Card className="h-full" hover={false}>
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between gap-2 border-b border-[var(--border-subtle)] px-4 py-2">
          <h3 className="text-sm font-medium text-[var(--text-secondary)] uppercase tracking-wider">
            Activity
          </h3>
          <div className="flex items-center gap-2">
            <StatusDot variant={isConnected ? 'success' : 'error'} />
            <span className="text-xs text-[var(--text-muted)]">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
        </div>
        <div className="overflow-y-auto overflow-thin-scroll max-h-[400px] flex-1 min-h-0">
          <AnimatePresence initial={false}>
            {events.length === 0 ? (
              <div className="text-center text-[var(--text-muted)] py-8 px-4">
                Waiting for events...
              </div>
            ) : (
              events.map((event) => (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, y: -20, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="border-b border-[var(--border-subtle)] py-2 px-4 last:border-0"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs text-[var(--text-muted)] font-mono shrink-0">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                      {event.signal_id && (
                        <span className="text-sm font-mono text-[var(--text-primary)] truncate">
                          {event.signal_id.slice(0, 16)}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <EventBadge event={event} />
                    </div>
                  </div>
                  {event.title && (
                    <div className="text-xs text-[var(--text-secondary)] mt-1 truncate">
                      {event.title}
                    </div>
                  )}
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </Card>
  )
}

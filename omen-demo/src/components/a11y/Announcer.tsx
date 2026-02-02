/**
 * Screen Reader Announcer
 *
 * Announces dynamic content to screen readers.
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface AnnouncerContextValue {
  announce: (message: string, priority?: 'polite' | 'assertive') => void
}

const AnnouncerContext = createContext<AnnouncerContextValue | null>(null)

export function AnnouncerProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('')
  const [priority, setPriority] = useState<'polite' | 'assertive'>('polite')

  const announce = useCallback(
    (msg: string, prio: 'polite' | 'assertive' = 'polite') => {
      setMessage('')
      setPriority(prio)
      setTimeout(() => setMessage(msg), 100)
    },
    []
  )

  return (
    <AnnouncerContext.Provider value={{ announce }}>
      {children}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {priority === 'polite' && message}
      </div>
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {priority === 'assertive' && message}
      </div>
    </AnnouncerContext.Provider>
  )
}

export function useAnnouncer(): AnnouncerContextValue {
  const context = useContext(AnnouncerContext)
  if (!context) {
    throw new Error('useAnnouncer must be used within AnnouncerProvider')
  }
  return context
}

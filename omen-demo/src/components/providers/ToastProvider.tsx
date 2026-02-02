/**
 * Toast Provider
 *
 * Provides toast notifications for errors and success messages.
 */

import { Toaster } from 'react-hot-toast'

export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-subtle)',
        },
        success: {
          iconTheme: {
            primary: 'var(--accent-green)',
            secondary: 'var(--bg-secondary)',
          },
        },
        error: {
          iconTheme: {
            primary: 'var(--accent-red)',
            secondary: 'var(--bg-secondary)',
          },
          duration: 5000,
        },
      }}
    />
  )
}

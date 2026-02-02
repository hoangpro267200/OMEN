/**
 * Language Switcher
 *
 * Allows users to change language.
 */

import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Globe } from 'lucide-react'
import { cn } from '../../lib/utils'

const LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'vi', name: 'Tiếng Việt', flag: '🇻🇳' },
]

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [])

  const current = LANGUAGES.find((l) => l.code === i18n.language)

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-3 py-2 rounded-[var(--radius-button)] hover:bg-[var(--bg-tertiary)] transition-colors border border-transparent focus:border-[var(--border-active)] focus:outline-none"
        aria-label="Change language"
        aria-expanded={open}
        aria-haspopup="true"
      >
        <Globe className="w-4 h-4 text-[var(--text-secondary)]" />
        <span className="text-sm text-[var(--text-secondary)]">
          {current?.flag ?? '🌐'}
        </span>
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-1 py-1 bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded-[var(--radius-card)] shadow-lg min-w-[140px]"
          role="menu"
        >
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              role="menuitem"
              onClick={() => {
                i18n.changeLanguage(lang.code)
                setOpen(false)
              }}
              className={cn(
                'w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors',
                'hover:bg-[var(--bg-tertiary)]',
                i18n.language === lang.code
                  ? 'text-[var(--accent-blue)]'
                  : 'text-[var(--text-secondary)]'
              )}
            >
              <span>{lang.flag}</span>
              <span>{lang.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

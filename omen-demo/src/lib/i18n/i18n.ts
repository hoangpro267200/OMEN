/**
 * Internationalization Setup
 *
 * Uses i18next for translations.
 */

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en.json'
import vi from './locales/vi.json'

const resources = {
  en: { translation: en },
  vi: { translation: vi },
}

const isDev = (import.meta as { env?: { DEV?: boolean } }).env?.DEV ?? false

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    debug: isDev,
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  })

export default i18n

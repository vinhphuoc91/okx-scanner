import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import en from './en'
import vi from './vi'
import type { Locale } from './types'

const LOCALE_KEY = 'okx-locale'

const MESSAGES: Record<Locale, Record<string, string>> = { vi, en }

type Params = Record<string, string | number>

interface I18nContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  toggleLocale: () => void
  t: (key: string, params?: Params) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

function readStoredLocale(): Locale {
  try {
    const stored = localStorage.getItem(LOCALE_KEY)
    if (stored === 'en' || stored === 'vi') return stored
  } catch {
    /* ignore */
  }
  return 'vi'
}

function interpolate(template: string, params?: Params): string {
  if (!params) return template
  return template.replace(/\{\{(\w+)\}\}/g, (_, key: string) =>
    params[key] !== undefined ? String(params[key]) : `{{${key}}}`,
  )
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(readStoredLocale)

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next)
    try {
      localStorage.setItem(LOCALE_KEY, next)
    } catch {
      /* ignore */
    }
  }, [])

  const toggleLocale = useCallback(() => {
    setLocale(locale === 'vi' ? 'en' : 'vi')
  }, [locale, setLocale])

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const t = useCallback(
    (key: string, params?: Params) => {
      const msg = MESSAGES[locale][key] ?? MESSAGES.en[key] ?? key
      return interpolate(msg, params)
    },
    [locale],
  )

  const value = useMemo(
    () => ({ locale, setLocale, toggleLocale, t }),
    [locale, setLocale, toggleLocale, t],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useTranslation() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useTranslation must be used within I18nProvider')
  return ctx
}

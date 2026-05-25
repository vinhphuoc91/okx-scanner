import { Languages } from 'lucide-react'
import { useTranslation } from '../../i18n/I18nProvider'

export function LanguageToggle() {
  const { locale, toggleLocale, t } = useTranslation()

  return (
    <button
      type="button"
      onClick={toggleLocale}
      title={t('lang.label')}
      className="flex items-center gap-1.5 rounded-lg border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-xs text-[#e6edf3] hover:bg-[#30363d]"
    >
      <Languages className="h-3.5 w-3.5 text-[#388bfd]" />
      <span className="font-medium">{locale === 'vi' ? 'EN' : 'VI'}</span>
    </button>
  )
}

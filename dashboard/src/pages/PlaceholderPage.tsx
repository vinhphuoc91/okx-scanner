import { Construction } from 'lucide-react'
import { useTranslation } from '../i18n/I18nProvider'

interface Props {
  titleKey: string
  descriptionKey?: string
}

export function PlaceholderPage({ titleKey, descriptionKey }: Props) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center justify-center p-16 text-center">
      <Construction className="mb-4 h-12 w-12 text-[#484f58]" />
      <h1 className="mb-2 text-lg font-semibold text-[#e6edf3]">{t(titleKey)}</h1>
      <p className="max-w-sm text-sm text-[#8b949e]">
        {t(descriptionKey ?? 'placeholder.default')}
      </p>
    </div>
  )
}

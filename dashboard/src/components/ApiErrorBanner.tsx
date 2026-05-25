import { AlertCircle, RefreshCw } from 'lucide-react'
import { useTranslation } from '../i18n/I18nProvider'

interface Props {
  message: string
  onRetry: () => void
}

export function ApiErrorBanner({ message, onRetry }: Props) {
  const { t } = useTranslation()

  return (
    <div className="flex items-center gap-3 border-b border-[#f85149]/30 bg-[#f85149]/10 px-6 py-2.5">
      <AlertCircle className="h-4 w-4 shrink-0 text-[#f85149]" />
      <p className="flex-1 text-sm text-[#f85149]">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="flex items-center gap-1.5 rounded-md border border-[#f85149]/40 px-2.5 py-1 text-xs text-[#f85149] hover:bg-[#f85149]/10"
      >
        <RefreshCw className="h-3 w-3" />
        {t('common.retry')}
      </button>
    </div>
  )
}

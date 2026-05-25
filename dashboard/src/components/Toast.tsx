import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, XCircle } from 'lucide-react'

export type ToastType = 'success' | 'error'

interface ToastState {
  message: string
  type: ToastType
}

export function useToast() {
  const [toast, setToast] = useState<ToastState | null>(null)

  const show = useCallback((message: string, type: ToastType = 'success') => {
    setToast({ message, type })
  }, [])

  useEffect(() => {
    if (!toast) return
    const id = setTimeout(() => setToast(null), 3500)
    return () => clearTimeout(id)
  }, [toast])

  const Toast = toast ? (
    <div
      className={`fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm shadow-lg ${
        toast.type === 'success'
          ? 'border-[#3fb950]/40 bg-[#3fb950]/15 text-[#3fb950]'
          : 'border-[#f85149]/40 bg-[#f85149]/15 text-[#f85149]'
      }`}
    >
      {toast.type === 'success' ? (
        <CheckCircle2 className="h-4 w-4 shrink-0" />
      ) : (
        <XCircle className="h-4 w-4 shrink-0" />
      )}
      {toast.message}
    </div>
  ) : null

  return { show, Toast }
}

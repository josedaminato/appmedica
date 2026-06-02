import { CheckCircle2, XCircle } from "lucide-react"

interface FeedbackBannerProps {
  message: string
  variant?: "success" | "error"
}

export function FeedbackBanner({ message, variant = "success" }: FeedbackBannerProps) {
  const isSuccess = variant === "success"
  return (
    <p
      className={`mb-4 flex items-center gap-2 text-sm rounded-md border px-3 py-2 ${
        isSuccess
          ? "text-emerald-800 dark:text-emerald-200 border-emerald-500/30 bg-emerald-500/10"
          : "text-destructive border-destructive/30 bg-destructive/5"
      }`}
      role="status"
    >
      {isSuccess ? (
        <CheckCircle2 className="h-4 w-4 shrink-0" aria-hidden />
      ) : (
        <XCircle className="h-4 w-4 shrink-0" aria-hidden />
      )}
      {message}
    </p>
  )
}

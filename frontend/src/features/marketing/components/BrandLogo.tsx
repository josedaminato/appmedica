import { cn } from "@/lib/utils"
import { BRAND_LOGOS } from "@/lib/constants"

type Props = {
  variant?: "full" | "mark"
  className?: string
}

/** Logo AppMedica (login, sidebar). */
export function BrandLogo({ variant = "full", className }: Props) {
  const src = variant === "mark" ? BRAND_LOGOS.appmedica.mark : BRAND_LOGOS.appmedica.full

  return (
    <img
      src={src}
      alt="AppMedica"
      className={cn(variant === "mark" ? "h-9 w-9" : "h-10 w-auto max-w-[200px]", className)}
      decoding="async"
    />
  )
}

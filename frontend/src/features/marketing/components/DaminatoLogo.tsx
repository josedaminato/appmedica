import { BRAND_LOGOS } from "@/lib/constants"
import { cn } from "@/lib/utils"

type Props = {
  variant?: "header" | "footer" | "footer-bottom"
  className?: string
}

const srcByVariant = {
  header: BRAND_LOGOS.daminatoweb.isologo,
  footer: BRAND_LOGOS.daminatoweb.isologo,
  "footer-bottom": BRAND_LOGOS.daminatoweb.footer,
} as const

const classByVariant = {
  header: "navbar__logo",
  footer: "footer__logo",
  "footer-bottom": "footer__bottom-logo",
} as const

export function DaminatoLogo({ variant = "header", className }: Props) {
  return (
    <img
      src={srcByVariant[variant]}
      alt="Daminato Web"
      className={cn(classByVariant[variant], className)}
      loading={variant === "header" ? "eager" : "lazy"}
      width={variant === "header" ? 160 : undefined}
      height={variant === "header" ? 64 : undefined}
    />
  )
}

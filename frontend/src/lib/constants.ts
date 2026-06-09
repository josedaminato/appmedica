export const APP_NAME = "AppMedica"
export const TOKEN_KEY = "appmedica_token"

/** Rutas de acceso a la app desde la landing comercial. */
export const APP_LOGIN_PATH = "/login"
export const APP_REGISTER_PATH = "/register"
export const APP_DASHBOARD_PATH = "/inicio"

/** Logos reales (landingpageDaminato). AppMedica usa SVG en login/panel. */
export const BRAND_LOGOS = {
  daminatoweb: {
    isologo: "/logos/daminatoweb-isologo.png",
    footer: "/logos/daminatoweb-footer.png",
  },
  appmedica: {
    full: "/logos/appmedica.svg",
    mark: "/logos/appmedica-mark.svg",
  },
} as const

/** Soporte humano (dueño del producto). */
export const SUPPORT_WHATSAPP_DISPLAY = "+54 9 11 2765-4198"
export const SUPPORT_WHATSAPP_PHONE = "+5491127654198"
export const SUPPORT_EMAIL = "contacto@daminatoweb.com"
export const SUPPORT_WHATSAPP_PREFILL =
  "Hola, necesito ayuda urgente con AppMedica."

/**
 * Precio público de AppMedica en pesos argentinos (ARS).
 * Infra Hostinger KVM 1 (multi-tenant): ~$28.000/mes — varios consultorios en el mismo VPS.
 */
export const PRICING_ARS = {
  appMedicaMonthly: "$25.000",
} as const

/** Servicios de agencia: presupuesto a medida (sin cifra fija en la web). */
export const PRICING_AGENCY_COPY = {
  ads: "Honorarios mensuales + inversión publicitaria",
  web: "Pago único según alcance del sitio",
} as const

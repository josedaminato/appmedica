import { SUPPORT_WHATSAPP_PHONE } from "@/lib/constants"

export const WHATSAPP_BASE_URL = "https://wa.me"

export function generateWhatsAppUrl(message: string) {
  return `${WHATSAPP_BASE_URL}/${SUPPORT_WHATSAPP_PHONE.replace(/\D/g, "")}?text=${encodeURIComponent(message)}`
}

export const WHATSAPP_MESSAGES = {
  DIAGNOSTICO: "Hola, quiero más pacientes para mi consultorio. Vi daminatoweb.com y me gustaría recibir una propuesta.",
  CONTACTO: "Hola, quiero recibir una propuesta para hacer crecer mi consultorio.",
} as const

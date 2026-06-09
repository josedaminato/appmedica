import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthContext"
import { DaminatoLogo } from "@/features/marketing/components/DaminatoLogo"
import { APP_DASHBOARD_PATH, APP_LOGIN_PATH } from "@/lib/constants"
import { generateWhatsAppUrl, WHATSAPP_MESSAGES } from "../utils/constants"
import { scrollToSection } from "../utils/scrollUtils"

const NAV_ITEMS = [
  { id: "servicios", label: "Servicios" },
  { id: "proceso", label: "Proceso" },
  { id: "appmedica", label: "AppMedica" },
  { id: "porque", label: "Por qué yo" },
  { id: "contacto", label: "Contacto" },
  { id: "faq", label: "FAQ" },
] as const

export function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { isAuthenticated } = useAuth()
  const consultorioPath = isAuthenticated ? APP_DASHBOARD_PATH : APP_LOGIN_PATH
  const whatsappUrl = generateWhatsAppUrl(WHATSAPP_MESSAGES.DIAGNOSTICO)

  useEffect(() => {
    document.body.style.overflow = mobileMenuOpen ? "hidden" : ""
    return () => {
      document.body.style.overflow = ""
    }
  }, [mobileMenuOpen])

  function handleSectionClick(sectionId: string) {
    scrollToSection(sectionId)
    setMobileMenuOpen(false)
  }

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white transition-all duration-300 shadow-lg border-b-[3px] border-dw-accent">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16 sm:h-20">
            <Link to="/" className="flex items-center" aria-label="Daminato Web — inicio">
              <DaminatoLogo variant="header" className="h-8 sm:h-12 md:h-16 w-auto" />
            </Link>

            <div className="hidden lg:flex items-center space-x-4 xl:space-x-6">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleSectionClick(item.id)}
                  className="text-dark hover:text-primary transition-colors font-medium text-sm xl:text-base py-2 px-1"
                >
                  {item.label}
                </button>
              ))}
              <Link
                to={consultorioPath}
                className="text-dark hover:text-primary transition-colors font-medium text-sm xl:text-base py-2 px-1 whitespace-nowrap"
              >
                Ir a mi consultorio
              </Link>
              <button
                type="button"
                onClick={() => handleSectionClick("contacto")}
                className="bg-primary text-white px-4 xl:px-6 py-2 rounded-lg hover:bg-primary-dark transition-colors duration-300 font-medium text-sm xl:text-base whitespace-nowrap"
              >
                Quiero más pacientes
              </button>
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                data-event="whatsapp_click"
                data-location="navbar_cta"
                className="border-2 border-primary text-primary px-4 xl:px-6 py-2 rounded-lg hover:bg-primary hover:text-white transition-colors duration-300 font-medium text-sm xl:text-base whitespace-nowrap"
              >
                Contacto
              </a>
            </div>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 text-dark focus:outline-none"
              aria-label={mobileMenuOpen ? "Cerrar menú" : "Abrir menú"}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </nav>

      <div
        className={`fixed inset-0 z-40 lg:hidden transition-transform duration-300 ease-in-out ${
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-hidden={!mobileMenuOpen}
      >
        <div className="fixed inset-0 bg-white">
          <div className="flex flex-col h-full pt-20 pb-6 px-4 overflow-y-auto">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => handleSectionClick(item.id)}
                className="text-left py-4 px-4 text-dark text-lg font-medium border-b border-gray-200 hover:text-primary transition-colors"
              >
                {item.label}
              </button>
            ))}
            <Link
              to={consultorioPath}
              onClick={() => setMobileMenuOpen(false)}
              className="text-left py-4 px-4 text-dark text-lg font-medium border-b border-gray-200 hover:text-primary transition-colors"
            >
              Ir a mi consultorio
            </Link>
            <button
              type="button"
              onClick={() => handleSectionClick("contacto")}
              className="mt-6 mx-4 bg-primary text-white px-6 py-4 rounded-lg hover:bg-primary-dark transition-colors duration-300 font-semibold text-center text-lg"
            >
              Quiero más pacientes
            </button>
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              data-event="whatsapp_click"
              data-location="navbar_mobile_cta"
              className="mt-4 mx-4 border-2 border-primary text-primary px-6 py-4 rounded-lg hover:bg-primary hover:text-white transition-colors duration-300 font-semibold text-center text-lg"
            >
              Contacto
            </a>
          </div>
        </div>
      </div>
    </>
  )
}

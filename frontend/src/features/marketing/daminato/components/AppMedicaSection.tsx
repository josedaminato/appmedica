import { Link } from "react-router-dom"
import { APP_REGISTER_PATH, PRICING_ARS } from "@/lib/constants"
import { scrollToSection } from "../utils/scrollUtils"

const APP_FEATURES = [
  "Agenda con estados de turno (confirmado, asistió, ausente, cancelado)",
  "Gestión de pacientes con historial",
  "Control de obras sociales, prepagas y PAMI",
  "Dashboard de cobros y deudas",
  "Reclamos a obras sociales",
  "Exportación a Excel",
  "Multi-profesional por consultorio",
  "Funciona desde el celular sin instalar nada",
] as const

const SPECIALTIES = ["Médicos clínicos", "Psicólogos", "Nutricionistas", "Odontólogos", "Kinesiólogos", "Traumatólogos"] as const

export function AppMedicaSection() {
  return (
    <section id="appmedica" className="section appmedica" aria-labelledby="appmedica-title">
      <div className="container">
        <header className="section-header fade-in">
          <h2 id="appmedica-title">Menos tiempo administrando. Más tiempo atendiendo pacientes.</h2>
        </header>

        <div className="appmedica__grid">
          <div className="appmedica__text fade-in">
            <p>
              AppMedica centraliza agenda, pacientes, obras sociales y cobros para que puedas enfocarte en lo importante:
              tu práctica profesional.
            </p>
            <p className="appmedica__note font-semibold text-[var(--color-primary)]">
              {PRICING_ARS.appMedicaMonthly}/mes por consultorio · pesos argentinos
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button type="button" className="btn btn--primary btn--lg" onClick={() => scrollToSection("contacto")}>
                Solicitar una demostración
              </button>
              <Link to={APP_REGISTER_PATH} className="btn btn--outline btn--lg text-center">
                Conocer AppMedica
              </Link>
            </div>
          </div>

          <div className="fade-in">
            <ul className="feature-list" aria-label="Funcionalidades de AppMedica">
              {APP_FEATURES.map((item) => (
                <li key={item}>
                  <svg className="feature-list__check" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
            <div className="specialties" aria-label="Especialidades">
              {SPECIALTIES.map((s) => (
                <span key={s} className="specialty-badge">
                  {s}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

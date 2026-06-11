import { APP_NAME, PRICING_AGENCY_COPY, PRICING_ARS } from "@/lib/constants"
import { scrollToSection } from "../utils/scrollUtils"

const SERVICIOS = [
  {
    step: "01",
    title: "Conseguimos pacientes nuevos",
    description:
      "Campañas en Google y Meta orientadas a generar consultas reales para tu especialidad y zona.",
    price: PRICING_AGENCY_COPY.ads,
    cta: "Consultar disponibilidad",
    action: () => scrollToSection("contacto"),
  },
  {
    step: "02",
    title: "Convertimos consultas en turnos",
    description:
      "Diseñamos páginas web profesionales que transmiten confianza y facilitan el contacto con nuevos pacientes.",
    price: PRICING_AGENCY_COPY.web,
    cta: "Ver ejemplos",
    action: () => scrollToSection("contacto"),
  },
  {
    step: "03",
    title: "Organizamos la gestión diaria",
    description:
      `${APP_NAME} organiza agenda, pacientes y obras sociales para que dejes las planillas y te enfoques en atender.`,
    price: `${PRICING_ARS.appMedicaMonthly}/mes por consultorio`,
    cta: `Conocer ${APP_NAME}`,
    action: () => scrollToSection("appmedica"),
  },
] as const

export function Servicios() {
  return (
    <section id="servicios" className="section servicios" aria-labelledby="servicios-title">
      <div className="container">
        <header className="section-header fade-in">
          <h2 id="servicios-title">Cómo ayudamos a tu consultorio a crecer</h2>
          <p>
            Tres soluciones que trabajan juntas para ayudarte a atraer pacientes, convertir consultas en turnos y
            organizar la gestión diaria de tu consultorio. {APP_NAME} en pesos argentinos; captación y web a presupuesto.
          </p>
        </header>

        <div className="services-grid">
          {SERVICIOS.map((item) => (
            <article key={item.step} className="service-card fade-in">
              <span className="service-card__badge">Paso {item.step}</span>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
              <p className="service-card__price">{item.price}</p>
              <button type="button" className="btn btn--outline" onClick={item.action}>
                {item.cta}
              </button>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

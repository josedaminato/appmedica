import { APP_NAME } from "@/lib/constants"

/** Ilustración del hero: consultorio + captación digital (sin foto stock externa). */
export function HeroVisual() {
  return (
    <div className="hero-visual" aria-hidden="true">
      <div className="hero-visual__frame">
        <img
          className="hero-visual__photo"
          src="/images/hero-consultorio.jpg"
          alt=""
          width={640}
          height={480}
          loading="eager"
          decoding="async"
        />
        <div className="hero-visual__card hero-visual__card--top">
          <span className="hero-visual__card-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </span>
          <div>
            <p className="hero-visual__card-label">Agenda del consultorio</p>
            <p className="hero-visual__card-value">Turnos organizados</p>
          </div>
        </div>
        <div className="hero-visual__card hero-visual__card--bottom">
          <span className="hero-visual__card-icon hero-visual__card-icon--accent" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a2 2 0 01-2-2v-1M13 8V6a4 4 0 00-8 0v2" />
            </svg>
          </span>
          <div>
            <p className="hero-visual__card-label">Nuevos contactos</p>
            <p className="hero-visual__card-value">Pacientes por WhatsApp y web</p>
          </div>
        </div>
      </div>
      <div className="hero-visual__chips">
        <span className="hero-visual__chip">Google Ads</span>
        <span className="hero-visual__chip">Web profesional</span>
        <span className="hero-visual__chip">{APP_NAME}</span>
      </div>
    </div>
  )
}

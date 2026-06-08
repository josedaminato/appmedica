import { Link } from "react-router-dom"
import "../landing.css"

const features = [
  {
    title: "Agenda y turnos",
    description:
      "Día a día con duración, modalidad y aviso de solapamiento. Confirmar, asistir, reprogramar y cerrar el turno en pocos clics.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <path d="M16 2v4M8 2v4M3 10h18" />
      </svg>
    ),
  },
  {
    title: "Pacientes",
    description: "Ficha completa, búsqueda y ficha administrativa. Importás tu Excel actual y exportás cuando quieras.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  {
    title: "Cobros y deuda",
    description:
      "Cuánto te deben los particulares y las obras sociales, cobros parciales y registro al instante. Adiós planilla de deudores.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  },
  {
    title: "Obras sociales",
    description: "Reclamos y liquidaciones: facturado, cobrado o rechazado. Ranking por demora para saber cuál te paga peor.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 12l2 2 4-4" />
        <path d="M21 12c0 5-3.5 7.5-8.5 9-5-1.5-8.5-4-8.5-9V5l8.5-3L21 5z" />
      </svg>
    ),
  },
  {
    title: "Reportes y exportación",
    description: "Resumen mensual de turnos, cobros y deuda. Descarga a Excel o CSV para tu contador, listas o respaldos.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="M7 15l4-4 3 3 5-6" />
      </svg>
    ),
  },
  {
    title: "Equipo con roles",
    description: "Dueño, profesional y staff. Cada profesional ve solo su agenda y su cartera; vos ves todo.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="9" cy="7" r="3" />
        <path d="M2 21v-1a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v1" />
        <path d="M19 8v6M22 11h-6" />
      </svg>
    ),
  },
  {
    title: "Recordatorios y calendario",
    description: "Recordatorio por WhatsApp desde la agenda, email opcional y sincronización con Google/Apple Calendar.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" />
      </svg>
    ),
  },
  {
    title: "Seguro y en la nube",
    description: "Cada consultorio ve solo sus datos. Acceso desde cualquier dispositivo, sin instalar nada.",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
] as const

export function LandingPage() {
  return (
    <div className="landing-page">
      <div className="sheet">
        <header className="hero">
          <div className="hero-top">
            <div className="brand">
              <span className="logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="#eafaf5" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 5v14M5 12h14" />
                </svg>
              </span>
              <span>
                AppMedica
                <small>por daminatoweb</small>
              </span>
            </div>
            <nav className="hero-nav" aria-label="Acceso a la app">
              <Link to="/login" className="nav-login">
                Ingresar
              </Link>
              <Link to="/register" className="nav-register">
                Probar gratis
              </Link>
            </nav>
          </div>

          <div className="hero-content">
            <span className="eyebrow">Gestión de consultorios · Argentina</span>
            <h1>
              El consultorio, <em>ordenado</em>. Sin Excel.
            </h1>
            <p className="lede">
              Agenda, pacientes, obras sociales y cobros en un solo lugar. Pensado para consultorios de salud que quieren
              dejar las planillas y ver de un vistazo qué se debe, qué se cobró y qué falta cerrar.
            </p>

            <div className="hero-actions">
              <Link to="/register" className="action-primary">
                Crear mi consultorio
              </Link>
              <Link to="/login" className="action-secondary">
                Ya tengo cuenta
              </Link>
            </div>

            <div className="hero-tags">
              <span className="tag">Agenda inteligente</span>
              <span className="tag">Cobros y deuda</span>
              <span className="tag">Obras sociales</span>
              <span className="tag">Reportes y export Excel</span>
              <span className="tag">Multiusuario por roles</span>
            </div>
          </div>
        </header>

        <main className="body">
          <div className="section-title">Todo lo que necesita el día a día</div>

          <div className="grid">
            {features.map((feature) => (
              <div key={feature.title} className="feature">
                <span className="ic">{feature.icon}</span>
                <div>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="value">
            <div>
              <div className="num">1</div>
              <div className="lbl">Lugar para agenda, cobros y obras sociales</div>
            </div>
            <div>
              <div className="num">0</div>
              <div className="lbl">Planillas de Excel sueltas para mantener</div>
            </div>
            <div>
              <div className="num">3</div>
              <div className="lbl">Roles para trabajar en equipo con orden</div>
            </div>
          </div>
        </main>

        <section className="cta">
          <div>
            <h2>¿Lo probamos en tu consultorio?</h2>
            <p>Registrate en minutos o pedinos una demo en vivo con tus datos.</p>
          </div>
          <div className="contacts">
            <Link to="/register" className="contact contact-register">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M19 8v6M22 11h-6" />
              </svg>
              <span>
                Crear cuenta gratis
                <small>Empezá ahora</small>
              </span>
            </Link>
            <a className="contact" href="https://wa.me/5491127654198" target="_blank" rel="noreferrer">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M.057 24l1.687-6.163a11.867 11.867 0 0 1-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.82 11.82 0 0 1 8.413 3.488 11.82 11.82 0 0 1 3.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 0 1-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.82 9.82 0 0 0 1.504 5.26l-.999 3.648 3.984-1.607zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z" />
              </svg>
              <span>
                +54 9 11 2765-4198
                <small>WhatsApp</small>
              </span>
            </a>
            <a className="contact" href="mailto:contacto@daminatoweb.com">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="m22 7-10 5L2 7" />
              </svg>
              <span>
                contacto@daminatoweb.com
                <small>Email</small>
              </span>
            </a>
          </div>
        </section>

        <footer className="foot">
          <span>
            <strong>AppMedica</strong> — software de gestión para consultorios de salud.
          </span>
          <span>daminatoweb.com</span>
        </footer>
      </div>
    </div>
  )
}

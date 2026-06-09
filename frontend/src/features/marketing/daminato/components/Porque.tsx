const BENEFICIOS = [
  {
    title: "Hablo el idioma de los consultorios",
    description:
      "Trabajo exclusivamente con profesionales de la salud y entiendo cómo funciona la realidad del sector en Argentina.",
    icon: (
      <path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7z" />
    ),
  },
  {
    title: "Mendoza, con mirada nacional",
    description:
      "Conozco obras sociales, prepagas, PAMI y la dinámica real de un consultorio argentino — no hablo como una agencia genérica.",
    icon: (
      <>
        <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
        <circle cx="12" cy="9" r="2.5" />
      </>
    ),
  },
  {
    title: "Resultados que podés revisar",
    description:
      "Sin promesas vacías: reportes claros, números reales y decisiones basadas en lo que está pasando en tu consultorio.",
    icon: (
      <>
        <path d="M3 3v18h18" />
        <path d="M7 16l4-6 4 4 5-8" />
      </>
    ),
  },
] as const

export function Porque() {
  return (
    <section id="porque" className="section porque" aria-labelledby="porque-title">
      <div className="container">
        <header className="section-header fade-in">
          <h2 id="porque-title">Por qué trabajar conmigo</h2>
        </header>
        <div className="porque-grid">
          {BENEFICIOS.map((item) => (
            <article key={item.title} className="porque-item fade-in">
              <svg className="porque-item__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                {item.icon}
              </svg>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

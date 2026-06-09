const DOLORES = [
  {
    icon: "🗓️",
    text: "Tenés semanas llenas y otras con huecos imposibles de cubrir.",
  },
  {
    icon: "💬",
    text: "Contestás WhatsApp todo el día y aun así perdés consultas.",
  },
  {
    icon: "💸",
    text: "No sabés exactamente cuánto facturaste ni cuánto te deben.",
  },
  {
    icon: "📊",
    text: "Seguís usando Excel porque cambiar parece complicado.",
  },
] as const

export function Problema() {
  return (
    <section id="problema" className="section problema" aria-labelledby="problema-title">
      <div className="container">
        <header className="section-header fade-in">
          <h2 id="problema-title">¿Te está pasando esto?</h2>
        </header>
        <div className="cards-row cards-row--4">
          {DOLORES.map((item) => (
            <article key={item.text} className="card fade-in">
              <div className="card__icon" aria-hidden="true">
                {item.icon}
              </div>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

// TODO: Reemplazar con testimonios reales de profesionales de la salud (cita + nombre + especialidad).
const TESTIMONIOS_PLACEHOLDER = [
  {
    quote:
      "Daminato Web nos ayudó a ordenar nuestra estrategia digital y aumentar las consultas.",
    author: "Nombre del profesional",
    role: "Especialidad · Ciudad",
  },
  {
    quote: "TODO: Agregar testimonio real con resultado concreto (ej. más turnos, mejor organización).",
    author: "Nombre del profesional",
    role: "Especialidad · Ciudad",
  },
  {
    quote: "TODO: Agregar testimonio real que refuerce confianza en el proceso de captación.",
    author: "Nombre del profesional",
    role: "Especialidad · Ciudad",
  },
] as const

export function Testimonials() {
  return (
    <section id="testimonios" className="py-16 sm:py-20 md:py-24 border-t border-gray-100 bg-white" aria-labelledby="testimonios-title">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <header className="text-center mb-12 sm:mb-16 fade-in">
          <h2 id="testimonios-title" className="text-2xl sm:text-3xl md:text-4xl font-bold text-dark mb-3 sm:mb-4 px-2">
            Profesionales que ya confiaron en nosotros
          </h2>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {TESTIMONIOS_PLACEHOLDER.map((item, index) => (
            <blockquote
              key={index}
              className="fade-in bg-gray-50/50 p-6 sm:p-8 rounded-xl border border-gray-100 hover:border-gray-200 transition-all duration-300 flex flex-col"
            >
              <p className="text-base sm:text-lg text-gray-700 leading-relaxed flex-1 mb-6">&ldquo;{item.quote}&rdquo;</p>
              <footer>
                <cite className="not-italic font-semibold text-dark block">{item.author}</cite>
                <p className="text-sm text-gray-500 mt-1">{item.role}</p>
              </footer>
            </blockquote>
          ))}
        </div>
      </div>
    </section>
  )
}

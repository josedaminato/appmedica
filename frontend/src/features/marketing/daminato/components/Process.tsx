const STEPS = [
  {
    number: "01",
    title: "Diagnóstico",
    description: "Revisión de la situación actual: web, presencia en buscadores, captación actual.",
  },
  {
    number: "02",
    title: "Plan",
    description: "Plan concreto: qué se hace, en qué orden y qué se mide.",
  },
  {
    number: "03",
    title: "Implementación + optimización",
    description: "Web, campañas activas y seguimiento con datos. Ajustes según resultados.",
  },
] as const

export function Process() {
  return (
    <section id="proceso" className="py-16 sm:py-20 md:py-24 border-t border-gray-100 bg-[#f4f4f5]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12 sm:mb-16 fade-in">
          <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-dark mb-3 sm:mb-4 px-2">
            Cómo es el <span className="text-primary">proceso</span>
          </h2>
          <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-2xl mx-auto px-4">
            Diagnóstico, plan e implementación.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8">
          {STEPS.map((step, index) => (
            <div key={step.number} className="fade-in relative">
              <div className="rounded-xl p-6 sm:p-8 transition-opacity duration-300 hover:opacity-95 bg-primary">
                <div className="text-3xl sm:text-4xl md:text-5xl font-bold opacity-20 mb-3 sm:mb-4 text-white">{step.number}</div>
                <h3 className="text-lg sm:text-xl md:text-2xl font-semibold mb-3 sm:mb-4 text-white">{step.title}</h3>
                <p className="text-sm sm:text-base leading-relaxed text-white/80">{step.description}</p>
              </div>
              {index < STEPS.length - 1 && (
                <div className="hidden md:block absolute top-1/2 -right-4 transform -translate-y-1/2 z-10" aria-hidden="true">
                  <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

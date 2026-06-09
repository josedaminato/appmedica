const PASOS = [
  { number: "01", title: "Web optimizada", description: "Presencia clara, profesional y orientada a contacto." },
  { number: "02", title: "Campañas en Google", description: "Aparición cuando las personas ya están buscando el servicio." },
  { number: "03", title: "Medición real", description: "Datos concretos para entender qué funciona y qué no." },
] as const

export function Solucion() {
  return (
    <section id="solucion" className="py-16 sm:py-20 md:py-24 bg-white border-t border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14 sm:mb-16 fade-in">
          <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-dark mb-4 px-2">Enfoque</h2>
          <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
            No trabajo acciones aisladas. Trabajo un sistema integrado.
          </p>
        </div>
        <div className="relative">
          <div className="hidden md:block absolute top-8 left-[10%] right-[10%] h-0.5 bg-gray-200" aria-hidden="true" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-4">
            {PASOS.map((step) => (
              <div key={step.number} className="fade-in relative flex flex-col items-center md:items-start">
                <div className="w-16 h-16 rounded-full flex items-center justify-center text-white font-bold text-lg mb-4 flex-shrink-0 bg-primary">
                  {step.number}
                </div>
                <div className="text-center md:text-left">
                  <h3 className="text-lg sm:text-xl md:text-2xl font-semibold text-dark mb-2 md:mb-3">{step.title}</h3>
                  <p className="text-sm sm:text-base text-gray-600 leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

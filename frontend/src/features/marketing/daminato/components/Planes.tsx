const MODALIDADES = [
  {
    title: "Piloto 30 días",
    description: "Implementamos el sistema y analizamos datos reales durante el primer mes.",
    tagline: "Ideal para evaluar con números antes de decidir continuidad.",
  },
  {
    title: "Trabajo mensual",
    description: "Optimización continua, seguimiento y ajustes basados en resultados.",
    tagline: "Para quienes buscan captación sostenida y medible.",
  },
] as const

export function Planes() {
  return (
    <section id="planes" className="py-16 sm:py-20 md:py-24 bg-white border-t border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12 sm:mb-16 fade-in">
          <p className="text-sm sm:text-base text-gray-500 max-w-xl mx-auto mb-4 px-4">
            No trabajamos con contratos largos obligatorios. Primero se valida con datos.
          </p>
          <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-dark mb-3 sm:mb-4 px-2">
            Modalidades de trabajo
          </h2>
          <p className="text-base sm:text-lg md:text-xl text-gray-600 max-w-2xl mx-auto px-4">
            Dos formas de empezar. El diagnóstico inicial es sin costo.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 max-w-4xl mx-auto">
          {MODALIDADES.map((item) => (
            <div
              key={item.title}
              className="fade-in bg-gray-50/50 p-6 sm:p-8 rounded-xl border border-gray-100 hover:border-gray-200 transition-all duration-300"
            >
              <h3 className="text-lg sm:text-xl font-semibold text-dark mb-3">{item.title}</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed mb-2">{item.description}</p>
              <p className="text-sm text-gray-500 leading-relaxed">{item.tagline}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

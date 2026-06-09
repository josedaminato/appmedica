import { scrollToSection } from "../utils/scrollUtils"

const METRICAS = [
  { valor: "17.300", label: "Clics totales" },
  { valor: "394.000", label: "Impresiones" },
  { valor: "2.300", label: "Clics a WhatsApp" },
  { valor: "$630.000", label: "Inversión en ads" },
] as const

export function CasoReal() {
  return (
    <section id="caso-real" className="py-16 sm:py-20 md:py-24 border-t border-gray-100 bg-[#f4f4f5]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10 sm:mb-12 fade-in">
          <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-bold text-dark mb-3 sm:mb-4 px-2">
            Caso real — Clínica dental
          </h2>
        </div>

        <div className="fade-in space-y-8 sm:space-y-10">
          <p className="text-base sm:text-lg text-gray-700 leading-relaxed">
            La clínica necesitaba aumentar consultas y no tenía visibilidad clara en Google.
          </p>
          <p className="text-base sm:text-lg text-gray-700 leading-relaxed">
            Se implementó un sistema de captación con web optimizada, campañas y medición de contactos.
          </p>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-5">
            {METRICAS.map((m) => (
              <div
                key={m.label}
                className="bg-gray-50/80 rounded-lg p-5 sm:p-6 border border-gray-100 text-center overflow-hidden min-w-0 transition-colors duration-300 hover:bg-gray-50"
              >
                <p className="text-lg sm:text-xl md:text-2xl font-bold tabular-nums font-mono text-primary">{m.valor}</p>
                <p className="text-xs sm:text-sm text-gray-600 font-medium uppercase tracking-wide">{m.label}</p>
              </div>
            ))}
          </div>

          <div className="space-y-3 text-base sm:text-lg text-gray-700 leading-relaxed">
            <p>Los contactos representan personas reales que iniciaron conversación.</p>
            <p>La conversión final depende del consultorio.</p>
            <p>El sistema permitió generar demanda y medirla con claridad.</p>
          </div>

          <div className="text-center pt-2">
            <button
              type="button"
              onClick={() => scrollToSection("proceso")}
              className="inline-flex items-center gap-2 font-semibold hover:opacity-80 transition-colors duration-300 text-base sm:text-lg text-primary"
            >
              Ver proceso
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

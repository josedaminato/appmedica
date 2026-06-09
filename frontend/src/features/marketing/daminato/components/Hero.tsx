import { scrollToSection } from "../utils/scrollUtils"

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16 sm:pt-20 bg-white">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 sm:py-24 md:py-32 relative z-20">
        <div className="fade-in text-center">
          <h1 className="animate-hero-title text-2xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-6xl font-bold text-dark mb-5 sm:mb-6 leading-tight px-2 sm:px-0 break-words">
            Conseguí más pacientes para tu consultorio sin depender del boca en boca.
          </h1>
          <p className="animate-hero-subtitle text-base sm:text-lg md:text-xl text-gray-600 mb-8 sm:mb-10 leading-relaxed px-2 sm:px-0 max-w-2xl mx-auto">
            Implementamos campañas, páginas web y herramientas para que tu agenda deje de tener espacios vacíos.
          </p>
          <div className="animate-hero-buttons flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button
              type="button"
              onClick={() => scrollToSection("contacto")}
              className="inline-flex bg-primary text-white px-6 sm:px-8 py-3 sm:py-4 rounded-lg text-base sm:text-lg font-medium hover:bg-primary-dark transition-all duration-300 w-full sm:w-auto text-center min-h-[48px] items-center justify-center"
            >
              Quiero más pacientes
            </button>
            <button
              type="button"
              onClick={() => scrollToSection("servicios")}
              className="inline-flex border-2 border-primary text-primary px-6 sm:px-8 py-3 sm:py-4 rounded-lg text-base sm:text-lg font-medium hover:bg-primary hover:text-white transition-all duration-300 w-full sm:w-auto text-center min-h-[48px] items-center justify-center"
            >
              Ver cómo funciona
            </button>
          </div>
        </div>
      </div>

      <div className="absolute bottom-6 sm:bottom-10 left-1/2 transform -translate-x-1/2 opacity-60 hidden sm:block" aria-hidden="true">
        <svg className="w-5 h-5 sm:w-6 sm:h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </section>
  )
}

const FAQS = [
  {
    pregunta: "¿Ya tengo a alguien que me hace la web o el marketing. ¿Por qué cambiar?",
    respuesta:
      "Si te está funcionando y tenés datos claros de cuántas consultas llegan, perfecto. El cambio tiene sentido cuando no sabés qué está pasando, no ves resultados o querés un sistema integrado (web + ads + medición) en un solo lugar.",
  },
  {
    pregunta: "¿Garantizás pacientes o consultas?",
    respuesta:
      "No. Trabajamos con datos: clics, impresiones, contactos a WhatsApp. La conversión a paciente depende del consultorio.",
  },
  {
    pregunta: "¿Cuánto tarda en verse algo?",
    respuesta:
      "Depende del nicho y la competencia. En general, en 2 a 4 semanas hay datos concretos. Las campañas se optimizan con el tiempo.",
  },
  {
    pregunta: "¿Cómo medís los resultados?",
    respuesta: "Impresiones, clics y costo en Google Ads. Clics a WhatsApp o formulario en la web. Reportes con datos concretos.",
  },
  {
    pregunta: "¿Trabajás solo con odontólogos?",
    respuesta:
      "El foco principal es salud: odontólogos, consultorios, clínicas. Pero si tu actividad profesional tiene un perfil similar (servicios locales, consultas por turno), podemos evaluarlo en el diagnóstico.",
  },
] as const

export function FAQ() {
  return (
    <section id="faq" className="py-16 sm:py-20 md:py-24 bg-white border-t border-gray-100">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12 sm:mb-16 fade-in">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-dark mb-3 sm:mb-4 px-2">Preguntas frecuentes</h2>
          <p className="text-base sm:text-lg text-gray-600">Preguntas frecuentes.</p>
        </div>
        <div className="space-y-6">
          {FAQS.map((faq) => (
            <div
              key={faq.pregunta}
              className="fade-in bg-white p-6 sm:p-8 rounded-xl border border-gray-100 hover:border-gray-200 transition-all duration-300"
            >
              <h3 className="text-base sm:text-lg font-semibold text-dark mb-3">{faq.pregunta}</h3>
              <p className="text-sm sm:text-base text-gray-600 leading-relaxed">{faq.respuesta}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

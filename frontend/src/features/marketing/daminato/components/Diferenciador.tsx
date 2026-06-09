const PARRAFOS = [
  "No prometo pacientes garantizados. Prometo claridad en el proceso.",
  "Mi trabajo es generar y medir oportunidades de contacto.",
  "La conversión final depende del funcionamiento interno del consultorio.",
] as const

export function Diferenciador() {
  return (
    <section id="diferenciador" className="py-16 sm:py-20 md:py-24 bg-white border-t border-gray-100">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="fade-in">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-dark mb-6 sm:mb-8">Criterio de trabajo</h2>
          <div className="space-y-4">
            {PARRAFOS.map((texto) => (
              <p
                key={texto}
                className="rounded-lg py-3 text-[1.15rem] border-l-4 border-dw-accent bg-[#f0faf5] pl-5"
              >
                {texto}
              </p>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

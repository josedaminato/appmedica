import { useState } from "react"
import { generateWhatsAppUrl, WHATSAPP_MESSAGES } from "../utils/constants"

export function Contact() {
  const [formData, setFormData] = useState({
    nombre: "",
    especialidad: "",
    ciudad: "",
    whatsapp: "",
    mejora: "",
  })

  const whatsappUrl = generateWhatsAppUrl(WHATSAPP_MESSAGES.DIAGNOSTICO)

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  function buildWhatsAppMessage() {
    const parts: string[] = [WHATSAPP_MESSAGES.DIAGNOSTICO]
    if (formData.nombre) parts.push(`\nNombre: ${formData.nombre}`)
    if (formData.especialidad) parts.push(`\nEspecialidad: ${formData.especialidad}`)
    if (formData.ciudad) parts.push(`\nCiudad: ${formData.ciudad}`)
    if (formData.whatsapp) parts.push(`\nWhatsApp: ${formData.whatsapp}`)
    if (formData.mejora) parts.push(`\nQué me gustaría mejorar: ${formData.mejora}`)
    return parts.join("")
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    window.open(generateWhatsAppUrl(buildWhatsAppMessage()), "_blank", "noopener,noreferrer")
  }

  const inputClass =
    "w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-colors duration-200"

  return (
    <section id="contacto" className="py-16 sm:py-20 md:py-24 border-t border-gray-100 bg-[#f4f4f5]">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10 sm:mb-12 fade-in">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold text-dark mb-3 sm:mb-4">
            Revisemos juntos cómo hacer crecer tu consultorio
          </h2>
          <p className="text-base sm:text-lg text-gray-600 max-w-xl mx-auto">
            Completá el formulario y te voy a decir cuál es la estrategia más conveniente para tu caso, incluso si hoy no
            necesitás trabajar conmigo.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="fade-in space-y-4 sm:space-y-5">
          <div>
            <label htmlFor="nombre" className="block text-sm font-medium text-dark mb-1">
              Nombre
            </label>
            <input type="text" id="nombre" name="nombre" value={formData.nombre} onChange={handleChange} placeholder="Tu nombre" className={inputClass} />
          </div>
          <div>
            <label htmlFor="especialidad" className="block text-sm font-medium text-dark mb-1">
              Especialidad
            </label>
            <input
              type="text"
              id="especialidad"
              name="especialidad"
              value={formData.especialidad}
              onChange={handleChange}
              placeholder="Ej: Odontología, Clínica general"
              className={inputClass}
            />
          </div>
          <div>
            <label htmlFor="ciudad" className="block text-sm font-medium text-dark mb-1">
              Ciudad
            </label>
            <input type="text" id="ciudad" name="ciudad" value={formData.ciudad} onChange={handleChange} placeholder="Ej: Mendoza, Buenos Aires" className={inputClass} />
          </div>
          <div>
            <label htmlFor="whatsapp" className="block text-sm font-medium text-dark mb-1">
              WhatsApp
            </label>
            <input type="tel" id="whatsapp" name="whatsapp" value={formData.whatsapp} onChange={handleChange} placeholder="Ej: 261 123 4567" className={inputClass} />
          </div>
          <div>
            <label htmlFor="mejora" className="block text-sm font-medium text-dark mb-1">
              ¿Qué te gustaría mejorar?
            </label>
            <textarea
              id="mejora"
              name="mejora"
              value={formData.mejora}
              onChange={handleChange}
              rows={3}
              placeholder="Ej: Más consultas, ordenar la captación, medir resultados..."
              className={`${inputClass} resize-none`}
            />
          </div>
          <button
            type="submit"
            className="w-full flex items-center justify-center gap-2 bg-[#25D366] text-white px-6 py-4 rounded-lg text-base sm:text-lg font-semibold hover:bg-[#20BA5A] transition-all duration-300 min-h-[48px]"
            data-event="whatsapp_click"
            data-location="form_cta"
          >
            <svg className="w-5 h-5 sm:w-6 sm:h-6" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z" />
            </svg>
            Quiero recibir una propuesta
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          O por WhatsApp:{" "}
          <a
            href={whatsappUrl}
            target="_blank"
            rel="noopener noreferrer"
            data-event="whatsapp_click"
            data-location="contacto_directo"
            className="text-primary font-semibold hover:underline break-all"
          >
            escribir aquí
          </a>
        </p>
      </div>
    </section>
  )
}

import { APP_NAME, PROFILE_LINKS } from "@/lib/constants"

const LINKS = [
  { href: PROFILE_LINKS.linkedin, label: "LinkedIn" },
  { href: PROFILE_LINKS.appMedicaRepo, label: `${APP_NAME} en GitHub` },
] as const

export function SobreMi() {
  return (
    <section id="sobre" className="py-16 sm:py-20 md:py-24 bg-white border-t border-gray-100 scroll-mt-24" aria-labelledby="sobre-title">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="fade-in">
          <h2 id="sobre-title" className="text-2xl sm:text-3xl md:text-4xl font-bold text-dark mb-4">
            Quién está detrás
          </h2>
          <p className="text-base sm:text-lg text-gray-600 leading-relaxed mb-4">
            Creé Daminato Web y desarrollé {APP_NAME}. Daminato Web es el trabajo de captación para consultorios:
            sitios, campañas y medición. {APP_NAME} es el software que armé para ordenar agenda, pacientes y reportes
            en el mismo consultorio.
          </p>
          <p className="text-base sm:text-lg text-gray-600 leading-relaxed mb-6">
            Si estás evaluando mi perfil, el producto y el código están públicos.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            {LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center min-h-[48px] px-5 py-3 rounded-lg border-2 border-primary text-primary font-medium hover:bg-primary hover:text-white transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

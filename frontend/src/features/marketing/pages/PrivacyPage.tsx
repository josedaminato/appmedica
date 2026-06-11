import { Link } from "react-router-dom"
import { DaminatoLogo } from "@/features/marketing/components/DaminatoLogo"
import { SUPPORT_EMAIL } from "@/lib/constants"

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-white text-[#1e293b]">
      <header className="border-b px-4 py-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <Link to="/" aria-label="Volver al inicio">
            <DaminatoLogo variant="header" className="h-10 w-auto" />
          </Link>
          <Link to="/" className="text-sm text-[#1a5c4a] hover:underline">
            Volver al inicio
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-10 prose prose-slate">
        <h1>Política de privacidad</h1>
        <p className="text-sm text-gray-600">Última actualización: junio 2026</p>
        <p>
          AppMedica y Daminato Web tratan datos de consultorios y pacientes con fines exclusivamente administrativos
          (agenda, pagos registrados, obras sociales). No reemplaza historia clínica ni diagnóstico médico.
        </p>
        <h2>Qué datos recopilamos</h2>
        <ul>
          <li>Datos del consultorio y usuarios (nombre, email, rol).</li>
          <li>Datos administrativos de pacientes cargados por el profesional (nombre, DNI, contacto, obra social).</li>
          <li>Información de turnos, pagos registrados y reclamos a obras sociales.</li>
        </ul>
        <h2>Cómo los usamos</h2>
        <p>Para operar el software contratado, dar soporte y mejorar el servicio. No vendemos datos a terceros.</p>
        <h2>Seguridad y conservación</h2>
        <p>
          Los datos se alojan en servidores con acceso restringido. El consultorio es responsable de la veracidad de la
          información que carga y del uso conforme a la normativa argentina aplicable (Ley 25.326 y disposiciones del
          sector salud).
        </p>
        <h2>Contacto</h2>
        <p>
          Consultas sobre privacidad: <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
        </p>
      </main>
    </div>
  )
}

import { Link } from "react-router-dom"
import { DaminatoLogo } from "@/features/marketing/components/DaminatoLogo"
import { APP_NAME, SUPPORT_EMAIL } from "@/lib/constants"

export function TermsPage() {
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
        <h1>Términos de uso — {APP_NAME}</h1>
        <p className="text-sm text-gray-600">Última actualización: junio 2026</p>
        <p>
          Al crear una cuenta en {APP_NAME} aceptás estos términos. El servicio es un sistema de gestión administrativa
          para consultorios de salud en Argentina.
        </p>
        <h2>Uso del servicio</h2>
        <ul>
          <li>Debés usar la plataforma solo para fines lícitos y profesionales.</li>
          <li>Sos responsable de las credenciales de acceso de tu equipo.</li>
          <li>Los datos de pacientes los cargás y administrás bajo tu responsabilidad profesional.</li>
        </ul>
        <h2>Alcance del producto</h2>
        <p>
          {APP_NAME} no es historia clínica electrónica ni dispositivo médico. No garantiza resultados de captación de
          pacientes ni recordatorios automáticos salvo que estén contratados y configurados expresamente.
        </p>
        <h2>Pago y suspensión</h2>
        <p>
          Los precios publicados en la web están expresados en pesos argentinos (ARS). El servicio se presta según el
          acuerdo comercial con Daminato Web. Podemos suspender el acceso por falta de pago o uso indebido, previa
          comunicación cuando sea posible.
        </p>
        <h2>Contacto</h2>
        <p>
          <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
        </p>
      </main>
    </div>
  )
}

import { AppMedicaSection } from "../daminato/components/AppMedicaSection"
import { Contact } from "../daminato/components/Contact"
import { FAQ } from "../daminato/components/FAQ"
import { Footer } from "../daminato/components/Footer"
import { Hero } from "../daminato/components/Hero"
import { Navbar } from "../daminato/components/Navbar"
import { Planes } from "../daminato/components/Planes"
import { Problema } from "../daminato/components/Problema"
import { Process } from "../daminato/components/Process"
import { Servicios } from "../daminato/components/Servicios"
import { WhatsAppFloat } from "../daminato/components/WhatsAppFloat"
import { useDaminatoLanding } from "../hooks/useDaminatoLanding"
import "../daminato-marketing.css"
import "../daminato-landing.css"

export function LandingPage() {
  useDaminatoLanding()

  return (
    <div className="daminato-landing min-w-0 overflow-x-hidden">
      <a href="#main" className="sr-only">
        Saltar al contenido principal
      </a>

      <Navbar />

      <main id="main">
        <Hero />
        <Problema />
        <Servicios />
        <Process />
        <Planes />
        <AppMedicaSection />
        <Contact />
        <FAQ />
      </main>

      <Footer />
      <WhatsAppFloat />
    </div>
  )
}

import { useEffect } from "react"

export function useDaminatoLanding() {
  useEffect(() => {
    document.body.classList.add("daminato-landing-body")

    const fadeEls = document.querySelectorAll(".daminato-landing .fade-in")
    let observer: IntersectionObserver | undefined

    if (fadeEls.length) {
      if ("IntersectionObserver" in window) {
        observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                entry.target.classList.add("visible", "is-visible")
                observer?.unobserve(entry.target)
              }
            })
          },
          { rootMargin: "0px 0px -40px 0px", threshold: 0.08 },
        )
        fadeEls.forEach((el) => observer?.observe(el))
      } else {
        fadeEls.forEach((el) => el.classList.add("visible", "is-visible"))
      }
    }

    const handleWhatsAppClick = (e: Event) => {
      const target = (e.target as HTMLElement).closest("[data-event='whatsapp_click']")
      if (!target) return
      const location = target.getAttribute("data-location") || "unknown"
      const gtag = (window as Window & { gtag?: (...args: unknown[]) => void }).gtag
      if (typeof gtag === "function") {
        gtag("event", "whatsapp_click", { location })
      }
      window.dispatchEvent(new CustomEvent("whatsapp_click", { detail: { location } }))
    }
    document.addEventListener("click", handleWhatsAppClick)

    return () => {
      observer?.disconnect()
      document.removeEventListener("click", handleWhatsAppClick)
      document.body.style.overflow = ""
      document.body.classList.remove("daminato-landing-body")
    }
  }, [])
}

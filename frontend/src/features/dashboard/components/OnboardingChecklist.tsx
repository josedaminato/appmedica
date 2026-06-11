import { Link } from "react-router-dom"
import { CheckCircle2, Circle } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type Step = {
  id: string
  label: string
  done: boolean
  href: string
  cta: string
}

type Props = {
  steps: Step[]
}

export function OnboardingChecklist({ steps }: Props) {
  const pending = steps.filter((s) => !s.done)
  if (pending.length === 0) return null

  const next = pending[0]

  return (
    <Card className="mb-8 border-primary/20 bg-primary/5">
      <CardHeader>
        <CardTitle className="text-base">Primeros pasos en tu consultorio</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          En 15 minutos tenés agenda y pacientes organizados. Si ya tenés una planilla, importalos desde Pacientes.
        </p>
        <ul className="space-y-2">
          {steps.map((step) => (
            <li key={step.id} className="flex items-start gap-2 text-sm">
              {step.done ? (
                <CheckCircle2 className="h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
              ) : (
                <Circle className="h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />
              )}
              <span className={cn(step.done && "text-muted-foreground line-through")}>{step.label}</span>
            </li>
          ))}
        </ul>
        <Button asChild>
          <Link to={next.href}>{next.cta}</Link>
        </Button>
      </CardContent>
    </Card>
  )
}

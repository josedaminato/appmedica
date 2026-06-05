import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { DURATION_PRESETS } from "@/lib/appointment-schedule"
import { cn } from "@/lib/utils"

interface DurationPickerProps {
  value: number
  onChange: (minutes: number) => void
  endPreview?: string
  label?: string
  hideEndPreview?: boolean
}

export function DurationPicker({
  value,
  onChange,
  endPreview,
  label = "Duración de este turno",
  hideEndPreview = false,
}: DurationPickerProps) {
  const presetActive = DURATION_PRESETS.includes(value as (typeof DURATION_PRESETS)[number])

  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-2">
        {DURATION_PRESETS.map((mins) => (
          <Button
            key={mins}
            type="button"
            size="sm"
            variant={value === mins ? "default" : "outline"}
            onClick={() => onChange(mins)}
          >
            {mins} min
          </Button>
        ))}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground shrink-0">Otra:</span>
        <Input
          type="number"
          min={5}
          max={240}
          step={5}
          className={cn("w-24", presetActive && "text-muted-foreground")}
          value={value}
          onChange={(e) => onChange(Math.max(5, Number(e.target.value) || 5))}
        />
        <span className="text-xs text-muted-foreground">minutos</span>
      </div>
      {!hideEndPreview && endPreview && (
        <p className="text-sm text-muted-foreground">
          Termina a las <span className="font-medium text-foreground">{endPreview}</span>
        </p>
      )}
    </div>
  )
}

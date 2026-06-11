import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface AddPaymentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  patientName?: string
  onSubmit: (amount: number, method: string) => Promise<void>
  loading?: boolean
}

export function AddPaymentDialog({
  open,
  onOpenChange,
  patientName,
  onSubmit,
  loading,
}: AddPaymentDialogProps) {
  const [amount, setAmount] = useState("")
  const [method, setMethod] = useState("cash")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    await onSubmit(Number(amount), method)
    setAmount("")
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Registrar cobro</DialogTitle>
        </DialogHeader>
        {patientName && <p className="text-sm text-muted-foreground -mt-2">{patientName}</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>Monto ($)</Label>
            <Input type="number" min={1} value={amount} onChange={(e) => setAmount(e.target.value)} required autoFocus />
          </div>
          <div className="space-y-2">
            <Label>Método</Label>
            <Select value={method} onValueChange={setMethod}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="cash">Efectivo</SelectItem>
                <SelectItem value="transfer">Transferencia</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Guardando..." : "Registrar"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

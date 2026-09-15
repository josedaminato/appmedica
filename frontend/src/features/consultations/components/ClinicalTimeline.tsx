import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { formatDate } from "@/lib/format"
import type { ConsultationListItem } from "@/types/api"
import {
  consultationKind,
  consultationPath,
  groupClinicalTimeline,
  timelineSortKey,
} from "../consultationPresentation"

function kindLabel(item: ConsultationListItem): string {
  const kind = consultationKind(item)
  if (kind === "note") return "Nota clínica"
  if (kind === "amendment") return "Corrección"
  return "Consulta"
}

function entryDate(item: ConsultationListItem): string {
  return formatDate(timelineSortKey(item))
}

export function ClinicalTimeline({ items }: { items: ConsultationListItem[] }) {
  const entries = groupClinicalTimeline(items)
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">Sin consultas registradas</p>
  }

  return (
    <ul className="space-y-4">
      {entries.map(({ primary, amendments }) => (
        <li key={primary.id} className="border-b pb-4 last:border-0 last:pb-0">
          <TimelineRow item={primary} />
          {amendments.map((amendment) => (
            <div key={amendment.id} className="mt-3 ml-4 border-l-2 border-muted pl-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                Corrección — {entryDate(amendment)}
              </p>
              {amendment.amend_reason && (
                <p className="text-sm text-muted-foreground mb-1">{amendment.amend_reason}</p>
              )}
              <TimelineRow item={amendment} nested />
            </div>
          ))}
        </li>
      ))}
    </ul>
  )
}

function TimelineRow({ item, nested }: { item: ConsultationListItem; nested?: boolean }) {
  const canOpen = item.status === "finalized" || item.status === "draft"
  return (
    <div className="flex justify-between items-start gap-3">
      <div>
        {!nested && (
          <p className="text-sm font-medium">
            {entryDate(item)}
            {" · "}
            {kindLabel(item)}
            {item.status === "draft" ? " · Borrador" : ""}
          </p>
        )}
        {item.professional_name && (
          <p className="text-xs text-muted-foreground">{item.professional_name}</p>
        )}
        <p className="text-sm">{item.diagnosis || item.reason || item.evolution || "—"}</p>
      </div>
      {canOpen && (
        <Button variant="ghost" size="sm" asChild>
          <Link to={consultationPath(item)}>
            {item.status === "draft" ? "Continuar" : "Ver"}
          </Link>
        </Button>
      )}
    </div>
  )
}

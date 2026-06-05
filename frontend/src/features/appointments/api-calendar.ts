import { apiRequest } from "@/lib/api-client"

export type CalendarFeedInfo = {
  feed_url: string
  webcal_url: string
  scope: "professional" | "organization"
  scope_label: string
}

export function getCalendarFeed(): Promise<CalendarFeedInfo> {
  return apiRequest<CalendarFeedInfo>("/calendar/feed")
}

export function regenerateCalendarFeed(): Promise<CalendarFeedInfo> {
  return apiRequest<CalendarFeedInfo>("/calendar/feed/regenerate", { method: "POST" })
}

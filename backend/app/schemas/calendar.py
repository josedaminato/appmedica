from pydantic import BaseModel, Field


class CalendarFeedResponse(BaseModel):
    feed_url: str
    webcal_url: str
    scope: str = Field(description="professional | organization")
    scope_label: str

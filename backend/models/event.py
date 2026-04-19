"""Pydantic models for Event."""
from pydantic import BaseModel
from typing import Optional, List


class EventBase(BaseModel):
    entity_id: str
    event_type: str  # filing | insider_sale | acquisition | news
    headline: str
    amount: Optional[float] = None
    currency: Optional[str] = "USD"
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    occurred_at: Optional[str] = None


class EventCreate(EventBase):
    pass


class Event(EventBase):
    id: str
    ingested_at: str
    plain_english: Optional[str] = None
    market_impact: Optional[str] = None
    invest_signal: Optional[str] = None
    for_you: Optional[str] = None
    sector_tags: Optional[List[str]] = None
    enriched_at: Optional[str] = None
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    entity_sector: Optional[str] = None

    class Config:
        from_attributes = True

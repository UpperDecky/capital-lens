"""Pydantic models for Entity."""
from pydantic import BaseModel
from typing import Optional


class EntityBase(BaseModel):
    name: str
    type: str  # company | individual
    sector: str
    net_worth: Optional[float] = None
    description: Optional[str] = None


class EntityCreate(EntityBase):
    pass


class Entity(EntityBase):
    id: str
    created_at: str

    class Config:
        from_attributes = True

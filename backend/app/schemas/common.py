"""Shared API response models."""

from pydantic import BaseModel
from typing import Any, Optional


class ErrorResponse(BaseModel):
    error: str
    code: str
    detail: Optional[Any] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    features: int
    layers: list[str]

"""Pydantic schemas for coin resolver endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ResolveCoinRequest(BaseModel):
    text: str


class ResolveCoinResponse(BaseModel):
    coin: str | None
    status: Literal["supported", "unsupported", "ambiguous", "not_found", "error"]
    method: str
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float
    llm_used: bool
    debug_trace: list[dict[str, Any]] = Field(default_factory=list)
    gemini_key_loaded: bool = False
    gemini_client_available: bool = False


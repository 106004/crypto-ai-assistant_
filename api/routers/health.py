"""Health check router."""

from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get("/health", name="health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
def root_health_check() -> dict[str, str]:
    return {"status": "ok"}

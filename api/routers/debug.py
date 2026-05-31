"""Debug router for inspecting registered FastAPI routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.routing import APIRoute


router = APIRouter(prefix="/debug", tags=["debug"])
_EXCLUDED_PATHS = {"/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect"}


def list_registered_routes(app) -> list[dict[str, object]]:
    """Return a compact list of app routes for debugging."""

    routes: list[dict[str, object]] = []
    for route in getattr(app, "routes", []):
        if not isinstance(route, APIRoute):
            continue
        if route.path in _EXCLUDED_PATHS:
            continue

        methods = sorted(method for method in (route.methods or set()) if method not in {"HEAD", "OPTIONS"})
        routes.append(
            {
                "path": route.path,
                "methods": methods,
                "name": route.name,
            }
        )

    return routes


@router.get("/routes")
def debug_routes(request: Request) -> dict[str, list[dict[str, object]]]:
    return {"routes": list_registered_routes(request.app)}


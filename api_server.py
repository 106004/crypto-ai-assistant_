"""FastAPI app assembly for the coin resolver API."""

from __future__ import annotations

from fastapi import FastAPI

from api.routers.coin import router as coin_router
from api.routers.health import router as health_router


app = FastAPI(title="Crypto Coin Resolver API")
app.include_router(health_router)
app.include_router(coin_router)

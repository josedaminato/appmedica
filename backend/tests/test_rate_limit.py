"""Verifica el rate limiting (anti fuerza bruta) y su respuesta 429."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.rate_limit import (
    limiter,
    login_limit,
    password_reset_limit,
    register_limit,
)


def _build_probe_app() -> FastAPI:
    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"error": {"code": "RATE_LIMITED", "message": "Demasiados intentos."}},
        )

    @app.post("/probe-rate-limit")
    @limiter.limit("3/minute")
    def probe(request: Request) -> dict:
        return {"ok": True}

    return app


def test_blocks_after_limit_and_returns_429_envelope():
    limiter.enabled = True
    client = TestClient(_build_probe_app())

    for _ in range(3):
        assert client.post("/probe-rate-limit").status_code == 200

    blocked = client.post("/probe-rate-limit")
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["error"]["code"] == "RATE_LIMITED"


def test_limit_config_reads_settings():
    settings = get_settings()
    assert login_limit() == settings.rate_limit_login
    assert register_limit() == settings.rate_limit_register
    assert password_reset_limit() == settings.rate_limit_password_reset

"""Same-origin, bounded research demo. It does not retain submitted text."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.error import URLError

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .contracts import parse_turns
from .engine import create_engine

WEB = Path(__file__).resolve().parent.parent / "web"
MAX_BODY = 64 * 1024


class RateLimiter:
    def __init__(self, limit=20, window=60, capacity=2048):
        self.limit, self.window, self.capacity = limit, window, capacity
        self.hits = OrderedDict()

    def allow(self, client, now):
        hits = self.hits.get(client)
        if hits is None:
            if len(self.hits) >= self.capacity:
                self.hits.popitem(last=False)
            hits = self.hits[client] = deque()
        else:
            self.hits.move_to_end(client)
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


def create_app(engine=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        selected = os.getenv("CARETRACE_MODEL", "source")
        app.state.engine = engine or create_engine(selected)
        app.state.slot = asyncio.Semaphore(1)
        app.state.limiter = RateLimiter()
        yield
        app.state.engine = None

    app = FastAPI(title="CareTrace Research API", version="0.1.0", lifespan=lifespan)
    app.mount("/assets", StaticFiles(directory=WEB), name="assets")

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path == "/docs":
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    async def index():
        return FileResponse(WEB / "index.html")

    @app.get("/health/live")
    async def live():
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready(request: Request):
        if getattr(request.app.state, "engine", None) is None:
            raise HTTPException(503, "Model is not ready.")
        return {"status": "ready", "engine": request.app.state.engine.name}

    @app.post("/api/v1/extract")
    async def extract(request: Request):
        if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
            raise HTTPException(415, "Send JSON with a transcript field.")
        client = request.client.host if request.client else "unknown"
        if not request.app.state.limiter.allow(client, time.monotonic()):
            raise HTTPException(429, "Request limit reached. Try again in a minute.", headers={"Retry-After": "60"})
        chunks, total = [], 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > MAX_BODY:
                raise HTTPException(413, "Request is too large.")
            chunks.append(chunk)
        try:
            body = json.loads(b"".join(chunks))
            if not isinstance(body, dict) or not isinstance(body.get("transcript"), str):
                raise ValueError("Send a transcript string.")
            turns = parse_turns(body["transcript"])
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        if request.app.state.slot.locked():
            raise HTTPException(429, "The model is busy. Try again shortly.")
        async with request.app.state.slot:
            try:
                orders = await run_in_threadpool(request.app.state.engine.extract, turns)
            except (ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(422, f"Could not extract orders: {exc}") from exc
            except (URLError, TimeoutError, OSError) as exc:
                raise HTTPException(503, "The local model service is unavailable.") from exc
        return {"engine": request.app.state.engine.name, "orders": orders,
                "research_only": True, "note": "Evidence links require human review."}

    return app


app = create_app()

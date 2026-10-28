"""FastAPI uygulaması."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.db import init_db, get_session
from app.pipeline import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with get_session() as db:
        seed(db)
    yield


app = FastAPI(title="Bilanço API", version=__version__, lifespan=lifespan,
              description="Otomatik veri toplayan, doğrulayan ve analiz eden finansal platform — Bankalar modülü")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}

"""FastAPI application entry point for VITAVIA."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db.database import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize durable history tables while retaining in-memory live state."""
    init_db()
    yield


app = FastAPI(
    title="VITAVIA",
    description="Prototype backend for an intelligent connected ambulance system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)

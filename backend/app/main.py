from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401  -- ensures models are registered before create_all
from .routers import interactions, hcp, chat

app = FastAPI(title="AI-First HCP CRM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interactions.router)
app.include_router(hcp.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup():
    # In production, use Alembic migrations instead of create_all.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}

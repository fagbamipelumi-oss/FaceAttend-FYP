from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  registers all models on Base
from app.api import attendance, auth, people, recognition, sessions
from app.core.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="FaceAttend-FYP API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Vite falls back to the next free port (5174, 5175, ...) if 5173 is
    # already taken, so allow the common dev range rather than hardcoding one.
    allow_origin_regex=r"http://localhost:517\d",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(people.router)
app.include_router(sessions.router)
app.include_router(recognition.router)
app.include_router(attendance.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

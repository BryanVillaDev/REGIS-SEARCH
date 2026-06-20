from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, jobs, pins, records, search
from app.core.bootstrap import bootstrap_app
from app.core.config import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap_app()
    yield


app = FastAPI(
    title="REGIS Search API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(records.router, prefix="/api/records", tags=["records"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(pins.router, prefix="/api/pins", tags=["pins"])

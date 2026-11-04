import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.rate_limit import limiter
from app.api import profiles, auth, cabinet, pools, themes, library
from app.db.base import Base
from app.db.session import engine
from app.services.questions import start_watcher

app = FastAPI(title=settings.APP_NAME)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


# ensure dirs
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# mount uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# create tables
Base.metadata.create_all(bind=engine)
try:
    from app.migrations_fix import apply_fallback_migrations
    apply_fallback_migrations()
except Exception as e:
    print(f"Fallback migrations failed: {e}")

# start questions watcher
try:
    if settings.QUESTIONS_WATCH_ENABLED:
        start_watcher()
except Exception as e:
    print(f"Failed to start questions watcher: {e}")

app.include_router(profiles.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(cabinet.router, prefix="/api")
app.include_router(pools.router, prefix="/api")
app.include_router(themes.router, prefix="/api")
app.include_router(library.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}

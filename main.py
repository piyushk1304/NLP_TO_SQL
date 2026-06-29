import config

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from api.router import upload_router, schema_router, ask_router, download_router, cache_router, info_router
from database.db import init_database
import logging
import time
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    print("\n" + "="*60)
    print("[SYSTEM] NLP → SQL Backend Started")
    print("="*60 + "\n")
    yield
    print("\n[SYSTEM] Shutting down...")

app = FastAPI(
    title="NLP → SQL Backend System",
    description="Natural Language to SQL conversion with KPI Intelligence",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error", "detail": str(exc)}
    )

# Include all routers with prefix (order matters for Swagger UI)
app.include_router(upload_router, prefix="/api")
app.include_router(schema_router, prefix="/api")
app.include_router(ask_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(cache_router, prefix="/api")
app.include_router(info_router, prefix="")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
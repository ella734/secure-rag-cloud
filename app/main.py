"""FastAPI application entrypoint for SecureRAG Cloud."""

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes import router, get_rag_engine
from app.monitoring import logger, correlation_id_ctx


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and graceful shutdown lifecycle."""
    logger.info(
        f"Starting {settings.app_name} [Environment: {settings.environment}]",
        extra={"extra_data": {"port": settings.app_port, "provider": settings.llm_provider}},
    )
    # Warm up RAG index
    get_rag_engine()
    yield
    logger.info(f"Shutting down {settings.app_name}.")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production-Ready RAG Platform on Azure with LLMOps, Observability, and LLM Security",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Injects and propagates unique correlation ID across request life cycle."""
    start_time = time.perf_counter()
    req_cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    token = correlation_id_ctx.set(req_cid)

    try:
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Correlation-ID"] = req_cid
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response
    finally:
        correlation_id_ctx.reset(token)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """RFC 7807 compliant global exception handler."""
    cid = correlation_id_ctx.get()
    logger.error(
        f"Unhandled server error: {str(exc)}",
        exc_info=True,
        extra={"extra_data": {"path": request.url.path, "correlation_id": cid}},
    )
    return JSONResponse(
        status_code=500,
        content={
            "type": "https://tools.ietf.org/html/rfc7807",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred processing your request.",
            "correlation_id": cid,
        },
    )


# Register API v1 routes
app.include_router(router)


@app.get("/", summary="Root index redirecting to documentation")
async def root():
    return {
        "service": settings.app_name,
        "status": "online",
        "documentation": "/docs",
        "api_v1": "/api/v1/query",
        "health": "/api/v1/health",
        "metrics": "/api/v1/metrics",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)

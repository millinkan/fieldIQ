from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging

from app import __version__
from app.api import simulate, roster, pdv, squad, model_info, credits, training, v3_intelligence
from app.core.model_init import init_model
from app.core.config import settings, N_FEATURES
from app.core.cache import cache_health
from app.core.exceptions import FieldIQError
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.credits import CreditsMiddleware
from app.middleware.auth import APIKeyMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FieldIQ v%s starting — initialising PyTorch model...", __version__)
    init_model()
    logger.info("Model ready")
    yield
    logger.info("FieldIQ shutting down")


app = FastAPI(
    title="FieldIQ Pro API",
    description=(
        "WC 2026 Predictive Intelligence Platform — v3\n\n"
        "Enterprise-grade football analytics: MLP match prediction, Monte Carlo "
        "tournament simulation, PDV discipline engine, SRR bench depth, and four "
        "contextual intelligence layers (fatigue, chemistry, momentum, tactical).\n\n"
        "Multi-provider data ingestion: API-Sports, Sportmonks, FootyStats, StatsBomb."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(CreditsMiddleware)
app.add_middleware(APIKeyMiddleware)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(simulate.router, prefix="/v1/tournament", tags=["Tournament"])
app.include_router(roster.router, prefix="/v1/squad", tags=["Squad"])
app.include_router(pdv.router, prefix="/v1/pdv", tags=["PDV"])
app.include_router(squad.router, prefix="/v1/srr", tags=["SRR"])
app.include_router(model_info.router, prefix="/v1/model", tags=["Model"])
app.include_router(credits.router, prefix="/v1/credits", tags=["Credits"])
app.include_router(training.router, prefix="/v1/model", tags=["Training"])
app.include_router(v3_intelligence.router, prefix="/v1/v3", tags=["V3 Intelligence"])


@app.exception_handler(FieldIQError)
async def fieldiq_error_handler(request: Request, exc: FieldIQError):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "code": "VALIDATION_ERROR",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "INTERNAL_ERROR"},
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "fieldiq-api",
        "version": __version__,
        "features": N_FEATURES,
        "layers": ["fatigue_travel", "chemistry_synergy", "momentum_clutch", "tactical_matchup"],
        "cache": cache_health(),
        "auth_enforced": settings.ENFORCE_API_KEY,
        "rate_limit_enforced": settings.ENFORCE_RATE_LIMIT,
        "credits_enforced": settings.ENFORCE_CREDITS,
    }


@app.get("/")
def root():
    return {
        "message": f"FieldIQ Pro API v{__version__} — visit /docs for Swagger UI",
        "docs": "/docs",
        "health": "/health",
    }

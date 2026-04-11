import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.counseling.broker import JointSessionBroker
from app.api.websockets import router as websockets_router

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from prometheus_fastapi_instrumentator import Instrumentator
import structlog

# Initialize Sentry
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
    )

# Configure Structured Logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    app.state.broker = JointSessionBroker(redis_url=redis_url)
    yield
    # Cleanup tasks could be added here if necessary


app = FastAPI(title="RelationshipAI - FastAPI Service", lifespan=lifespan)
app.include_router(websockets_router)

# Instrument Prometheus
Instrumentator().instrument(app).expose(app)


@app.get("/")
async def root():
    return {"message": "RelationshipAI FastAPI Service is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text as sa_text

from app.api.routes_audit import router as audit_router
from app.api.routes_auth import router as auth_router
from app.api.routes_compliance import router as compliance_router
from app.api.routes_dashboard import router as dashboard_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_query import router as query_router
from app.api.routes_runtime import router as runtime_router
from app.api.routes_settings import router as settings_router
from app.config import get_settings
from app.db.session import engine
from app.services.request_context import get_request_id, reset_request_id, set_request_id


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [req=%(request_id)s] %(name)s: %(message)s",
)
for _handler in logging.getLogger().handlers:
    _handler.addFilter(RequestIdLogFilter())

logger = logging.getLogger(__name__)
settings = get_settings()


def _check_postgres() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        return {"status": "up"}
    except Exception:
        logger.exception("Postgres health check failed")
        return {"status": "down", "error": "internal_error"}


def _check_qdrant() -> dict:
    try:
        from app.services.retrieval import get_qdrant

        get_qdrant().get_collections()
        return {"status": "up"}
    except Exception:
        logger.exception("Qdrant health check failed")
        return {"status": "down", "error": "internal_error"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_secret_key in {"change-me", "change-me-in-production"}:
        logger.warning("APP_SECRET_KEY is still set to a default placeholder. Change it in .env for production.")
    if settings.retrieval_warmup_on_startup:
        try:
            from app.services.embeddings import embed_texts

            logger.info("Warming retrieval embedding model '%s'", settings.embedding_model)
            embed_texts(["retrieval warmup"])
            logger.info("Retrieval embedding model is ready")
        except Exception:
            logger.exception("Retrieval embedding warmup failed; first RAG query may be slow or unavailable")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

templates = Jinja2Templates(directory="app/ui/templates")
static_path = Path("app/ui/static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    incoming_request_id = request.headers.get("X-Request-ID", "").strip()
    request_id = incoming_request_id or str(uuid4())
    token = set_request_id(request_id)
    request.state.request_id = request_id
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
        return response
    except Exception:
        logger.exception("Unhandled error for %s %s", request.method, request.url.path)
        raise
    finally:
        reset_request_id(token)


app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(compliance_router)
app.include_router(runtime_router)
app.include_router(settings_router)


@app.get("/health")
def health():
    return _health_response()


@app.get("/health/ready")
def health_ready():
    return _health_response()


def _health_response() -> JSONResponse:
    postgres = _check_postgres()
    qdrant = _check_qdrant()

    required_ok = postgres["status"] == "up" and qdrant["status"] == "up"
    body = {
        "status": "ok" if required_ok else "degraded",
        "components": {
            "api": {"status": "up"},
            "postgres": postgres,
            "qdrant": qdrant,
            "generation": {
                "required": False,
                "provider": settings.generation_provider,
                "endpoint": settings.opencode_go_base_url,
                "configured": bool(settings.opencode_api_key),
            },
        },
    }
    return JSONResponse(status_code=200 if required_ok else 503, content=body)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/query", response_class=HTMLResponse)
def query_page(request: Request):
    return templates.TemplateResponse("query.html", {"request": request})

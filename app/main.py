import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import requests
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
from app.services.multimodal import build_llm_headers, resolve_llm_base_url
from app.services.refresh import refresh_scheduler_loop
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


def _check_qdrant() -> dict:
    try:
        from app.services.retrieval import get_qdrant

        get_qdrant().get_collections()
        return {"status": "up"}
    except Exception:
        logger.exception("Qdrant health check failed")
        return {"status": "down", "error": "internal_error"}


def _check_postgres() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        return {"status": "up"}
    except Exception:
        logger.exception("Postgres health check failed")
        return {"status": "down", "error": "internal_error"}


def _check_llm_backend() -> dict:
    try:
        response = requests.get(
            f"{resolve_llm_base_url()}/models",
            headers=build_llm_headers(),
            timeout=3,
        )
        if response.ok:
            return {"status": "up"}
        return {"status": "down", "error": f"http_status:{response.status_code}"}
    except Exception as exc:
        return {"status": "down", "error": str(exc)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_secret_key in {"change-me", "change-me-in-production"}:
        logger.warning("APP_SECRET_KEY is still set to a default placeholder. Change it in .env for production.")
    stop_event: asyncio.Event | None = None
    task: asyncio.Task | None = None
    if settings.refresh_scheduler_enabled:
        stop_event = asyncio.Event()
        task = asyncio.create_task(refresh_scheduler_loop(stop_event))
    try:
        yield
    finally:
        if stop_event and task:
            stop_event.set()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


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
    llm = _check_llm_backend()

    required_ok = postgres["status"] == "up" and qdrant["status"] == "up"
    body = {
        "status": "ok" if required_ok else "degraded",
        "components": {
            "api": {"status": "up"},
            "postgres": postgres,
            "qdrant": qdrant,
            "llm": {"required": False, **llm},
        },
    }
    return JSONResponse(status_code=200 if required_ok else 503, content=body)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/query", response_class=HTMLResponse)
def query_page(request: Request):
    return templates.TemplateResponse("query.html", {"request": request})

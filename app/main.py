import logging
from contextlib import asynccontextmanager
from pathlib import Path

import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes_auth import router as auth_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_query import router as query_router
from app.config import get_settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup checks: verify required services are reachable."""
    # --- Secret key check ---
    if settings.app_secret_key == "change-me":
        logger.warning("APP_SECRET_KEY is still the default 'change-me'. Change it in .env for production!")

    # --- SentenceTransformer check ---
    try:
        from app.services.retrieval import get_embedder
        get_embedder()
        logger.info("Embedding model loaded successfully.")
    except Exception:
        logger.exception("FATAL: Cannot load sentence-transformers model. Install sentence-transformers and use Python 3.11/3.12.")
        raise

    # --- Qdrant check ---
    try:
        from app.services.retrieval import get_qdrant
        get_qdrant().get_collections()
        logger.info("Qdrant is reachable.")
    except Exception:
        logger.exception("FATAL: Cannot connect to Qdrant at %s", settings.qdrant_url)
        raise

    # --- PostgreSQL check ---
    try:
        from sqlalchemy import text as sa_text
        from app.db.session import engine
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        logger.info("PostgreSQL is reachable.")
    except Exception:
        logger.exception("FATAL: Cannot connect to PostgreSQL at %s", settings.database_url)
        raise

    # --- Ollama check (warn only) ---
    try:
        resp = requests.get(settings.ollama_url, timeout=5)
        if resp.ok:
            logger.info("Ollama is reachable at %s", settings.ollama_url)
        else:
            logger.warning("Ollama returned status %d. LLM answers may not work.", resp.status_code)
    except Exception:
        logger.warning("Ollama is NOT reachable at %s. LLM answers will be unavailable until Ollama is started.", settings.ollama_url)

    yield  # app runs


app = FastAPI(title=settings.app_name, lifespan=lifespan)

templates = Jinja2Templates(directory="app/ui/templates")
static_path = Path("app/ui/static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(query_router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/query", response_class=HTMLResponse)
def query_page(request: Request):
    return templates.TemplateResponse("query.html", {"request": request})

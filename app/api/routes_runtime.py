from fastapi import APIRouter, Depends

from app.api.routes_auth import require_roles
from app.db.models import User
from app.services.model_usage import configured_model_usage

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


@router.get("/models")
def runtime_models(user: User = Depends(require_roles("Admin"))):
    return configured_model_usage()

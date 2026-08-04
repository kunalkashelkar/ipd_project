from backend.app.routers.features import router as features_router
from backend.app.routers.health import router as health_router
from backend.app.routers.model import router as model_router
from backend.app.routers.parser import router as parser_router
from backend.app.routers.projects import router as projects_router
from backend.app.routers.semantic import router as semantic_router
from backend.app.routers.taint import router as taint_router
from backend.app.routers.upload import router as upload_router

__all__ = ["health_router", "projects_router", "upload_router", "parser_router", "taint_router", "features_router", "model_router", "semantic_router"]

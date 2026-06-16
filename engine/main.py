import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .audit import log_processor, log_queue
from .auth import initialize_auth
from .config import APP_TITLE, logger, validate_config
from .migrations import ensure_schema
from .demo.mocks import mock_service_response
from .services.security import is_local_mock_client
from .models import TenantSuppliedError
from .routes import admin, runtime

OPENAPI_SECURITY_SCHEME = {
    "type": "http",
    "scheme": "bearer",
    "description": (
        "Bearer tokens configured via DECISION_ENGINE_AUTH_TOKENS or "
        "DECISION_ENGINE_AUTH_TOKENS_FILE. Generate local demo tokens with "
        "scripts/create_demo_env.sh."
    ),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_config()
    initialize_auth()
    ensure_schema()
    task = asyncio.create_task(log_processor())
    logger.info("%s started.", APP_TITLE)
    yield
    await log_queue.put(None)
    await log_queue.join()
    task.cancel()
    logger.info("%s shutdown.", APP_TITLE)


app = FastAPI(title=APP_TITLE, lifespan=lifespan)


@app.exception_handler(TenantSuppliedError)
async def tenant_supplied_handler(request: Request, exc: TenantSuppliedError):
    return JSONResponse(status_code=403, content={"detail": str(exc)})


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="0.2.0",
        routes=app.routes,
        description="Multi-tenant decision engine prototype with demo bearer auth.",
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "BearerAuth"
    ] = OPENAPI_SECURITY_SCHEME
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/admin/overview")


class AdminSPAStaticFiles(StaticFiles):
    """Serve built assets; SPA fallback only for extensionless document routes."""

    _ASSET_SUFFIXES = (
        ".js",
        ".css",
        ".map",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".woff",
        ".woff2",
        ".ttf",
        ".json",
    )

    @staticmethod
    def _should_spa_fallback(path: str) -> bool:
        if not path or path == "/":
            return True
        lower = path.lower()
        if any(lower.endswith(ext) for ext in AdminSPAStaticFiles._ASSET_SUFFIXES):
            return False
        return True

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and self._should_spa_fallback(path):
                return FileResponse(str(UI_DIST / "index.html"))
            raise


@app.api_route(
    "/mock/{mock_name}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def mock_service(mock_name: str, request: Request):
    client_host = request.client.host if request.client else None
    if not is_local_mock_client(client_host):
        raise HTTPException(
            status_code=403,
            detail="Mock endpoints are available on localhost for local demo only.",
        )
    return await mock_service_response(mock_name)


app.include_router(runtime.router)
app.include_router(admin.router)

UI_DIST = Path(__file__).resolve().parent.parent / "ui" / "dist"
if not UI_DIST.is_dir():
    raise RuntimeError(
        f"Admin UI build missing at {UI_DIST}. Run: cd ui && npm ci && npm run build"
    )
app.mount(
    "/admin",
    AdminSPAStaticFiles(directory=str(UI_DIST), html=True),
    name="admin",
)

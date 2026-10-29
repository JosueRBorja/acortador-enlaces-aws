import logging
from contextlib import asynccontextmanager
from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.app.config import Settings, get_settings
from backend.app.repository import LinkRepository
from backend.app.schemas import LinkInfo, ShortenRequest, ShortenResponse
from backend.app.service import LinkService

logger = logging.getLogger(__name__)


def get_service(request: Request) -> LinkService:
    return request.app.state.service


Service = Annotated[LinkService, Depends(get_service)]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=settings.log_level.upper())
        repository = LinkRepository(settings)
        app.state.service = LinkService(repository)
        try:
            yield
        finally:
            repository.close()

    app = FastAPI(title="Nexo · Acortador de enlaces", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    async def database_error(request: Request, exc: Exception) -> JSONResponse:
        # Registrar el tipo de error evita exponer URLs privadas o detalles de AWS al usuario.
        logger.error("Error de almacenamiento: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"detail": "Almacenamiento temporalmente no disponible. Intenta más tarde."},
        )

    app.add_exception_handler(ClientError, database_error)
    app.add_exception_handler(BotoCoreError, database_error)

    @app.get("/health", tags=["Estado"])
    def health() -> dict[str, str]:
        """Comprueba el proceso; no afirma que DynamoDB esté disponible."""
        return {"status": "ok"}

    @app.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
    def shorten(payload: ShortenRequest, service: Service):
        item = service.create(str(payload.original_url))
        return {**item, "short_url": f"{settings.public_base_url}/{item['short_code']}"}

    def find_or_404(short_code: str, service: LinkService) -> dict[str, str]:
        item = service.find(short_code)
        if item is None:
            raise HTTPException(status_code=404, detail="El enlace solicitado no existe.")
        return item

    @app.get("/urls/{short_code}", response_model=LinkInfo)
    def info(short_code: str, service: Service):
        return find_or_404(short_code, service)

    @app.get("/{short_code}", response_class=RedirectResponse, status_code=307)
    def redirect(short_code: str, service: Service):
        item = find_or_404(short_code, service)
        return RedirectResponse(item["original_url"], status_code=307)

    return app


app = create_app()

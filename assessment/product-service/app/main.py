from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import categories, products, health
from app.core.logger import setup_logging, logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from app.core.config import settings

setup_logging()

app = FastAPI(title=settings.PROJECT_NAME)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"type": "about:blank", "title": exc.detail, "status": exc.status_code, "detail": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"type": "about:blank", "title": "Validation Error", "status": 422, "detail": exc.errors()}
    )

app.include_router(categories.router)
app.include_router(products.router)
app.include_router(health.router)

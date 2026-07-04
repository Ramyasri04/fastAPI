from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import auth, users, health
from app.core.logger import setup_logging, logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

setup_logging()

app = FastAPI(title="Auth Service")

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

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(health.router)

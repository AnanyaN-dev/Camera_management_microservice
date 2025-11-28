# This file contains all custom exceptions + global FastAPI exception handlers.
# This file is for:
# → To separate business logic errors (like "Camera not found") from Python's internal errors.
# → To provide clean JSON error responses in the API.
#
# The API layer and service layer never return "raw errors".
# Instead, they raise these custom exceptions, and FastAPI converts them
# into user-friendly JSON using the handlers below.

# CUSTOM EXCEPTIONS (used in service & repository)

#service errors
class NotFoundError(Exception):
    """Raised when a resource (camera/feed) is not found."""

    pass


class ConflictError(Exception):
    """Raised when a conflict occurs (example: duplicate feed, duplicate configuration)."""

    pass


class ValidationError(Exception):
    """Raised when business validation rules fail (not Pydantic validation)."""

    pass


# GLOBAL EXCEPTION HANDLERS FOR FASTAPI
# These handlers automatically convert Python exceptions → JSON API responses.

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def register_error_handlers(app: FastAPI):
    """
    Register ALL exception handlers so every route returns consistent errors.
    This function must be called once from main.py.
    """

    # NotFoundError → 404
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "detail": str(exc),
                "path": str(request.url),
            },
        )

    # ConflictError → 409
    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return JSONResponse(
            status_code=409,
            content={
                "error": "Conflict",
                "detail": str(exc),
                "path": str(request.url),
            },
        )

    # ValidationError → 400
    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation Error",
                "detail": str(exc),
                "path": str(request.url),
            },
        )

    # Catch-all fallback → 500
    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        """
        Final fallback for any unexpected/unhandled error.
        Important:
        → We do NOT expose full stack trace to clients.
        → Prevents leaking internal server details.
        """
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "Something went wrong on the server.",
                "path": str(request.url),
            },
        )

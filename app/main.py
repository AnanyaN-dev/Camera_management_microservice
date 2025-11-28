# This is the entry point of the entire FastAPI application.
# When we run the server (uvicorn app.main:app), THIS file is executed.
# This file is responsible for:
#   1. Creating the FastAPI app instance
#   2. Setting up global logging from core/logging.py
#   3. Registering global error handlers from core/exceptions.py
#   4. Including all routers (API endpoints)
# No business logic or repository logic should be placed here.

from fastapi import FastAPI

# import the camera router
from app.api.camera_api import router as camera_router
# import global error handlers
from app.core.exceptions import register_error_handlers
# import our centralized logging setup
from app.core.logging import setup_logging

# 1. Create FastAPI application
app = FastAPI(
    title="Camera Management Microservice",
    description="A modular FastAPI microservice for managing cameras, feeds, and status",
    version="1.0.0",
)


# 2. Setup Logging
# This applies the global logging configuration defined in logging.py
setup_logging()

# 3. Register Global Exception Handlers
register_error_handlers(app)


# 4. Include Routers
# This attaches all /cameras/... endpoints to the main app.
app.include_router(camera_router)


# OPTIONAL: Root endpoint (good for sanity tests)
@app.get("/")
def root():
    return {"message": "Camera Management Microservice is running!"}

# This file contains reusable pytest fixtures.
# Fixtures make tests cleaner by avoiding repeated code.

# We define:
#  TestClient fixture for API testing
#  Repository fixture (in-memory database)
#  Service fixture (uses repo)
#  Common payloads for creating cameras during tests(DATA)

import pytest
from fastapi.encoders import jsonable_encoder
# It is a FastAPI utility function that converts Python objects
# into data formats that can be safely stored or returned as JSON.
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import CameraNetworkInfo, NewCameraData, VideoFeedSetup
from app.repository.memory_repo import SimpleCameraMemoryStorage
from app.service.camera_service import CameraService


# test client fixture
@pytest.fixture
def client():
    # ensure API uses a clean repo before every test
    from app.api.camera_api import repo

    repo._store.clear()  # reset dictionary
    return TestClient(app)


# Repository fixture for repo + service tests
@pytest.fixture
def repo():
    return SimpleCameraMemoryStorage()


# Inject repo into service layer for isolated service tests
@pytest.fixture
def service(repo):
    return CameraService(repo)


# Base Pydantic model payload
@pytest.fixture
def camera_payload_model():
    return NewCameraData(
        camera_name="TestCam",
        camera_model="ModelX",
        network_setup=CameraNetworkInfo(ip_address="192.168.0.10"),
        available_feeds=[
            VideoFeedSetup(feed_protocol="rtsp", feed_port=554, feed_path="/main")
        ],
    )


# Used directly by service + repo tests
@pytest.fixture
def camera_payload(camera_payload_model):
    return camera_payload_model


# JSON version for API tests
@pytest.fixture
def camera_payload_json(camera_payload_model):
    return jsonable_encoder(camera_payload_model)

# depends coz: To inject the service class (CameraService) automatically into routes
# Defines all HTTP endpoints for cameras and feeds.
# Converts service exceptions into HTTP errors.
import logging  # (ADDED COMMENT) importing logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.exceptions import ConflictError, NotFoundError
from app.models.schemas import (CameraDetails, CameraState, CameraUpdate,
                                FeedUpdate, NewCameraData, VideoFeedInfo,
                                VideoFeedSetup)
from app.repository.memory_repo import SimpleCameraMemoryStorage
from app.service.camera_service import CameraService

logger = logging.getLogger(__name__)  # (ADDED COMMENT) creating logger for this file

# APIRouter(): A folder where all camera-related API endpoints will live
## Instead of putting every API directly in main.py,you group them.
router = APIRouter(prefix="/cameras", tags=["Camera Management"])
# This creates a router that contains all camera routes:

# GLOBAL REPO + SERVICE CREATED ONLY ONCE
# These SINGLE instances will be shared across ALL requests + tests.
repo = SimpleCameraMemoryStorage()  # empty db
# create a camera service object and connect with the repo onject
service = CameraService(repo)  # service connected to repo
# now service can call repo functions:
# self.repo.add_camera()
# self.repo.get_camera()


# Dependency injection for service (FastAPI will inject this automatically)
# FastAPI will automatically give (inject) an object/function
# result into your route or class without you manually creating it each time.
def get_service():
    return service


# When you write Depends(get_service),
# FastAPI calls this function
# It returns the service object
# The service is then injected into API functions


# 1. ADD THE CAMERA (POST)
@router.post("/", response_model=CameraDetails)
def add_camera(data: NewCameraData, service: CameraService = Depends(get_service)):
    # Depends(get_service) this return service that is : service = CameraService(repo)

    logger.info("API: Received request to ADD a camera")  # (ADDED COMMENT)

    try:
        cam = service.add_camera(data)
        logger.info(
            f"API: Camera successfully added with ID={cam.camera_id}"
        )  # (ADDED COMMENT)
        return cam
    except ConflictError as e:
        logger.warning(
            f"API: Conflict while adding camera → {str(e)}"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(
            f"API: Unexpected error while adding camera → {str(e)}"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=400, detail=str(e))


# 2. GET CAMERA BY ID (GET)
@router.get("/{camera_id}", response_model=CameraDetails)
def get_camera(camera_id: UUID, service: CameraService = Depends(get_service)):
    logger.info(f"API: Request to GET camera ID={camera_id}")  # (ADDED COMMENT)
    try:
        cam = service.get_camera(camera_id)
        logger.info(
            f"API: Successfully fetched camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return cam
    except NotFoundError as e:
        logger.warning(f"API: Camera ID={camera_id} not found")  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))


# 3. DELETE CAMERA (DELETE)
@router.delete("/{camera_id}")
def delete_camera(camera_id: UUID, service: CameraService = Depends(get_service)):
    logger.info(f"API: Request to DELETE camera ID={camera_id}")  # (ADDED COMMENT)
    try:
        service.remove_camera(camera_id)
        logger.info(
            f"API: Successfully deleted camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return {"message": "Camera removed successfully"}
    except NotFoundError as e:
        logger.warning(
            f"API: Cannot delete, camera ID={camera_id} not found"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))


# 4. LIST ALL CAMERAS (GET)
@router.get("/", response_model=list[CameraDetails])
def list_cameras(
    model: str | None = None,
    ip_from: str | None = None,
    ip_to: str | None = None,
    online: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    service: CameraService = Depends(get_service),
):
    logger.info("API: Request to LIST cameras")  # (ADDED COMMENT)
    cams = service.list_cameras(
        model=model,
        ip_from=ip_from,
        ip_to=ip_to,
        online=online,
        page=page,
        page_size=page_size,
    )
    logger.info(f"API: Returned {len(cams)} cameras in list")  # (ADDED COMMENT)
    return cams


# 5. UPDATE CAMERA (PATCH)
@router.patch("/{camera_id}", response_model=CameraDetails)
def update_camera(
    camera_id: UUID,
    updates: CameraUpdate,
    service: CameraService = Depends(get_service),
):
    logger.info(f"API: Request to UPDATE camera ID={camera_id}")  # (ADDED COMMENT)
    try:
        cam = service.update_camera(camera_id, updates)
        logger.info(
            f"API: Successfully updated camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return cam
    except NotFoundError as e:
        logger.warning(
            f"API: Cannot update, camera ID={camera_id} not found"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))


# 6. ADD FEED / STREAM TO CAMERA
@router.post("/{camera_id}/feeds", response_model=dict)
def add_feed(
    camera_id: UUID,
    feed: VideoFeedSetup,
    service: CameraService = Depends(get_service),
):
    logger.info(f"API: Request to ADD FEED to camera ID={camera_id}")  # (ADDED COMMENT)
    try:
        new_feed = service.add_feed(camera_id, feed)
        logger.info(f"API: Feed added to camera ID={camera_id}")  # (ADDED COMMENT)
        return {"message": "Feed added", "feed": new_feed}
    except NotFoundError as e:
        logger.warning(
            f"API: Cannot add feed, camera ID={camera_id} not found"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        logger.warning(
            f"API: Feed conflict for camera ID={camera_id} → {str(e)}"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=409, detail=str(e))


# 7. UPDATE FEED
@router.patch("/{camera_id}/feeds/{feed_id}")
def update_feed(
    camera_id: UUID,
    feed_id: UUID,
    updates: FeedUpdate,
    service: CameraService = Depends(get_service),
):
    logger.info(
        f"API: Request to UPDATE feed ID={feed_id} for camera ID={camera_id}"
    )  # (ADDED COMMENT)
    try:
        updated = service.update_feed(camera_id, feed_id, updates)
        logger.info(f"API: Successfully updated feed ID={feed_id}")  # (ADDED COMMENT)
        return {"message": "Feed updated", "feed": updated}
    except NotFoundError as e:
        logger.warning(f"API: Feed or camera not found for update")  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))


# 8. DELETE FEED
@router.delete("/{camera_id}/feeds/{feed_id}")
def delete_feed(
    camera_id: UUID, feed_id: UUID, service: CameraService = Depends(get_service)
):
    logger.info(
        f"API: Request to DELETE feed ID={feed_id} from camera ID={camera_id}"
    )  # (ADDED COMMENT)
    try:
        service.remove_feed(camera_id, feed_id)
        logger.info(f"API: Successfully deleted feed ID={feed_id}")  # (ADDED COMMENT)
        return {"message": "Feed removed successfully"}
    except NotFoundError as e:
        logger.warning(f"API: Cannot delete feed, not found")  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))


# 9. GET FEEDS (LIST)
@router.get("/{camera_id}/feeds", response_model=list[VideoFeedInfo])
def get_camera_feeds(
    camera_id: UUID,
    protocol: str | None = None,
    port: int | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    service: CameraService = Depends(get_service),
):
    logger.info(
        f"API: Request to LIST FEEDS of camera ID={camera_id}"
    )  # (ADDED COMMENT)
    try:
        feeds = service.list_feeds(
            camera_id=camera_id,
            protocol=protocol,
            port=port,
            q=q,
            page=page,
            page_size=page_size,
        )
        logger.info(
            f"API: Returned {len(feeds)} feeds for camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return feeds
    except NotFoundError as e:
        logger.warning(f"API: Camera not found while listing feeds")  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))


# 10. HEARTBEAT
@router.post("/{camera_id}/heartbeat")
def heartbeat(camera_id: UUID, service: CameraService = Depends(get_service)):
    logger.info(f"API: HEARTBEAT received for camera ID={camera_id}")  # (ADDED COMMENT)
    try:
        result = service.heartbeat(camera_id)
        logger.info(
            f"API: Heartbeat updated for camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return result
    except NotFoundError as e:
        logger.warning(
            f"API: Cannot update heartbeat → camera not found"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))


# 11. CAMERA STATUS
@router.get("/{camera_id}/status", response_model=CameraState)
def camera_status(camera_id: UUID, service: CameraService = Depends(get_service)):
    logger.info(
        f"API: Request to GET STATUS of camera ID={camera_id}"
    )  # (ADDED COMMENT)
    try:
        status_bool = service.is_online(camera_id)
        cam = service.get_camera(camera_id)

        logger.info(
            f"API: Returned status for camera ID={camera_id}"
        )  # (ADDED COMMENT)

        return CameraState(
            camera_id=camera_id,
            is_online=status_bool,
            last_known_checkin=cam.last_known_checkin,
        )

    except NotFoundError as e:
        logger.warning(
            f"API: Camera ID={camera_id} not found for status check"
        )  # (ADDED COMMENT)
        raise HTTPException(status_code=404, detail=str(e))

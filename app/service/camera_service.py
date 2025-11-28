# CAMERA SERVICE (BUSINESS LOGIC LAYER)
# This layer:
#   - Applies BUSINESS RULES
#   - Prevents duplicates (IP, names, feeds)
#   - Filters + Pagination
#   - Handles heartbeat & status
# The API layer only *calls* these functions.
# The Repository layer only stores raw data.


import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import Config
from app.core.exceptions import ConflictError, NotFoundError
from app.models.schemas import (CameraDetails, CameraUpdate, FeedUpdate,
                                NewCameraData, VideoFeedInfo, VideoFeedSetup)
from app.repository.memory_repo import SimpleCameraMemoryStorage

# It creates a logger specific to the current file.
logger = logging.getLogger(__name__)


class CameraService:
    def __init__(self, repo: SimpleCameraMemoryStorage):
        self.repo = repo

    # ADD CAMERA
    def add_camera(self, data: NewCameraData) -> CameraDetails:

        # RULE 1: Prevent duplicate camera IP addresses
        for cam in self.repo.list_cameras():
            if cam.network_setup.ip_address == data.network_setup.ip_address:
                logger.warning(
                    f"[ADD CAMERA] Duplicate IP rejected: {data.network_setup.ip_address}"
                )
                raise ConflictError("A camera with this IP address already exists.")

        # RULE 2: Prevent duplicate (camera_name + camera_model) combo
        for cam in self.repo.list_cameras():
            if (
                cam.camera_name == data.camera_name
                and cam.camera_model == data.camera_model
            ):
                logger.warning(
                    f"[ADD CAMERA] Duplicate name+model rejected: {data.camera_name} | {data.camera_model}"
                )
                raise ConflictError("A camera with same name and model already exists.")

        cam = self.repo.add_camera(data)
        logger.info(f"[ADD CAMERA] Camera created with ID={cam.camera_id}")
        return cam

    # GET CAMERA
    def get_camera(self, camera_id: UUID) -> CameraDetails:
        cam = self.repo.get_camera(camera_id)
        if cam is None:
            logger.warning(f"[GET CAMERA] Not found: {camera_id}")
            raise NotFoundError("Camera not found.")
        return cam

    # DELETE CAMERA
    def remove_camera(self, camera_id: UUID) -> bool:
        removed = self.repo.remove_camera(camera_id)
        if not removed:
            logger.warning(f"[DELETE CAMERA] Camera not found: {camera_id}")
            raise NotFoundError("Camera not found.")
        return True

    # LIST CAMERAS + FILTERING + PAGINATION
    def list_cameras(
        self,
        model: str | None = None,
        ip_from: str | None = None,
        ip_to: str | None = None,
        online: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ):

        import ipaddress

        cameras = self.repo.list_cameras()

        # FILTER 1 → model substring
        if model:
            cameras = [c for c in cameras if model.lower() in c.camera_model.lower()]

        # FILTER 2 → IP RANGE
        if ip_from or ip_to:
            try:
                ip_from_v = ipaddress.ip_address(ip_from) if ip_from else None
                ip_to_v = ipaddress.ip_address(ip_to) if ip_to else None
            except ValueError:
                raise ConflictError("Invalid IP format.")

            def in_range(ip):
                ip_obj = ipaddress.ip_address(ip)
                if ip_from_v and ip_obj < ip_from_v:
                    return False
                if ip_to_v and ip_obj > ip_to_v:
                    return False
                return True

            cameras = [c for c in cameras if in_range(c.network_setup.ip_address)]

        # FILTER 3 → online/offline
        if online is not None:
            result = []
            for cam in cameras:
                if self.is_online(cam.camera_id) == online:
                    result.append(cam)
            cameras = result

        # PAGINATION
        start = (page - 1) * page_size
        end = start + page_size
        return cameras[start:end]

    # UPDATE CAMERA
    def update_camera(self, camera_id: UUID, updates: CameraUpdate):
        cam = self.repo.update_camera(camera_id, updates)
        if cam is None:
            raise NotFoundError("Camera not found.")
        return cam

    # ADD FEED
    def add_feed(self, camera_id: UUID, feed_data: VideoFeedSetup) -> VideoFeedInfo:
        cam = self.repo.get_camera(camera_id)
        if cam is None:
            raise NotFoundError("Camera not found.")

        # RULE 1 → Prevent duplicate (protocol + port) for same camera
        for f in cam.available_feeds:
            if (
                f.feed_protocol == feed_data.feed_protocol
                and f.feed_port == feed_data.feed_port
            ):
                raise ConflictError(
                    "A feed with same protocol and port already exists for this camera."
                )

        # RULE 2 → Prevent duplicate port across ALL cameras
        for other in self.repo.list_cameras():
            for f in other.available_feeds:
                if f.feed_port == feed_data.feed_port:
                    raise ConflictError(
                        f"Feed port {feed_data.feed_port} already used by another camera."
                    )

        new_feed = self.repo.add_feed(camera_id, feed_data)
        return new_feed

    # UPDATE FEED
    def update_feed(self, camera_id: UUID, feed_id: UUID, updates: FeedUpdate):
        updated = self.repo.update_feed(camera_id, feed_id, updates)
        if updated is None:
            raise NotFoundError("Camera or Feed not found.")
        return updated

    # REMOVE FEED
    def remove_feed(self, camera_id: UUID, feed_id: UUID):
        removed = self.repo.remove_feed(camera_id, feed_id)
        if not removed:
            raise NotFoundError("Camera or Feed not found.")
        return True

    # LIST FEEDS
    def list_feeds(
        self,
        camera_id: UUID,
        protocol: str | None = None,
        port: int | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ):
        cam = self.repo.get_camera(camera_id)
        if cam is None:
            raise NotFoundError("Camera not found.")

        feeds = list(cam.available_feeds)

        if protocol:
            feeds = [f for f in feeds if f.feed_protocol.lower() == protocol.lower()]

        if port is not None:
            feeds = [f for f in feeds if f.feed_port == port]

        if q:
            q_lower = q.lower()
            feeds = [f for f in feeds if q_lower in f.feed_path.lower()]

        start = (page - 1) * page_size
        end = start + page_size
        return feeds[start:end]

    # HEARTBEAT
    def heartbeat(self, camera_id: UUID):
        cam = self.repo.get_camera(camera_id)
        if cam is None:
            raise NotFoundError("Camera not found.")

        cam.last_known_checkin = datetime.now(timezone.utc)
        cam.last_updated_on = datetime.now(timezone.utc)

        self.repo._store[camera_id] = cam
        return {"message": "Heartbeat updated"}

    # ONLINE STATUS
    def is_online(self, camera_id: UUID) -> bool:
        cam = self.repo.get_camera(camera_id)
        if cam is None:
            raise NotFoundError("Camera not found.")

        if cam.last_known_checkin is None:
            return False

        now = datetime.now(timezone.utc)
        diff = now - cam.last_known_checkin

        if diff.total_seconds() > Config.HEARTBEAT_TIMEOUT:
            return False
        else:
            return True


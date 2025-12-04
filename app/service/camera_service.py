# CAMERA SERVICE (BUSINESS LOGIC LAYER)
# This layer:
#   Applies BUSINESS RULES
#   Prevents duplicates (IP, names, feeds)
#   Filters + Pagination
#   Handles heartbeat & status
# The API layer only calls these functions.
# The Repository layer only stores raw data.
# Service depends on the Interface not directly on the memeory_repo.py.


import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import Config
from app.core.exceptions import ConflictError, NotFoundError
from app.models.schemas import (CameraDetails, CameraUpdate, FeedUpdate,
                                NewCameraData, VideoFeedInfo, VideoFeedSetup)
from app.repository.interface import CameraRepositoryInterface

# It creates a logger specific to the current file.
logger = logging.getLogger(__name__)


class CameraService:
    def __init__(self, repo: CameraRepositoryInterface):
        self.repo = repo

    # ADD CAMERA
    def add_camera(self, data: NewCameraData) -> CameraDetails:

        logger.info("[SERVICE] Adding new camera")  # (ADDED COMMENT)

        # RULE 1: Prevent duplicate camera IP addresses
        for cam in self.repo.list_cameras():
            if cam.network_setup.ip_address == data.network_setup.ip_address:
                # data is automatically created by FastAPI + Pydantic, based on the request body.
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

        cam.last_known_checkin = datetime.now(timezone.utc)  # (ADDED HEARTBEAT HERE)
        cam.last_updated_on = datetime.now(timezone.utc)  # (ADDED HEARTBEAT HERE)

        logger.info(
            f"[ADD CAMERA] Camera created with ID={cam.camera_id}"
        )  # (ADDED COMMENT)
        return cam

    # GET CAMERA
    def get_camera(self, camera_id: UUID) -> CameraDetails:
        logger.info(f"[SERVICE] Getting camera ID={camera_id}")  # (ADDED COMMENT)

        cam = self.repo.get_camera(camera_id)
        if cam is None:
            logger.warning(f"[GET CAMERA] Not found: {camera_id}")  # (ADDED COMMENT)
            raise NotFoundError("Camera not found.")
        return cam

    # DELETE CAMERA
    def remove_camera(self, camera_id: UUID) -> bool:
        logger.info(f"[SERVICE] Removing camera ID={camera_id}")  # (ADDED COMMENT)

        removed = self.repo.remove_camera(camera_id)
        if not removed:
            logger.warning(
                f"[DELETE CAMERA] Camera not found: {camera_id}"
            )  # (ADDED COMMENT)
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

        logger.info("[SERVICE] Listing cameras with filters")

        import ipaddress

        cameras = self.repo.list_cameras()

        # FILTER 1 : model substring
        if model:
            filtered = []
            for c in cameras:
                if model.lower() in c.camera_model.lower():
                    filtered.append(c)
            cameras = filtered

        # FILTER 2 : IP RANGE
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

            filtered = []
            for c in cameras:
                if in_range(c.network_setup.ip_address):
                    filtered.append(c)
            cameras = filtered

        # FILTER 3 → online/offline
        if online is not None:
            filtered = []
            for c in cameras:
                if self.is_online(c.camera_id) == online:
                    filtered.append(c)
            cameras = filtered

        # PAGINATION
        start = (page - 1) * page_size
        end = start + page_size

        logger.info(f"[SERVICE] Returning {len(cameras[start:end])} cameras")
        return cameras[start:end]

    # UPDATE CAMERA
    def update_camera(self, camera_id: UUID, updates: CameraUpdate) -> CameraDetails:
        logger.info(f"[SERVICE] Updating camera ID={camera_id}")  # (ADDED COMMENT)

        cam = self.repo.update_camera(camera_id, updates)
        if cam is None:
            logger.warning(
                "[SERVICE] Update failed — camera not found"
            )  # (ADDED COMMENT)
            raise NotFoundError("Camera not found.")

        cam.last_known_checkin = datetime.now(timezone.utc)  # (ADDED HEARTBEAT HERE)
        cam.last_updated_on = datetime.now(timezone.utc)  # (ADDED HEARTBEAT HERE)

        return cam

    def add_feed(self, camera_id: UUID, feed_data: VideoFeedSetup) -> VideoFeedInfo:
        logger.info(f"[SERVICE] Adding feed to camera ID={camera_id}")

        cam = self.repo.get_camera(camera_id)
        if cam is None:
            logger.warning("[SERVICE] Cannot add feed — camera not found")
            raise NotFoundError("Camera not found.")

        # RULE: Prevent duplicate (protocol + port)
        for f in cam.available_feeds:
            if (
                f.feed_protocol == feed_data.feed_protocol
                and f.feed_port == feed_data.feed_port
            ):
                logger.warning("[SERVICE] Feed duplicate protocol+port")
                raise ConflictError(
                    "A feed with same protocol and port already exists for this camera."
                )

        new_feed = self.repo.add_feed(camera_id, feed_data)
        if new_feed is None:
            raise NotFoundError("Camera not found while adding feed.")

        cam.last_known_checkin = datetime.now(timezone.utc)
        cam.last_updated_on = datetime.now(timezone.utc)

        return new_feed

    # UPDATE FEED
    def update_feed(
        self, camera_id: UUID, feed_id: UUID, updates: FeedUpdate
    ) -> VideoFeedInfo:
        logger.info(f"[SERVICE] Updating feed ID={feed_id}")  # (ADDED COMMENT)

        updated = self.repo.update_feed(camera_id, feed_id, updates)
        if updated is None:
            logger.warning(
                "[SERVICE] Update feed failed — camera or feed not found"
            )  # (ADDED COMMENT)
            raise NotFoundError("Camera or Feed not found.")

        cam = self.repo.get_camera(camera_id)
        if cam is None:
            raise NotFoundError("Camera not found.")  # safety

        cam.last_known_checkin = datetime.now(timezone.utc)
        cam.last_updated_on = datetime.now(timezone.utc)

        return updated

    # REMOVE FEED
    def remove_feed(self, camera_id: UUID, feed_id: UUID) -> bool:
        logger.info(f"[SERVICE] Removing feed ID={feed_id}")  # (ADDED COMMENT)

        removed = self.repo.remove_feed(camera_id, feed_id)
        if not removed:
            logger.warning(
                "[SERVICE] Failed to remove feed — not found"
            )  # (ADDED COMMENT)
            raise NotFoundError("Camera or Feed not found.")

        cam = self.repo.get_camera(camera_id)
        if cam is None:
            raise NotFoundError("Camera not found.")

        cam.last_known_checkin = datetime.now(timezone.utc)
        cam.last_updated_on = datetime.now(timezone.utc)

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
        logger.info(f"[SERVICE] Listing feeds for camera ID={camera_id}")

        cam = self.repo.get_camera(camera_id)
        if cam is None:
            logger.warning("[SERVICE] Cannot list feeds — camera not found")
            raise NotFoundError("Camera not found.")

        feeds = list(cam.available_feeds)

        if protocol:
            filtered = []
            for f in feeds:
                if f.feed_protocol.lower() == protocol.lower():
                    filtered.append(f)
            feeds = filtered

        if port is not None:
            filtered = []
            for f in feeds:
                if f.feed_port == port:
                    filtered.append(f)
            feeds = filtered

        if q:
            q_lower = q.lower()
            filtered = []
            for f in feeds:
                if q_lower in f.feed_path.lower():
                    filtered.append(f)
            feeds = filtered

        start = (page - 1) * page_size
        end = start + page_size

        logger.info(f"[SERVICE] Returning {len(feeds[start:end])} feeds")
        return feeds[start:end]

    # HEARTBEAT
    def heartbeat(self, camera_id: UUID):
        logger.info(
            f"[SERVICE] Heartbeat received for camera ID={camera_id}"
        )  # (ADDED COMMENT)

        cam = self.repo.get_camera(camera_id)
        if cam is None:
            logger.warning(
                "[SERVICE] Heartbeat failed — camera not found"
            )  # (ADDED COMMENT)
            raise NotFoundError("Camera not found.")

        cam.last_known_checkin = datetime.now(timezone.utc)
        cam.last_updated_on = datetime.now(timezone.utc)

        logger.info("[SERVICE] Heartbeat updated")  # (ADDED COMMENT)
        return {"message": "Heartbeat updated"}

    # ONLINE STATUS
    def is_online(self, camera_id: UUID) -> bool:
        logger.info(
            f"[SERVICE] Checking online status for camera ID={camera_id}"
        )  # (ADDED COMMENT)

        cam = self.repo.get_camera(camera_id)
        if cam is None:
            logger.warning(
                "[SERVICE] Cannot check status — camera not found"
            )  # (ADDED COMMENT)
            raise NotFoundError("Camera not found.")

        if cam.last_known_checkin is None:
            logger.info(
                "[SERVICE] Camera offline — no heartbeat yet"
            )  # (ADDED COMMENT)
            return False

        now = datetime.now(timezone.utc)
        diff = now - cam.last_known_checkin

        if diff.total_seconds() > Config.HEARTBEAT_TIMEOUT:
            logger.info(
                "[SERVICE] Camera offline — heartbeat timeout"
            )  # (ADDED COMMENT)
            return False
        else:
            logger.info("[SERVICE] Camera online — heartbeat OK")  # (ADDED COMMENT)
            return True

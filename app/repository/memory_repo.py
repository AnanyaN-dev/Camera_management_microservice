# I have written the "database" logic here — but this is not a real database.
# This is a simple **in-memory storage** using a Python dictionary.
# in-memory means:
# → Fast
# → Perfect for unit testing
# → No external dependency
# → Automatically resets every application restart
#
# This file contains ONLY data operations (CRUD).
# No business logic here. That belongs in the service layer.

# This memory repository follows the Dependency Inversion Principle because
# it depends on an interface, not on the service,
# and the service depends on the same interface instead of this concrete implementation.

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

# Import Pydantic models
from app.models.schemas import (CameraDetails, CameraUpdate, FeedUpdate,
                                NewCameraData, VideoFeedInfo, VideoFeedSetup)
from app.repository.interface import CameraRepositoryInterface

# Create a logger specific to this module.
# __name__ → "app.repository.memory_repo"
logger = logging.getLogger(__name__)
# We do NOT configure logging here. That is done globally in logging.py.
# Here we only use logger.info(), logger.debug(), logger.warning() to write logs.


class SimpleCameraMemoryStorage(CameraRepositoryInterface):
    """
    A simple in-memory database (dictionary-based).
    This class implements the CameraRepositoryInterface.
    It handles CRUD operations for cameras and their feeds.
    """

    def __init__(self):
        # Internal store (key: camera_id, value: CameraDetails)
        self._store: Dict[UUID, CameraDetails] = {}
        # Key   = camera UUID
        # Value = CameraDetails object
        # _store : this is internal databse of mine

        logger.debug(
            "[REPO INIT] In-memory camera storage initialized."
        )  # (ADDED COMMENT)

    # ADD CAMERA (CREATE)
    def add_camera(self, data: NewCameraData) -> CameraDetails:
        """
        -> function tells it will return either cameradetails.
        IF IT WILL BE -> optional[cameradetails], then it will retuen none or cameradetails
        Create a new camera entry with generated UUID and timestamps.
        """

        logger.info("[REPO] Starting process to add new camera")  # (ADDED COMMENT)

        camera_id = uuid4()  # generate a camera id
        now = datetime.now(timezone.utc)

        # Build feed objects WITH feed_id
        feeds_with_ids: List[VideoFeedInfo] = []
        # data.available_feeds is initialized by Pydantic inside NewCameraData
        for feed in data.available_feeds:
            feed_dict = feed.model_dump()
            # model_dump() is a Pydantic function.
            # It converts a Pydantic object into a normal Python dictionary.

            # Create a new VideoFeedInfo object
            # We are copying the values from feed_dict into this class
            new_feed = VideoFeedInfo(
                feed_protocol=feed_dict["feed_protocol"],
                feed_port=feed_dict["feed_port"],
                feed_path=feed_dict["feed_path"],
                feed_id=uuid4(),
            )
            feeds_with_ids.append(new_feed)

        # Build full camera record
        # The data object is a Pydantic model sent from the API.
        # I convert it into a normal Python dictionary using model_dump() so I can easily access the values using keys.
        cam_dict = data.model_dump()

        camera_record = CameraDetails(
            camera_name=cam_dict["camera_name"],
            camera_model=cam_dict["camera_model"],
            network_setup=cam_dict["network_setup"],
            image_settings=cam_dict["image_settings"],
            available_feeds=feeds_with_ids,
            camera_id=camera_id,
            added_on=now,
            last_updated_on=now,
            last_known_checkin=None,
        )

        # Save inside the dictionary
        self._store[camera_id] = camera_record

        logger.info(
            f"[REPO][ADD_CAMERA] Added camera ID={camera_id}"
        )  # (ADDED COMMENT)
        logger.debug(
            f"[REPO][ADD_CAMERA] Full record: {camera_record}"
        )  # (ADDED COMMENT)

        return camera_record

    # REMOVE CAMERA (DELETE)
    def remove_camera(self, camera_id: UUID) -> bool:
        """
        Remove a camera using its ID.
        """

        logger.info(
            f"[REPO] Request to remove camera ID={camera_id}"
        )  # (ADDED COMMENT)

        if camera_id in self._store:
            del self._store[camera_id]
            logger.info(
                f"[REPO][REMOVE_CAMERA] Removed camera ID={camera_id}"
            )  # (ADDED COMMENT)
            return True
        else:
            logger.debug(
                f"[REPO][REMOVE_CAMERA] Camera ID={camera_id} not found."
            )  # (ADDED COMMENT)
            return False

    # GET CAMERA (READ ONE)
    def get_camera(self, camera_id: UUID) -> Optional[CameraDetails]:
        logger.info(f"[REPO] Fetching camera ID={camera_id}")  # (ADDED COMMENT)

        cam = self._store.get(camera_id)
        # This retrieves your stored CameraDetails object and stores it in a local variable named cam.

        if cam is None:
            logger.debug(
                f"[REPO][GET_CAMERA] Camera ID={camera_id} not found."
            )  # (ADDED COMMENT)
        else:
            logger.debug(
                f"[REPO][GET_CAMERA] Retrieved camera ID={camera_id}"
            )  # (ADDED COMMENT)

        return cam

    # LIST ALL CAMERAS (READ MANY)
    def list_cameras(self) -> List[CameraDetails]:
        logger.info("[REPO] Listing all cameras")  # (ADDED COMMENT)
        logger.debug(
            f"[REPO][LIST_CAMERAS] Count={len(self._store)}"
        )  # (ADDED COMMENT)
        return list(self._store.values())

    # UPDATE CAMERA (PATCH)
    def update_camera(
        self, camera_id: UUID, updates: CameraUpdate
    ) -> Optional[CameraDetails]:

        logger.info(
            f"[REPO] Request to update camera ID={camera_id}"
        )  # (ADDED COMMENT)

        cam = self._store.get(camera_id)
        if cam is None:
            logger.debug(
                f"[REPO][UPDATE_CAMERA] Camera ID={camera_id} not found."
            )  # (ADDED COMMENT)
            return None

        changed = False

        if updates.camera_name is not None:
            cam.camera_name = updates.camera_name
            changed = True

        if updates.camera_model is not None:
            cam.camera_model = updates.camera_model
            changed = True

        if updates.network_setup is not None:
            cam.network_setup = updates.network_setup
            changed = True

        if updates.image_settings is not None:
            cam.image_settings = updates.image_settings
            changed = True

        if changed:
            cam.last_updated_on = datetime.now(timezone.utc)
            self._store[camera_id] = cam
            logger.info(
                f"[REPO][UPDATE_CAMERA] Updated camera ID={camera_id}"
            )  # (ADDED COMMENT)
            logger.debug(
                f"[REPO][UPDATE_CAMERA] Updated record: {cam}"
            )  # (ADDED COMMENT)
        else:
            logger.debug(
                f"[REPO][UPDATE_CAMERA] No fields updated for camera ID={camera_id}"
            )  # (ADDED COMMENT)

        return cam

    # ADD FEED
    def add_feed(
        self, camera_id: UUID, feed: VideoFeedSetup
    ) -> Optional[VideoFeedInfo]:

        logger.info(f"[REPO] Adding feed to camera ID={camera_id}")  # (ADDED COMMENT)

        cam = self._store.get(camera_id)
        if cam is None:
            logger.debug(
                f"[REPO][ADD_FEED] Camera ID={camera_id} not found."
            )  # (ADDED COMMENT)
            return None

        feed_dict = feed.model_dump()

        new_feed = VideoFeedInfo(
            feed_protocol=feed_dict["feed_protocol"],
            feed_port=feed_dict["feed_port"],
            feed_path=feed_dict["feed_path"],
            feed_id=uuid4(),
        )

        cam.available_feeds.append(new_feed)
        cam.last_updated_on = datetime.now(timezone.utc)
        self._store[camera_id] = cam

        logger.info(
            f"[REPO][ADD_FEED] Added feed ID={new_feed.feed_id} to camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return new_feed

    # UPDATE FEED
    def update_feed(
        self, camera_id: UUID, feed_id: UUID, updates: FeedUpdate
    ) -> Optional[VideoFeedInfo]:

        logger.info(
            f"[REPO] Updating feed ID={feed_id} for camera ID={camera_id}"
        )  # (ADDED COMMENT)

        cam = self._store.get(camera_id)
        if cam is None:
            logger.debug(
                f"[REPO][UPDATE_FEED] Camera ID={camera_id} not found."
            )  # (ADDED COMMENT)
            return None

        for idx, feed in enumerate(cam.available_feeds):
            if feed.feed_id == feed_id:

                if updates.feed_protocol is not None:
                    feed.feed_protocol = updates.feed_protocol

                if updates.feed_port is not None:
                    feed.feed_port = updates.feed_port

                if updates.feed_path is not None:
                    feed.feed_path = updates.feed_path

                cam.available_feeds[idx] = feed
                cam.last_updated_on = datetime.now(timezone.utc)
                self._store[camera_id] = cam

                logger.info(
                    f"[REPO][UPDATE_FEED] Updated feed ID={feed_id} for camera ID={camera_id}"
                )  # (ADDED COMMENT)
                logger.debug(
                    f"[REPO][UPDATE_FEED] Updated record: {feed}"
                )  # (ADDED COMMENT)
                return feed

        logger.debug(
            f"[REPO][UPDATE_FEED] Feed ID={feed_id} not found for camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return None

    # REMOVE FEED
    def remove_feed(self, camera_id: UUID, feed_id: UUID) -> bool:

        logger.info(
            f"[REPO] Removing feed ID={feed_id} from camera ID={camera_id}"
        )  # (ADDED COMMENT)

        cam = self._store.get(camera_id)
        if cam is None:
            logger.debug(
                f"[REPO][REMOVE_FEED] Camera ID={camera_id} not found."
            )  # (ADDED COMMENT)
            return False

        for idx, feed in enumerate(cam.available_feeds):
            if feed.feed_id == feed_id:

                cam.available_feeds.pop(idx)
                cam.last_updated_on = datetime.now(timezone.utc)
                self._store[camera_id] = cam

                logger.info(
                    f"[REPO][REMOVE_FEED] Removed feed ID={feed_id} from camera ID={camera_id}"
                )  # (ADDED COMMENT)
                return True

        logger.debug(
            f"[REPO][REMOVE_FEED] Feed ID={feed_id} not found for camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return False

    # GET FEED
    def get_feed(self, camera_id: UUID, feed_id: UUID) -> Optional[VideoFeedInfo]:

        logger.info(
            f"[REPO] Getting feed ID={feed_id} for camera ID={camera_id}"
        )  # (ADDED COMMENT)

        cam = self._store.get(camera_id)
        if cam is None:
            logger.debug(
                f"[REPO][GET_FEED] Camera ID={camera_id} not found."
            )  # (ADDED COMMENT)
            return None

        for feed in cam.available_feeds:
            if feed.feed_id == feed_id:
                return feed

        logger.debug(
            f"[REPO][GET_FEED] Feed ID={feed_id} not found for camera ID={camera_id}"
        )  # (ADDED COMMENT)
        return None

    # LIST FEEDS (RAW - NO FILTERS, NO PAGINATION)
    def list_feeds(
        self,
        camera_id: UUID,
        protocol: str | None = None,
        port: int | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[VideoFeedInfo]:

        logger.info(f"[REPO] Listing feeds for camera ID={camera_id}")

        cam = self._store.get(camera_id)
        if cam is None:
            logger.debug(f"[REPO][LIST_FEEDS] Camera ID={camera_id} not found.")
            return []

        # RETURN ALL FEEDS — no filtering, no pagination
        return list(cam.available_feeds)

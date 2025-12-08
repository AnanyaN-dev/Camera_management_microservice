# This file defines the *interface* (i.e., contract / blueprint) for any camera storage system.
# Why do we need this?
# Because this allows you to change your storage in the future (SQLite → PostgreSQL → Redis → anything)
# without touching the service or API layer.
# This is the "Dependency Inversion Principle" (D in SOLID).

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.models.schemas import (CameraDetails, CameraUpdate, FeedUpdate,
                                NewCameraData, VideoFeedInfo, VideoFeedSetup)


class CameraRepositoryInterface(ABC):
    """
    This interface tells how ANY storage system should behave.

    A storage can be:
        - in-memory dictionary (like our mock DB)
        - SQL database
        - NoSQL database
    """

    @abstractmethod
    def add_camera(self, data: NewCameraData) -> CameraDetails:
        """
        Add a new camera and return the created CameraDetails object.
        """

    @abstractmethod
    def remove_camera(self, camera_id: UUID) -> bool:
        """
        Remove a camera using its ID.
        Returns True if removed, False if not found.
        """

    @abstractmethod
    def get_camera(self, camera_id: UUID) -> Optional[CameraDetails]:
        # -> this is type hint that tells what the fucntion will return.
        # Optional means it will either return  the object or None if not found.
        """
        Fetch a camera using its ID.
        Returns None if not found.
        """

    @abstractmethod
    def list_cameras(self) -> List[CameraDetails]:
        """
        Return a list of ALL stored cameras.
        """

    @abstractmethod
    def update_camera(
        self, camera_id: UUID, updates: CameraUpdate
    ) -> Optional[CameraDetails]:
        """
        Update selective fields of a camera.
        Returns the updated camera or None.
        """

    @abstractmethod
    def add_feed(
        self, camera_id: UUID, feed: VideoFeedSetup
    ) -> Optional[VideoFeedInfo]:
        """
        Add a new feed/stream entry to a camera.
        Returns the VideoFeedInfo or None if camera not found.
        """

    @abstractmethod
    def update_feed(
        self, camera_id: UUID, feed_id: UUID, updates: FeedUpdate
    ) -> Optional[VideoFeedInfo]:
        """
        Update one existing feed/stream of a camera.
        Returns the updated feed or None.
        """

    @abstractmethod
    def remove_feed(self, camera_id: UUID, feed_id: UUID) -> bool:
        """
        Delete a feed belonging to a camera.
        Returns True if removed, False otherwise.
        """

    @abstractmethod
    def get_feed(self, camera_id: UUID, feed_id: UUID) -> Optional[VideoFeedInfo]:
        """
        Fetch one feed for a given camera.
        """

    @abstractmethod
    def list_feeds(
        self,
        camera_id: UUID,
        protocol: str | None = None,
        port: int | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[VideoFeedInfo]:
        """
        Return filtered + paginated list of feeds for a camera.
        """

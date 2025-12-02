# This file contains all the Pydantic models (schemas) used for:
# validating incoming API data (requests)
# shaping outgoing API responses

# Why Pydantic?
# Because Pydantic automatically:
# checks types (ex: int, str, UUID)
# validates values (ex: port range, IP format)
# rejects bad input with clear errors
# converts Python objects → JSON

# These models make sure that ONLY valid and clean data enters your system.

# Because Pydantic cannot express everything using Python types alone.
# Python types only tell:
# this is int
# this is str
# this is list
# Pydantic Field() allows:
# required /mandatory(...) or optional fields
# max length
# min length
# value range
# default factory.for mutable obj.
# metadata for API docs.

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence
from uuid import UUID

from pydantic import BaseModel, Field, IPvAnyAddress

# NETWORK CONFIGURATION MODEL
class CameraNetworkInfo(BaseModel):
    # This represents the network configuration of the camera.
    # Example: IP address like "192.168.0.10"
    ip_address: IPvAnyAddress = Field(
        ...,
        description="The camera's unique IP address (mandatory). Pydantic ensures it is valid.",
    )


# IMAGE QUALITY SETTINGS
class ImageQuality(BaseModel):
    # These are basic image settings (0 to 100) used by cameras.

    brightness: int = Field(
        50,
        ge=0,#minimun
        le=100, #maximun
        description="Brightness level (0-100). Default = 50", #for documentation part for the developers to understand
    )

    contrast: int = Field(
        50,
        ge=0,
        le=100,
        description="Contrast level (0-100). Default = 50",
    )

    saturation: int = Field(
        50,
        ge=0,
        le=100,
        description="Color saturation level (0-100). Default = 50",
    )


# VIDEO FEED (STREAM) SETUP FOR ADDING A NEW FEED
class VideoFeedSetup(BaseModel):
    # A camera can have multiple video feeds or streams (like multiple channels in a TV).
    # These parameters describe how to access one specific feed.

    feed_protocol: str = Field(
        ...,
        pattern="^(rtsp|http)$",
        description="Protocol for the video feed (allowed: 'rtsp' or 'http').",
    )

    feed_port: int = Field(
        ...,
        ge=1,
        le=65535,
        description="Port number for the video feed. Example: 554 for RTSP.",
    )

    feed_path: str = Field(
        "/",
        description="Path component of the stream URL. Example: '/', '/main', '/live'.",
    )

    # NOTE:
    # feed_user and feed_password are NOT included right now.
    # They can be added in the future when implementing authentication.


# VIDEO FEED INFO (WITH feed_id)
class VideoFeedInfo(VideoFeedSetup):
    # Extends VideoFeedSetup and adds a feed_id.
    # feed_id uniquely identifies each stream.
    feed_id: UUID

# NEW CAMERA DATA (REQUEST MODEL)
class NewCameraData(BaseModel):
    # This is the model expected when the user adds a new camera.
    # It contains everything required to set up the camera.

    camera_name: str = Field(
        ...,
        description="A human-readable name for the camera. (Example: 'Entrance Cam 1')",
    )

    camera_model: str = Field(
        ..., description="The make/model of the camera. (Example: 'Sony IMX332')"
    )

    network_setup: CameraNetworkInfo

    image_settings: ImageQuality = Field(
        default_factory=lambda: ImageQuality(
            brightness=50, contrast=50, saturation=50
        ),
        description="Initial image settings. Default = (50,50,50).",
    )

    # available_feeds is a list because a camera may have multiple streams.
    available_feeds: Sequence[VideoFeedSetup] = Field(
        default_factory=list,
        description="List of initial feeds provided by the camera. Can be empty.",
    )

# FULL CAMERA DETAILS (RESPONSE MODEL)
class CameraDetails(NewCameraData):
    # Inherits everything from NewCameraData AND adds additional system fields.

    camera_id: UUID  # The unique identifier of this camera.

    # Response version of feeds (with feed_id)
    available_feeds: List[VideoFeedInfo]

    added_on: datetime  # Timestamp of when the camera was created.
    last_updated_on: datetime  # Timestamp of last modification.
    last_known_checkin: Optional[datetime] = None  # Heartbeat timestamp.


# CAMERA UPDATE MODEL (PATCH REQUEST)
class CameraUpdate(BaseModel):
    # All fields optional → user can update one or multiple fields.

    camera_name: Optional[str] = None
    camera_model: Optional[str] = None
    network_setup: Optional[CameraNetworkInfo] = None
    image_settings: Optional[ImageQuality] = None

# FEED UPDATE MODEL
class FeedUpdate(BaseModel):
    # Optional fields so that PATCH can update selective feed properties.

    feed_protocol: Optional[str] = Field(
        None,
        pattern="^(rtsp|http)$",
        description="New protocol (rtsp/http). Optional.",
    )
    feed_port: Optional[int] = Field(
        None, ge=1, le=65535, description="New port number."
    )
    feed_path: Optional[str] = None

# CAMERA STATUS RESPONSE
class CameraState(BaseModel):
    # Represents camera's online/offline status.

    camera_id: UUID
    is_online: bool
    last_known_checkin: Optional[datetime] = None

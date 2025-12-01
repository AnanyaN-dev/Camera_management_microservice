# This file loads configuration settings for the entire application.
# Why keep a separate config file
# → So that important constants (timeouts, default ports, etc.)
#   are all in ONE place.
# → Easier to change values without touching business logic.
#
# We load values from a `.env` file using python-dotenv module.
# If the value is not present in `.env`, we use the default fallback.

import os

from dotenv import load_dotenv

# Load the .env file into environment variables.
load_dotenv()


class Config:
    """
    Configuration holder for all environment-based or default constants.
    """

    # HEARTBEAT TIMEOUT (SECONDS)
    # If a camera's heartbeat is older than this value → camera is considered OFFLINE.
    HEARTBEAT_TIMEOUT: int = int(os.getenv("HEARTBEAT_TIMEOUT", 60))

    # Default ports for different stream types.
    # These are optional helpers (not used actively in core logic,
    # but useful for future enhancements).
    DEFAULT_RTSP_HQ_PORT: int = int(os.getenv("DEFAULT_RTSP_HQ_PORT", 554))

    DEFAULT_RTSP_LQ_PORT: int = int(os.getenv("DEFAULT_RTSP_LQ_PORT", 8554))

    DEFAULT_HTTP_PORT: int = int(os.getenv("DEFAULT_HTTP_PORT", 8080))

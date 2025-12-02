# This file sets up centralized logging configuration for the entire application.
#
# Why do we use a global logging setup?
# To make all logs across API, service, and repository look consistent.
# To help with debugging, monitoring, and understanding system behavior.
# To avoid having to configure logging separately inside each file.
#
# Logging is VERY important in microservices because:
# It helps catch errors early
# Tracks execution flow
# Makes debugging issues easier
# Helps with production monitoring
#
# Here, we use Python's built-in logging + dictConfig so that:
#  every log includes a timestamp
#  shows which module/file created the log
#  prints log level (INFO, WARNING, ERROR, DEBUG)

import logging
import os
from logging.config import dictConfig
# (ADDED COMMENT): This import is required to enable log file rotation
from logging.handlers import RotatingFileHandler  # (ADDED COMMENT)

# (ADDED) Ensure logs folder exists
os.makedirs("logs", exist_ok=True)  # will create /logs folder

LOG_FILE = "logs/app_logs.json"  # (ADDED COMMENT) log file inside /logs folder

# Formatting and structure for all logs printed by the application.
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    # How log messages should look
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"},
        # (ADDED COMMENT): JSON formatter for structured logs written into a file
        "json": {
            "format": (
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"module": "%(name)s", "message": "%(message)s"}'
            )
        },
    },
    # Where logs should go (console + log file)
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        # (ADDED COMMENT): This writes structured JSON logs into app_logs.json
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "json",
            "filename": LOG_FILE,
            "maxBytes": 2 * 1024 * 1024,  # 2MB size per log file (ADDED COMMENT)
            "backupCount": 3,  # keep last 3 rotated files (ADDED COMMENT)
            "level": "INFO",
        },
    },
    # The ROOT logger configuration:
    # → log level = INFO (you can switch to DEBUG if you want more details)
    # → all logs go to console
    "root": {
        "level": "INFO",
        "handlers": [
            "console",
            "file",  # (ADDED COMMENT): also send logs to JSON file
        ],
    },
}


def setup_logging():
    """
    Apply the above logging configuration globally.
    This should be executed once inside main.py during application startup.
    """
    dictConfig(LOG_CONFIG)

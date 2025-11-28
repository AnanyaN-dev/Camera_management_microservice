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
from logging.config import dictConfig

# Formatting and structure for all logs printed by the application.
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    # How log messages should look
    "formatters": {
        "default": {"format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s"}
    },
    # Where logs should go (for now: console/terminal)
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    # The ROOT logger configuration:
    # → log level = INFO (you can switch to DEBUG if you want more details)
    # → all logs go to console
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}


def setup_logging():
    """
    Apply the above logging configuration globally.
    This should be executed once inside main.py during application startup.
    """
    dictConfig(LOG_CONFIG)

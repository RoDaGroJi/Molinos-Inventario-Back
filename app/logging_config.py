"""
Configuración de logging para la aplicación.
"""

import logging
import logging.config
from .config import get_settings

settings = get_settings()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG" if settings.debug else "INFO",
            "formatter": "detailed" if settings.debug else "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "": {  # root logger
            "level": "DEBUG" if settings.debug else "INFO",
            "handlers": ["console", "file"],
        },
        "sqlalchemy.engine": {
            "level": "INFO" if settings.debug else "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


def setup_logging():
    """Configura el logging de la aplicación."""
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configurado para ambiente: {settings.environment}")
    return logger

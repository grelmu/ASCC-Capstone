import pkg_resources
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = None

#
# Initialize logging - logging via uvicorn is kinda messed up
#

import os
import logging
import logging.config

LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "DEBUG"))
if 'uvicorn.error' in logging.root.manager.loggerDict.keys():
    LOG_LEVEL = logging.getLevelName(logging.getLogger('uvicorn.error').level)

def logger_reconfig():
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(name)s %(asctime)s %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S",

            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            __name__: {
                "handlers": ["default"],
                "level": LOG_LEVEL, 
            },
            "fastapi": {
                "handlers": ["default"],
                "level": LOG_LEVEL, 
            },
            "alembic": {
                "handlers": ["default"],
                "level": LOG_LEVEL, 
            },
            "sqlalchemy": {
                "handlers": ["default"],
                "level": "WARN", 
            },
        },
    })

logger_reconfig()

logger = logging.getLogger(__name__)
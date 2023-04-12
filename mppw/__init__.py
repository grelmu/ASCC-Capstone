import pkg_resources
import importlib_metadata

try:
    __version__ = pkg_resources.get_distribution(__name__).version
except:
    __version__ = None

try:
    distribution = importlib_metadata.Distribution.from_name(__name__)
    with open(distribution.locate_file("MPPW_RELEASE_NOTES.md"), "r") as f:
        RELEASE_NOTES = f.read()
except:
    RELEASE_NOTES = None

#
# Initialize logging - logging via uvicorn is kinda messed up
#

import os
import logging
import logging.config

LOG_LEVEL = logging.getLevelName(os.environ.get("LOG_LEVEL", "DEBUG"))
if "uvicorn.error" in logging.root.manager.loggerDict.keys():
    LOG_LEVEL = logging.getLevelName(logging.getLogger("uvicorn.error").level)


def logger_reconfig():
    logging.config.dictConfig(
        {
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
                "mkdocs": {
                    "handlers": ["default"],
                    "level": LOG_LEVEL,
                },
            },
        }
    )


logger_reconfig()

logger = logging.getLogger(__name__)

try:
    from . import pcl
except ImportError as ex:
    logger.warn(f"Could not load PCL bindings:\n{ex}")

CACHE_DIR = os.environ.get("MPPW_CACHE_DIR", ".mppw/cache")

#
# Rebuild guide files if required
#

_GUIDE_DIR = os.path.join(os.path.dirname(__file__), "guide")
_GUIDE_PREBUILD_SITE_DIR = os.path.join(_GUIDE_DIR, "site")
_GUIDE_CACHE_SITE_DIR = os.path.join(CACHE_DIR, "guide", "site")
_GUIDE_SITE_FORCE_REBUILD = (
    os.environ.get("MPPW_GUIDE_SITE_FORCE_REBUILD", "false").lower() == "true"
)

if os.path.exists(_GUIDE_PREBUILD_SITE_DIR) and not _GUIDE_SITE_FORCE_REBUILD:
    GUIDE_SITE_DIR = _GUIDE_PREBUILD_SITE_DIR
else:
    GUIDE_SITE_DIR = _GUIDE_CACHE_SITE_DIR
    if not os.path.exists(GUIDE_SITE_DIR) or _GUIDE_SITE_FORCE_REBUILD:

        import shutil

        shutil.rmtree(GUIDE_SITE_DIR, ignore_errors=True)
        os.makedirs(GUIDE_SITE_DIR, exist_ok=True)

        import mkdocs.config
        import mkdocs.commands.build

        config = mkdocs.config.load_config(
            os.path.join(os.path.dirname(__file__), "guide", "mkdocs.yml")
        )
        config.docs_dir = os.path.join(_GUIDE_DIR, "docs")
        config.site_dir = GUIDE_SITE_DIR
        mkdocs.commands.build.build(config)

import sys
import logging.config
import os

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

handlers = None


def init(force=False):
    global handlers

    if handlers is not None:
        return

    handlers = []
    if force:
        if sys.stdin.isatty() and sys.stdout.isatty():
            handlers.append("console")
        else:
            if Path("/dev/log").resolve().is_socket():
                handlers.append("syslog")
            else:
                print("panic now!")

    """export AIOPENAPI3_LOGGING_HANDLERS=debug to get /tmp/aiopenapi3-debug.log"""
    handlers.extend(filter(lambda x: len(x), os.environ.get("AIOPENAPI3_LOGGING_HANDLERS", "").split(",")))

    logging.config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "notimestamp": {
                    "class": "logging.Formatter",
                    "format": "%(name)-9s %(levelname)-4s %(message)s",
                },
                "detailed": {
                    "class": "logging.Formatter",
                    "format": "%(asctime)s %(name)-9s %(levelname)-4s %(message)s",
                },
                "plain": {
                    "class": "logging.Formatter",
                    "format": "%(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "DEBUG",
                    "formatter": "plain",
                },
                "syslog": {
                    "class": "logging.handlers.SysLogHandler",
                    "level": "DEBUG",
                    "formatter": "notimestamp",
                    "address": "/dev/log",
                    "facility": "user",
                },
                "debug": {
                    "class": "logging.handlers.WatchedFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": "/tmp/aiopenapi3-debug.log",
                },
            },
            #            "root": {"level": "DEBUG", "handlers": handlers},
            "loggers": {
                "aiopenapi3": {"level": "DEBUG", "handlers": handlers},
                "httpx": {"level": "DEBUG", "propagate": False, "handlers": handlers},
            },
        }
    )

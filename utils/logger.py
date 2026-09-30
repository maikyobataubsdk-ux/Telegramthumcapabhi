import logging
import sys

def setup_logger():
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(stream_handler)

    return logger

logger = setup_logger()

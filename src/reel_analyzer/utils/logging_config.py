import logging
import os

def setup_logging(level: str = "INFO") -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=lvl,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # reduzir barulho de libs
    for noisy in ("httpx", "urllib3"):
        logging.getLogger(noisy).setLevel(os.environ.get("NOISY_LOG_LEVEL", "WARNING"))

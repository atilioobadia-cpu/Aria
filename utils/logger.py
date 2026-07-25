import logging
import sys


def setup_logger(name="aria"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
        )
        handler.terminator = "\n"
        logger.addHandler(handler)
        logger.propagate = False

    class _FlushHandler(logging.StreamHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()

    if logger.handlers:
        old = logger.handlers[0]
        flush_handler = _FlushHandler(stream=old.stream)
        flush_handler.setFormatter(old.formatter)
        logger.removeHandler(old)
        logger.addHandler(flush_handler)
    return logger

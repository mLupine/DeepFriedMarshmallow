import logging
import os


logger = logging.getLogger("DeepFriedMarshmallow")
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [Deep-Fried Marshmallow] %(message)s"))

if logger.level == logging.NOTSET:
    try:
        logger.setLevel(os.getenv("DFM_LOG_LEVEL", logging.WARN))
        sh.setLevel(os.getenv("DFM_LOG_LEVEL", logging.WARN))
    except ValueError:
        logger.setLevel(logging.WARN)
        sh.setLevel(logging.WARN)

logger.addHandler(sh)

import logging
import os

if os.getenv("DFM_LOG_LEVEL", None) is not None:
    logger = logging.getLogger("DeepFriedMarshmallow")

    if logger.level == logging.NOTSET:
        try:
            logger.setLevel(os.getenv("DFM_LOG_LEVEL", logging.WARN))
        except ValueError:
            logger.setLevel(logging.WARN)

        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [Deep-Fried Marshmallow] %(message)s"))
        sh.setLevel(logging.DEBUG)
        logger.addHandler(sh)
else:

    class DummyLogger:
        def __getattr__(self, item):
            def noop(*args, **kwargs):
                pass

            return noop

    logger = DummyLogger()

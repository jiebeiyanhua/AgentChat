import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def times(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.process_time()
        result = func(*args, **kwargs)
        end_time = time.process_time()
        logger.info("Function '%s' executed in %.4f seconds.", func.__name__, end_time - start_time)
        return result

    return wrapper

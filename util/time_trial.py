import time
from functools import wraps


def times(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        start_time = time.process_time()
        result = func(*args,**kwargs)
        end_time = time.process_time()
        print(f"本次执行所花费了{end_time-start_time:4f}秒")
        return result
    return wrapper



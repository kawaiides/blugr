from tqdm import tqdm
from functools import wraps
import multiprocessing.pool

def timeout(max_timeout):
    """Timeout decorator, parameter in seconds."""
    def timeout_decorator(item):
        """Wrap the original function."""
        @wraps(item)
        def func_wrapper(*args, **kwargs):
            """Closure for function."""
            pool = multiprocessing.pool.ThreadPool(processes=1)
            async_result = pool.apply_async(item, args, kwargs)
            # raises a TimeoutError if execution exceeds max_timeout
            return async_result.get(max_timeout)
        return func_wrapper
    return timeout_decorator

# Decorator to add tqdm progress bar to any function
def with_tqdm(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Use tqdm to wrap the function's execution
        with tqdm(total=1, desc=func.__name__) as pbar:
            result = func(*args, **kwargs)
            pbar.update(1)  # Update progress bar when function completes
        return result
    return wrapper


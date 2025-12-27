"""
Exercise 5: Rate Limiter Decorator

Create a decorator that limits function call frequency.
See EXERCISES.md for full requirements.
"""

import time
from functools import wraps


def rate_limit(max_calls=3, time_window=5):
    """
    TODO: Implement rate limiter decorator
    
    Requirements:
    - Accept max_calls and time_window (seconds) as parameters
    - Track call timestamps
    - Raise exception if rate limit exceeded
    - Remove old timestamps outside the time window
    """
    def decorator(func):
        # Store timestamps in closure
        call_times = []
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            pass  # Replace with your implementation
        return wrapper
    return decorator


# Test cases
if __name__ == "__main__":
    @rate_limit(max_calls=3, time_window=5)
    def api_call(endpoint):
        return f"Called {endpoint}"
    
    @rate_limit(max_calls=2, time_window=3)
    def limited_function(x):
        return x * 2
    
    # Test
    print(api_call("/users"))
    print(api_call("/posts"))
    print(api_call("/comments"))
    
    try:
        print(api_call("/likes"))  # Should raise exception
    except Exception as e:
        print(f"Caught expected error: {e}")
    
    # Wait and try again
    print("\nWaiting 5 seconds...")
    time.sleep(5)
    print(api_call("/likes"))  # Should work now
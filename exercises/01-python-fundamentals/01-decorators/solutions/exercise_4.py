"""
Exercise 4: Retry Decorator with Exponential Backoff

Create a decorator that retries failed function calls.
See EXERCISES.md for full requirements.
"""

import time
from functools import wraps


def retry(max_attempts=3, base_delay=1):
    """
    TODO: Implement retry decorator with exponential backoff
    
    Requirements:
    - Accept max_attempts and base_delay as parameters
    - Wait base_delay * (2 ** attempt) seconds between retries
    - Raise the exception if all attempts fail
    - Print retry information
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            pass  # Replace with your implementation
        return wrapper
    return decorator


# Test cases
if __name__ == "__main__":
    import random
    
    @retry(max_attempts=3, base_delay=1)
    def unreliable_function():
        """Succeeds 30% of the time"""
        if random.random() < 0.7:
            raise ConnectionError("Connection failed")
        return "Success!"
    
    @retry(max_attempts=5, base_delay=0.5)
    def flaky_api():
        """Succeeds 50% of the time"""
        if random.random() < 0.5:
            raise ValueError("API error")
        return {"status": "ok"}
    
    # Test
    try:
        result = unreliable_function()
        print(f"Result: {result}")
    except ConnectionError as e:
        print(f"Failed after all retries: {e}")
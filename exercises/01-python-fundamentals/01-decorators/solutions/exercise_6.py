"""
Exercise 6: Memoization with TTL (Time-To-Live)

Create a decorator that caches results with expiration.
See EXERCISES.md for full requirements.
"""

import time
from functools import wraps


def memoize_with_ttl(ttl=60):
    """
    TODO: Implement memoization with TTL decorator
    
    Requirements:
    - Accept ttl (time-to-live in seconds) as parameter
    - Store results with timestamps
    - Return cached result if not expired
    - Recalculate if cache expired or doesn't exist
    """
    def decorator(func):
        # Store cache in closure: {args: (result, timestamp)}
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            pass  # Replace with your implementation
        return wrapper
    return decorator


# Test cases
if __name__ == "__main__":
    @memoize_with_ttl(ttl=2)
    def expensive_calculation(x):
        print(f"Computing {x}**2...")
        time.sleep(1)
        return x ** 2
    
    @memoize_with_ttl(ttl=3)
    def fetch_data(url):
        print(f"Fetching {url}...")
        time.sleep(0.5)
        return f"Data from {url}"
    
    # Test
    print("First call (should compute):")
    print(expensive_calculation(5))
    
    print("\nSecond call (should use cache):")
    print(expensive_calculation(5))
    
    print("\nWaiting 3 seconds for cache to expire...")
    time.sleep(3)
    
    print("\nThird call (should compute again):")
    print(expensive_calculation(5))
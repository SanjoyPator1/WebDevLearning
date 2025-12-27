"""
Exercise 10: Decorator Chain Challenge

Combine multiple decorators and understand execution order.
See EXERCISES.md for full requirements.
"""

import time
import random
from functools import wraps


# Import or reimplement decorators from previous exercises
def timer(func):
    """Measures execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        print(f"{func.__name__} took {duration:.4f} seconds")
        return result
    return wrapper


def log(func):
    """Logs function calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"[LOG] {func.__name__} returned {result}")
        return result
    return wrapper


def retry(max_attempts=3, base_delay=1):
    """Retries function on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"All {max_attempts} attempts failed.")
                        raise
        return wrapper
    return decorator


def memoize_with_ttl(ttl=60):
    """Caches results with expiration"""
    def decorator(func):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            current_time = time.time()
            
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl:
                    print(f"[CACHE] Returning cached result for {func.__name__}")
                    return result
            
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
        return wrapper
    return decorator


# TODO: Apply decorators in the correct order
# Think about: Which decorator should be outermost? Innermost?
# Experiment with different orders and observe the behavior

def flaky_fetch(url):
    """
    Simulates an unreliable API call that sometimes fails.
    
    TODO: Decorate this function with:
    - @timer (to measure total time)
    - @log (to log each attempt)
    - @retry (to retry on failure)
    - @memoize_with_ttl (to cache successful results)
    
    Challenge: Find the right order!
    """
    print(f"  -> Executing flaky_fetch for {url}")
    if random.random() < 0.6:
        raise ConnectionError("Network error")
    return f"Data from {url}"


# Test cases
if __name__ == "__main__":
    print("=" * 60)
    print("Testing decorator chain")
    print("=" * 60)
    
    try:
        result = flaky_fetch("https://api.example.com/data")
        print(f"\nFinal result: {result}\n")
    except ConnectionError as e:
        print(f"\nFailed: {e}\n")
    
    # Try calling again (should use cache if first call succeeded)
    print("=" * 60)
    print("Second call (testing cache)")
    print("=" * 60)
    try:
        result = flaky_fetch("https://api.example.com/data")
        print(f"\nFinal result: {result}\n")
    except ConnectionError as e:
        print(f"\nFailed: {e}\n")
    
    print("=" * 60)
    print("\nChallenge Questions:")
    print("1. What order did you apply the decorators?")
    print("2. Why does decorator order matter?")
    print("3. What happens if you reverse the order?")
    print("4. Which decorator sees the original function?")
    print("5. Which decorator sees all the others?")
    print("=" * 60)
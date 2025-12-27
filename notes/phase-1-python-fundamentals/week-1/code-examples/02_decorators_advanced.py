"""
Day 2: Advanced Decorators - Code Examples
"""

import time
import functools
from typing import Any, Callable


# ============================================================================
# Example 1: Decorator with Parameters (Decorator Factory)
# ============================================================================

def repeat(times: int):
    """Decorator factory that repeats function execution"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


@repeat(times=3)
def greet(name: str):
    print(f"Hello, {name}!")
    return f"Greeted {name}"


# ============================================================================
# Example 2: Rate Limiter Decorator
# ============================================================================

def rate_limit(max_calls: int, period: float):
    """Limit function calls to max_calls per period (seconds)"""
    def decorator(func: Callable) -> Callable:
        calls = []
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls outside the period
            calls[:] = [call_time for call_time in calls if now - call_time < period]
            
            if len(calls) >= max_calls:
                raise Exception(f"Rate limit: {max_calls} calls per {period}s")
            
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator


@rate_limit(max_calls=3, period=5)
def api_call(endpoint: str):
    return f"Called {endpoint}"


# ============================================================================
# Example 3: Retry Decorator with Exponential Backoff
# ============================================================================

def retry(max_attempts: int = 3, base_delay: float = 1):
    """Retry decorator with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator


@retry(max_attempts=3, base_delay=0.5)
def unreliable_function():
    import random
    if random.random() < 0.7:
        raise ConnectionError("Simulated failure")
    return "Success!"


# ============================================================================
# Example 4: Class-Based Decorator
# ============================================================================

class CountCalls:
    """Decorator that counts function calls"""
    
    def __init__(self, func: Callable):
        functools.update_wrapper(self, func)
        self.func = func
        self.count = 0
    
    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"Call {self.count} of {self.func.__name__}")
        return self.func(*args, **kwargs)
    
    def reset_count(self):
        """Reset the call counter"""
        self.count = 0


@CountCalls
def process_data(data: Any):
    return f"Processed: {data}"


# ============================================================================
# Example 5: Class-Based Decorator with Parameters
# ============================================================================

class Cached:
    """Class-based caching decorator with TTL"""
    
    def __init__(self, ttl: float = 60):
        self.ttl = ttl
        self.cache = {}
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from arguments
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            
            # Check if cached and not expired
            if key in self.cache:
                result, timestamp = self.cache[key]
                if now - timestamp < self.ttl:
                    print(f"Cache hit for {key}")
                    return result
            
            # Calculate and cache
            result = func(*args, **kwargs)
            self.cache[key] = (result, now)
            return result
        return wrapper


@Cached(ttl=5)
def expensive_operation(x: int, y: int):
    print(f"Computing {x} + {y}")
    time.sleep(1)
    return x + y


# ============================================================================
# Example 6: Method Decorator
# ============================================================================

def method_timer(func: Callable) -> Callable:
    """Timer decorator specifically for methods"""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start = time.time()
        result = func(self, *args, **kwargs)
        end = time.time()
        print(f"{self.__class__.__name__}.{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper


class DataProcessor:
    @method_timer
    def process(self, data):
        time.sleep(0.5)
        return f"Processed {len(data)} items"


# ============================================================================
# Example 7: Authentication Decorator
# ============================================================================

# Simulated user for demo
current_user = {"name": "Alice", "authenticated": True, "roles": ["admin"]}


def require_auth(func: Callable) -> Callable:
    """Require authentication"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.get("authenticated"):
            raise PermissionError("Authentication required")
        return func(*args, **kwargs)
    return wrapper


def require_role(role: str):
    """Require specific role"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if role not in current_user.get("roles", []):
                raise PermissionError(f"Role '{role}' required")
            return func(*args, **kwargs)
        return wrapper
    return decorator


@require_auth
@require_role("admin")
def delete_user(user_id: int):
    return f"Deleted user {user_id}"


# ============================================================================
# Example 8: Deprecation Warning
# ============================================================================

import warnings


def deprecated(reason: str = None, replacement: str = None):
    """Mark function as deprecated"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"{func.__name__} is deprecated"
            if reason:
                msg += f": {reason}"
            if replacement:
                msg += f". Use {replacement} instead"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator


@deprecated(reason="Use new_api instead", replacement="new_api")
def old_api(data):
    return f"Old: {data}"


# ============================================================================
# Example 9: Chaining Decorators
# ============================================================================

def log_calls(func: Callable) -> Callable:
    """Log function calls"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper


def convert_to_upper(func: Callable) -> Callable:
    """Convert string result to uppercase"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, str):
            return result.upper()
        return result
    return wrapper


@log_calls
@convert_to_upper
def get_message():
    return "hello world"


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Repeat Decorator")
    print("=" * 60)
    result = greet("Bob")
    print(f"Final result: {result}\n")
    
    print("=" * 60)
    print("Example 2: Rate Limiter")
    print("=" * 60)
    try:
        for i in range(5):
            print(api_call(f"/api/endpoint{i}"))
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}\n")
    
    print("=" * 60)
    print("Example 3: Retry Decorator")
    print("=" * 60)
    try:
        result = unreliable_function()
        print(f"Result: {result}\n")
    except Exception as e:
        print(f"Failed after retries: {e}\n")
    
    print("=" * 60)
    print("Example 4: Class-Based Decorator - Call Counter")
    print("=" * 60)
    process_data("item1")
    process_data("item2")
    print(f"Total calls: {process_data.count}\n")
    
    print("=" * 60)
    print("Example 5: Cached Decorator with TTL")
    print("=" * 60)
    print(expensive_operation(5, 3))
    print(expensive_operation(5, 3))  # Should use cache
    time.sleep(6)  # Wait for cache to expire
    print(expensive_operation(5, 3))  # Should recompute
    print()
    
    print("=" * 60)
    print("Example 6: Method Decorator")
    print("=" * 60)
    processor = DataProcessor()
    processor.process([1, 2, 3, 4, 5])
    print()
    
    print("=" * 60)
    print("Example 7: Authentication Decorator")
    print("=" * 60)
    try:
        result = delete_user(123)
        print(result)
    except PermissionError as e:
        print(f"Error: {e}")
    print()
    
    print("=" * 60)
    print("Example 8: Deprecation Warning")
    print("=" * 60)
    old_api("test data")
    print()
    
    print("=" * 60)
    print("Example 9: Chaining Decorators")
    print("=" * 60)
    message = get_message()
    print(f"Final message: {message}")

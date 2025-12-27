# Day 2: Decorators - Advanced

**Date**: Week 1, Day 2  
**Phase**: 1 - Python Fundamentals  
**Topic**: Advanced Decorator Patterns

---

## Learning Objectives

- Create decorators that accept arguments
- Build decorator factories
- Understand class-based decorators
- Chain decorators effectively
- Apply decorators to methods

---

## Decorators with Arguments

Sometimes you want to configure decorator behavior. To do this, you need a decorator factory - a function that returns a decorator.

### The Pattern

```python
def decorator_factory(arg1, arg2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Use arg1 and arg2 here
            return func(*args, **kwargs)
        return wrapper
    return decorator

@decorator_factory("config1", "config2")
def my_function():
    pass
```

### Example: Repeat Decorator with Count

```python
from functools import wraps

def repeat(times):
    """Decorator factory that repeats function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                result = func(*args, **kwargs)
            return result  # Return last result
        return wrapper
    return decorator

@repeat(times=3)
def greet(name):
    print(f"Hello, {name}!")
    
greet("Alice")  # Prints 3 times
```

### Example: Rate Limiter

```python
import time
from functools import wraps

def rate_limit(max_calls, period):
    """Limit function calls to max_calls per period (in seconds)"""
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Remove calls outside the period
            calls[:] = [call for call in calls if now - call < period]
            
            if len(calls) >= max_calls:
                raise Exception(f"Rate limit exceeded: {max_calls} calls per {period}s")
            
            calls.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=3, period=10)
def api_call():
    print("API called")
```

### Example: Retry Decorator

```python
import time
from functools import wraps

def retry(max_attempts=3, delay=1):
    """Retry failed function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise
                    print(f"Attempt {attempts} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2)
def unreliable_function():
    import random
    if random.random() < 0.7:
        raise Exception("Random failure")
    return "Success"
```

---

## Class-Based Decorators

Decorators can also be classes that implement `__call__`:

```python
from functools import wraps

class CountCalls:
    """Decorator that counts function calls"""
    
    def __init__(self, func):
        wraps(func)(self)
        self.func = func
        self.count = 0
    
    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"Call {self.count} of {self.func.__name__}")
        return self.func(*args, **kwargs)

@CountCalls
def say_hello():
    print("Hello!")

say_hello()  # Call 1 of say_hello
say_hello()  # Call 2 of say_hello
```

### Class-Based Decorator with Arguments

```python
from functools import wraps

class Retry:
    """Class-based retry decorator with configuration"""
    
    def __init__(self, max_attempts=3, delay=1):
        self.max_attempts = max_attempts
        self.delay = delay
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < self.max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= self.max_attempts:
                        raise
                    time.sleep(self.delay)
        return wrapper

@Retry(max_attempts=5, delay=2)
def flaky_operation():
    pass
```

---

## Method Decorators

Decorators can be applied to methods, but you need to handle the `self` parameter:

```python
from functools import wraps

def method_timer(func):
    """Timer decorator for methods"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start = time.time()
        result = func(self, *args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f}s")
        return result
    return wrapper

class Calculator:
    @method_timer
    def slow_calculation(self, x):
        time.sleep(1)
        return x * 2
```

---

## Preserving Decorators Information

Use `functools.wraps` and handle signatures properly:

```python
from functools import wraps
import inspect

def smart_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Access original function's signature
        sig = inspect.signature(func)
        print(f"Function signature: {sig}")
        return func(*args, **kwargs)
    return wrapper
```

---

## Decorator Chaining Best Practices

Order matters when stacking decorators:

```python
@timer        # Applied last (outermost)
@logger       # Applied second
@validate     # Applied first (innermost)
def my_function():
    pass

# Equivalent to:
my_function = timer(logger(validate(my_function)))
```

---

## Common Patterns

### 1. Authentication Decorator

```python
def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not user_is_authenticated():
            raise PermissionError("Authentication required")
        return func(*args, **kwargs)
    return wrapper
```

### 2. Permission Decorator

```python
def require_permission(permission):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not user_has_permission(permission):
                raise PermissionError(f"Permission '{permission}' required")
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_permission("admin")
def delete_user(user_id):
    pass
```

### 3. Deprecation Warning

```python
import warnings

def deprecated(replacement=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"{func.__name__} is deprecated"
            if replacement:
                msg += f", use {replacement} instead"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@deprecated(replacement="new_function")
def old_function():
    pass
```

---

## Key Takeaways

1. **Decorator factories** enable parameterized decorators
2. **Class-based decorators** provide state management
3. **Method decorators** need to handle `self` parameter
4. **Order matters** when stacking multiple decorators
5. **Always use `@wraps`** to preserve metadata

---

## Practice Exercises

See: `exercises/python-fundamentals/decorators/EXERCISES.md` (Exercises 5-8)

---

## Code Examples

All runnable code: `code-examples/02_decorators_advanced.py`

---

## Tomorrow's Topic

**Day 3: Context Managers** - The `with` statement and `__enter__`/`__exit__` methods.

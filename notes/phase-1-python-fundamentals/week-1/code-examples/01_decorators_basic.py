"""
Day 1: Decorators - Basic Examples
All code examples from the day-1-decorators-basics.md notes
"""

import time
from functools import wraps


# ============================================================================
# Example 1: Basic Decorator (No Arguments)
# ============================================================================

def my_decorator(func):
    """Basic decorator that adds behavior before and after function call"""
    def wrapper():
        print("Something before the function")
        func()
        print("Something after the function")
    return wrapper


@my_decorator
def say_hello():
    print("Hello!")


# ============================================================================
# Example 2: Decorator with Function Arguments
# ============================================================================

def my_decorator_with_args(func):
    """Decorator that handles functions with arguments"""
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Finished {func.__name__}")
        return result
    return wrapper


@my_decorator_with_args
def add(a, b):
    """Add two numbers"""
    return a + b


@my_decorator_with_args
def greet(name, greeting="Hello"):
    """Greet someone with a custom greeting"""
    return f"{greeting}, {name}!"


# ============================================================================
# Example 3: Using @wraps to Preserve Metadata
# ============================================================================

def decorator_without_wraps(func):
    """Decorator without @wraps - loses metadata"""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def decorator_with_wraps(func):
    """Decorator with @wraps - preserves metadata"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


@decorator_without_wraps
def function_a():
    """This is function A"""
    pass


@decorator_with_wraps
def function_b():
    """This is function B"""
    pass


# ============================================================================
# Example 4: Timer Decorator
# ============================================================================

def timer(func):
    """Decorator to measure execution time of a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper


@timer
def slow_function():
    """Simulates a slow function"""
    time.sleep(1)
    return "Done"


@timer
def fast_function():
    """A fast function"""
    return sum(range(1000))


# ============================================================================
# Example 5: Logger Decorator
# ============================================================================

def logger(func):
    """Decorator that logs function calls and results"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper


@logger
def multiply(a, b):
    """Multiply two numbers"""
    return a * b


@logger
def power(base, exponent=2):
    """Raise base to the power of exponent"""
    return base ** exponent


# ============================================================================
# Example 6: Input Validation Decorator
# ============================================================================

def validate_positive(func):
    """Decorator to ensure the argument is positive"""
    @wraps(func)
    def wrapper(x):
        if x < 0:
            raise ValueError(f"Number must be positive, got {x}")
        return func(x)
    return wrapper


@validate_positive
def square_root(x):
    """Calculate square root of a positive number"""
    return x ** 0.5


@validate_positive
def factorial_simple(n):
    """Calculate factorial of a positive number"""
    if n == 0:
        return 1
    return n * factorial_simple(n - 1)


# ============================================================================
# Example 7: Memoization/Caching Decorator
# ============================================================================

def memoize(func):
    """Decorator that caches function results"""
    cache = {}
    
    @wraps(func)
    def wrapper(*args):
        if args in cache:
            print(f"Returning cached result for {args}")
            return cache[args]
        print(f"Computing result for {args}")
        result = func(*args)
        cache[args] = result
        return result
    return wrapper


@memoize
def fibonacci(n):
    """Calculate nth Fibonacci number"""
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


@memoize
def expensive_calculation(x, y):
    """Simulate an expensive calculation"""
    time.sleep(0.5)  # Simulate delay
    return x ** y


# ============================================================================
# Example 8: Multiple Decorators
# ============================================================================

def bold(func):
    """Wrap result in <b> tags"""
    @wraps(func)
    def wrapper():
        return "<b>" + func() + "</b>"
    return wrapper


def italic(func):
    """Wrap result in <i> tags"""
    @wraps(func)
    def wrapper():
        return "<i>" + func() + "</i>"
    return wrapper


def underline(func):
    """Wrap result in <u> tags"""
    @wraps(func)
    def wrapper():
        return "<u>" + func() + "</u>"
    return wrapper


@bold
@italic
@underline
def greet_styled():
    """Return a greeting"""
    return "Hello, World!"


# ============================================================================
# Example 9: Repeat Decorator
# ============================================================================

def repeat(func):
    """Decorator that calls the function twice"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func(*args, **kwargs)
        func(*args, **kwargs)
    return wrapper


@repeat
def say_hi():
    """Say hi"""
    print("Hi!")


# ============================================================================
# Example 10: Debug Decorator
# ============================================================================

def debug(func):
    """Decorator for debugging - prints function signature and return value"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        args_repr = [repr(a) for a in args]
        kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        print(f"Calling {func.__name__}({signature})")
        result = func(*args, **kwargs)
        print(f"{func.__name__!r} returned {result!r}")
        return result
    return wrapper


@debug
def make_greeting(name, age=None):
    """Create a greeting message"""
    if age is None:
        return f"Hi, {name}!"
    return f"Hi, {name}! You are {age} years old."


# ============================================================================
# Main Execution - Uncomment sections to test
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Example 1: Basic Decorator")
    print("=" * 60)
    say_hello()
    print()
    
    print("=" * 60)
    print("Example 2: Decorator with Arguments")
    print("=" * 60)
    result = add(5, 3)
    print(f"Result: {result}")
    print()
    result = greet("Alice", greeting="Hi")
    print(f"Result: {result}")
    print()
    
    print("=" * 60)
    print("Example 3: Metadata Preservation")
    print("=" * 60)
    print(f"Without @wraps: {function_a.__name__}, {function_a.__doc__}")
    print(f"With @wraps: {function_b.__name__}, {function_b.__doc__}")
    print()
    
    print("=" * 60)
    print("Example 4: Timer Decorator")
    print("=" * 60)
    slow_function()
    fast_function()
    print()
    
    print("=" * 60)
    print("Example 5: Logger Decorator")
    print("=" * 60)
    multiply(5, 3)
    power(2, 3)
    power(5)  # Using default exponent
    print()
    
    print("=" * 60)
    print("Example 6: Input Validation")
    print("=" * 60)
    print(f"Square root of 16: {square_root(16)}")
    try:
        print(square_root(-4))
    except ValueError as e:
        print(f"Error: {e}")
    print()
    
    print("=" * 60)
    print("Example 7: Memoization")
    print("=" * 60)
    print(f"Fibonacci(10): {fibonacci(10)}")
    print(f"Fibonacci(10) again: {fibonacci(10)}")  # Uses cache
    print()
    print(f"Expensive calc(2, 10): {expensive_calculation(2, 10)}")
    print(f"Expensive calc(2, 10) again: {expensive_calculation(2, 10)}")
    print()
    
    print("=" * 60)
    print("Example 8: Multiple Decorators")
    print("=" * 60)
    print(greet_styled())
    print()
    
    print("=" * 60)
    print("Example 9: Repeat Decorator")
    print("=" * 60)
    say_hi()
    print()
    
    print("=" * 60)
    print("Example 10: Debug Decorator")
    print("=" * 60)
    make_greeting("Bob")
    make_greeting("Alice", age=30)
    print()

"""
Exercise 2: Logging Decorator

Create a decorator that logs function calls.
See EXERCISES.md for full requirements.
"""

from functools import wraps


def log(func):
    """
    TODO: Implement logging decorator
    
    Requirements:
    - Log function name, args, and kwargs before call
    - Log return value after call
    - Handle both positional and keyword arguments
    """
    pass  # Replace with your implementation


# Test cases
if __name__ == "__main__":
    @log
    def add(a, b):
        return a + b
    
    @log
    def greet(name, greeting="Hello"):
        return f"{greeting}, {name}!"
    
    # Test
    print(add(5, 3))
    print(greet("Alice"))
    print(greet("Bob", greeting="Hi"))

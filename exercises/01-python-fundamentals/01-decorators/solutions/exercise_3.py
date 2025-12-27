"""
Exercise 3: Validation Decorator

Create a decorator that validates function argument types.
See EXERCISES.md for full requirements.
"""

from functools import wraps
from typing import get_type_hints
import inspect


def validate_types(func):
    """
    TODO: Implement type validation decorator
    
    Requirements:
    - Check if arguments match function's type hints
    - Raise TypeError if types don't match
    - Work with both positional and keyword arguments
    - Use typing.get_type_hints() and inspect.signature()
    """
    pass  # Replace with your implementation


# Test cases
if __name__ == "__main__":
    @validate_types
    def divide(a: int, b: int) -> float:
        return a / b
    
    @validate_types
    def greet(name: str, age: int) -> str:
        return f"{name} is {age} years old"
    
    # Test valid calls
    print(divide(10, 2))
    print(greet("Alice", 25))
    
    # Test invalid calls (should raise TypeError)
    try:
        divide("10", 2)
    except TypeError as e:
        print(f"Caught expected error: {e}")
    
    try:
        greet("Bob", "twenty")
    except TypeError as e:
        print(f"Caught expected error: {e}")
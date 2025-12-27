"""
Exercise 8: Deprecation Warning Decorator

Create a decorator that warns about deprecated functions.
See EXERCISES.md for full requirements.
"""

import warnings
from functools import wraps


def deprecated(reason=None, replacement=None):
    """
    TODO: Implement deprecation warning decorator
    
    Requirements:
    - Accept optional reason and replacement parameters
    - Use Python's warnings module
    - Still execute the function
    - Show warning with proper message formatting
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            pass  # Replace with your implementation
        return wrapper
    return decorator


# Test cases
if __name__ == "__main__":
    @deprecated(reason="Use new_function instead", replacement="new_function")
    def old_function(x):
        return x * 2
    
    @deprecated()
    def another_old_function(x, y):
        return x + y
    
    @deprecated(replacement="calculate_total_v2")
    def calculate_total(items):
        return sum(items)
    
    # Test
    print("Calling deprecated functions:")
    print(old_function(5))
    print(another_old_function(3, 7))
    print(calculate_total([1, 2, 3, 4]))
    
    # Note: Warnings are shown in stderr, not stdout
    # Run with: python -W all exercise_8.py to see all warnings
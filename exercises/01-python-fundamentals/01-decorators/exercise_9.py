"""
Exercise 9: Class-Based Decorator with State

Create a class-based decorator that tracks call counts.
See EXERCISES.md for full requirements.
"""

from functools import update_wrapper


class CallCounter:
    """
    TODO: Implement class-based decorator
    
    Requirements:
    - Use __init__ and __call__ methods
    - Track call count as instance variable
    - Preserve function metadata
    - Allow access to call_count attribute
    """
    
    def __init__(self, func):
        pass  # Replace with your implementation
    
    def __call__(self, *args, **kwargs):
        pass  # Replace with your implementation


# Test cases
if __name__ == "__main__":
    @CallCounter
    def function_a():
        return "A"
    
    @CallCounter
    def function_b(x):
        return f"B({x})"
    
    @CallCounter
    def function_c(x, y):
        return x + y
    
    # Test
    print(function_a())
    print(function_a())
    print(function_a())
    
    print(function_b(1))
    print(function_b(2))
    
    print(function_c(5, 3))
    
    # Check counts
    print(f"\nfunction_a called {function_a.call_count} times")
    print(f"function_b called {function_b.call_count} times")
    print(f"function_c called {function_c.call_count} times")
    
    # Check metadata preservation
    print(f"\nfunction_a name: {function_a.__name__}")
    print(f"function_a doc: {function_a.__doc__}")
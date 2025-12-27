"""
Exercise 1: Basic Timer Decorator

Create a decorator that measures and prints execution time.
See EXERCISES.md for full requirements.
"""

import time
from functools import wraps


def timer(func):
    """
    TODO: Implement timer decorator
    
    Requirements:
    - Measure execution time using time.time()
    - Print function name and time taken
    - Return the function's result
    - Use @wraps to preserve metadata
    """
    pass  # Replace with your implementation


# Test cases
if __name__ == "__main__":
    @timer
    def slow_function():
        time.sleep(2)
        return "Done"
    
    @timer
    def fast_function():
        return sum(range(1000))
    
    # Test
    print("Testing slow_function:")
    result1 = slow_function()
    print(f"Result: {result1}\n")
    
    print("Testing fast_function:")
    result2 = fast_function()
    print(f"Result: {result2}")

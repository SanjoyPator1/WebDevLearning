# Python Fundamentals - Decorators Exercises

**Topic**: Decorators (Days 1-2)  
**Difficulty**: Beginner to Intermediate  
**Total Exercises**: 10

---

## Instructions

- Solve each exercise in the corresponding Python file (exercise_1.py, exercise_2.py, etc.)
- Test your solutions by running the files
- Save your completed solutions in the `solutions/` folder
- Try to solve without looking at hints first
- Each exercise builds on previous concepts

---

## Exercise 1: Basic Timer Decorator

**Difficulty**: Easy  
**File**: `exercise_1.py`

Create a decorator called `@timer` that measures and prints how long a function takes to execute.

**Requirements**:
- Print the function name and execution time
- Return the function's result
- Use `time.time()` for timing
- Don't forget `@wraps`!

**Example Usage**:
```python
@timer
def slow_function():
    time.sleep(2)
    return "Done"

result = slow_function()
# Should print: slow_function took 2.00xx seconds
# Should return: "Done"
```

**Hints**:
- Import `time` and `functools.wraps`
- Store start time before calling function
- Calculate duration after function returns

---

## Exercise 2: Logging Decorator with Levels

**Difficulty**: Easy  
**File**: `exercise_2.py`

Create a decorator `@log` that logs function calls with different log levels (INFO, DEBUG, ERROR).

**Requirements**:
- Log function name, arguments, and return value
- Handle both positional and keyword arguments
- Format the log message nicely
- Return the function's result unchanged

**Example Usage**:
```python
@log
def add(a, b):
    return a + b

@log
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

add(5, 3)
# Output: [LOG] Calling add with args=(5, 3), kwargs={}
# Output: [LOG] add returned 8

greet("Alice", greeting="Hi")
# Output: [LOG] Calling greet with args=('Alice',), kwargs={'greeting': 'Hi'}
# Output: [LOG] greet returned Hi, Alice!
```

---

## Exercise 3: Validation Decorator

**Difficulty**: Medium  
**File**: `exercise_3.py`

Create a decorator `@validate_types` that validates function argument types at runtime.

**Requirements**:
- Check if arguments match the function's type hints
- Raise `TypeError` if types don't match
- Work with both positional and keyword arguments
- Use the `typing` module and `inspect` module

**Example Usage**:
```python
from typing import get_type_hints

@validate_types
def divide(a: int, b: int) -> float:
    return a / b

divide(10, 2)  # Works fine
divide("10", 2)  # Raises TypeError: Expected int for 'a', got str
```

**Hints**:
- Use `inspect.signature()` to get parameter names
- Use `typing.get_type_hints()` to get type annotations
- Match argument values with expected types

---

## Exercise 4: Retry Decorator with Exponential Backoff

**Difficulty**: Medium  
**File**: `exercise_4.py`

Create a decorator `@retry` that retries a function if it raises an exception, with exponential backoff.

**Requirements**:
- Accept `max_attempts` and `base_delay` as parameters
- Wait `base_delay * (2 ** attempt)` seconds between retries
- Raise the exception if all attempts fail
- Print retry information

**Example Usage**:
```python
@retry(max_attempts=3, base_delay=1)
def unreliable_api_call():
    import random
    if random.random() < 0.7:
        raise ConnectionError("API unavailable")
    return "Success"

unreliable_api_call()
# Attempt 1 failed: API unavailable. Retrying in 1s...
# Attempt 2 failed: API unavailable. Retrying in 2s...
# Success!
```

**Hints**:
- This is a decorator factory (takes parameters)
- Use a `for` loop or `while` loop for retries
- Calculate delay: `base_delay * (2 ** attempt)`

---

## Exercise 5: Rate Limiter Decorator

**Difficulty**: Medium  
**File**: `exercise_5.py`

Create a decorator `@rate_limit` that limits how many times a function can be called within a time window.

**Requirements**:
- Accept `max_calls` and `time_window` (in seconds) as parameters
- Track call timestamps
- Raise exception if rate limit exceeded
- Remove old timestamps outside the time window

**Example Usage**:
```python
@rate_limit(max_calls=3, time_window=5)
def api_call(endpoint):
    return f"Called {endpoint}"

api_call("/users")   # OK
api_call("/posts")   # OK
api_call("/comments")  # OK
api_call("/likes")   # Raises Exception: Rate limit exceeded (3 calls per 5s)
```

**Hints**:
- Store timestamps in a list in the decorator's closure
- Use `time.time()` to get current timestamp
- Filter out old timestamps before checking limit

---

## Exercise 6: Memoization with TTL (Time-To-Live)

**Difficulty**: Medium-Hard  
**File**: `exercise_6.py`

Create a decorator `@memoize_with_ttl` that caches function results but expires them after a certain time.

**Requirements**:
- Accept `ttl` (time-to-live in seconds) as parameter
- Store results with timestamps
- Return cached result if not expired
- Recalculate if cache expired or doesn't exist

**Example Usage**:
```python
@memoize_with_ttl(ttl=2)
def expensive_calculation(x):
    time.sleep(1)
    return x ** 2

print(expensive_calculation(5))  # Takes 1 second, returns 25
print(expensive_calculation(5))  # Instant (cached), returns 25
time.sleep(3)
print(expensive_calculation(5))  # Takes 1 second (cache expired), returns 25
```

**Hints**:
- Store both result and timestamp: `{args: (result, timestamp)}`
- Check if `current_time - cached_time > ttl`

---

## Exercise 7: Authorization Decorator

**Difficulty**: Medium  
**File**: `exercise_7.py`

Create a decorator `@require_role` that checks if a user has the required role before executing a function.

**Requirements**:
- Accept a role name as parameter
- Check against a global or passed-in user object
- Raise `PermissionError` if user doesn't have the role
- Work with methods (handle `self` parameter)

**Example Usage**:
```python
current_user = {"name": "Alice", "roles": ["admin", "editor"]}

@require_role("admin")
def delete_user(user_id):
    return f"Deleted user {user_id}"

@require_role("superadmin")
def delete_all_users():
    return "Deleted all users"

delete_user(123)  # Works (user has admin role)
delete_all_users()  # Raises PermissionError
```

**Hints**:
- Use a global variable or pass user in function arguments
- Check if role is in `user["roles"]`

---

## Exercise 8: Deprecation Warning Decorator

**Difficulty**: Easy-Medium  
**File**: `exercise_8.py`

Create a decorator `@deprecated` that warns users when they call a deprecated function.

**Requirements**:
- Accept optional `reason` and `replacement` parameters
- Use Python's `warnings` module
- Still execute the function
- Show deprecation warning only once per session

**Example Usage**:
```python
@deprecated(reason="Use new_function instead", replacement="new_function")
def old_function(x):
    return x * 2

old_function(5)
# DeprecationWarning: old_function is deprecated: Use new_function instead. 
# Use new_function instead.
```

**Hints**:
- Import `warnings` module
- Use `warnings.warn(message, DeprecationWarning)`
- `stacklevel=2` shows warning at caller location

---

## Exercise 9: Class-Based Decorator with State

**Difficulty**: Medium-Hard  
**File**: `exercise_9.py`

Create a class-based decorator `@CallCounter` that counts how many times each function has been called.

**Requirements**:
- Use a class with `__init__` and `__call__` methods
- Track call count as instance variable
- Add a method to get call statistics
- Preserve function metadata

**Example Usage**:
```python
@CallCounter
def function_a():
    return "A"

@CallCounter
def function_b():
    return "B"

function_a()
function_a()
function_b()

print(function_a.call_count)  # 2
print(function_b.call_count)  # 1
```

**Hints**:
- Store count in `self.count` in `__init__`
- Increment in `__call__`
- Use `functools.update_wrapper(self, func)` for metadata

---

## Exercise 10: Decorator Chain Challenge

**Difficulty**: Hard  
**File**: `exercise_10.py`

Create a function that combines multiple decorators. Use decorators from previous exercises:
- `@timer` - to measure execution time
- `@log` - to log calls
- `@retry` - to retry on failure
- `@memoize_with_ttl` - to cache results

**Requirements**:
- Apply decorators in the correct order
- Function should retry on exception, log each attempt, measure total time, and cache successful results
- Test with a function that sometimes fails

**Example Usage**:
```python
@timer
@log
@retry(max_attempts=3, base_delay=0.1)
@memoize_with_ttl(ttl=5)
def flaky_fetch(url):
    import random
    if random.random() < 0.5:
        raise ConnectionError("Network error")
    return f"Data from {url}"

flaky_fetch("https://api.example.com")
```

**Challenge**: Understand why decorator order matters and explain the execution flow.

---

## Bonus Challenges

### Bonus 1: Async Decorator
Create a decorator that works with async functions using `asyncio`.

### Bonus 2: Decorator with Context
Create a decorator that uses a context manager internally.

### Bonus 3: Performance Profiler
Create a decorator that profiles memory usage and CPU time.

---

## Testing Your Solutions

Run your solution files:
```bash
python exercise_1.py
python exercise_2.py
# etc.
```

Check if they produce expected output and handle edge cases:
- What happens with no arguments?
- What happens with None values?
- What happens with wrong types?

---

## Submission

Once completed, move your solutions to the `solutions/` folder:
```bash
mv exercise_1.py solutions/exercise_1_solution.py
# or copy if you want to keep the starter
cp exercise_1.py solutions/exercise_1_solution.py
```

---

## Additional Resources

- [Python Decorators Documentation](https://docs.python.org/3/glossary.html#term-decorator)
- [Real Python - Decorators](https://realpython.com/primer-on-python-decorators/)
- [PEP 318 - Decorators](https://www.python.org/dev/peps/pep-0318/)

---

**Happy Coding!** Remember: The best way to learn is by doing. Don't be afraid to experiment and make mistakes.

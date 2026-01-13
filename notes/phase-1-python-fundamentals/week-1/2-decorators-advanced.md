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

## Decorators with Arguments

So far, decorators directly modified a function’s behavior. However, sometimes you need to **customize how a decorator works** — for example, by passing configuration values, flags, or limits.

To achieve this, Python uses a **decorator factory**.

A decorator factory is **not a decorator itself**.
It is a function that **returns a decorator**.

---

### Why a Decorator Factory Is Needed

A normal decorator has this shape:

```python
decorator(func) -> wrapped_function
```

But when you write:

```python
@decorator(arg1, arg2)
```

Python interprets it as:

```python
decorator(arg1, arg2)(func)
```

This means:

- The first call receives configuration values
- The second call receives the function to decorate

A single function cannot handle both roles cleanly, so we split it into **three layers**.

---

### The Three-Layer Structure Explained

```python
def decorator_factory(arg1, arg2):     # 1. Configuration layer
    def decorator(func):              # 2. Decoration layer
        @wraps(func)
        def wrapper(*args, **kwargs): # 3. Execution layer
            # Use arg1 and arg2 here
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 1. Decorator Factory (Outer Function)

- Runs **once**, when the function is defined
- Receives configuration values (`arg1`, `arg2`)
- Returns a decorator

#### 2. Decorator (Middle Function)

- Receives the target function (`func`)
- Returns a wrapped version of that function

#### 3. Wrapper (Inner Function)

- Runs **every time the function is called**
- Has access to:

  - The original function
  - The configuration arguments
  - The function’s runtime arguments

---

### How Python Applies This Decorator

```python
@decorator_factory("config1", "config2")
def my_function():
    pass
```

Python executes this in steps:

```python
decorator = decorator_factory("config1", "config2")
my_function = decorator(my_function)
```

After this:

- `my_function` now refers to `wrapper`
- `wrapper` remembers:

  - `func`
  - `"config1"`
  - `"config2"`

This works because of **closures**.

---

### When to Use Decorators with Arguments

Use this pattern when:

- You need configurable behavior (timeouts, retries, logging levels)
- The decorator should behave differently per function
- You want reusable, parameterized decorators

---

### Key Takeaway

A decorator with arguments is:

- A function that **returns a decorator**
- Which returns a **wrapper**
- That executes with access to both configuration and runtime values

Understanding this pattern makes advanced decorators predictable and easy to reason about.

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
```

#### Example Usage

```python
@repeat(times=3)
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")  # Prints 3 times
```

#### What This Code Is Doing (Plain Explanation)

1. **Decorator factory (`repeat`)**

   - `repeat(times)` is not the decorator itself
   - It returns a decorator configured with how many times the function should run
   - This allows the decorator to be reusable with different repeat counts

2. **Wrapping the original function**

   - The `decorator` function receives the target function (`func`)
   - `@wraps(func)` preserves the function’s metadata (name, docstring, etc.)

3. **Repeating function execution**

   - The `wrapper` function executes the original function inside a loop
   - The loop runs `times` number of times
   - Each iteration calls the original function with the same arguments

4. **Returning the result**

   - The result of the last function call is stored
   - The wrapper returns the final result after all repetitions complete

---

This pattern is useful when you want to:

- retry an operation
- repeat logging or printing
- apply repeated side effects
- control execution behavior without modifying the function itself

---

### Example: Rate Limiter

```python
import time
from functools import wraps

def rate_limit(max_calls, period):
    """
    Limits how many times a function can be called within a given time period.

    max_calls : maximum number of allowed calls
    period    : time window in seconds
    """

    # This list stores timestamps of previous function calls
    calls = []

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            # Get the current time
            now = time.time()

            # Step 1: Remove old calls that are outside the time period
            valid_calls = []
            for call_time in calls:
                if now - call_time < period:
                    valid_calls.append(call_time)

            # Update the calls list with only valid timestamps
            calls.clear()
            for call_time in valid_calls:
                calls.append(call_time)

            # Step 2: Check if the rate limit is exceeded
            if len(calls) >= max_calls:
                raise Exception(
                    "Rate limit exceeded: "
                    + str(max_calls)
                    + " calls per "
                    + str(period)
                    + " seconds"
                )

            # Step 3: Record the current call
            calls.append(now)

            # Step 4: Call the original function
            return func(*args, **kwargs)

        return wrapper

    return decorator

```

#### Example Usage

```python
@rate_limit(max_calls=3, period=10)
def api_call():
    print("API called")

```

#### What This Code Is Doing (Plain Explanation)

1.  **`calls` list**

    - Stores timestamps of each function call
    - Persists across function calls because of closures

2.  **Removing expired calls**

    - We loop through existing timestamps
    - Keep only those within the allowed time window
    - Old timestamps are discarded

3.  **Rate limit check**

    - If the number of recent calls reaches `max_calls`
    - An exception is raised immediately

4.  **Recording the call**

    - If allowed, we store the current timestamp
    - Then execute the original function

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

#### Example Usage

```python
@retry(max_attempts=3, delay=2)
def unreliable_function():
    import random
    if random.random() < 0.7:
        raise Exception("Random failure")
    return "Success"
```

#### What This Code Is Doing

1. **Decorator factory (`retry`)**

   - `retry(max_attempts, delay)` returns a decorator
   - The decorator is configured with:

     - how many times the function can be retried
     - how long to wait between retries

2. **Wrapping the original function**

   - The `decorator` receives the target function
   - `@wraps(func)` preserves the original function’s metadata

3. **Attempt counter**

   - `attempts` starts at `0`
   - It tracks how many times the function has failed

4. **Retry loop**

   - The function call is wrapped inside a `while` loop
   - The loop continues until:

     - the function succeeds, or
     - the maximum number of attempts is reached

5. **Successful execution**

   - If `func(*args, **kwargs)` runs without error
   - Its return value is immediately returned
   - No further retries occur

6. **Handling failure**

   - If an exception is raised:

     - the attempt counter is incremented
     - if retries remain, execution pauses for `delay` seconds
     - a retry message is printed

7. **Final failure**

   - If the function fails `max_attempts` times
   - The last exception is re-raised
   - This ensures errors are not silently swallowed

---

This pattern is useful when dealing with:

- unstable network requests
- temporary system failures
- APIs with intermittent errors
- operations that may succeed after a short delay

---

## Class-Based Decorators

Decorators can also be classes that implement `__call__`:

In Python, decorators are not limited to functions.  
A decorator can also be implemented as a **class** by defining the `__call__` method.

When a class is used as a decorator:

- The function being decorated is passed to the class constructor (`__init__`)
- The class instance replaces the original function
- Calling the function actually invokes the instance’s `__call__` method

This makes the class behave like a function while allowing it to store state.

---

### How Class-Based Decorators Work

1. **Decoration time**

   - Python creates an instance of the decorator class
   - The decorated function is passed to `__init__`
   - The instance replaces the original function name

2. **Call time**

   - Each time the function is called, `__call__` executes
   - The original function can be invoked inside `__call__`
   - Any instance variables persist across calls

---

### Why Use a Class-Based Decorator?

Class-based decorators are useful when:

- You need to **store state** across multiple function calls
- The decorator logic is **too complex** for nested functions
- You want a clearer separation of behavior and data
- You need reusable, configurable decorator objects

---

### Function-Based vs Class-Based Decorators

- Function-based decorators are lightweight and simple
- Class-based decorators are better for:
  - counters
  - caches
  - rate limiting
  - metrics
  - logging with internal state

Both approaches follow the same decorator concept; the difference lies in structure and state management.

---

### Key Requirement

To be used as a decorator, a class must:

- Accept the function in `__init__`
- Implement `__call__` so the instance is callable

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

### What Are Methods?

A **method** is a function that is defined inside a class and operates on an object created from that class.

In Python:

- Functions belong to modules
- Methods belong to classes
- Methods are functions that are **bound to an instance**

---

### Methods vs Functions

A normal function:

```python
def add(a, b):
    return a + b
```

A method:

```python
class Calculator:
    def add(self, a, b):
        return a + b
```

Key difference:

- Methods receive `self` as the first argument
- `self` refers to the object calling the method

---

### What Is `self`?

`self` is a reference to the **current object instance**.

When you write:

```python
calc = Calculator()
calc.add(2, 3)
```

Python internally translates it to:

```python
Calculator.add(calc, 2, 3)
```

That is why:

- `self` must be present in method definitions
- Decorators applied to methods must handle `self`

---

### Why Methods Matter

Methods allow functions to:

- access object data (attributes)
- modify object state
- represent object behavior

They are fundamental to **object-oriented programming** in Python.

---

### Connection to Method Decorators

Because methods automatically receive `self`, decorators applied to methods must:

- accept `self` explicitly
- forward it correctly to the original method

This is the only conceptual difference between decorating a function and decorating a method.

---

## Method Decorators

Decorators can be applied to methods, but you need to handle the `self` parameter:

Method decorators are decorators applied to **class methods** instead of standalone functions.  
They work the same way as function decorators, with one important difference:  
**methods automatically receive `self` as their first argument**.

Because of this, the wrapper function must explicitly accept `self` and pass it to the original method.

---

### How Method Decorators Work

1. **Decoration time**

   - The decorator receives the method function (not the class instance)
   - The method is wrapped before the class is instantiated

2. **Call time**

   - When the method is called on an object
   - `self` is automatically passed to the wrapper
   - The wrapper must forward `self` to the original method

3. **Wrapper signature**

   - The wrapper’s first parameter must be `self`
   - Remaining positional and keyword arguments follow
   - Failing to include `self` will cause argument errors

---

### Why `self` Must Be Handled Explicitly

- Methods are just functions defined inside a class
- Python automatically injects `self` at call time
- The decorator does **not** add `self` for you
- The wrapper must match the method’s calling convention

---

### When to Use Method Decorators

Method decorators are useful for:

- timing class operations
- logging method calls
- validating object state
- enforcing permissions
- tracking per-instance behavior

---

### Key Rule

For method decorators, always define the wrapper as:

```python
def wrapper(self, *args, **kwargs):

```

This ensures correct binding and predictable behavior.

```python
import time
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

When a function is wrapped by a decorator, its original metadata can be lost.  
This includes important information such as the function name, docstring, and signature.

Using `functools.wraps` ensures that the wrapper function copies this metadata from the original function.  
This makes decorated functions behave correctly with tools like debuggers, documentation generators, and introspection utilities.

In this example:

- `@wraps(func)` preserves the function’s identity
- `inspect.signature(func)` retrieves the original function’s parameter signature
- The decorator adds behavior without altering how the function appears to users or tools

Preserving decorator information is a best practice for writing clean and maintainable decorators.

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

When multiple decorators are applied to a single function, they are executed in a specific order.  
Decorators are applied from **bottom to top**, meaning the decorator closest to the function runs first.

Because each decorator wraps the result of the previous one, the order can change the behavior of the function.  
For this reason, decorators should be stacked intentionally and consistently.

Common best practices include:

- placing validation decorators closest to the function
- adding logging or monitoring around validated logic
- applying timing or performance decorators as the outermost layer

Understanding and controlling decorator order helps prevent unexpected behavior and makes the code easier to reason about.

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

## Common Decorator Patterns

Decorators are often used to apply **cross-cutting concerns** — logic that should run _before or after_ a function without changing the function’s core behavior.  
Typical use cases include authentication, authorization, logging, and warnings.

Below are some common real-world patterns and how they work.

---

### 1. Authentication Decorator

**Purpose:**  
Ensure that a function is executed **only if the user is authenticated**.

**What happens conceptually:**

- The decorator wraps the target function.
- Before the function runs, it checks authentication status.
- If the user is not authenticated, execution is blocked.
- If authenticated, the original function is executed normally.

**Why this is useful:**  
You avoid repeating authentication checks inside every protected function.

```python
from functools import wraps

def require_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not user_is_authenticated():
            raise PermissionError("Authentication required")
        return func(*args, **kwargs)
    return wrapper

```

---

### 2. Permission Decorator (Decorator with Arguments)

**Purpose:**  
Restrict access to a function based on **specific permissions** (e.g., admin, editor).

**What happens conceptually:**

- The outer function receives configuration (`permission`).
- It returns a decorator.
- The decorator wraps the target function.
- At runtime, the wrapper checks whether the user has the required permission.
- If not, execution is denied.

**Why this pattern is important:**  
It allows **configurable behavior** using decorators.

```python
from functools import wraps

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

---

### 3. Deprecation Warning Decorator

**Purpose:**  
Warn developers that a function should no longer be used and may be removed later.

**What happens conceptually:**

- The decorator intercepts the function call.
- A warning is emitted **every time the function is used**.
- The function still executes normally.

**Why this is useful:**  
It helps maintain backward compatibility while guiding users toward newer APIs.

```python
import warnings
from functools import wraps

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

### Key Takeaways 

- Decorators let you **separate concerns** from business logic
- Authentication and permissions are classic real-world use cases
- Decorators with arguments allow **configurable behavior**
- `functools.wraps` preserves function metadata
- Deprecation decorators are critical for long-term API stability

---

## Practice Exercises

See: `exercises/python-fundamentals/decorators/EXERCISES.md` (Exercises 5-8)

---

## Code Examples

All runnable code: `code-examples/02_decorators_advanced.py`

---

## Tomorrow's Topic

**Day 3: Context Managers** - The `with` statement and `__enter__`/`__exit__` methods.

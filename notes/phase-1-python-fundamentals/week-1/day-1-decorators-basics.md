# Day 1: Decorators - Basics

**Date**: Week 1, Day 1  
**Phase**: 1 - Python Fundamentals  
**Topic**: Introduction to Decorators

---

## Learning Objectives

- Understand what decorators are and why they're useful
- Learn decorator syntax and how they work internally
- Write basic function decorators
- Understand the `@wraps` decorator
- Apply decorators to real-world scenarios

---

## What are Decorators?

A decorator is a function that takes another function as an argument, adds some functionality, and returns a new function. Decorators allow you to modify or enhance the behavior of functions or methods without changing their code.

### Why Use Decorators?

- **Code reusability**: Apply the same functionality to multiple functions
- **Separation of concerns**: Keep business logic separate from cross-cutting concerns (logging, timing, authentication)
- **Clean syntax**: The `@decorator` syntax is readable and elegant
- **DRY principle**: Don't Repeat Yourself

---

## Basic Decorator Syntax

### Without @ Syntax

```python
def my_decorator(func):
    def wrapper():
        print("Something before the function")
        func()
        print("Something after the function")
    return wrapper

def say_hello():
    print("Hello!")

# Manually wrap the function
say_hello = my_decorator(say_hello)
say_hello()
```

### With @ Syntax (Preferred)

```python
def my_decorator(func):
    def wrapper():
        print("Something before the function")
        func()
        print("Something after the function")
    return wrapper

@my_decorator
def say_hello():
    print("Hello!")

say_hello()
```

The `@my_decorator` syntax is just syntactic sugar for `say_hello = my_decorator(say_hello)`.

---

## How Decorators Work

When you use `@decorator`, Python does the following:

1. Defines the function
2. Passes it to the decorator
3. Replaces the original function with the returned function

```python
# This:
@decorator
def func():
    pass

# Is equivalent to:
def func():
    pass
func = decorator(func)
```

---

## Decorators with Arguments

Most functions take arguments, so your wrapper needs to handle them:

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Finished {func.__name__}")
        return result
    return wrapper

@my_decorator
def add(a, b):
    return a + b

result = add(5, 3)  # Works with any number of arguments
print(result)
```

**Key points**:
- Use `*args` and `**kwargs` to accept any arguments
- Pass them to the original function
- Return the result from the original function

---

## The functools.wraps Decorator

When you wrap a function, you lose its metadata (name, docstring, etc.):

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def greet(name):
    """Greets a person by name."""
    return f"Hello, {name}!"

print(greet.__name__)  # Output: wrapper (not greet!)
print(greet.__doc__)   # Output: None
```

Use `functools.wraps` to preserve function metadata:

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)  # This preserves metadata
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def greet(name):
    """Greets a person by name."""
    return f"Hello, {name}!"

print(greet.__name__)  # Output: greet
print(greet.__doc__)   # Output: Greets a person by name.
```

**Always use `@wraps(func)` in your decorators!**

---

## Common Use Cases

### 1. Timing Functions

```python
import time
from functools import wraps

def timer(func):
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
    time.sleep(1)
    return "Done"

slow_function()
```

### 2. Logging

```python
from functools import wraps

def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@logger
def add(a, b):
    return a + b

add(5, 3)
```

### 3. Input Validation

```python
from functools import wraps

def validate_positive(func):
    @wraps(func)
    def wrapper(x):
        if x < 0:
            raise ValueError("Number must be positive")
        return func(x)
    return wrapper

@validate_positive
def square_root(x):
    return x ** 0.5

print(square_root(16))  # Works
print(square_root(-4))  # Raises ValueError
```

### 4. Caching/Memoization

```python
from functools import wraps

def memoize(func):
    cache = {}
    @wraps(func)
    def wrapper(*args):
        if args in cache:
            print(f"Returning cached result for {args}")
            return cache[args]
        result = func(*args)
        cache[args] = result
        return result
    return wrapper

@memoize
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

print(fibonacci(10))  # Much faster with caching
```

---

## Multiple Decorators

You can stack multiple decorators:

```python
@decorator1
@decorator2
@decorator3
def my_function():
    pass

# Equivalent to:
my_function = decorator1(decorator2(decorator3(my_function)))
```

**Order matters!** Decorators are applied from bottom to top.

```python
def bold(func):
    def wrapper():
        return "<b>" + func() + "</b>"
    return wrapper

def italic(func):
    def wrapper():
        return "<i>" + func() + "</i>"
    return wrapper

@bold
@italic
def greet():
    return "Hello"

print(greet())  # Output: <b><i>Hello</i></b>
```

---

## Key Takeaways

1. **Decorators wrap functions** to add functionality without modifying their code
2. **Use `@decorator` syntax** for clean, readable code
3. **Accept `*args, **kwargs`** in the wrapper to handle any function signature
4. **Always use `@wraps(func)`** to preserve function metadata
5. **Decorators are powerful** for cross-cutting concerns like logging, timing, caching, validation
6. **Multiple decorators** can be stacked, applied bottom to top

---

## Practice Exercises

See the exercises folder: `exercises/python-fundamentals/decorators/EXERCISES.md`

Exercises 1-4 focus on today's content.

---

## Code Examples

All runnable code examples are in: `code-examples/01_decorators_basic.py`

---

## Common Mistakes to Avoid

1. **Forgetting to return the result** from the wrapper function
2. **Not using `*args, **kwargs`** when the function takes arguments
3. **Forgetting `@wraps(func)`** and losing function metadata
4. **Not returning the wrapper function** from the decorator

---

## Further Reading

- [PEP 318 - Decorators for Functions and Methods](https://www.python.org/dev/peps/pep-0318/)
- [Real Python - Primer on Python Decorators](https://realpython.com/primer-on-python-decorators/)
- [Python Documentation - functools.wraps](https://docs.python.org/3/library/functools.html#functools.wraps)

---

## Tomorrow's Topic

**Day 2: Advanced Decorators** - Decorators with arguments, class decorators, and decorator factories.

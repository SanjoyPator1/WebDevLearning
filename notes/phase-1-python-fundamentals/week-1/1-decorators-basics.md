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

### \*args and \*\*kwargs in Python (with Decorators)

#### What are \*args and \*\*kwargs

In Python, `*args` and `**kwargs` are used to pass a variable number of arguments to a function.

- `*args` collects extra positional arguments into a tuple
- `**kwargs` collects extra keyword arguments into a dictionary

They are commonly used in decorators so the decorator can work with any function signature.

---

#### \*args (Positional Arguments)

`*args` allows a function to accept any number of positional arguments.

```python
def example(*args):
    print(args)

example(1, 2, 3)
```

Output:

```
(1, 2, 3)
```

Here, `args` is a tuple containing all positional arguments.

---

#### \*\*kwargs (Keyword Arguments)

`**kwargs` allows a function to accept any number of named arguments.

```python
def example(**kwargs):
    print(kwargs)

example(a=1, b=2)
```

Output:

```
{'a': 1, 'b': 2}
```

Here, `kwargs` is a dictionary mapping argument names to values.

---

#### Using \*args and \*\*kwargs Together

Both can be used in the same function.

```python
def example(*args, **kwargs):
    print(args)
    print(kwargs)

example(1, 2, x=10, y=20)
```

- Positional values go into `args`
- Named values go into `kwargs`

---

#### Why Decorators Use \*args and \*\*kwargs

Decorators wrap functions, but wrapped functions may take different arguments.
Using `*args` and `**kwargs` makes the decorator reusable.

Without them, the decorator would only work for functions with a fixed signature.

---

#### Decorator Example with \*args and \*\*kwargs

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Finished {func.__name__}")
        return result
    return wrapper
```

```python
@my_decorator
def add(a, b):
    return a + b
```

```python
result = add(5, 3)
print(result)
```

---

#### What Happens Internally

Calling:

```python
add(5, 3)
```

Is equivalent to:

```python
wrapper(5, 3)
```

Inside `wrapper`:

- `args` becomes `(5, 3)`
- `kwargs` becomes `{}`

The original function is called as:

```python
func(*args, **kwargs)
```

---

#### Important Rules

- `*args` must come before `**kwargs`
- Names `args` and `kwargs` are conventions, not keywords
- Use unpacking (`*` and `**`) when passing them to another function

---

#### One-Line Summary

`*args` handles extra positional arguments, and `**kwargs` handles extra keyword arguments, allowing decorators and functions to work with any input signature.

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

One of the most common and practical uses of decorators is **measuring how long a function takes to execute**.  
This is especially useful for performance monitoring, debugging slow code, and profiling critical sections of an application.

Instead of adding timing logic inside every function, a decorator allows this behavior to be **reused across multiple functions** without modifying their core logic.

In this example:

- The decorator records the time just before the function starts executing
- It runs the original function
- It records the time again after execution finishes
- It prints the total execution time
- Finally, it returns the original function’s result

The `@wraps` decorator is used to preserve the original function’s metadata such as its name and docstring.

This approach keeps timing logic **separate from business logic**, making the code cleaner and easier to maintain.

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

Logging is another widely used application of decorators.  
A logging decorator allows you to automatically record information about function calls without adding logging code inside the function itself.

In this example:

- The decorator logs the function name before execution
- It logs the positional and keyword arguments passed to the function
- It executes the original function
- It logs the returned value after execution
- Finally, it returns the result unchanged

This pattern is useful for:

- debugging
- tracing program flow
- monitoring function behavior in production
- understanding how functions are being called

By using a decorator, logging becomes reusable and can be easily applied to any function with a single line, keeping business logic clean and focused.

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

Decorators are often used to enforce input validation rules in a consistent and reusable way.  
Instead of repeating validation logic inside every function, a decorator allows you to define the rule once and apply it wherever needed.

In this example:

- The decorator checks whether the input value is positive
- If the validation fails, it raises an appropriate error
- If the validation passes, it calls the original function
- The original function remains focused only on its core logic

This approach is useful when:

- the same validation logic applies to multiple functions
- input rules must be enforced consistently
- separating validation from business logic improves readability

Using decorators for validation helps keep functions clean, predictable, and easier to maintain.

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

Caching, also known as memoization, is a common optimization technique used to store the results of expensive function calls and reuse them when the same inputs occur again.

Decorators provide a clean way to add caching behavior without modifying the function’s implementation.

In this example:

- A dictionary is used to store previously computed results
- The function arguments are used as the cache key
- If the result is already cached, it is returned immediately
- If not, the function is executed and the result is stored for future calls

This approach is especially effective for:

- recursive functions
- functions with repeated inputs
- computationally expensive operations

By separating caching logic from the function itself, decorators make performance optimizations easy to apply and maintain.

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

Python allows multiple decorators to be applied to a single function.  
This is known as _stacking decorators_ and is commonly used when a function needs to be enhanced with multiple independent behaviors.

When multiple decorators are applied:

- Each decorator wraps the function returned by the decorator below it
- The decorators are applied **from bottom to top**
- The final function is a nested chain of wrappers

You can stack multiple decorators:

```python
@decorator1
@decorator2
@decorator3
def my_function():
    pass
```


#### Is equivalent to:
```python
my_function = decorator1(decorator2(decorator3(my_function)))
```

Because of this nesting, the order of decorators matters.
Changing the order can change the behavior and the final output.

In the example below:

- The innermost decorator (italic) runs first
- Its result is then passed to the outer decorator (bold)
- This produces nested HTML-style formatting

Understanding decorator order is important when combining features such as logging, authentication, validation, and caching in real applications.

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
3. **Accept `\*args, **kwargs`\*\* in the wrapper to handle any function signature
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
2. **Not using `\*args, **kwargs`\*\* when the function takes arguments
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

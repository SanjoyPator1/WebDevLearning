# Day 3: Context Managers

**Date**: Week 1, Day 3  
**Phase**: 1 - Python Fundamentals  
**Topic**: Context Managers and the `with` Statement

---

## Learning Objectives

- Understand context managers and their purpose
- Learn the `__enter__` and `__exit__` protocol
- Use the `with` statement effectively
- Handle exceptions in context managers
- Apply context managers to resource management

---

## Context Managers in Python

A **context manager** is a Python construct that allows you to **allocate and release resources precisely when you want to**. They help manage **setup and cleanup operations automatically**, reducing boilerplate code and preventing resource leaks.

Common use cases for context managers include:

- File operations (opening/closing files)
- Database connections (connecting/disconnecting)
- Lock acquisition and release (thread synchronization)
- Temporary changes to program state (e.g., changing working directories)

---

### The `with` Statement

The `with` statement simplifies the use of context managers. It ensures that **resources are properly cleaned up** after use, even if an exception occurs.

```python
with open('file.txt', 'r') as f:
    content = f.read()
# File is automatically closed here, even if an exception occurred
```

**Explanation:**

1. `open('file.txt', 'r')` returns a file object that supports the context manager protocol.
2. `as f` assigns the file object to the variable `f`.
3. The code inside the `with` block uses the file.
4. Once the block is exited, Python automatically calls `f.close()`, even if an error occurred inside the block.

---

### Why Use Context Managers?

Without a context manager, you'd have to manually manage resources:

```python
f = open('file.txt', 'r')
try:
    content = f.read()
finally:
    f.close()
```

- This works, but it is more verbose.
- The `with` statement **automates this pattern**, making the code cleaner and safer.

---

### How Context Managers Work

A context manager must implement two special methods:

1. `__enter__(self)` – called at the start of the `with` block; its return value is assigned to the variable after `as`.
2. `__exit__(self, exc_type, exc_value, traceback)` – called at the end of the `with` block, even if an exception occurs. It handles cleanup.

Example with a custom context manager:

```python
class MyContext:
    def __enter__(self):
        print("Entering the context")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print("Exiting the context")

with MyContext() as ctx:
    print("Inside the context")
```

Output:

```
Entering the context
Inside the context
Exiting the context
```

**Explanation:**

- `__enter__` is executed first, allowing resource setup.
- The block runs normally.
- `__exit__` runs last, ensuring cleanup even if an exception occurs inside the block.

---

## The Context Manager Protocol

A **context manager** in Python follows a **protocol**, meaning it must implement **two special methods**:

1. **`__enter__()`** – executed **when entering** the `with` block.

   - Sets up resources (e.g., opens a file, acquires a lock).
   - Its return value is assigned to the variable after `as`.

2. **`__exit__(exc_type, exc_val, exc_tb)`** – executed **when exiting** the `with` block.

   - Handles cleanup (e.g., closes a file, releases a lock).
   - Called **even if an exception occurs** inside the block.
   - Can suppress exceptions by returning `True`; returning `False` propagates them.

---

### Example: Custom Context Manager

```python
class MyContextManager:
    def __enter__(self):
        print("Entering context")
        return self  # This object is assigned to 'cm'

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting context")
        # Returning False propagates exceptions, True suppresses them
        return False

with MyContextManager() as cm:
    print("Inside context")
    # Uncomment the next line to see how exception handling works
    # 1 / 0
```

**Output without exception:**

```
Entering context
Inside context
Exiting context
```

**Output with exception (`1 / 0` inside block):**

```
Entering context
Inside context
Exiting context
ZeroDivisionError: division by zero
```

**Explanation:**

- `__enter__` runs first, setting up resources.
- The block executes normally.
- `__exit__` runs last, handling cleanup.
- If `__exit__` returned `True`, the exception would be suppressed. Returning `False` propagates it.

---

## Creating Custom Context Managers

Custom context managers allow you to **define your own setup and cleanup logic** using the context manager protocol (`__enter__` and `__exit__`).
They are useful when you want to manage resources that are not handled by Python’s built-in context managers.

Typical use cases:

- File handling with additional logic (logging, validation)
- Database connections
- Network connections
- Resource allocation and release

---

### Example 1: File Handler with Logging

This example demonstrates a custom context manager that:

- Opens a file when entering the context
- Logs the operation
- Ensures the file is closed when exiting the context

```python
class FileHandler:
    def __init__(self, filename, mode='r'):
        self.filename = filename
        self.mode = mode
        self.file = None

    def __enter__(self):
        print(f"Opening {self.filename}")
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            print(f"Closing {self.filename}")
            self.file.close()
        return False
```

#### Using the FileHandler

```python
with FileHandler('data.txt', 'r') as f:
    content = f.read()
    print(content)
```

**Explanation:**

- `__init__` stores the filename and mode but does not open the file.
- `__enter__` opens the file and returns the file object.
- The returned file object is assigned to `f`.
- `__exit__` closes the file, ensuring cleanup even if an exception occurs.
- Returning `False` means any exception will propagate normally.

This pattern is safer and more expressive than manually opening and closing files.

---

### Example 2: Database Connection Manager (Simulated)

This example shows how a context manager can be used to manage a database connection lifecycle.

```python
class DatabaseConnection:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = None

    def __enter__(self):
        print(f"Connecting to {self.db_name}")
        # Simulate a database connection
        self.connection = f"Connection to {self.db_name}"
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Closing connection to {self.db_name}")
        self.connection = None
        return False
```

#### Using the DatabaseConnection

```python
with DatabaseConnection('mydb') as conn:
    print(f"Using {conn}")
```

**Explanation:**

- `__enter__` simulates opening a database connection and returns it.
- The connection is available inside the `with` block.
- `__exit__` ensures the connection is closed, regardless of success or failure.
- Returning `False` allows exceptions to propagate normally.

---

### Key Takeaways

- Custom context managers encapsulate **resource management logic**.
- `__enter__` handles setup and returns the resource.
- `__exit__` handles cleanup and is always executed.
- Returning `True` suppresses exceptions; returning `False` propagates them.
- This pattern makes code cleaner, safer, and easier to maintain.

---

## Exception Handling in Context Managers

One of the most powerful features of context managers is their ability to **handle exceptions automatically**.

When an exception occurs inside a `with` block, Python passes detailed exception information to the `__exit__` method, allowing the context manager to:

- Log the error
- Clean up resources
- Decide whether to suppress or propagate the exception

---

### Exception Information Passed to `__exit__`

The `__exit__` method receives three arguments related to the exception:

```text
exc_type → The exception class (e.g., ValueError)
exc_val  → The exception instance (error message)
exc_tb   → The traceback object
```

If no exception occurs, all three values are `None`.

---

### Example: Suppressing Exceptions in a Context Manager

```python
class SafeOperation:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"Exception occurred: {exc_type.__name__}: {exc_val}")
            return True  # Suppress the exception
        return False
```

#### Using the Context Manager

```python
with SafeOperation():
    raise ValueError("Something went wrong")

print("Execution continues")
```

**Output:**

```
Exception occurred: ValueError: Something went wrong
Execution continues
```

---

### What Happens Internally

1. Python enters the `with` block and calls `__enter__`.
2. An exception is raised inside the block.
3. Python calls `__exit__`, passing:

   - `exc_type = ValueError`
   - `exc_val = ValueError("Something went wrong")`
   - `exc_tb = traceback`

4. `__exit__` returns `True`, so:

   - The exception is considered handled
   - Program execution continues normally

---

### Propagating Exceptions Instead

If you want the exception to propagate (default behavior), return `False`:

```python
def __exit__(self, exc_type, exc_val, exc_tb):
    return False
```

In this case, Python will re-raise the exception after `__exit__` finishes.

---

### What Does “Suppressing an Exception” Mean?

When an exception occurs in Python, the **default behavior** is:

- Stop normal execution
- Show an error (traceback)
- Exit the current flow

Example:

```python
1 / 0
print("This will not run")

```

Output:

```
ZeroDivisionError: division by zero

```

The program stops immediately.

---

#### What Happens Inside a `with` Block?

When an exception occurs inside a `with` block, Python does **not immediately raise it**.

Instead, Python:

1.  Pauses execution
2.  Calls the context manager’s `__exit__` method
3.  Passes the exception details to `__exit__`
4.  Waits for `__exit__` to return `True` or `False`

That return value decides **what happens next**.

---

#### Returning `True` from `__exit__` (Suppressing the Exception)

#### Meaning

Returning `True` tells Python:

> “I have handled this exception. Do not raise it again.”

This is called **suppressing the exception**.

#### Result

- No traceback is shown
- Program execution continues normally
- The exception is effectively swallowed

#### Example

```python
class SuppressExample:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exception handled inside __exit__")
        return True

```

```python
with SuppressExample():
    raise ValueError("This error will be suppressed")

print("Program continues")

```

Output:

```
Exception handled inside __exit__
Program continues

```

The exception occurred, but the program did not crash.

---

#### Returning `False` from `__exit__` (Not Suppressing the Exception)

#### Meaning

Returning `False` tells Python:

> “I did not handle this exception. Raise it normally.”

This is the **default behavior**.

#### Result

- Python re-raises the exception
- A traceback is shown
- Execution stops (unless caught elsewhere)

#### Example

```python
class PropagateExample:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Cleanup done, but exception not handled")
        return False

```

```python
with PropagateExample():
    raise RuntimeError("This error will propagate")

print("This will not run")

```

Output:

```
Cleanup done, but exception not handled
RuntimeError: This error will propagate

```

---

#### Key Rule to Remember (Very Important)

| `__exit__` Return Value | Meaning                        | Exception Raised? |
| ----------------------- | ------------------------------ | ----------------- |
| `True`                  | Exception handled (suppressed) | No                |
| `False`                 | Exception not handled          | Yes               |

---

#### Why Does Python Use This Design?

This design allows context managers to:

- Clean up resources safely
- Decide intelligently what to do with errors
- Implement patterns like retries, logging, or rollbacks

Example real-world uses:

- Database transaction rollback but continue program
- Logging an error and moving on
- Ignoring expected or non-critical errors

---

#### One-Line Mental Model

> **Returning `True` = “I handled it, move on.”**  
> **Returning `False` = “I didn’t handle it, crash if needed.”**

---

### Practical Use Cases

Exception handling in context managers is commonly used for:

- Graceful error handling in database transactions
- Rolling back operations on failure
- Logging errors without crashing the program
- Ensuring cleanup while allowing errors to surface

---

### Key Takeaways

- `__exit__` is always executed, even when an exception occurs.
- Exception details are passed into `__exit__`.
- Returning `True` suppresses the exception.
- Returning `False` propagates the exception.
- This makes context managers ideal for safe and controlled resource handling.

---

## The `contextlib` Module

Python provides the **`contextlib`** module to make writing context managers **simpler and more readable**.

Instead of defining a class with `__enter__` and `__exit__`, `contextlib` allows you to write context managers using **generator functions** and the `@contextmanager` decorator.

This approach is ideal when:

- Setup and cleanup logic is simple
- You want less boilerplate code
- A full class would be overkill

---

### Using the `@contextmanager` Decorator

The `@contextmanager` decorator converts a generator function into a context manager.

#### How It Works Conceptually

- Code **before `yield`** acts like `__enter__`
- The value passed to `yield` is assigned to the variable after `as`
- Code **after `yield`** acts like `__exit__`
- The `finally` block ensures cleanup even if an exception occurs

---

### Example: File Handler Using `contextlib`

```python
from contextlib import contextmanager

@contextmanager
def file_handler(filename, mode='r'):
    print(f"Opening {filename}")
    f = open(filename, mode)
    try:
        yield f  # Value provided to the 'as' clause
    finally:
        print(f"Closing {filename}")
        f.close()
```

#### Using the Context Manager

```python
with file_handler('data.txt') as f:
    content = f.read()
```

**Explanation:**

- The file is opened before `yield`
- `yield f` provides the file object to the `with` block
- The `finally` block ensures the file is closed
- Cleanup happens even if an exception occurs

---

### Mapping to the Context Manager Protocol

| `contextlib` Code Location | Equivalent Protocol Method  |
| -------------------------- | --------------------------- |
| Before `yield`             | `__enter__`                 |
| Value yielded              | Return value of `__enter__` |
| After `yield`              | `__exit__`                  |

---

### Example: Timer Context Manager

This example measures how long a block of code takes to execute.

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name="Operation"):
    start = time.time()
    print(f"Starting {name}")
    try:
        yield
    finally:
        end = time.time()
        print(f"{name} took {end - start:.4f} seconds")
```

#### Using the Timer

```python
with timer("Data processing"):
    time.sleep(1)
    # Perform some operation
```

**Explanation:**

- Timing starts before entering the block
- Timing ends after the block exits
- Execution time is printed regardless of success or failure

---

### Example: Temporary Directory Context Manager

This context manager creates a temporary directory and automatically deletes it when done.

```python
import os
import tempfile
import shutil
from contextlib import contextmanager

@contextmanager
def temporary_directory():
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)
```

#### Using the Temporary Directory

```python
with temporary_directory() as tmpdir:
    filepath = os.path.join(tmpdir, 'temp.txt')
    with open(filepath, 'w') as f:
        f.write("Temporary data")
```

After exiting the `with` block, the temporary directory is automatically removed.

This logic creates a temporary folder for you, lets you use it for some work, and then automatically deletes it when you are done.

First, a new temporary directory is created on the system. This directory exists only for a short time and is meant for temporary files.

Then, control is given to you so you can use that directory. While you are using it, you can create files inside it and work with them normally.

Once your work is finished and you exit the block, Python automatically cleans up by deleting the temporary directory along with everything inside it. This cleanup happens even if something goes wrong during your work.

---

### Temporary Directory Context Manager

This context manager creates a temporary directory, allows it to be used safely, and automatically deletes it when the work is done.

When the context starts, a new temporary directory is created:

```python
temp_dir = tempfile.mkdtemp()
```

This directory exists on disk and has a unique name.

The directory path is then provided to the `with` block:

```python
yield temp_dir
```

The value yielded becomes available as `tmpdir`, which can be used to create and access files inside the directory.

After the `with` block finishes, cleanup logic is executed:

```python
shutil.rmtree(temp_dir)
```

This removes the directory and all its contents. The cleanup runs even if an exception occurs, ensuring no temporary files are left behind.

---

### Why This Is Useful

- Temporary files are cleaned up automatically
- No manual deletion is required
- Cleanup is guaranteed, even on errors
- Keeps the filesystem clean

---

### Key Idea

A temporary directory is **created**, **used**, and **deleted automatically** using a context manager.

---

### When to Use `contextlib` vs Class-Based Context Managers

| Use Case                       | Recommended Approach |
| ------------------------------ | -------------------- |
| Simple setup/cleanup           | `@contextmanager`    |
| Complex state or reuse         | Class-based          |
| Multiple methods or attributes | Class-based          |
| Short, readable context        | `contextlib`         |

---

### Key Takeaways

- `contextlib` simplifies context manager creation
- `@contextmanager` uses `yield` to split setup and cleanup logic
- Code before `yield` runs on entry
- Code after `yield` runs on exit
- `finally` ensures reliable cleanup
- This approach reduces boilerplate while keeping behavior explicit

---

## Understanding `yield` in `contextlib` Context Managers

In `contextlib`, the `yield` keyword is used to **split a function into two phases**:

1. **Setup phase** (before `yield`)
2. **Cleanup phase** (after `yield`)

When a function is decorated with `@contextmanager`, Python treats it as a **generator-based context manager**.

---

### What `yield` Means Here (Important)

In a `@contextmanager` function:

- Code **before `yield`** runs when entering the `with` block
- The value passed to `yield` becomes the value after `as`
- Code **after `yield`** runs when exiting the `with` block

So `yield` acts as a **pause point** in the function.

---

### Simple Mental Model

Think of `yield` as saying:

> “Give this value to the `with` block, pause execution here, and resume after the block finishes.”

---

### Example: Minimal `yield` Context Manager

```python
from contextlib import contextmanager

@contextmanager
def simple_context():
    print("Before yield (entering context)")
    yield
    print("After yield (exiting context)")
```

```python
with simple_context():
    print("Inside with block")
```

**Output:**

```
Before yield (entering context)
Inside with block
After yield (exiting context)
```

---

### Example: `yield` Providing a Value

```python
@contextmanager
def resource_provider():
    resource = "Important Resource"
    yield resource
```

```python
with resource_provider() as res:
    print(res)
```

**Explanation:**

- `yield resource` sends `"Important Resource"` to `res`
- `res` exists only inside the `with` block

---

### Why `yield` Must Be Used Exactly Once

In a `@contextmanager` function:

- `yield` **must appear exactly once**
- Multiple `yield` statements are not allowed

Reason:

- The context manager protocol expects:

  - One entry
  - One exit

---

### How Exceptions Interact with `yield`

If an exception occurs inside the `with` block:

- Execution resumes **after `yield`**
- The exception is re-raised at the `yield` point
- Cleanup code still executes

That’s why cleanup logic is usually placed inside a `finally` block.

```python
@contextmanager
def safe_context():
    print("Setup")
    try:
        yield
    finally:
        print("Cleanup")
```

---

### Mapping `yield` to the Context Manager Protocol

| `@contextmanager`   | Equivalent Method           |
| ------------------- | --------------------------- |
| Code before `yield` | `__enter__`                 |
| Value yielded       | Return value of `__enter__` |
| Code after `yield`  | `__exit__`                  |

---

### Key Takeaways

- `yield` pauses execution and hands control to the `with` block
- It replaces the need for `__enter__` and `__exit__`
- Code before `yield` runs on entry
- Code after `yield` runs on exit
- Cleanup code always runs if placed in `finally`
- `yield` is the core mechanism behind `contextlib`

---

## Useful `contextlib` Utilities

The `contextlib` module provides several helper utilities that make context management easier and more flexible. These utilities are especially useful when working with resources, cleanup logic, or exception handling.

---

### `suppress()`

The `suppress()` context manager is used to **ignore specific exceptions**.

If the specified exception occurs inside the `with` block, it is silently suppressed. Any other exception will still be raised.

```python
from contextlib import suppress
import os

with suppress(FileNotFoundError):
    os.remove('nonexistent.txt')
```

**Explanation:**

- If the file does not exist, `FileNotFoundError` is raised.
- `suppress(FileNotFoundError)` catches and ignores it.
- Program execution continues normally.
- Other exceptions (e.g., `PermissionError`) are not suppressed.

**Use cases:**

- Optional cleanup
- Deleting files that may or may not exist
- Ignoring expected, non-critical errors

---

### `closing()`

The `closing()` utility ensures that an object’s `close()` method is called when leaving the context.

It is useful for objects that provide a `close()` method but do **not** implement the context manager protocol.

```python
from contextlib import closing
from urllib.request import urlopen

with closing(urlopen('http://example.com')) as page:
    content = page.read()
```

**Explanation:**

- `urlopen()` returns an object that must be closed.
- `closing()` wraps it in a context manager.
- `page.close()` is called automatically on exit.

**Use cases:**

- Network connections
- Legacy APIs
- Objects that require explicit cleanup

---

### `ExitStack`

`ExitStack` allows you to **dynamically manage multiple context managers**, especially when the number of resources is not known in advance.

```python
from contextlib import ExitStack

with ExitStack() as stack:
    files = [stack.enter_context(open(f)) for f in file_list]
```

**Explanation:**

- Context managers are entered dynamically using `enter_context()`.
- All registered contexts are exited automatically.
- Resources are cleaned up in **reverse order** of entry.

**Use cases:**

- Opening a variable number of files
- Conditional resource management
- Complex setup/cleanup logic

---

### When to Use These Utilities

| Utility      | Purpose                                     |
| ------------ | ------------------------------------------- |
| `suppress()` | Ignore specific, expected exceptions        |
| `closing()`  | Ensure `close()` is called on exit          |
| `ExitStack`  | Manage many or conditional context managers |

---

### Key Takeaways

- `contextlib` provides powerful helpers beyond `@contextmanager`
- These utilities simplify exception handling and resource cleanup
- They help write safer, cleaner, and more maintainable code
- `ExitStack` is especially useful for dynamic resource management

---

## Common Use Cases of Context Managers

Context managers are especially useful when you need to **temporarily change state**, **acquire and release resources**, or **guarantee cleanup** regardless of how the code exits.

Below are some common and practical use cases.

---

### 1. Lock Management (Thread Safety)

Context managers are commonly used to manage locks in multithreaded programs. They ensure that a lock is **always released**, even if an exception occurs inside the critical section.

```python
import threading
from contextlib import contextmanager

@contextmanager
def acquired_lock(lock):
    lock.acquire()
    try:
        yield
    finally:
        lock.release()

```

#### Using the Lock

```python
lock = threading.Lock()

with acquired_lock(lock):
    # Critical section
    # Only one thread can execute this block at a time
    pass

```

**Why this is useful:**

- Prevents deadlocks
- Ensures lock release on errors
- Cleaner than manual acquire/release

#### Explanation of code - Lock Management (Thread Safety)

This context manager ensures that a lock is **always acquired before** entering a critical section and **always released afterward**, even if an exception occurs.

**Lock acquisition happens before entering the `with` block:**

```python
lock.acquire()

```

This guarantees exclusive access to shared resources.

**The `yield` statement marks the critical section:**

```python
yield

```

All code inside the `with acquired_lock(lock):` block executes at this point.

**Lock release is guaranteed using `finally`:**

```python
finally:
    lock.release()

```

Because `lock.release()` is inside `finally`, it executes no matter how the block exits, preventing deadlocks.

---

### 2. Temporarily Changing the Working Directory

This context manager temporarily changes the current working directory and restores it afterward.

```python
import os
from contextlib import contextmanager

@contextmanager
def change_dir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)

```

#### Using the Context Manager

```python
with change_dir('/tmp'):
    # All file operations happen inside /tmp
    pass
# Automatically back to the original directory

```

**Why this is useful:**

- Prevents accidental directory leaks
- Makes file operations predictable
- Ensures directory state is restored

#### Explanation of code - Temporarily Changing the Working Directory

This context manager temporarily changes the current working directory and restores it after the `with` block completes.

**Store the original directory before changing it:**

```python
old_dir = os.getcwd()

```

This ensures the previous state can be restored later.

**Change to the new directory:**

```python
os.chdir(path)

```

All file operations inside the `with` block now run in this directory.

**Pause execution and run the `with` block code:**

```python
yield

```

**Restore the original directory afterward:**

```python
finally:
    os.chdir(old_dir)

```

This guarantees that the working directory is always reset, even if an exception occurs.

---

### 3. Temporary Environment Variables

This context manager temporarily sets an environment variable and restores the original value afterward.

```python
import os
from contextlib import contextmanager

@contextmanager
def temporary_env_var(key, value):
    old_value = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old_value is None:
            del os.environ[key]
        else:
            os.environ[key] = old_value

```

#### Using the Context Manager

```python
with temporary_env_var("DEBUG", "true"):
    # Environment variable is set only inside this block
    pass

```

**Why this is useful:**

- Avoids global side effects
- Keeps environment changes scoped
- Useful for testing and configuration

#### Explanation of code - Temporary Environment Variables

This context manager temporarily sets an environment variable and restores its original value afterward.

**Save the current value (if it exists):**

```python
old_value = os.environ.get(key)

```

This allows the environment to be restored correctly.

**Set the temporary value:**

```python
os.environ[key] = value

```

The variable is now available inside the `with` block.

**Execute the block using the temporary environment:**

```python
yield

```

**Restore or remove the variable after execution:**

```python
if old_value is None:
    del os.environ[key]
else:
    os.environ[key] = old_value

```

This ensures:

- Variables are restored if they existed
- New variables are removed if they did not

---

### Key Idea

In all three examples:

- Code **before `yield`** runs when entering the `with` block
- Code **after `yield`** runs when exiting the block
- Cleanup logic is guaranteed using `finally`

---

### Key Pattern Across All Examples

Each example follows the same structure:

- Setup before entering the context
- Safe execution inside the `with` block
- Guaranteed cleanup in `finally`

This makes context managers ideal for managing **temporary changes** and **critical resources**.

---

### Key Takeaways

- Context managers enforce safe entry and exit
- They prevent resource leaks and inconsistent state
- They make code easier to read and reason about
- Ideal for locks, directories, environment variables, and more

---

## Key Takeaways

1. **Context managers** handle setup and cleanup automatically
2. **`__enter__` and `__exit__`** define the protocol
3. **`@contextmanager`** makes creating them easier
4. **Exception handling** in `__exit__` can suppress errors
5. **Resource management** is the primary use case

---

## Practice Exercises

See: `exercises/python-fundamentals/context-managers/EXERCISES.md`

---

## Code Examples

All runnable code: `code-examples/03_context_managers.py`

---

## Tomorrow's Topic

**Day 4: Generators** - Generator functions, expressions, and memory-efficient iteration.

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

## What are Context Managers?

Context managers handle setup and cleanup operations automatically. They're commonly used for:
- File operations
- Database connections
- Lock acquisition and release
- Temporary state changes

### The `with` Statement

```python
with open('file.txt', 'r') as f:
    content = f.read()
# File is automatically closed here
```

---

## The Context Manager Protocol

A context manager implements two methods:
- `__enter__()`: Called when entering the `with` block
- `__exit__(exc_type, exc_val, exc_tb)`: Called when exiting

```python
class MyContextManager:
    def __enter__(self):
        print("Entering context")
        return self  # Return value assigned to 'as' variable
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Exiting context")
        # Return True to suppress exceptions, False to propagate
        return False

with MyContextManager() as cm:
    print("Inside context")
```

---

## Creating Custom Context Managers

### Example: File Handler with Logging

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

with FileHandler('data.txt', 'r') as f:
    content = f.read()
```

### Example: Database Connection Manager

```python
class DatabaseConnection:
    def __init__(self, db_name):
        self.db_name = db_name
        self.connection = None
    
    def __enter__(self):
        print(f"Connecting to {self.db_name}")
        # Simulate connection
        self.connection = f"Connection to {self.db_name}"
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Closing connection to {self.db_name}")
        self.connection = None
        return False

with DatabaseConnection('mydb') as conn:
    print(f"Using {conn}")
```

---

## Exception Handling in Context Managers

The `__exit__` method receives exception information:

```python
class SafeOperation:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"Exception occurred: {exc_type.__name__}: {exc_val}")
            # Return True to suppress the exception
            return True  # Exception won't propagate
        return False

with SafeOperation():
    raise ValueError("Something went wrong")
# Exception is caught and suppressed
print("Execution continues")
```

---

## The contextlib Module

Python provides `contextlib` for easier context manager creation.

### Using @contextmanager Decorator

```python
from contextlib import contextmanager

@contextmanager
def file_handler(filename, mode='r'):
    print(f"Opening {filename}")
    f = open(filename, mode)
    try:
        yield f  # Value provided to 'as' clause
    finally:
        print(f"Closing {filename}")
        f.close()

with file_handler('data.txt') as f:
    content = f.read()
```

### Example: Timer Context Manager

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name="Operation"):
    start = time.time()
    print(f"Starting {name}")
    yield
    end = time.time()
    print(f"{name} took {end - start:.4f} seconds")

with timer("Data processing"):
    time.sleep(1)
    # Process data here
```

### Example: Temporary Directory

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

with temporary_directory() as tmpdir:
    # Use tmpdir for temporary files
    filepath = os.path.join(tmpdir, 'temp.txt')
    with open(filepath, 'w') as f:
        f.write("Temporary data")
# tmpdir is automatically cleaned up
```

---

## Useful contextlib Utilities

### suppress()

```python
from contextlib import suppress

# Suppress specific exceptions
with suppress(FileNotFoundError):
    os.remove('nonexistent.txt')
# No error raised if file doesn't exist
```

### closing()

```python
from contextlib import closing
from urllib.request import urlopen

with closing(urlopen('http://example.com')) as page:
    content = page.read()
# Automatically calls page.close()
```

### ExitStack

```python
from contextlib import ExitStack

with ExitStack() as stack:
    files = [stack.enter_context(open(f)) for f in file_list]
    # All files automatically closed
```

---

## Common Use Cases

### 1. Lock Management

```python
import threading

@contextmanager
def acquired_lock(lock):
    lock.acquire()
    try:
        yield
    finally:
        lock.release()

lock = threading.Lock()
with acquired_lock(lock):
    # Critical section
    pass
```

### 2. Changing Directory

```python
import os

@contextmanager
def change_dir(path):
    old_dir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_dir)

with change_dir('/tmp'):
    # Work in /tmp
    pass
# Back to original directory
```

### 3. Environment Variables

```python
import os

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

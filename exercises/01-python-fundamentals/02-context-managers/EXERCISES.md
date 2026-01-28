# Python Fundamentals - Context Managers Exercises

**Topic**: Context Managers (Week 1, Day 3)  
**Difficulty**: Beginner to Intermediate  
**Total Exercises**: 6

---

## Instructions

- Solve each exercise in the corresponding Python file (exercise_1.py, exercise_2.py, etc.)
- Test your solutions by running the files
- Save completed solutions in the `solutions/` folder
- Review day-3-context-managers.md notes if you get stuck

---

## Exercise 1: Basic Context Manager Class

**Difficulty**: Easy  
**File**: `exercise_1.py`

Create a context manager class that prints messages when entering and exiting.

**Requirements**:
- Create a class called `MessagePrinter`
- Implement `__enter__` and `__exit__` methods
- `__enter__` should print "Entering context" and return self
- `__exit__` should print "Exiting context"
- Should work with the `with` statement

**Example Usage**:
```python
with MessagePrinter():
    print("Inside the context")

# Output:
# Entering context
# Inside the context
# Exiting context
```

**Hints**:
- `__enter__(self)` is called when entering the `with` block
- `__exit__(self, exc_type, exc_val, exc_tb)` is called when exiting
- Return False from `__exit__` to not suppress exceptions

---

## Exercise 2: File Handler Context Manager

**Difficulty**: Easy-Medium  
**File**: `exercise_2.py`

Create a context manager that handles file operations with logging.

**Requirements**:
- Class name: `FileHandler`
- Takes filename and mode as parameters
- Logs when file is opened and closed
- Returns the file object from `__enter__`
- Ensures file is closed even if error occurs
- Handle the case where file doesn't exist

**Example Usage**:
```python
with FileHandler('test.txt', 'w') as f:
    f.write("Hello, World!")
# Should print: "Opening test.txt"
# Should print: "Closing test.txt"

with FileHandler('data.txt', 'r') as f:
    content = f.read()
    print(content)
```

**Hints**:
- Store the file object as an instance variable in `__init__`
- Open the file in `__enter__`
- Close the file in `__exit__`
- Use try-except to handle file errors

---

## Exercise 3: Timer Context Manager

**Difficulty**: Medium  
**File**: `exercise_3.py`

Create a context manager that measures execution time of a code block.

**Requirements**:
- Class name: `Timer`
- Measure time when entering and exiting
- Print elapsed time when exiting
- Optional name parameter for labeling
- Store elapsed time as an attribute

**Example Usage**:
```python
with Timer("Data processing"):
    # Simulate some work
    time.sleep(2)
# Output: Data processing took 2.00 seconds

timer = Timer()
with timer:
    # Some code
    pass
print(f"Elapsed: {timer.elapsed:.2f}s")
```

**Hints**:
- Use `time.time()` to get current timestamp
- Calculate difference between exit and enter times
- Format output to 2 decimal places

---

## Exercise 4: Database Connection Manager (Simulated)

**Difficulty**: Medium  
**File**: `exercise_4.py`

Create a context manager that simulates database connection handling.

**Requirements**:
- Class name: `DatabaseConnection`
- Takes database name as parameter
- Simulate connecting in `__enter__`
- Simulate disconnecting in `__exit__`
- Handle exceptions and rollback on error
- Commit on success

**Example Usage**:
```python
with DatabaseConnection("mydb") as conn:
    print(f"Connected to {conn.db_name}")
    # Simulate query
    conn.execute("SELECT * FROM users")
# Output: Connecting to mydb
# Output: Executing: SELECT * FROM users
# Output: Committing transaction
# Output: Closing connection to mydb

# With error
try:
    with DatabaseConnection("mydb") as conn:
        raise ValueError("Query failed")
except ValueError:
    pass
# Output: Connecting to mydb
# Output: Rolling back transaction
# Output: Closing connection to mydb
```

**Hints**:
- Check if `exc_type` is None in `__exit__` (no exception)
- If `exc_type` is not None, there was an exception
- Simulate methods like `execute()`, `commit()`, `rollback()`

---

## Exercise 5: Temporary Directory Context Manager

**Difficulty**: Medium  
**File**: `exercise_5.py`

Create a context manager that creates a temporary directory and cleans it up.

**Requirements**:
- Class name: `TempDirectory`
- Create temporary directory in `__enter__`
- Return the directory path
- Delete directory and all contents in `__exit__`
- Handle cleanup even if exception occurs

**Example Usage**:
```python
with TempDirectory() as temp_dir:
    print(f"Using temp directory: {temp_dir}")
    # Create files in temp_dir
    with open(os.path.join(temp_dir, 'test.txt'), 'w') as f:
        f.write("temporary data")
# Directory and all files are deleted
```

**Hints**:
- Use `tempfile.mkdtemp()` to create temp directory
- Use `shutil.rmtree()` to delete directory and contents
- Use try-finally in `__exit__` to ensure cleanup

---

## Exercise 6: Context Manager Decorator

**Difficulty**: Medium-Hard  
**File**: `exercise_6.py`

Create a context manager using the `@contextmanager` decorator.

**Requirements**:
- Use `from contextlib import contextmanager`
- Create at least 3 different context managers using decorator:
  1. `change_directory(path)` - temporarily change working directory
  2. `suppress_stdout()` - suppress print statements
  3. `acquire_lock(lock)` - acquire and release a threading lock

**Example Usage**:
```python
@contextmanager
def change_directory(path):
    # Your implementation here
    pass

current = os.getcwd()
with change_directory('/tmp'):
    print(os.getcwd())  # /tmp
print(os.getcwd())  # back to original

@contextmanager
def suppress_stdout():
    # Your implementation here
    pass

print("This will print")
with suppress_stdout():
    print("This won't print")
print("This will print again")

@contextmanager
def acquire_lock(lock):
    # Your implementation here
    pass

lock = threading.Lock()
with acquire_lock(lock):
    # Critical section
    pass
```

**Hints**:
- Use `yield` to separate setup and teardown code
- Save original state before changing it
- Restore original state after yield
- Use try-finally to ensure cleanup

---

## Bonus Exercise 7: Nested Context Managers

**Difficulty**: Hard  
**File**: `exercise_7.py` (Optional)

Create a context manager that manages multiple resources.

**Requirements**:
- Class name: `MultiResource`
- Takes multiple context managers as arguments
- Enters all of them in order
- Exits all of them in reverse order (even if one fails)
- Returns all entered values as a tuple

**Example Usage**:
```python
with MultiResource(
    FileHandler('file1.txt', 'w'),
    FileHandler('file2.txt', 'w'),
    Timer("Multi-resource operation")
) as (f1, f2, timer):
    f1.write("Data 1")
    f2.write("Data 2")
# All resources properly closed
```

---

## Testing Your Solutions

```bash
# Run each exercise
python exercise_1.py
python exercise_2.py
# etc.

# Create test files for file operations
touch test.txt
echo "test data" > data.txt
```

---

## Common Patterns to Practice

### Pattern 1: Resource Management
```python
class ResourceManager:
    def __enter__(self):
        # Acquire resource
        return resource
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Release resource
        return False  # Don't suppress exceptions
```

### Pattern 2: State Changes
```python
class StateChanger:
    def __enter__(self):
        # Save original state
        # Change to new state
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original state
        return False
```

### Pattern 3: Using @contextmanager
```python
from contextlib import contextmanager

@contextmanager
def my_context():
    # Setup
    try:
        yield  # Code block executes here
    finally:
        # Cleanup (always runs)
```

---

## Key Concepts to Remember

1. **`__enter__`**: Called when entering `with` block, returns value for `as` clause
2. **`__exit__`**: Called when exiting, receives exception info if any
3. **Return False**: From `__exit__` to propagate exceptions
4. **Return True**: From `__exit__` to suppress exceptions
5. **Always cleanup**: Use try-finally to ensure cleanup happens

---

## Exception Handling in `__exit__`

```python
def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type is None:
        # No exception occurred
        print("Success!")
    else:
        # Exception occurred
        print(f"Exception: {exc_type.__name__}: {exc_val}")
    
    # Cleanup code here (always runs)
    
    return False  # Let exception propagate
    # return True  # Suppress exception
```

---

## Real-World Use Cases

Context managers are perfect for:
- **File operations**: Ensure files are closed
- **Database connections**: Commit or rollback transactions
- **Locks**: Acquire and release locks
- **Timing**: Measure execution time
- **Temporary state**: Change and restore settings
- **Resource cleanup**: Ensure cleanup happens

---

## Resources

- [Python Context Managers Documentation](https://docs.python.org/3/reference/datamodel.html#context-managers)
- [contextlib Module](https://docs.python.org/3/library/contextlib.html)
- [PEP 343 - The "with" Statement](https://www.python.org/dev/peps/pep-0343/)

---

**Good luck!** Context managers are powerful tools for managing resources and ensuring cleanup. Practice these exercises to master them!

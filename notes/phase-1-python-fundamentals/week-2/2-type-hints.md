# Day 6: Type Hints & Static Type Checking

**Date**: Week 1, Day 6  
**Phase**: 1 - Python Fundamentals  
**Topic**: Type Annotations, Type Checking, and Type Safety

---

## Learning Objectives

- Understand what type hints are and why they matter
- Master basic and advanced type annotations
- Use the `typing` module effectively
- Perform static type checking with mypy
- Apply type hints in real-world code
- Understand when and how to use generic types
- Create type-safe APIs and functions

---

## What are Type Hints?

Type hints (also called type annotations) are **optional syntax** that specify the expected types of variables, function parameters, and return values.

They provide a way to **document and enforce** what types your code expects without changing how Python runs.

### Python is Dynamically Typed

By default, Python doesn't enforce types at runtime:

```python
def add(a, b):
    return a + b

# All of these work!
add(1, 2)              # 3
add("Hello", "World")  # "HelloWorld"
add([1, 2], [3, 4])    # [1, 2, 3, 4]
```

**Why this is flexible:**

- Same function works with multiple types
- Quick to write
- Easy to prototype

**Why this can cause problems:**

- Type errors only appear at runtime
- Bugs can hide until specific code paths execute
- Harder to understand what types are expected

---

### The Problem: Silent Type Bugs

Without type hints, bugs can go undetected:

```python
def calculate_discount(price, discount):
    return price - (price * discount)

# Intended usage
result = calculate_discount(100, 0.2)  # 80.0 - Correct!

# Accidental bug - passing discount as percentage instead of decimal
result = calculate_discount(100, 20)   # -1900.0 - Wrong!
```

**What happened:**

- Function expected discount as decimal (0.2 for 20%)
- Developer passed percentage (20)
- Calculation is wrong but Python doesn't complain
- Bug only discovered when users complain about negative prices

**This is a runtime error that could have been caught before running the code.**

---

### Type Hints to the Rescue

With type hints, we can specify expected types:

```python
def calculate_discount(price: float, discount: float) -> float:
    """Calculate price after discount.

    Args:
        price: Original price
        discount: Discount as decimal (e.g., 0.2 for 20%)

    Returns:
        Price after discount
    """
    return price - (price * discount)
```

Now tools like mypy can catch the bug **before running the code**:

```bash
$ mypy script.py
script.py:10: error: Argument 2 to "calculate_discount" has incompatible type "int"; expected "float"
```

The bug is caught during development, not in production.

---

### Why Use Type Hints?

**Benefit 1: Better IDE Support**

Your IDE can provide better assistance:

```python
def get_user(user_id: int) -> dict[str, str]:
    return {"id": str(user_id), "name": "Alice"}

# IDE knows this returns a dict
user = get_user(123)
name = user["name"]  # IDE autocompletes "name" key
```

**What you get:**

- Autocomplete for function parameters
- Autocomplete for return value attributes
- Inline error detection
- Smart refactoring suggestions

---

**Benefit 2: Catch Bugs Early**

Static analysis tools can find bugs before runtime:

```python
def greet(name: str) -> str:
    return f"Hello, {name}"

# mypy catches this immediately
greet(123)  # Error: Argument has incompatible type "int"; expected "str"
```

**What this prevents:**

- TypeError exceptions at runtime
- Null reference errors
- Type mismatches in function calls
- Invalid method calls

---

**Benefit 3: Self-Documenting Code**

Type hints serve as inline documentation:

```python
# Without type hints - what types are expected?
def process_data(items, limit, callback):
    pass

# With type hints - crystal clear!
def process_data(
    items: list[dict[str, str]],
    limit: int,
    callback: Callable[[str], bool]
) -> list[str]:
    pass
```

**What this provides:**

- Clear expectations for function inputs
- Clear expectations for function outputs
- No need to read implementation to understand interface
- Better than comments (can become outdated)

---

**Benefit 4: Safer Refactoring**

When you change a function signature, type checkers find all affected code:

```python
# Original function
def get_user(user_id: int) -> dict[str, str]:
    return {"id": str(user_id), "name": "Alice"}

# Change to return a custom type
def get_user(user_id: int) -> User:
    return User(id=user_id, name="Alice")

# mypy finds all places where code expects dict
# and shows what needs to be updated
```

**What this enables:**

- Confident code changes
- Find all breaking changes immediately
- Team collaboration without fear
- Large-scale refactoring

---

### Important: Type Hints Are Optional

**Critical concept to understand:**

Type hints are **metadata for tools**, not runtime checks:

```python
# This is valid Python - no type hints required
def greet(name):
    return f"Hello, {name}"

# This is also valid - with type hints
def greet(name: str) -> str:
    return f"Hello, {name}"

# Both work exactly the same at runtime!
greet(123)  # Python runs this without error in both versions
```

**What this means:**

- Type hints don't change Python's behavior
- Python doesn't enforce types at runtime
- Type hints are for static analysis tools (mypy, IDEs)
- You can add type hints gradually to existing code

**To actually enforce types:**

- Use static type checkers (mypy, pyright)
- Run them in CI/CD pipelines
- Integrate with your editor

---

## Basic Type Annotations

### Variable Annotations

You can annotate variables with their expected types:

```python
# Basic types
name: str = "Alice"
age: int = 30
price: float = 19.99
is_active: bool = True

# Type declaration without initial value
username: str
count: int

# Later assignment
username = "bob"
count = 42
```

**When to use variable annotations:**

- When type isn't obvious from assignment
- When declaring variables without immediate assignment
- For class attributes
- For documenting complex types

**When you can skip them:**

```python
# Type is obvious - annotation optional
name = "Alice"  # Clearly a string
count = 42      # Clearly an integer
```

---

### Function Annotations

Function annotations specify parameter types and return type:

```python
def greet(name: str) -> str:
    """Greet a person by name.

    Args:
        name: Person's name

    Returns:
        Greeting message
    """
    return f"Hello, {name}!"
```

**Anatomy of function annotations:**

```
def function_name(param1: Type1, param2: Type2) -> ReturnType:
                         ↑              ↑            ↑
                        Parameter   types         Return type
```

**Key points:**

- Parameter types come after the parameter name
- Return type comes after `->`
- All annotations are optional
- Can mix annotated and non-annotated parameters

---

### Multiple Parameters and Return Types

```python
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

def divide(a: float, b: float) -> float:
    """Divide two floats."""
    return a / b

def swap(a: int, b: int) -> tuple[int, int]:
    """Swap two values and return both."""
    return b, a

# Function with no return value
def print_message(msg: str) -> None:
    """Print a message (returns None)."""
    print(msg)
```

**Understanding `-> None`:**

- Means the function returns `None`
- Same as functions without explicit `return`
- Different from no annotation (which could return anything)

**Why annotate None returns:**

- Makes intent explicit
- Prevents accidental use of return value
- Type checker verifies you don't return anything else

---

### Collection Types

**Python 3.9+ uses built-in types directly:**

```python
# Lists
names: list[str] = ["Alice", "Bob", "Charlie"]
numbers: list[int] = [1, 2, 3, 4, 5]

# Dictionaries
ages: dict[str, int] = {"Alice": 30, "Bob": 25}
scores: dict[str, float] = {"math": 95.5, "english": 88.0}

# Sets
unique_ids: set[int] = {1, 2, 3, 4, 5}

# Tuples (fixed size)
coordinates: tuple[float, float] = (10.5, 20.3)
rgb: tuple[int, int, int] = (255, 128, 0)
```

**Important syntax notes:**

- Use square brackets `[]` for type parameters
- List, dict, set, tuple are lowercase
- Tuple types specify each element's type

---

**Python 3.8 and earlier requires importing from typing:**

```python
from typing import List, Dict, Set, Tuple

names: List[str] = ["Alice", "Bob"]
ages: Dict[str, int] = {"Alice": 30}
unique_ids: Set[int] = {1, 2, 3}
point: Tuple[float, float] = (10.5, 20.3)
```

**Recommendation:**

- Use lowercase built-in types if on Python 3.9+
- Import from `typing` only if on Python 3.8 or earlier
- Be consistent within your project

---

### Nested Collections

You can nest type annotations for complex data structures:

```python
# List of lists
matrix: list[list[int]] = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]

# Dictionary with list values
student_grades: dict[str, list[float]] = {
    "Alice": [95.0, 87.5, 92.0],
    "Bob": [88.0, 91.5, 85.0]
}

# List of tuples
points: list[tuple[float, float]] = [
    (10.5, 20.3),
    (15.2, 30.1),
    (5.0, 8.5)
]

# Dictionary with dictionary values
user_data: dict[str, dict[str, str]] = {
    "user1": {"name": "Alice", "email": "alice@example.com"},
    "user2": {"name": "Bob", "email": "bob@example.com"}
}
```

**When nesting gets complex:**

- Consider using type aliases (covered later)
- Consider using TypedDict for structured dictionaries
- Keep nesting to 2-3 levels maximum for readability

---

## Advanced Type Hints

### Optional Types

`Optional[Type]` means the value can be `Type` or `None`:

```python
from typing import Optional

def find_user(user_id: int) -> Optional[str]:
    """Find user by ID.

    Returns:
        Username if found, None if not found
    """
    users = {1: "Alice", 2: "Bob"}
    return users.get(user_id)

# Usage
user = find_user(1)  # Type: Optional[str] (str | None)

if user is not None:
    print(f"Found: {user}")  # Type checker knows user is str here
else:
    print("User not found")
```

**How Optional works:**

```python
# These are equivalent:
Optional[str]  # Explicit Optional
str | None     # Python 3.10+ union syntax
```

**Why use Optional:**

- Makes nullable values explicit
- Type checker can verify None checks
- Documents that function might return None
- Prevents "NoneType has no attribute" errors

---

**Modern syntax (Python 3.10+):**

```python
def find_user(user_id: int) -> str | None:
    users = {1: "Alice", 2: "Bob"}
    return users.get(user_id)
```

**Recommendation:**

- Use `str | None` syntax on Python 3.10+
- Use `Optional[str]` on older versions
- Be consistent within your project

---

### Union Types

`Union[Type1, Type2]` means the value can be one of multiple types:

```python
from typing import Union

def process_id(id_value: Union[int, str]) -> str:
    """Process ID that could be int or str.

    Args:
        id_value: ID as integer or string

    Returns:
        Normalized ID as string
    """
    if isinstance(id_value, int):
        return f"ID-{id_value:06d}"
    else:
        return id_value.upper()

# Valid calls
process_id(123)      # "ID-000123"
process_id("abc")    # "ABC"
```

**How Union works:**

- Value can be any of the specified types
- Type checker verifies all possible types are handled
- Use `isinstance()` to narrow type in code

---

**Modern syntax (Python 3.10+):**

```python
def process_id(id_value: int | str) -> str:
    if isinstance(id_value, int):
        return f"ID-{id_value:06d}"
    else:
        return id_value.upper()
```

**Union of multiple types:**

```python
def process_value(val: int | float | str) -> str:
    """Accept int, float, or str."""
    return str(val)
```

**When to use Union:**

- Functions that genuinely accept multiple types
- Migration from untyped to typed code
- Handling external data with variable types

**When to avoid Union:**

- If you're just avoiding thinking about types
- When overloading or generics would be better
- When it makes the function too complex

---

### Any Type

`Any` means **any type is acceptable** (disables type checking for that value):

```python
from typing import Any

def process_data(data: Any) -> None:
    """Process data of any type.

    Warning: Using Any disables type checking!
    """
    print(data)

# All valid - type checker accepts anything
process_data(42)
process_data("hello")
process_data([1, 2, 3])
process_data({"key": "value"})
```

**What Any means:**

- Type checker assumes any operation is valid
- No type safety for that value
- Equivalent to no type annotation

**When to use `Any`:**

- Working with truly dynamic data (JSON from external APIs)
- Gradual typing (adding types to legacy code)
- Placeholder during development
- Framework code that handles arbitrary types

**When NOT to use `Any`:**

- As a shortcut to avoid thinking about types
- When you actually know the type
- When Union or generics would work better
- In public APIs (makes the API less safe)

**Example of proper Any usage:**

```python
import json
from typing import Any

def parse_json(text: str) -> Any:
    """Parse JSON string. Return type depends on JSON content."""
    return json.loads(text)  # Could be dict, list, str, int, etc.
```

---

### Literal Types

`Literal` is used to **restrict a variable or parameter to a fixed set of exact values**.
Unlike normal type hints (like `str` or `int`), `Literal` enforces **specific allowed values**.

This gives you **enum-like safety** while keeping the code simple.

---

### Basic Example

```python
from typing import Literal

def set_log_level(level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]) -> None:
    """
    Set the logging level.

    Args:
        level: Must be one of the predefined log levels
    """
    print(f"Log level set to: {level}")
```

Here, `level` is:

- A string
- But only **one of the specified values**

---

### What This Enforces

```python
# Valid values (exact matches)
set_log_level("DEBUG")
set_log_level("INFO")
```

```python
# Invalid values (caught by type checkers)
set_log_level("TRACE")   # Not allowed
set_log_level("debug")   # Case-sensitive
set_log_level("Info")    # Case-sensitive
```

These errors are detected **before runtime** by tools like `mypy` or IDEs.

---

### Why `Literal` Is Useful

Without `Literal`:

- Any string would be accepted
- Typos would fail only at runtime (or silently)

With `Literal`:

- Allowed values are explicitly documented
- Typos are caught early
- APIs become self-describing
- Refactoring becomes safer

---

### Literal vs Enum (Conceptual Difference)

- `Literal`:

  - Lightweight
  - No runtime object
  - Best for small, fixed options

- `Enum`:

  - Runtime construct
  - Useful when values have behavior or identity

---

### Mixing Multiple Literal Value Types

`Literal` is not limited to a single type.

```python
from typing import Literal

def process_value(value: Literal[1, 2, "auto", "manual"]) -> None:
    pass
```

```python
process_value(1)        # Valid
process_value("auto")   # Valid
process_value(3)        # Invalid
process_value("other")  # Invalid
```

Each value must match **exactly**.

---

### Common Use Cases

- Configuration options
- Mode or feature switches
- Status and state values
- API versions and flags
- Function parameters with limited valid values

---

### Key Takeaways

- `Literal` restricts values, not just types
- Matching is exact and case-sensitive
- Acts like an enum at the type level
- Great for safer and more expressive APIs

---

### Callable Types

`Callable` is used to **type-annotate functions that are passed as arguments to other functions**.  
It makes it explicit **what kind of function is expected**: its parameters and its return type.

This improves:

- Readability
- Static type checking
- Editor auto-completion
- API clarity

---

### Basic Example

```python
from typing import Callable

def apply_operation(
    x: int,
    y: int,
    operation: Callable[[int, int], int]
) -> int:
    """
    Apply an operation to two numbers.

    Args:
        x: First integer
        y: Second integer
        operation: A function that takes two integers
                   and returns an integer

    Returns:
        The result of applying the operation
    """
    return operation(x, y)

```

Here, `operation` must be:

- A function
- That accepts **two `int` arguments**
- And returns an `int`

---

### Callable Syntax Explained

```
Callable[[param_type1, param_type2, ...], return_type]

```

Example:

```
Callable[[int, int], int]

```

- Parameters: `int`, `int`
- Return type: `int`

---

### Common Callable Examples

```python
from typing import Callable, Any

```

```python
# Function that takes no arguments and returns a string
callback: Callable[[], str]

```

```python
# Function that takes two integers and returns a boolean
comparator: Callable[[int, int], bool]

```

```python
# Function that takes a string and an integer and returns nothing
handler: Callable[[str, int], None]

```

```python
# Function with any parameters and any return type
# (use sparingly – reduces type safety)
func: Callable[..., Any]

```

---

### Real-World Usage Example

```python
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

```

```python
result1 = apply_operation(5, 3, add)        # 8
result2 = apply_operation(5, 3, multiply)  # 15

```

The same function (`apply_operation`) works with different behaviors depending on the callable passed.

---

### Why Callable Is Useful

Without `Callable`, it is unclear:

- What parameters the function should accept
- What it should return

With `Callable`, the contract is explicit and enforceable by type checkers.

---

### When to Use `Callable`

Use `Callable` when your function accepts another function, such as:

- Callback functions
- Event handlers
- Strategy pattern implementations
- Decorators
- Higher-order functions (functions that operate on other functions)

---

### Key Takeaways

- `Callable` describes **function signatures**
- It improves code correctness and documentation
- Prefer explicit parameter and return types
- Avoid `Callable[..., Any]` unless absolutely necessary

---

## Generic Types

Generics allow creating reusable, type-safe code that works with multiple types.

### Understanding the Problem

Without generics, you need separate functions for each type:

```python
def get_first_int(items: list[int]) -> int:
    return items[0]

def get_first_str(items: list[str]) -> str:
    return items[0]

def get_first_float(items: list[float]) -> float:
    return items[0]

# Need to create a new function for every type!
```

**This is repetitive and doesn't scale.**

---

### TypeVar - Creating Generic Types

`TypeVar` lets you create a type variable that represents "any type":

```python
from typing import TypeVar

T = TypeVar('T')  # T can be any type

def get_first(items: list[T]) -> T:
    """Get first item from list.

    Works with any type - preserves the type!
    """
    return items[0]
```

**How this works:**

```python
# Type is inferred from usage
first_num = get_first([1, 2, 3])      # Type: int
first_str = get_first(["a", "b"])     # Type: str
first_float = get_first([1.5, 2.5])   # Type: float
```

**What happens:**

- Type checker sees `list[int]` argument
- Infers `T = int`
- Return type becomes `int`
- Same function works for all types, but maintains type safety

**Benefits:**

- Write once, use with any type
- Type safety preserved
- IDE autocomplete works correctly
- No need for type casting

---

### Generic Classes

You can create classes that work with any type:

```python
from typing import Generic, TypeVar

T = TypeVar('T')

class Stack(Generic[T]):
    """Generic stack that works with any type."""

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        """Add item to stack."""
        self._items.append(item)

    def pop(self) -> T:
        """Remove and return top item."""
        return self._items.pop()

    def peek(self) -> T:
        """Return top item without removing."""
        return self._items[-1]

    def is_empty(self) -> bool:
        """Check if stack is empty."""
        return len(self._items) == 0
```

**Using the generic class:**

```python
# Type-safe integer stack
int_stack: Stack[int] = Stack()
int_stack.push(1)
int_stack.push(2)
num = int_stack.pop()  # Type: int

# Type-safe string stack
str_stack: Stack[str] = Stack()
str_stack.push("hello")
str_stack.push("world")
text = str_stack.pop()  # Type: str

# Type error - caught by mypy!
int_stack.push("string")  # Error: expected int, got str
```

**What this provides:**

- Same implementation for all types
- Type safety for each instance
- No runtime overhead
- Clear intent in type annotations

---

### Bounded TypeVars

`TypeVar` can be **restricted** so that only certain types (or subclasses) are allowed.
This lets you write **generic but type-safe** functions.

There are **two common ways** to restrict a `TypeVar`:

1. Restrict to a fixed set of types
2. Restrict to a base class and its subclasses

---

### Restricting to Specific Types

You can limit a type variable to **only a predefined list of types**.

```python
from typing import TypeVar

# Number can be either int or float (and nothing else)
Number = TypeVar("Number", int, float)

def add_numbers(a: Number, b: Number) -> Number:
    """Add two numeric values of the same type."""
    return a + b
```

#### Valid Usage

```python
add_numbers(5, 3)        # int + int → int
add_numbers(5.5, 3.2)    # float + float → float
```

#### Invalid Usage (Caught by Type Checkers)

```python
add_numbers("5", "3")    # Error: str is not allowed
add_numbers(5, 3.2)      # Error: mixed types
```

#### What This Guarantees

- Only `int` or `float` are accepted
- Both parameters must be the **same type**
- The return type matches the input type
- Type safety without losing flexibility

---

### Restricting to Subclasses (Using `bound`)

A **bounded `TypeVar`** allows you to restrict a generic type so that it can only be a **specific base class or any of its subclasses**.

This is useful when:

- You want to accept different related types
- You need to ensure certain methods or attributes exist
- You want to preserve the _exact_ input type in the return value

---

### Defining a Base Class and Subclasses

```python
from typing import TypeVar

class Animal:
    def speak(self) -> str:
        return "..."

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"

class Cat(Animal):
    def speak(self) -> str:
        return "Meow!"
```

Here:

- `Animal` defines a common interface (`speak`)
- `Dog` and `Cat` are concrete subclasses
- All subclasses share the same method but implement it differently

---

### Creating a Bounded TypeVar

```python
AnimalType = TypeVar("AnimalType", bound=Animal)
```

This means:

- `AnimalType` **must be `Animal` or a subclass of `Animal`**
- Any other type (like `str`, `int`, etc.) is rejected by type checkers
- The bound guarantees the presence of `.speak()`

---

### Using the Bounded TypeVar in a Function

```python
def make_speak(animal: AnimalType) -> AnimalType:
    """
    Make the animal speak and return the same object.
    """
    print(animal.speak())
    return animal
```

#### What This Signature Guarantees

- Input must be an `Animal` or subclass
- `.speak()` is always safe to call
- The return type is **the same concrete type** as the input

This is more powerful than:

```python
def make_speak(animal: Animal) -> Animal:
    ...
```

because that version would lose information about whether the object was a `Dog` or a `Cat`.

---

### Using the Function

```python
dog = make_speak(Dog())
cat = make_speak(Cat())
```

Type checkers infer:

- `dog` is of type `Dog`
- `cat` is of type `Cat`

The specific type is preserved, not widened to `Animal`.

---

### Invalid Usage (Caught by Type Checkers)

```python
make_speak("dog")  # Error: str is not a subclass of Animal
```

This fails because:

- `str` does not inherit from `Animal`
- It does not have a `.speak()` method
- It violates the `bound=Animal` constraint

---

### Why `bound` Is Important

Using `bound` allows you to:

- Enforce class-based constraints
- Safely call subclass methods
- Preserve precise return types
- Write reusable, type-safe APIs

This pattern is widely used in:

- Frameworks
- Fluent interfaces
- Library and SDK design
- Code that operates on class hierarchies

---

### Key Takeaway

A bounded `TypeVar` (`bound=BaseClass`) lets you write **generic functions that work with subclasses while keeping strict type safety and precise return types**.

### Using the Bounded TypeVar

```python
dog = make_speak(Dog())  # Type is Dog
cat = make_speak(Cat())  # Type is Cat
```

```python
make_speak("dog")  # Error: str is not a subclass of Animal
```

#### Why This Matters

- Methods like `.speak()` are guaranteed to exist
- The **exact type is preserved** (`Dog` stays `Dog`)
- Safer than using the base class directly
- Enables fluent APIs and chaining

---

### When to Use Bounded TypeVars

- Framework and library code
- Functions operating on class hierarchies
- APIs that must preserve concrete types
- When you need both **flexibility and safety**

---

### Key Takeaways

- Use `TypeVar(T, A, B)` to restrict to specific types
- Use `TypeVar(T, bound=BaseClass)` to restrict to subclasses
- Bounded TypeVars prevent invalid usage at type-check time
- They enable powerful, expressive, and safe generic APIs

---

## Type Aliases

Type aliases allow you to give **meaningful names to existing types**.  
They **do not create new types** — they only improve clarity and readability.

> Think of type aliases as _labels for intent_, not new data types.

---

### Simple Type Alias

```python
from typing import TypeAlias

UserId: TypeAlias = int
Username: TypeAlias = str

def get_user(user_id: UserId) -> Username:
    """Get username by user ID."""
    users = {1: "Alice", 2: "Bob"}
    return users.get(user_id, "Unknown")

```

**Why this is useful:**

- `UserId` is more descriptive than a plain `int`
- Function signatures become self-documenting
- Improves readability without changing runtime behavior
- Makes future changes easier (e.g., `int → UUID`)

---

### What Type Aliases Do (and Don’t Do)

- Improve readability and intent
- Help document domain concepts
- Work with type checkers
- Do **not** enforce runtime checks
- Do **not** create distinct types at runtime

```python
UserId = int  # Same runtime type, clearer meaning

```

---

### Complex Type Alias

#### Without Type Alias

```python
def process_users(
    data: dict[int, dict[str, int | str | list[str]]]
) -> list[dict[str, int | str | list[str]]]:
    pass

```

This is hard to read and difficult to maintain.

---

#### With Type Alias

```python
from typing import TypeAlias

UserData: TypeAlias = dict[str, int | str | list[str]]
UserMap: TypeAlias = dict[int, UserData]

def process_users(data: UserMap) -> list[UserData]:
    pass

```

**What improves here:**

- Clear separation of data structures
- No repeated complex type definitions
- Easier to update and refactor
- Function intent is immediately visible

---

### Benefits of Type Aliases

- Significantly improve readability
- Reduce repetition of complex types
- Make refactoring safer and simpler
- Serve as lightweight documentation
- Scale well in large codebases

---

### Common Patterns

#### Geometric Types

```python
Point: TypeAlias = tuple[float, float]
Polygon: TypeAlias = list[Point]

```

---

#### JSON-like Structures

```python
from typing import Any

JSON: TypeAlias = dict[str, Any]
JSONList: TypeAlias = list[JSON]

```

---

#### Callback Types

```python
from typing import Callable

SuccessCallback: TypeAlias = Callable[[str], None]
ErrorCallback: TypeAlias = Callable[[Exception], None]

```

---

### When to Use Type Aliases

Use type aliases when:

- A type appears multiple times
- A type is complex or deeply nested
- You want to communicate intent clearly
- The underlying type may change later

Avoid them when:

- The type is trivial and used only once
- The alias reduces clarity instead of improving it

---

### Key Idea

Type aliases are about **expressing meaning**, not changing behavior.  
They make complex code easier to read, understand, and maintain.

---

## NewType — Creating Distinct Types

`NewType` lets you create **logically distinct types** for the type checker, even though they are the **same underlying type at runtime**.

This is especially useful when multiple values share the same primitive type (like `int`) but represent **different concepts**.

---

### Basic Usage

```python
from typing import NewType

# Distinct types (both are int at runtime)
UserId = NewType("UserId", int)
ProductId = NewType("ProductId", int)

def get_user(user_id: UserId) -> str:
    """Get user by ID."""
    return f"User {user_id}"

def get_product(product_id: ProductId) -> str:
    """Get product by ID."""
    return f"Product {product_id}"
```

Here:

- `UserId` and `ProductId` are **not interchangeable**
- Type checkers treat them as different types
- At runtime, they are still plain integers

---

### Creating and Using NewType Values

```python
user_id = UserId(123)
product_id = ProductId(456)

get_user(user_id)        # OK
get_product(product_id)  # OK
```

---

### Type Safety in Action

```python
get_user(product_id)   # ❌ Type error
get_product(user_id)   # ❌ Type error
get_user(123)          # ❌ Type error
```

**Why these are errors:**

- `ProductId` ≠ `UserId`
- A raw `int` is not automatically a `UserId`
- You must explicitly construct the correct type

This prevents entire classes of bugs caused by mixing identifiers.

---

### Runtime Behavior (Important)

```python
isinstance(user_id, int)  # True
```

- `NewType` has **zero runtime cost**
- No wrapper objects
- No performance penalty
- Safety exists only at type-check time

---

### Why Use NewType

- Prevents mixing similar-looking values
- Makes APIs harder to misuse
- Improves readability and intent
- Catches bugs before runtime
- Ideal for IDs, tokens, keys, and handles

---

### Real-World Example (Web Application)

```python
from typing import NewType

UserId = NewType("UserId", int)
PostId = NewType("PostId", int)
CommentId = NewType("CommentId", int)

def delete_comment(user_id: UserId, comment_id: CommentId) -> bool:
    """Delete a comment."""
    return True
```

#### What the Type Checker Protects You From

```python
delete_comment(post_id, comment_id)   # ❌ wrong ID type
delete_comment(comment_id, user_id)   # ❌ arguments swapped
```

These mistakes are common in real systems and **hard to detect at runtime**, but trivial for a type checker.

---

### NewType vs Type Alias

| Feature                    | TypeAlias | NewType |
| -------------------------- | --------- | ------- |
| Creates a new logical type | ❌        | ✅      |
| Runtime overhead           | ❌        | ❌      |
| Prevents mixing values     | ❌        | ✅      |
| Improves readability       | ✅        | ✅      |
| Type-checker enforced      | Limited   | Strong  |

---

### When to Use NewType

Use `NewType` when:

- Multiple values share the same base type
- Mixing them would be a serious bug
- You want stronger guarantees than aliases

Avoid it when:

- The distinction is not meaningful
- Values are frequently converted back and forth
- Simplicity matters more than strictness

---

### Key Idea

`NewType` adds **semantic meaning** to primitive types and lets the type checker enforce correctness — without changing runtime behavior.

## Protocol — Structural Subtyping

`Protocol` lets you define **interfaces by behavior**, not by inheritance.
If an object has the required methods and attributes, it is accepted — regardless of its class hierarchy.

This is **typed duck typing**.

> “If it looks like a duck and quacks like a duck, it’s a duck.”

---

### The Problem with Inheritance-Based Interfaces

```python
class DrawableBase:
    def draw(self) -> None:
        raise NotImplementedError

class Circle(DrawableBase):
    def draw(self) -> None:
        print("Drawing circle")

def render(obj: DrawableBase) -> None:
    obj.draw()
```

**Limitations of this approach:**

- Classes **must inherit** from `DrawableBase`
- You cannot use:

  - Third-party classes
  - Built-in types
  - Existing classes you don’t control

- Forces an artificial inheritance relationship
- Tight coupling between code and type hierarchy

---

### Solution: Protocol (Structural Typing)

```python
from typing import Protocol

class Drawable(Protocol):
    """Anything that can be drawn."""

    def draw(self) -> None:
        ...
```

The protocol defines **what an object must be able to do**, not what it must inherit from.

---

### Using the Protocol

```python
class Circle:
    def draw(self) -> None:
        print("Drawing circle")

class Square:
    def draw(self) -> None:
        print("Drawing square")

class Text:
    def display(self) -> None:
        print("Displaying text")
```

No inheritance. No base classes.
Only method compatibility matters.

---

### Consuming the Protocol

```python
def render(obj: Drawable) -> None:
    """Render any drawable object."""
    obj.draw()
```

---

### What the Type Checker Accepts

```python
render(Circle())   # OK
render(Square())   # OK
```

```python
render(Text())     # Error: Text does not implement draw()
```

**Why `Text` fails:**

- Method name does not match
- Structural requirements are not satisfied

---

### How Protocol Works

- Matching is **structural**, not nominal
- Type checker looks for:

  - Required methods
  - Correct method signatures

- Inheritance is irrelevant
- Runtime behavior is unchanged

---

### Protocol vs Inheritance

| Feature                  | Inheritance | Protocol |
| ------------------------ | ----------- | -------- |
| Requires subclassing     | Yes         | No       |
| Works with external code | No          | Yes      |
| Structural typing        | No          | Yes      |
| Flexible APIs            | Limited     | High     |
| Matches duck typing      | No          | Yes      |

---

### Why Protocol Is Powerful

- Decouples interfaces from implementations
- Enables clean, flexible APIs
- Works naturally with Python’s dynamic nature
- Ideal for libraries, frameworks, and plugins

---

### Common Use Cases

- Callback interfaces
- Pluggable components
- Framework extension points
- Testing and mocking
- Adapting third-party or legacy code

---

### Key Idea

`Protocol` defines **what an object can do**, not **what it is**.
If an object satisfies the structure, it satisfies the type.

## TypedDict — Typed Dictionaries

`TypedDict` lets you define **exact dictionary shapes**: which keys exist and what types their values have.
This brings type safety and clarity to one of Python’s most flexible (and error-prone) data structures.

---

### The Problem with Plain `dict`

```python
user = {
    "id": 1,
    "name": "Alice",
    "email": "alice@example.com"
}

# Typos are not caught until runtime
print(user["nane"])  # KeyError at runtime
```

**Issues with plain dictionaries:**

- No guarantee which keys exist
- No guarantee of value types
- Typos are silent until runtime
- IDEs cannot reliably autocomplete keys

---

### Solution: TypedDict

```python
from typing import TypedDict

class User(TypedDict):
    id: int
    name: str
    email: str
    is_active: bool
```

This defines the **expected structure** of the dictionary.

---

### Using a TypedDict

```python
user: User = {
    "id": 1,
    "name": "Alice",
    "email": "alice@example.com",
    "is_active": True
}
```

- All required keys must be present
- Each value must match the declared type

---

### Errors Caught by the Type Checker

```python
bad_user: User = {
    "id": "1",                 # Error: expected int
    "name": "Bob",
    "email": "bob@example.com"
    # Error: missing required key "is_active"
}
```

These mistakes are caught **before runtime**.

---

### TypedDict in Functions

```python
def process_user(user: User) -> str:
    # IDE knows user["name"] is a str
    return user["name"].upper()
```

**Benefits inside functions:**

- Key autocomplete
- Correct value types inferred
- Safer refactoring

---

### Optional Keys with `NotRequired`

```python
from typing import TypedDict, NotRequired

class UserProfile(TypedDict):
    id: int
    name: str
    email: str
    phone: NotRequired[str]
    age: NotRequired[int]
```

- Required keys must always exist
- Optional keys may be missing or present

---

### Valid Usage with Optional Keys

```python
profile: UserProfile = {
    "id": 1,
    "name": "Alice",
    "email": "alice@example.com"
}
```

```python
profile2: UserProfile = {
    "id": 2,
    "name": "Bob",
    "email": "bob@example.com",
    "phone": "555-1234",
    "age": 30
}
```

Both are valid.

---

### What TypedDict Guarantees

- Exact key names
- Correct value types
- Early detection of missing or extra keys
- Better IDE support and documentation

---

### TypedDict vs `dict[str, Any]`

| Feature          | `dict[str, Any]` | `TypedDict` |
| ---------------- | ---------------- | ----------- |
| Key validation   | No               | Yes         |
| Value validation | No               | Yes         |
| Autocomplete     | Poor             | Excellent   |
| Runtime overhead | None             | None        |
| Static safety    | Low              | High        |

---

### Common Use Cases

- API request and response payloads
- JSON-like data structures
- Configuration dictionaries
- Database query results
- Data exchanged between services

---

### Key Idea

`TypedDict` keeps the **flexibility of dictionaries** while adding **compile-time guarantees** about their structure.

## Type Checking with mypy

mypy is the most popular static type checker for Python.

### Installing mypy

```bash
pip install mypy
```

### Basic Usage

```bash
# Check a single file
mypy script.py

# Check all Python files in directory
mypy src/

# Check with strict mode (enables many checks)
mypy --strict script.py
```

---

### Example: Type Checking in Action

**script.py:**

```python
def greet(name: str) -> str:
    return f"Hello, {name}"

def add(a: int, b: int) -> int:
    return a + b

# Correct usage
print(greet("Alice"))
print(add(5, 3))

# Type errors
print(greet(123))        # Error: expected str, got int
print(add("5", "3"))     # Error: expected int, got str
result: str = add(5, 3)  # Error: expected str, got int
```

**Running mypy:**

```bash
$ mypy script.py

script.py:11: error: Argument 1 to "greet" has incompatible type "int"; expected "str"
script.py:12: error: Argument 1 to "add" has incompatible type "str"; expected "int"
script.py:12: error: Argument 2 to "add" has incompatible type "str"; expected "int"
script.py:13: error: Incompatible types in assignment (expression has type "int", variable has type "str")
Found 4 errors in 1 file (checked 1 source file)
```

**All errors caught before running the code!**

---

### mypy Configuration

Create `mypy.ini` for project-wide settings:

```ini
[mypy]
# Python version to target
python_version = 3.11

# Show error codes
show_error_codes = True

# Warn about returning Any
warn_return_any = True

# Warn about unused configs
warn_unused_configs = True

# Disallow functions without type hints
disallow_untyped_defs = True

# Disallow incomplete type hints
disallow_incomplete_defs = True

# Per-module options
[mypy-tests.*]
disallow_untyped_defs = False
```

Or use `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

---

### Common mypy Options

```bash
# Disallow functions without type hints
mypy --disallow-untyped-defs script.py

# Disallow any use of 'Any'
mypy --disallow-any-explicit script.py

# Strict mode (enables many checks)
mypy --strict script.py

# Ignore missing imports for third-party libraries
mypy --ignore-missing-imports script.py

# Show error codes (helpful for configuration)
mypy --show-error-codes script.py

# Generate HTML report
mypy --html-report ./mypy-report script.py
```

**Recommended workflow:**

1. Start with basic mypy (no flags)
2. Add `--disallow-untyped-defs` for new code
3. Eventually use `--strict` for maximum safety

---

### Ignoring Specific Errors

Sometimes you need to ignore type errors (use sparingly):

```python
from typing import Any

def legacy_function(data: Any) -> Any:
    # Ignore type checking for this specific line
    result = data.some_method()  # type: ignore
    return result

# Ignore specific error code
value = get_value()  # type: ignore[attr-defined]

# Ignore entire function (discouraged)
def untyped_function():  # type: ignore
    pass
```

**When to use `# type: ignore`:**

- Working with untyped third-party libraries
- Temporary workaround during migration
- Known limitation in type checker
- Interfacing with dynamic code

**When NOT to use it:**

- To avoid fixing real type errors
- As a shortcut to avoid thinking
- In new code (add proper types instead)

**Best practice:**

- Always include a comment explaining why
- Track all ignores and plan to remove them
- Use specific error codes when possible

---

## Real-World Examples

### Example 1: Type-Safe API Response

This example shows how `TypedDict` helps model **real-world API responses** in a safe and predictable way.

An API response usually has a fixed structure:

- A flag indicating success or failure
- Data when the request succeeds
- An error message when it fails

By encoding this structure in a `TypedDict`, you get:

- A **guaranteed response shape** across your codebase
- Type-safe access to `success`, `data`, and `error`
- IDE autocomplete for response fields
- Early detection of missing keys or wrong value types

The control flow becomes clearer:

- When `success` is `True`, `data` is expected to be present
- When `success` is `False`, `error` is expected to be present

This pattern makes error handling explicit and avoids fragile assumptions about API responses.

```python
from typing import TypedDict, Optional

class APIResponse(TypedDict):
    success: bool
    data: Optional[dict[str, Any]]
    error: Optional[str]

def fetch_user_data(user_id: int) -> APIResponse:
    """Fetch user data from API.

    Returns:
        Typed API response with success/error status
    """
    try:
        # Simulate API call
        user_data = {"id": user_id, "name": "Alice"}

        return {
            "success": True,
            "data": user_data,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": str(e)
        }

# Usage with type safety
response = fetch_user_data(123)

if response["success"]:
    # Type checker knows data is not None here
    user = response["data"]
    print(f"User: {user['name']}")
else:
    # Type checker knows error is not None here
    print(f"Error: {response['error']}")
```

**What this provides:**

- Clear response structure
- Type-safe access to fields
- IDE autocomplete for response fields
- Catches missing error handling

---

### Example 2: Generic Repository Pattern

This example demonstrates how **generics (`TypeVar`) and protocols** enable reusable yet type-safe abstractions.

The repository:

- Works with _any_ model type
- Enforces that each model has an `id`
- Prevents mixing incompatible types

Key ideas illustrated here:

- `Protocol` defines a **structural requirement** (`id: int`) instead of inheritance
- `TypeVar` binds the repository instance to a **specific model type**
- Each repository instance is strongly typed:

  - A `Repository[User]` only accepts `User`
  - A `Repository[Product]` only accepts `Product`

As a result:

- You write the repository logic once
- You get full type safety per usage
- IDEs know exactly what type is returned from `get`, `save`, and `get_all`

This pattern is widely used in ORMs, data layers, and service abstractions.

```python
from typing import Generic, TypeVar, Protocol, Optional

class Model(Protocol):
    """Base model protocol - any class with an id."""
    id: int

T = TypeVar('T', bound=Model)

class Repository(Generic[T]):
    """Generic repository for database operations."""

    def __init__(self, model_class: type[T]) -> None:
        self.model_class = model_class
        self._storage: dict[int, T] = {}

    def save(self, item: T) -> T:
        """Save item to repository."""
        self._storage[item.id] = item
        return item

    def get(self, id: int) -> Optional[T]:
        """Get item by ID."""
        return self._storage.get(id)

    def get_all(self) -> list[T]:
        """Get all items."""
        return list(self._storage.values())

    def delete(self, id: int) -> bool:
        """Delete item by ID."""
        if id in self._storage:
            del self._storage[id]
            return True
        return False

# Usage with specific types
class User:
    def __init__(self, id: int, name: str) -> None:
        self.id = id
        self.name = name

class Product:
    def __init__(self, id: int, title: str, price: float) -> None:
        self.id = id
        self.title = title
        self.price = price

# Type-safe repositories
user_repo: Repository[User] = Repository(User)
product_repo: Repository[Product] = Repository(Product)

# Type-safe operations
user = User(1, "Alice")
user_repo.save(user)

retrieved = user_repo.get(1)  # Type: Optional[User]

# Type error - caught by mypy!
user_repo.save(Product(1, "Widget", 9.99))  # Error!
```

**Benefits:**

- One implementation for all types
- Type safety for each repository instance
- Prevents mixing different model types
- IDE knows exact types for autocomplete

---

### Example 3: Type-Safe Configuration

This example shows how `TypedDict` and `Literal` work together to model **nested application configuration**.

Configuration data is usually:

- Nested
- Loaded dynamically
- Accessed in many places

Typing it provides major benefits:

- Every required configuration key is enforced
- Nested structures are validated
- String-based options (like environment names) are restricted using `Literal`
- IDEs can autocomplete deeply nested keys

The use of `Literal` ensures only known environments are allowed, preventing subtle bugs caused by typos or unsupported values.

This approach:

- Documents configuration structure clearly
- Makes refactoring safer
- Catches configuration mistakes before deployment

It is especially useful for large applications and microservices.

```python
from typing import TypedDict, Literal

class DatabaseConfig(TypedDict):
    host: str
    port: int
    username: str
    password: str
    database: str

class CacheConfig(TypedDict):
    host: str
    port: int
    ttl: int

class AppConfig(TypedDict):
    environment: Literal["development", "staging", "production"]
    debug: bool
    database: DatabaseConfig
    cache: CacheConfig

def load_config() -> AppConfig:
    """Load application configuration."""
    return {
        "environment": "production",
        "debug": False,
        "database": {
            "host": "localhost",
            "port": 5432,
            "username": "admin",
            "password": "secret",
            "database": "myapp"
        },
        "cache": {
            "host": "localhost",
            "port": 6379,
            "ttl": 3600
        }
    }

def initialize_app(config: AppConfig) -> None:
    """Initialize application with config."""
    # IDE provides autocomplete for all nested keys!
    db_host = config["database"]["host"]
    cache_ttl = config["cache"]["ttl"]

    print(f"Connecting to database at {db_host}")
    print(f"Cache TTL: {cache_ttl}s")
```

**Type errors caught:**

```python
# Error: Invalid literal value
bad_config: AppConfig = {
    "environment": "prod",  # Error: not "development", "staging", or "production"
    "debug": False,
    # Error: Missing required keys "database" and "cache"
}
```

---

### Example 4: Type-Safe Decorator

This example highlights how `ParamSpec` and `TypeVar` enable **fully type-safe decorators**.

Decorators often break type information because they wrap functions with different signatures.  
`ParamSpec` solves this by capturing:

- The exact parameter types of the wrapped function
- The exact return type

What this achieves:

- The decorated function keeps its original signature
- IDE autocomplete works as if no decorator exists
- Type checkers correctly validate arguments and return values

Without `ParamSpec`, decorators often degrade types to `Any`, losing safety.

This pattern is essential for:

- Logging decorators
- Timing decorators
- Authentication/authorization wrappers
- Retry and caching decorators

It allows powerful abstraction **without sacrificing type correctness**.

```python
from typing import TypeVar, Callable, ParamSpec, cast
import time

P = ParamSpec('P')  # Captures parameter specification
R = TypeVar('R')    # Captures return type

def timer(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that times function execution.

    Preserves the original function's type signature!
    """
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.3f}s")
        return result

    return cast(Callable[P, R], wrapper)

@timer
def add(a: int, b: int) -> int:
    """Add two integers."""
    time.sleep(1)
    return a + b

@timer
def greet(name: str) -> str:
    """Greet someone."""
    time.sleep(0.5)
    return f"Hello, {name}"

# Type hints are preserved through the decorator!
result1: int = add(5, 3)        # Type: int - correct!
result2: str = greet("Alice")   # Type: str - correct!

# Type errors caught!
result3: str = add(5, 3)        # Error: int is not str
```

**What ParamSpec provides:**

- Preserves function signature through decorator
- Maintains parameter types
- Maintains return type
- IDE autocomplete works correctly

---

## Best Practices

### DO

**1. Start with function signatures**

Begin by typing public functions and module boundaries. These form the contract of your code and provide the most value early.

```python
def process_data(items: list[str]) -> dict[str, int]:
    """Process items and return their lengths."""
    return {item: len(item) for item in items}
```

Typing function inputs and outputs:

- Clarifies expected usage
- Helps callers understand behavior
- Gives immediate IDE and type-checker benefits

---

**2. Prefer specific types over `Any`**

Using precise types allows the type checker to actually help you.

```python
# Too vague
def process(data: Any) -> Any:
    pass

# Clear and safe
def process(data: list[int]) -> dict[str, int]:
    pass
```

Specific types:

- Catch incorrect inputs early
- Improve readability
- Make refactoring safer

---

**3. Use `Optional` for nullable values**

Whenever a value can be missing, represent that explicitly.

```python
def find_user(id: int) -> Optional[User]:
    """Return User if found, otherwise None."""
    pass
```

This forces callers to handle the `None` case and avoids hidden runtime errors.

---

**4. Create type aliases for complex types**

Complex annotations quickly become unreadable when repeated inline.

```python
UserData: TypeAlias = dict[str, int | str | list[str]]

def process(data: UserData) -> None:
    pass
```

Type aliases:

- Improve readability
- Reduce duplication
- Make changes easier and safer

---

**5. Use `Protocol` for flexible interfaces**

When behavior matters more than inheritance, use structural typing.

```python
class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()
```

This allows unrelated classes to work together as long as they follow the same “shape”.

---

### DON’T

**1. Don’t use `Any` everywhere**

Overusing `Any` disables most of the benefits of typing.

```python
def process(data: Any) -> Any:
    pass
```

Use `Any` only when:

- Interfacing with untyped libraries
- Gradually migrating legacy code
- There is genuinely no better type

---

**2. Don’t ignore type errors without understanding them**

Suppressing errors hides real problems.

```python
result = some_function()  # type: ignore
```

Only ignore errors when:

- You fully understand why it’s safe
- You leave a comment explaining the reason

---

**3. Don’t write overly complex inline annotations**

Long nested types hurt readability.

```python
def process(
    data: dict[str, list[tuple[int, Optional[Union[str, int, float]]]]]
) -> list[dict[str, Union[int, str]]]:
    pass
```

Prefer aliases instead:

```python
ComplexData: TypeAlias = dict[str, list[tuple[int, Optional[str | int | float]]]]
Result: TypeAlias = list[dict[str, int | str]]

def process(data: ComplexData) -> Result:
    pass
```

---

**4. Don’t type everything at once**

Typing is most effective when done incrementally.

Recommended order:

- Public APIs
- Core logic
- Frequently used modules
- Remaining internal helpers

This keeps changes manageable and avoids slowing development.

---

**5. Don’t mix annotation styles**

Stick to one consistent typing style throughout the codebase.

```python
# Inconsistent
from typing import List
def func1(items: List[str]) -> None: pass
def func2(items: list[str]) -> None: pass
```

Prefer modern built-in generics consistently:

```python
def func1(items: list[str]) -> None: pass
def func2(items: list[str]) -> None: pass
```

Consistency improves readability and reduces cognitive load.

## Type Checking Workflow

A consistent type-checking workflow helps catch bugs early and keeps large codebases reliable as they grow.

---

### Recommended Development Flow

```
1. Write Code with Type Hints
   ↓
2. IDE Shows Inline Type Errors
   ↓
3. Fix Issues During Development
   ↓
4. Run mypy Before Committing
   ↓
5. CI/CD Runs mypy Automatically
   ↓
6. Deploy with Confidence
```

**Why this works:**

- Errors are caught as early as possible
- Developers get fast feedback while writing code
- CI ensures type safety is enforced consistently
- Reduces runtime bugs caused by incorrect assumptions

---

### Editor / IDE Integration

Modern editors provide real-time type checking using static analyzers like Pyright or mypy.

- **VS Code**

  - Pylance (built-in with Python extension)
  - Fast feedback and excellent autocomplete

- **PyCharm**

  - Built-in type checking enabled by default
  - Deep understanding of Python typing

- **Vim / Neovim**

  - ALE or coc.nvim with Pyright
  - Lightweight but powerful

- **Sublime Text**

  - LSP plugin with Pyright

IDE integration allows you to:

- See type errors as you type
- Navigate types easily
- Get accurate autocomplete and refactoring support

---

### Running mypy Locally

Before committing code, run type checks manually:

```bash
mypy src/
```

This ensures:

- Your changes don’t introduce new type errors
- The codebase remains type-safe
- CI failures are avoided later

---

### CI/CD Integration

Automate type checking so it runs on every push or pull request.

```yaml
# .github/workflows/type-check.yml
name: Type Check

on: [push, pull_request]

jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install mypy
      - run: mypy src/
```

**Benefits of CI type checking:**

- Enforces typing standards across the team
- Prevents untyped or incorrectly typed code from merging
- Keeps long-term code quality high
- Makes refactoring safer over time

---

### Key Takeaway

Type checking is most effective when it is:

- **Continuous** (IDE + CI)
- **Automated** (no manual policing)
- **Incremental** (adopted gradually, not all at once)

When integrated well, static typing becomes a safety net rather than a burden.

## Key Takeaways

1. **Type hints are optional and static**
   Type hints do not affect Python’s runtime behavior. They exist for tools like IDEs, linters, and type checkers to analyze code correctness before execution.

2. **Adopt typing incrementally**
   Start by typing public APIs and core logic. Add advanced typing features only when they provide clear value. Avoid over-engineering early.

3. **Prefer built-in collection types (Python 3.9+)**
   Use `list`, `dict`, `set`, and `tuple` directly instead of `List`, `Dict`, etc., for cleaner and more modern annotations.

4. **`Optional[T]` explicitly models missing values**
   `Optional[T]` is equivalent to `T | None`. It clearly communicates that a value may be absent and forces callers to handle that case.

5. **`Union[A, B]` (or `A | B`) expresses multiple valid types**
   Use unions when a value can legitimately be more than one type. Prefer the `|` syntax in Python 3.10+ for readability.

6. **`TypeVar` enables generic, reusable code**
   Generics allow functions and classes to work with multiple types while preserving type safety and avoiding duplication.

7. **`Protocol` enables typed duck typing**
   Structural subtyping lets you define interfaces based on behavior (methods/attributes), not inheritance, aligning with Python’s design philosophy.

8. **`TypedDict` brings structure to dictionaries**
   Use `TypedDict` when working with structured dicts (APIs, configs, JSON). It provides key-level type safety and better IDE support.

9. **Static type checking catches bugs early**
   Tools like `mypy` detect mismatches, missing cases, and incorrect assumptions before runtime. Integrate them into local development and CI/CD.

10. **Type aliases improve clarity and maintainability**
    Aliases make complex types readable, reduce repetition, and allow changes in one place without touching all annotations.

---

These concepts together help write Python code that is clearer, safer, easier to refactor, and more scalable over time—without sacrificing Python’s flexibility.

---

## Practice Exercises

**Exercise 1: Basic Annotations**  
Add type hints to a set of functions without annotations. Verify with mypy.

**Exercise 2: Generic Stack**  
Implement a generic Stack class that works with any type and maintains type safety.

**Exercise 3: Type-Safe API Client**  
Create a type-safe API client using TypedDict for request/response models.

**Exercise 4: Protocol Design**  
Define a Protocol for a cache interface and implement it with multiple backends.

**Exercise 5: mypy Integration**  
Set up mypy for a project, configure strict mode, and fix all type errors.

See: `exercises/python-fundamentals/type-hints/EXERCISES.md`

---

## Code Examples

- Notebooks: `notebooks/06-type-hints.ipynb`
- All runnable code: `code-examples/06_type_hints.py`

---

## Next Steps

**Tomorrow**: Week 1 Review and Consolidation

**Resources:**

- [mypy Documentation](https://mypy.readthedocs.io/)
- [Python typing Module](https://docs.python.org/3/library/typing.html)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [Type Hints Cheat Sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html)
- [Real Python - Type Checking](https://realpython.com/python-type-checking/)

# Python Fundamentals - Type Hints Exercises

**Topic**: Type Hints (Days 4-5)  
**Difficulty**: Beginner to Intermediate  
**Total Exercises**: 6

---

## Exercise 1: Basic Type Annotations

**Difficulty**: Easy  
**File**: `exercise_1.py`

Add type hints to existing functions.

**Requirements**:
- Annotate all parameters and return types
- Use correct collection types
- Make code pass mypy --strict

**Given Code**:
```python
def calculate_average(numbers):
    return sum(numbers) / len(numbers)

def find_user(users, user_id):
    for user in users:
        if user['id'] == user_id:
            return user
    return None

def merge_dicts(dict1, dict2):
    result = dict1.copy()
    result.update(dict2)
    return result
```

---

## Exercise 2: Generic Function

**Difficulty**: Medium  
**File**: `exercise_2.py`

Create a generic function that works with any type.

**Requirements**:
- Use TypeVar
- Works with lists of any type
- Preserves type information
- Passes mypy checks

**Example**:
```python
def get_first_and_last(items: ???) -> ???:
    return items[0], items[-1]

# Should work with:
get_first_and_last([1, 2, 3])  # Returns (int, int)
get_first_and_last(["a", "b"])  # Returns (str, str)
```

---

## Exercise 3: Protocol for Duck Typing

**Difficulty**: Medium  
**File**: `exercise_3.py`

Define a Protocol for objects that can be serialized.

**Requirements**:
- Create Serializable Protocol
- Implement classes that match protocol
- Create function that accepts protocol
- No inheritance needed

---

## Exercise 4: TypedDict for Configuration

**Difficulty**: Medium  
**File**: `exercise_4.py`

Use TypedDict for configuration dictionaries.

**Requirements**:
- Define typed configuration structure
- Include required and optional fields
- Validate with mypy
- Create helper functions with proper types

---

## Exercise 5: Callable Type Hints

**Difficulty**: Medium  
**File**: `exercise_5.py`

Add type hints for functions that accept callbacks.

**Requirements**:
- Use Callable type
- Specify parameter and return types
- Handle different callback signatures
- Type decorators properly

---

## Exercise 6: Complex Nested Types

**Difficulty**: Hard  
**File**: `exercise_6.py`

Type hint complex nested data structures.

**Requirements**:
- Handle nested lists, dicts, tuples
- Use Union and Optional appropriately
- Create type aliases for clarity
- Pass mypy strict mode

**Example**:
```python
# Type this correctly:
data = {
    "users": [
        {
            "id": 1,
            "name": "Alice",
            "scores": [10, 20, 30],
            "metadata": {"level": 5, "premium": True}
        }
    ]
}
```

---

## Testing

```bash
# Install mypy
pip install mypy

# Check your code
mypy exercise_1.py
mypy --strict exercise_1.py
```

---

## Resources

- [Python Typing Documentation](https://docs.python.org/3/library/typing.html)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Real Python - Type Checking](https://realpython.com/python-type-checking/)

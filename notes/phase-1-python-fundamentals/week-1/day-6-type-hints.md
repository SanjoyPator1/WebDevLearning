# Day 6: Type Hints

**Topic**: Python Type Hints and Static Type Checking
**Focus**: Type annotations, mypy, and type safety

## Key Concepts

### Basic Type Hints

```python
def greet(name: str) -> str:
    return f"Hello, {name}"

age: int = 30
names: list[str] = ["Alice", "Bob"]
scores: dict[str, int] = {"Alice": 100}
```

### Complex Types

```python
from typing import List, Dict, Optional, Union, Tuple

def process_data(
    items: List[str],
    config: Dict[str, int],
    optional_param: Optional[str] = None
) -> Tuple[bool, str]:
    return True, "Success"
```

### Type Checking with mypy

```bash
pip install mypy
mypy your_script.py
```

## Code Examples: `code-examples/06_type_hints.py`

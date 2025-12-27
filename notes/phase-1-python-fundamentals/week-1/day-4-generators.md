# Day 4: Generators and Iterators

**Date**: Week 1, Day 4  
**Phase**: 1 - Python Fundamentals  
**Topic**: Generators, Iterators, and Memory-Efficient Iteration

---

## Learning Objectives

- Understand generators and their benefits
- Create generator functions with `yield`
- Use generator expressions
- Understand the iterator protocol
- Apply generators for memory-efficient data processing

---

## What are Generators?

Generators are functions that return an iterator and generate values lazily (on-demand) instead of computing them all at once. They're memory-efficient for large datasets.

### Generator vs Regular Function

```python
# Regular function - computes all values
def regular_range(n):
    result = []
    for i in range(n):
        result.append(i)
    return result

# Generator - yields values one at a time
def generator_range(n):
    for i in range(n):
        yield i

# Regular: stores all 1,000,000 numbers in memory
nums = regular_range(1000000)  

# Generator: stores only current number
nums_gen = generator_range(1000000)
```

---

## Creating Generators with `yield`

```python
def countdown(n):
    """Generator that counts down from n"""
    while n > 0:
        yield n
        n -= 1

for num in countdown(5):
    print(num)  # 5, 4, 3, 2, 1
```

### How `yield` Works

- **Pauses execution** and returns a value
- **Resumes** where it left off on next iteration
- **Maintains state** between calls

```python
def simple_generator():
    print("First yield")
    yield 1
    print("Second yield")
    yield 2
    print("Third yield")
    yield 3

gen = simple_generator()
print(next(gen))  # Prints: First yield, returns 1
print(next(gen))  # Prints: Second yield, returns 2
print(next(gen))  # Prints: Third yield, returns 3
```

---

## Generator Expressions

Similar to list comprehensions but with parentheses:

```python
# List comprehension - creates entire list
squares_list = [x**2 for x in range(1000000)]

# Generator expression - creates values on demand
squares_gen = (x**2 for x in range(1000000))

# Memory efficient iteration
for square in squares_gen:
    if square > 100:
        break
```

---

## Practical Examples

### 1. Reading Large Files

```python
def read_large_file(filepath):
    """Memory-efficient file reading"""
    with open(filepath) as f:
        for line in f:
            yield line.strip()

# Process one line at a time, not entire file
for line in read_large_file('huge_file.txt'):
    process(line)
```

### 2. Infinite Sequences

```python
def fibonacci():
    """Infinite Fibonacci sequence"""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# Generate Fibonacci numbers on demand
fib = fibonacci()
for _ in range(10):
    print(next(fib))
```

### 3. Pipeline Processing

```python
def read_data(filename):
    """Read data from file"""
    with open(filename) as f:
        for line in f:
            yield line.strip()

def filter_comments(lines):
    """Filter out comment lines"""
    for line in lines:
        if not line.startswith('#'):
            yield line

def parse_numbers(lines):
    """Parse lines as numbers"""
    for line in lines:
        try:
            yield int(line)
        except ValueError:
            pass

# Chain generators for efficient processing
numbers = parse_numbers(filter_comments(read_data('data.txt')))
total = sum(numbers)
```

---

## The Iterator Protocol

Generators implement the iterator protocol automatically, but you can create custom iterators:

```python
class CountDown:
    def __init__(self, start):
        self.current = start
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1

# Use like a generator
for num in CountDown(5):
    print(num)  # 5, 4, 3, 2, 1
```

---

## `yield from` for Delegation

```python
def generator1():
    yield 1
    yield 2

def generator2():
    yield 3
    yield 4

def combined():
    yield from generator1()
    yield from generator2()

list(combined())  # [1, 2, 3, 4]
```

---

## Generator Methods

### send()

```python
def echo_generator():
    while True:
        value = yield
        print(f"Received: {value}")

gen = echo_generator()
next(gen)  # Prime the generator
gen.send("Hello")  # Received: Hello
gen.send("World")  # Received: World
```

### close()

```python
def counter():
    n = 0
    while True:
        yield n
        n += 1

gen = counter()
print(next(gen))  # 0
print(next(gen))  # 1
gen.close()  # Stop the generator
# print(next(gen))  # Raises StopIteration
```

---

## Performance Benefits

```python
import sys

# List - stores everything in memory
numbers_list = [x for x in range(1000000)]
print(f"List size: {sys.getsizeof(numbers_list)} bytes")

# Generator - minimal memory
numbers_gen = (x for x in range(1000000))
print(f"Generator size: {sys.getsizeof(numbers_gen)} bytes")
```

---

## Key Takeaways

1. **Generators** produce values lazily, saving memory
2. **`yield`** pauses execution and returns values
3. **Generator expressions** use `()` instead of `[]`
4. **Generators are iterators** - use with `for` loops or `next()`
5. **Perfect for** large datasets, streams, infinite sequences

---

## Practice Exercises

See: `exercises/python-fundamentals/generators/EXERCISES.md`

---

## Code Examples

All runnable code: `code-examples/04_generators.py`

---

## Tomorrow's Topic

**Day 5: Async/Await Basics** - Introduction to asynchronous programming.

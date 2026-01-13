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

Generators are special functions that **produce values one at a time** instead of computing and storing all values in memory at once.

They return an **iterator** and generate values **lazily**, meaning:

- A value is produced **only when requested**
- Memory usage stays low, even for large datasets

Generators are especially useful when working with:

- Large or infinite sequences
- Streams of data
- Files, logs, or real-time data

---

### How Generators Work

A generator function looks like a normal function, but instead of `return`, it uses the `yield` keyword.

```python
def generator_example():
    yield 1
    yield 2
    yield 3
```

- Calling the function **does not execute it immediately**
- It returns a generator object
- Each call to `next()` resumes execution until the next `yield`

---

### Generator vs Regular Function

#### Regular Function (Eager Evaluation)

A regular function computes **all values upfront** and stores them in memory.

```python
def regular_range(n):
    result = []
    for i in range(n):
        result.append(i)
    return result
```

- All values are stored in a list
- Memory usage grows with input size
- Not efficient for large datasets

---

#### Generator Function (Lazy Evaluation)

A generator yields values **one at a time** as they are needed.

```python
def generator_range(n):
    for i in range(n):
        yield i
```

- Values are generated on demand
- Only the current value exists in memory
- Suitable for large or infinite sequences

---

### Memory Usage Comparison

```python
# Regular function: stores all values in memory
nums = regular_range(1_000_000)

# Generator: stores only the current value
nums_gen = generator_range(1_000_000)
```

- The regular function holds **1,000,000 integers in memory**
- The generator holds **only one integer at a time**

This is why generators are more memory-efficient.

---

### Key Differences Summary

| Aspect                  | Regular Function | Generator     |
| ----------------------- | ---------------- | ------------- |
| Value creation          | All at once      | One at a time |
| Memory usage            | High             | Low           |
| Uses `return`           | Yes              | No            |
| Uses `yield`            | No               | Yes           |
| Suitable for large data | No               | Yes           |

---

### When to Use Generators

Use generators when:

- You don’t need all values at once
- You are working with large datasets
- You want better memory efficiency
- Data is produced sequentially

---

## Creating Generators with `yield`

Generators are created by using the `yield` keyword inside a function.
When a function contains `yield`, it becomes a **generator function**.

Unlike `return`, `yield`:

- Sends a value to the caller
- Pauses the function’s execution
- Remembers its state for the next call

---

### Example: Countdown Generator

```python
def countdown(n):
    """Generator that counts down from n"""
    while n > 0:
        yield n
        n -= 1
```

Using the generator:

```python
for num in countdown(5):
    print(num)
```

**Output**

```
5
4
3
2
1
```

**Explanation**

- The function starts executing when the loop requests a value
- Each `yield n` returns the current value of `n`
- Execution pauses after `yield`
- On the next iteration, execution resumes from `n -= 1`

---

### How `yield` Works Internally

The `yield` keyword performs three important actions:

1. **Pauses execution**
   The function stops running at the `yield` statement.

2. **Returns a value**
   The value next to `yield` is sent to the caller.

3. **Preserves state**
   Local variables and execution position are remembered.

---

### Step-by-Step Execution Example

```python
def simple_generator():
    print("First yield")
    yield 1
    print("Second yield")
    yield 2
    print("Third yield")
    yield 3
```

```python
gen = simple_generator()
```

At this point:

- No code has executed yet
- A generator object is created

---

```python
next(gen)
```

- Prints: `First yield`
- Returns: `1`
- Execution pauses at the first `yield`

---

```python
next(gen)
```

- Resumes after the first `yield`
- Prints: `Second yield`
- Returns: `2`

---

```python
next(gen)
```

- Resumes again
- Prints: `Third yield`
- Returns: `3`

After this:

- The generator is exhausted
- Further calls to `next()` will raise `StopIteration`

---

### Key Differences: `yield` vs `return`

| Aspect           | `yield`     | `return`    |
| ---------------- | ----------- | ----------- |
| Stops function   | Temporarily | Permanently |
| Returns value    | Yes         | Yes         |
| Remembers state  | Yes         | No          |
| Allows iteration | Yes         | No          |

---

### Key Takeaways

- A function with `yield` becomes a generator
- Execution pauses and resumes automatically
- State is preserved between calls
- Ideal for sequential and memory-efficient data generation

---

## Generator Expressions

Generator expressions provide a **concise way to create generators** using syntax similar to list comprehensions, but with **parentheses instead of square brackets**.

They generate values **lazily**, meaning values are produced only when needed.

---

### Generator Expression vs List Comprehension

#### List Comprehension (Eager Evaluation)

```python
squares_list = [x**2 for x in range(1_000_000)]
```

- Computes all values immediately
- Stores the entire list in memory
- Higher memory usage

---

#### Generator Expression (Lazy Evaluation)

```python
squares_gen = (x**2 for x in range(1_000_000))
```

- Does not compute values upfront
- Produces values only when iterated
- Uses significantly less memory

---

### Iterating Over a Generator Expression

```python
for square in squares_gen:
    if square > 100:
        break
```

**Explanation**

- Values are generated one at a time
- Iteration stops as soon as the condition is met
- Unused values are never computed

This makes generator expressions ideal for:

- Large datasets
- Early termination scenarios
- Memory-efficient pipelines

---

### When to Use Generator Expressions

Use generator expressions when:

- You need simple, one-line generators
- Data size is large
- You don’t need to store all values
- You want readable and concise code

---

### Key Differences Summary

| Feature                 | List Comprehension | Generator Expression |
| ----------------------- | ------------------ | -------------------- |
| Syntax                  | `[]`               | `()`                 |
| Evaluation              | Eager              | Lazy                 |
| Memory usage            | High               | Low                  |
| Reusable                | Yes                | No                   |
| Suitable for large data | No                 | Yes                  |

---

## Practical Examples of Generators

Generators are especially powerful in real-world scenarios where:

- Data is large
- Data is produced continuously
- Processing can be done step-by-step

The following examples demonstrate common and practical generator use cases.

---

### 1. Reading Large Files Efficiently

When working with large files, loading the entire file into memory can be inefficient or impossible.  
Generators allow reading and processing **one line at a time**.

```python
def read_large_file(filepath):
    """Memory-efficient file reading"""
    with open(filepath) as f:
        for line in f:
            yield line.strip()

```

Usage:

```python
for line in read_large_file('huge_file.txt'):
    process(line)

```

**Why this works well**

- Only one line is in memory at any time
- Suitable for very large files
- Processing begins immediately without waiting for the full file to load

---

### 2. Infinite Sequences

Generators can represent **infinite sequences**, producing values only when requested.

```python
def fibonacci():
    """Infinite Fibonacci sequence"""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

```

Usage:

```python
fib = fibonacci()
for _ in range(10):
    print(next(fib))

```

**Key idea**

- The generator never ends on its own
- Values are generated on demand
- The consumer controls when to stop

This pattern is useful for streams, simulations, and real-time data generation.

---

### 3. Pipeline Processing with Generators

Generators can be chained together to form **processing pipelines**, where each step transforms the data.

```python
def read_data(filename):
    """Read data from file"""
    with open(filename) as f:
        for line in f:
            yield line.strip()

```

```python
def filter_comments(lines):
    """Filter out comment lines"""
    for line in lines:
        if not line.startswith('#'):
            yield line

```

```python
def parse_numbers(lines):
    """Parse lines as numbers"""
    for line in lines:
        try:
            yield int(line)
        except ValueError:
            pass

```

Chaining the generators:

```python
numbers = parse_numbers(filter_comments(read_data('data.txt')))
total = sum(numbers)

```

**Why this is powerful**

- Each generator performs a single responsibility
- Data flows step-by-step through the pipeline
- No intermediate lists are created
- Memory usage remains minimal

---

### Key Takeaways

- Generators enable memory-efficient data processing
- They are ideal for large files and infinite data
- Generator pipelines improve readability and performance
- Data is processed only when needed

---

## The Iterator Protocol

An **iterator** is an object that produces values one at a time using the iterator protocol.

The iterator protocol requires two special methods:

- `__iter__()` → returns the iterator object
- `__next__()` → returns the next value or raises `StopIteration`

Generators automatically follow this protocol, but you can also implement it manually.

---

### Example: Custom Iterator (Countdown)

```python
class CountDown:
    def __init__(self, start):
        self.current = start
```

- Stores the starting value
- Maintains internal state (`self.current`)

---

```python
    def __iter__(self):
        return self
```

- Makes the object iterable
- Required so the object can be used in a `for` loop

---

```python
    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1
```

- Produces the next value in the sequence
- Raises `StopIteration` to signal the end of iteration

---

### Using the Custom Iterator

```python
for num in CountDown(5):
    print(num)
```

**Output**

```
5
4
3
2
1
```

**Key points**

- The loop repeatedly calls `__next__()`
- Iteration stops automatically when `StopIteration` is raised
- Behavior is similar to a generator, but implemented manually

---

### Generators vs Custom Iterators

| Feature        | Generator | Custom Iterator |
| -------------- | --------- | --------------- |
| Boilerplate    | Minimal   | More code       |
| State handling | Automatic | Manual          |
| Readability    | High      | Lower           |
| Flexibility    | Medium    | High            |

---

## `yield from` for Delegation

The `yield from` statement is used to **delegate part of a generator’s work to another generator**.

It simplifies code that would otherwise require nested loops.

---

### Without `yield from`

```python
def combined():
    for value in generator1():
        yield value
    for value in generator2():
        yield value
```

---

### With `yield from`

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
```

```python
list(combined())
```

**Output**

```
[1, 2, 3, 4]
```

---

### Why Use `yield from`

- Makes generator code cleaner and more readable
- Automatically forwards:

  - Values
  - Exceptions
  - `StopIteration`

- Ideal for composing generators

---

### Key Takeaways

- Iterators follow the `__iter__` / `__next__` protocol
- Generators are a simpler way to create iterators
- `yield from` delegates iteration to another generator
- Useful for building modular, readable pipelines

---

## Generator Methods

Generator objects provide special methods that allow **two-way communication** and **controlled termination**.
The most commonly used generator methods are `send()` and `close()`.

---

### `send()` — Sending Data into a Generator

The `send()` method allows a value to be **sent back into a generator**, making generators interactive.

```python
def echo_generator():
    while True:
        value = yield
        print(f"Received: {value}")
```

**How this generator works**

- `yield` pauses execution and waits for a value
- The value passed via `send()` becomes the result of the `yield` expression
- The generator can react to external input

---

#### Using `send()`

```python
gen = echo_generator()
next(gen)          # Prime the generator
gen.send("Hello")  # Received: Hello
gen.send("World")  # Received: World
```

**Important points**

- The generator must be **primed** using `next()` before calling `send()`
- Calling `send(value)` resumes execution and injects `value` into the generator
- This enables bidirectional data flow

---

### When to Use `send()`

- Coroutines
- Event-driven systems
- State machines
- Interactive data processing

---

### `close()` — Stopping a Generator

The `close()` method terminates a generator explicitly.

```python
def counter():
    n = 0
    while True:
        yield n
        n += 1
```

---

#### Using `close()`

```python
gen = counter()

print(next(gen))  # 0
print(next(gen))  # 1

gen.close()       # Stop the generator
```

After calling `close()`:

- The generator raises `StopIteration`
- No further values can be produced
- Any cleanup logic inside `finally` blocks (if present) will run

```python
# print(next(gen))  # Raises StopIteration
```

---

### Key Differences Between Generator Methods

| Method        | Purpose                             |
| ------------- | ----------------------------------- |
| `next()`      | Resume generator and get next value |
| `send(value)` | Resume generator and send a value   |
| `close()`     | Terminate generator execution       |

---

### Key Takeaways

- `send()` allows values to be passed **into** a generator
- Generators must be primed before using `send()`
- `close()` stops a generator immediately
- Generator methods enable advanced control flows beyond simple iteration

---

## Performance Benefits of Generators

One of the biggest advantages of generators is their **memory efficiency**.  
Unlike lists, generators do not store all values in memory at once.

---

### Memory Usage Comparison

```python
import sys

```

#### List (Eager Evaluation)

```python
numbers_list = [x for x in range(1_000_000)]
print(f"List size: {sys.getsizeof(numbers_list)} bytes")

```

- All one million values are created immediately
- Memory usage grows with the size of the dataset
- Not suitable for very large or unbounded sequences

---

#### Generator (Lazy Evaluation)

```python
numbers_gen = (x for x in range(1_000_000))
print(f"Generator size: {sys.getsizeof(numbers_gen)} bytes")

```

- Values are not stored upfront
- Only the generator object exists in memory
- Memory usage remains almost constant

---

### Why Generators Are More Efficient

- They generate values only when requested
- They avoid creating large intermediate data structures
- They allow early termination without extra computation

---

### Important Note

`sys.getsizeof()` shows the size of the container object:

- For lists, it measures the list structure (not including all referenced objects)
- For generators, it measures only the generator object itself

Even with this limitation, the memory difference clearly demonstrates the efficiency of generators.

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

- Notebooks: `notebooks/04-generators.ipynb`
- All runnable code: `code-examples/04_generators.py`


---

## Tomorrow's Topic

**Day 5: Async/Await Basics** - Introduction to asynchronous programming.

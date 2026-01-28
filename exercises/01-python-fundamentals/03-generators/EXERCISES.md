# Python Fundamentals - Generators Exercises

**Topic**: Generators and Iterators (Week 1, Day 4)  
**Difficulty**: Beginner to Intermediate  
**Total Exercises**: 8

---

## Instructions

- Solve each exercise in the corresponding Python file (exercise_1.py, exercise_2.py, etc.)
- Test your solutions by running the files
- Save completed solutions in the `solutions/` folder
- Review day-4-generators.md notes if you get stuck

---

## Exercise 1: Basic Generator Function

**Difficulty**: Easy  
**File**: `exercise_1.py`

Create a generator that yields numbers from 1 to n.

**Requirements**:
- Function name: `number_generator(n)`
- Yield numbers from 1 to n (inclusive)
- Use `yield` keyword
- Should work with `for` loop and `next()`

**Example Usage**:
```python
for num in number_generator(5):
    print(num)
# Output: 1, 2, 3, 4, 5

gen = number_generator(3)
print(next(gen))  # 1
print(next(gen))  # 2
print(next(gen))  # 3
# next(gen) would raise StopIteration
```

**Hints**:
- Use a loop to generate numbers
- Use `yield` instead of `return`
- Each `yield` pauses the function

---

## Exercise 2: Fibonacci Generator

**Difficulty**: Easy-Medium  
**File**: `exercise_2.py`

Create an infinite Fibonacci sequence generator.

**Requirements**:
- Function name: `fibonacci()`
- Generate Fibonacci numbers infinitely
- First two numbers are 0 and 1
- Each subsequent number is sum of previous two

**Example Usage**:
```python
fib = fibonacci()
for _ in range(10):
    print(next(fib))
# Output: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34

# Or with limit
def fibonacci_limited(n):
    # Your implementation
    pass

print(list(fibonacci_limited(8)))
# Output: [0, 1, 1, 2, 3, 5, 8, 13]
```

**Hints**:
- Use `while True:` for infinite generator
- Keep track of last two numbers
- Update both numbers in each iteration

---

## Exercise 3: File Reader Generator

**Difficulty**: Medium  
**File**: `exercise_3.py`

Create a generator that reads a file line by line.

**Requirements**:
- Function name: `read_file_lines(filename)`
- Yield one line at a time
- Strip whitespace from each line
- Skip empty lines
- Handle file not found errors

**Example Usage**:
```python
for line in read_file_lines('data.txt'):
    print(line)
# Prints each non-empty line

# Count lines
line_count = sum(1 for _ in read_file_lines('data.txt'))
print(f"Lines: {line_count}")
```

**Bonus**: Create `read_file_chunks(filename, chunk_size)` that yields chunks of text.

**Hints**:
- Use `with open()` to open file
- Use `line.strip()` to remove whitespace
- Check `if line:` to skip empty lines

---

## Exercise 4: Prime Number Generator

**Difficulty**: Medium  
**File**: `exercise_4.py`

Create a generator that yields prime numbers.

**Requirements**:
- Function name: `prime_numbers()`
- Generate prime numbers infinitely
- Start from 2 (first prime)
- Efficiently check for primality

**Example Usage**:
```python
primes = prime_numbers()
for _ in range(10):
    print(next(primes))
# Output: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29

# Get first n primes
def first_n_primes(n):
    # Your implementation
    pass

print(first_n_primes(5))
# Output: [2, 3, 5, 7, 11]
```

**Hints**:
- Start from 2
- Check if number is divisible by any number from 2 to sqrt(n)
- Use a helper function `is_prime(n)`

---

## Exercise 5: Data Pipeline Generator

**Difficulty**: Medium  
**File**: `exercise_5.py`

Create a pipeline of generators to process data.

**Requirements**:
- Create 3 generators that chain together:
  1. `read_numbers(filename)` - reads numbers from file
  2. `filter_even(numbers)` - filters even numbers
  3. `square_numbers(numbers)` - squares each number

**Example Usage**:
```python
# File contains: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
numbers = read_numbers('numbers.txt')
evens = filter_even(numbers)
squared = square_numbers(evens)

result = list(squared)
print(result)  # [4, 16, 36, 64, 100]

# Or chained:
result = list(
    square_numbers(
        filter_even(
            read_numbers('numbers.txt')
        )
    )
)
```

**Hints**:
- Each generator takes an iterable and yields processed items
- Use `yield` in each generator
- Generators are lazy - they don't process until consumed

---

## Exercise 6: Custom Range Generator

**Difficulty**: Medium  
**File**: `exercise_6.py`

Create your own version of Python's `range()` function.

**Requirements**:
- Function name: `custom_range(start, stop=None, step=1)`
- Support single argument: `custom_range(5)` → 0, 1, 2, 3, 4
- Support two arguments: `custom_range(2, 5)` → 2, 3, 4
- Support three arguments: `custom_range(0, 10, 2)` → 0, 2, 4, 6, 8
- Support negative steps
- Handle edge cases

**Example Usage**:
```python
print(list(custom_range(5)))
# [0, 1, 2, 3, 4]

print(list(custom_range(2, 8)))
# [2, 3, 4, 5, 6, 7]

print(list(custom_range(0, 10, 2)))
# [0, 2, 4, 6, 8]

print(list(custom_range(10, 0, -2)))
# [10, 8, 6, 4, 2]
```

**Hints**:
- Handle when `stop` is None (shift arguments)
- Use a while loop with appropriate condition
- Check if step is positive or negative

---

## Exercise 7: Batch Generator

**Difficulty**: Medium-Hard  
**File**: `exercise_7.py`

Create a generator that yields items in batches.

**Requirements**:
- Function name: `batch_generator(iterable, batch_size)`
- Yield lists of items, each of size `batch_size`
- Last batch may be smaller if items don't divide evenly
- Work with any iterable (list, generator, etc.)

**Example Usage**:
```python
numbers = range(10)
for batch in batch_generator(numbers, 3):
    print(batch)
# Output:
# [0, 1, 2]
# [3, 4, 5]
# [6, 7, 8]
# [9]

# Process large data in batches
for batch in batch_generator(range(1000), 100):
    process_batch(batch)  # Process 100 items at a time
```

**Hints**:
- Use a list to collect batch items
- Yield when batch is full
- Don't forget to yield remaining items

---

## Exercise 8: Iterator Class

**Difficulty**: Medium-Hard  
**File**: `exercise_8.py`

Create a custom iterator class (not a generator function).

**Requirements**:
- Class name: `CountDown`
- Initialize with a starting number
- Implement `__iter__` and `__next__` methods
- Count down to 0
- Raise `StopIteration` when done

**Example Usage**:
```python
countdown = CountDown(5)
for num in countdown:
    print(num)
# Output: 5, 4, 3, 2, 1

# Manual iteration
countdown = CountDown(3)
print(next(countdown))  # 3
print(next(countdown))  # 2
print(next(countdown))  # 1
# next(countdown) raises StopIteration
```

**Bonus**: Create an `InfiniteCounter` class that counts up infinitely.

**Hints**:
- `__iter__` should return `self`
- `__next__` should return the next value or raise `StopIteration`
- Use an instance variable to track current position

---

## Bonus Exercise 9: Recursive Generator

**Difficulty**: Hard  
**File**: `exercise_9.py` (Optional)

Create a generator that traverses a nested data structure recursively.

**Requirements**:
- Function name: `flatten(nested_list)`
- Flatten arbitrarily nested lists
- Yield individual items one by one
- Use recursion with `yield from`

**Example Usage**:
```python
nested = [1, [2, 3], [4, [5, 6]], 7]
flat = list(flatten(nested))
print(flat)
# Output: [1, 2, 3, 4, 5, 6, 7]

deeply_nested = [1, [2, [3, [4, [5]]]]]
print(list(flatten(deeply_nested)))
# Output: [1, 2, 3, 4, 5]
```

**Hints**:
- Check if item is a list
- If list, recursively yield from flattening it
- If not list, yield the item
- Use `yield from` for recursive case

---

## Generator Expressions

Practice these in your exercise files:

```python
# List comprehension (creates whole list)
squares = [x**2 for x in range(10)]

# Generator expression (lazy evaluation)
squares_gen = (x**2 for x in range(10))

# Memory efficient filtering
evens = (x for x in range(1000000) if x % 2 == 0)

# Use in sum, max, min
total = sum(x**2 for x in range(100))
maximum = max(x for x in range(100) if x % 3 == 0)
```

---

## Testing Your Solutions

```bash
# Run each exercise
python exercise_1.py
python exercise_2.py
# etc.

# Create test data file
echo -e "1\n2\n3\n4\n5\n6\n7\n8\n9\n10" > numbers.txt

# Test with large data
python -c "
from exercise_7 import batch_generator
for batch in batch_generator(range(100), 10):
    print(f'Batch size: {len(batch)}')
"
```

---

## Key Concepts

### Generator vs Regular Function
```python
# Regular function - returns all at once
def regular_range(n):
    result = []
    for i in range(n):
        result.append(i)
    return result

# Generator - yields one at a time
def generator_range(n):
    for i in range(n):
        yield i
```

### Memory Efficiency
```python
# Uses lots of memory
big_list = [x**2 for x in range(1000000)]

# Uses minimal memory
big_gen = (x**2 for x in range(1000000))
```

### Generator Methods
```python
gen = number_generator(5)

# Send value to generator
gen.send(value)

# Close generator
gen.close()

# Throw exception into generator
gen.throw(Exception)
```

---

## Common Patterns

### Pattern 1: Infinite Generator
```python
def infinite_sequence():
    num = 0
    while True:
        yield num
        num += 1
```

### Pattern 2: Generator Pipeline
```python
def step1(data):
    for item in data:
        yield process1(item)

def step2(data):
    for item in data:
        yield process2(item)

# Chain them
result = step2(step1(source_data))
```

### Pattern 3: Generator with State
```python
def stateful_generator():
    state = initial_state
    while condition:
        value = compute(state)
        yield value
        state = update(state)
```

---

## Real-World Use Cases

Generators are perfect for:
- **Large files**: Read line by line without loading entire file
- **Infinite sequences**: Generate values on demand
- **Data pipelines**: Process data in stages
- **Memory efficiency**: Work with large datasets
- **Lazy evaluation**: Compute only when needed

---

## Performance Comparison

```python
import sys

# List - stores everything
numbers_list = [x for x in range(1000000)]
print(f"List size: {sys.getsizeof(numbers_list)} bytes")

# Generator - minimal memory
numbers_gen = (x for x in range(1000000))
print(f"Generator size: {sys.getsizeof(numbers_gen)} bytes")
```

---

## Resources

- [Python Generators Documentation](https://docs.python.org/3/howto/functional.html#generators)
- [PEP 255 - Simple Generators](https://www.python.org/dev/peps/pep-0255/)
- [Iterator Protocol](https://docs.python.org/3/library/stdtypes.html#iterator-types)

---

**Good luck!** Generators are a powerful tool for writing memory-efficient, readable code. Master them and you'll write better Python!

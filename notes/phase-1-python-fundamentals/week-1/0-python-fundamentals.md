# Day 0: Python Fundamentals - The Complete Foundation

**Purpose**: Comprehensive Python basics before diving into advanced concepts  
**Duration**: Take your time - this is your foundation  
**Audience**: Developers with some programming experience learning Python

---

## Table of Contents

1. [Python Basics](#python-basics)
2. [Variables and Data Types](#variables-and-data-types)
3. [Operators](#operators)
4. [Control Flow](#control-flow)
5. [Functions](#functions)
6. [Data Structures](#data-structures)
7. [String Operations](#string-operations)
8. [File Operations](#file-operations)
9. [Error Handling](#error-handling)
10. [Modules and Imports](#modules-and-imports)
11. [List Comprehensions](#list-comprehensions)
12. [Classes and Objects (OOP)](#classes-and-objects)
13. [Common Built-in Functions](#common-built-in-functions)
14. [Python Style Guide](#python-style-guide)

---

## Python Basics

### What Makes Python Special?

- **Interpreted**: No compilation needed
- **Dynamically Typed**: No need to declare types
- **Indentation-based**: Uses whitespace for code blocks
- **Multi-paradigm**: Supports procedural, OOP, and functional programming
- **Extensive Standard Library**: "Batteries included"

### Running Python Code

```python
# Interactive Python Shell (REPL)
$ python
>>> print("Hello, World!")
Hello, World!

# Running a script
$ python script.py

# Python file: script.py
print("Hello, World!")
```

### Comments

```python
# Single line comment

"""
Multi-line comment
or docstring
"""

'''
Also a multi-line
comment
'''
```

---

## Variables and Data Types

### Variables

Python variables don't need type declaration:

```python
# Variable assignment
name = "Alice"
age = 30
height = 5.8
is_student = False

# Multiple assignment
x, y, z = 1, 2, 3
a = b = c = 0

# Swapping variables
a, b = 5, 10
a, b = b, a  # Now a=10, b=5

# Variable naming rules
valid_name = "OK"
_private = "OK"
name2 = "OK"
# 2name = "Error" - can't start with number
# my-name = "Error" - no hyphens
```

### Basic Data Types

#### Numbers

```python
# Integer
count = 42
big_num = 1_000_000  # Underscores for readability

# Float
price = 19.99
scientific = 2.5e-3  # 0.0025

# Complex numbers (rarely used)
complex_num = 3 + 4j

# Arithmetic
result = 10 + 5   # Addition: 15
result = 10 - 5   # Subtraction: 5
result = 10 * 5   # Multiplication: 50
result = 10 / 5   # Division: 2.0 (always float)
result = 10 // 3  # Floor division: 3
result = 10 % 3   # Modulo: 1
result = 2 ** 3   # Exponentiation: 8

# Type conversion
x = int("42")      # String to int
y = float("3.14")  # String to float
z = str(42)        # Int to string
```

#### Strings

```python
# String creation
name = "Alice"
message = 'Hello'
multiline = """This is
a multiline
string"""

# String indexing (0-based)
text = "Python"
print(text[0])   # 'P'
print(text[-1])  # 'n' (last character)

# String slicing
print(text[0:3])   # 'Pyt' (start:end, end not included)
print(text[:3])    # 'Pyt' (start from beginning)
print(text[3:])    # 'hon' (to the end)
print(text[-3:])   # 'hon' (last 3 characters)
print(text[::2])   # 'Pto' (every 2nd character)
print(text[::-1])  # 'nohtyP' (reverse)

# String concatenation
greeting = "Hello" + " " + "World"
repeated = "Ha" * 3  # "HaHaHa"

# String methods
text = "  Python Programming  "
print(text.lower())          # "  python programming  "
print(text.upper())          # "  PYTHON PROGRAMMING  "
print(text.strip())          # "Python Programming" (remove whitespace)
print(text.replace("P", "J"))  # "  Jython Jrogramming  "
print(text.split())          # ['Python', 'Programming']
print("hello".capitalize())  # "Hello"
print("hello world".title()) # "Hello World"

# String formatting
name = "Alice"
age = 30

# f-strings (Python 3.6+, recommended)
message = f"My name is {name} and I'm {age} years old"
print(message)

# format() method
message = "My name is {} and I'm {} years old".format(name, age)
message = "My name is {0} and I'm {1} years old".format(name, age)
message = "My name is {n} and I'm {a} years old".format(n=name, a=age)

# Old style (avoid)
message = "My name is %s and I'm %d years old" % (name, age)

# String checking
print("Hello".startswith("He"))   # True
print("Hello".endswith("lo"))     # True
print("Hello".isalpha())          # True
print("123".isdigit())            # True
print("hello" in "hello world")   # True
```

#### Booleans

```python
# Boolean values
is_valid = True
is_empty = False

# Boolean operations
print(True and False)  # False
print(True or False)   # True
print(not True)        # False

# Comparison returns boolean
print(5 > 3)   # True
print(5 == 5)  # True
print(5 != 3)  # True

# Truthy and Falsy values
# Falsy: False, None, 0, 0.0, "", [], {}, ()
# Everything else is Truthy

if []:
    print("Won't print")  # Empty list is falsy

if [1, 2, 3]:
    print("Will print")   # Non-empty list is truthy
```

#### None Type

```python
# None represents absence of value
result = None

if result is None:
    print("No value")

# Check for None
if result:  # Not recommended for None
    pass

if result is None:  # Recommended
    pass
```

### Type Checking

```python
x = 42
print(type(x))      # <class 'int'>

# Check type
if isinstance(x, int):
    print("x is an integer")

# Multiple types
if isinstance(x, (int, float)):
    print("x is a number")
```

---

## Operators

### Arithmetic Operators

```python
a, b = 10, 3

print(a + b)   # 13  Addition
print(a - b)   # 7   Subtraction
print(a * b)   # 30  Multiplication
print(a / b)   # 3.333... Division (float)
print(a // b)  # 3   Floor division
print(a % b)   # 1   Modulo (remainder)
print(a ** b)  # 1000 Exponentiation

# Compound assignment
x = 5
x += 3   # x = x + 3, now x is 8
x -= 2   # x = x - 2, now x is 6
x *= 2   # x = x * 2, now x is 12
x /= 4   # x = x / 4, now x is 3.0
```

### Comparison Operators

```python
a, b = 5, 10

print(a == b)  # False  Equal to
print(a != b)  # True   Not equal to
print(a < b)   # True   Less than
print(a > b)   # False  Greater than
print(a <= b)  # True   Less than or equal to
print(a >= b)  # False  Greater than or equal to

# Chaining comparisons
x = 15
print(10 < x < 20)  # True (x is between 10 and 20)
```

### Logical Operators

```python
# and, or, not
a, b = True, False

print(a and b)  # False
print(a or b)   # True
print(not a)    # False

# Short-circuit evaluation
def expensive_check():
    print("Checking...")
    return True

# Second function won't be called if first is False
if False and expensive_check():
    pass  # expensive_check() never runs

# Practical example
age = 25
has_license = True

if age >= 18 and has_license:
    print("Can drive")
```

### Identity and Membership Operators

```python
# Identity operators: is, is not
a = [1, 2, 3]
b = [1, 2, 3]
c = a

print(a == b)   # True (same content)
print(a is b)   # False (different objects)
print(a is c)   # True (same object)

# Use 'is' for None checks
result = None
if result is None:
    print("No result")

# Membership operators: in, not in
fruits = ["apple", "banana", "cherry"]
print("apple" in fruits)      # True
print("orange" not in fruits)  # True

text = "Hello World"
print("World" in text)  # True
```

---

## Control Flow

### If-Elif-Else Statements

```python
# Basic if
age = 18
if age >= 18:
    print("Adult")

# if-else
age = 15
if age >= 18:
    print("Adult")
else:
    print("Minor")

# if-elif-else
score = 85
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
elif score >= 60:
    grade = "D"
else:
    grade = "F"
print(f"Grade: {grade}")

# Inline if (ternary operator)
age = 20
status = "Adult" if age >= 18 else "Minor"
print(status)

# Nested if
x = 10
if x > 0:
    if x % 2 == 0:
        print("Positive even number")
    else:
        print("Positive odd number")
```

### Loops

#### For Loops

```python
# Iterate over a sequence
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)

# Iterate over range
for i in range(5):  # 0, 1, 2, 3, 4
    print(i)

for i in range(2, 8):  # 2, 3, 4, 5, 6, 7
    print(i)

for i in range(0, 10, 2):  # 0, 2, 4, 6, 8 (step of 2)
    print(i)

# Enumerate (get index and value)
fruits = ["apple", "banana", "cherry"]
for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")

# Start enumerate from different number
for index, fruit in enumerate(fruits, start=1):
    print(f"{index}: {fruit}")

# Iterate over string
for char in "Python":
    print(char)

# Iterate over dictionary
person = {"name": "Alice", "age": 30, "city": "NYC"}

# Keys only
for key in person:
    print(key)

# Keys and values
for key, value in person.items():
    print(f"{key}: {value}")

# Values only
for value in person.values():
    print(value)

# Nested loops
for i in range(3):
    for j in range(3):
        print(f"({i}, {j})")
```

#### While Loops

```python
# Basic while loop
count = 0
while count < 5:
    print(count)
    count += 1

# While with else (executes if loop completes normally)
count = 0
while count < 5:
    print(count)
    count += 1
else:
    print("Loop completed")

# Infinite loop (use with caution)
# while True:
#     user_input = input("Enter 'quit' to exit: ")
#     if user_input == 'quit':
#         break
```

#### Break, Continue, Pass

```python
# break - exit loop completely
for i in range(10):
    if i == 5:
        break
    print(i)  # Prints 0, 1, 2, 3, 4

# continue - skip rest of iteration
for i in range(10):
    if i % 2 == 0:
        continue  # Skip even numbers
    print(i)  # Prints 1, 3, 5, 7, 9

# pass - do nothing (placeholder)
for i in range(5):
    if i == 3:
        pass  # TODO: implement later
    print(i)

# Practical example: find first number divisible by 7
for num in range(50, 100):
    if num % 7 == 0:
        print(f"Found: {num}")
        break
else:
    print("Not found")  # Executes if break was never called
```

---

## Functions

### Basic Functions

```python
# Simple function
def greet():
    print("Hello!")

greet()  # Call the function

# Function with parameters
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")

# Function with return value
def add(a, b):
    return a + b

result = add(5, 3)
print(result)  # 8

# Multiple return values
def get_stats(numbers):
    return min(numbers), max(numbers), sum(numbers)

minimum, maximum, total = get_stats([1, 2, 3, 4, 5])
print(f"Min: {minimum}, Max: {maximum}, Total: {total}")

# Return multiple values as tuple
stats = get_stats([1, 2, 3, 4, 5])
print(stats)  # (1, 5, 15)
```

### Default Arguments

```python
def greet(name, greeting="Hello"):
    print(f"{greeting}, {name}!")

greet("Alice")              # Hello, Alice!
greet("Bob", "Hi")          # Hi, Bob!
greet("Charlie", greeting="Hey")  # Hey, Charlie!

# Default mutable arguments (GOTCHA!)
# DON'T DO THIS:
def add_item_bad(item, items=[]):  # Reuses same list!
    items.append(item)
    return items

# DO THIS INSTEAD:
def add_item_good(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items

list1 = add_item_good("apple")
list2 = add_item_good("banana")  # Creates new list
print(list1)  # ['apple']
print(list2)  # ['banana']
```

### Variable Arguments

```python
# *args - arbitrary number of positional arguments
def sum_all(*args):
    total = 0
    for num in args:
        total += num
    return total

print(sum_all(1, 2, 3))        # 6
print(sum_all(1, 2, 3, 4, 5))  # 15

# **kwargs - arbitrary keyword arguments
def print_info(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")

print_info(name="Alice", age=30, city="NYC")

# Combining all
def complex_function(required, *args, default="value", **kwargs):
    print(f"Required: {required}")
    print(f"Args: {args}")
    print(f"Default: {default}")
    print(f"Kwargs: {kwargs}")

complex_function(
    "must_have",
    1, 2, 3,
    default="custom",
    extra1="value1",
    extra2="value2"
)
```

### Lambda Functions

```python
# Lambda - anonymous function
square = lambda x: x ** 2
print(square(5))  # 25

add = lambda x, y: x + y
print(add(3, 4))  # 7

# Common use with map, filter, sorted
numbers = [1, 2, 3, 4, 5]

# map - apply function to all elements
squared = list(map(lambda x: x ** 2, numbers))
print(squared)  # [1, 4, 9, 16, 25]

# filter - keep elements matching condition
evens = list(filter(lambda x: x % 2 == 0, numbers))
print(evens)  # [2, 4]

# sorted with key
people = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 35}
]
sorted_people = sorted(people, key=lambda x: x["age"])
print(sorted_people)
```

### Docstrings

```python
def calculate_area(length, width):
    """
    Calculate the area of a rectangle.
    
    Args:
        length (float): Length of the rectangle
        width (float): Width of the rectangle
    
    Returns:
        float: Area of the rectangle
    
    Example:
        >>> calculate_area(5, 3)
        15.0
    """
    return length * width

# Access docstring
print(calculate_area.__doc__)
help(calculate_area)
```

---

## Data Structures

### Lists

Lists are ordered, mutable collections.

```python
# Creating lists
empty_list = []
fruits = ["apple", "banana", "cherry"]
mixed = [1, "hello", 3.14, True]
nested = [[1, 2], [3, 4], [5, 6]]

# Accessing elements
print(fruits[0])   # "apple" (first)
print(fruits[-1])  # "cherry" (last)
print(fruits[1:])  # ["banana", "cherry"] (slicing)

# Modifying lists
fruits[1] = "blueberry"  # Change element
print(fruits)  # ["apple", "blueberry", "cherry"]

# List methods
fruits = ["apple", "banana"]

# append - add to end
fruits.append("cherry")
print(fruits)  # ["apple", "banana", "cherry"]

# insert - add at position
fruits.insert(1, "blueberry")
print(fruits)  # ["apple", "blueberry", "banana", "cherry"]

# extend - add multiple elements
fruits.extend(["date", "elderberry"])
print(fruits)

# remove - remove first occurrence
fruits.remove("banana")
print(fruits)

# pop - remove and return element
last = fruits.pop()  # Remove last
print(last)
first = fruits.pop(0)  # Remove first
print(first)

# index - find position
position = fruits.index("cherry")
print(position)

# count - count occurrences
numbers = [1, 2, 2, 3, 2, 4]
print(numbers.count(2))  # 3

# sort - sort in place
numbers = [3, 1, 4, 1, 5]
numbers.sort()
print(numbers)  # [1, 1, 3, 4, 5]

numbers.sort(reverse=True)
print(numbers)  # [5, 4, 3, 1, 1]

# sorted - return new sorted list
numbers = [3, 1, 4, 1, 5]
sorted_numbers = sorted(numbers)
print(numbers)         # [3, 1, 4, 1, 5] (unchanged)
print(sorted_numbers)  # [1, 1, 3, 4, 5]

# reverse - reverse in place
numbers.reverse()
print(numbers)

# clear - remove all elements
numbers.clear()
print(numbers)  # []

# List operations
list1 = [1, 2, 3]
list2 = [4, 5, 6]

# Concatenation
combined = list1 + list2
print(combined)  # [1, 2, 3, 4, 5, 6]

# Repetition
repeated = [1, 2] * 3
print(repeated)  # [1, 2, 1, 2, 1, 2]

# Length
print(len(list1))  # 3

# Check membership
print(2 in list1)  # True
print(10 in list1)  # False

# Unpacking
a, b, c = [1, 2, 3]
print(a, b, c)  # 1 2 3

# Unpacking with *
first, *middle, last = [1, 2, 3, 4, 5]
print(first)   # 1
print(middle)  # [2, 3, 4]
print(last)    # 5
```

### Tuples

Tuples are ordered, immutable collections.

```python
# Creating tuples
empty_tuple = ()
single = (1,)  # Note the comma
numbers = (1, 2, 3)
mixed = (1, "hello", 3.14)

# Accessing elements
print(numbers[0])   # 1
print(numbers[-1])  # 3
print(numbers[1:])  # (2, 3)

# Tuples are immutable
# numbers[0] = 10  # Error!

# Tuple operations
tuple1 = (1, 2, 3)
tuple2 = (4, 5, 6)

# Concatenation
combined = tuple1 + tuple2
print(combined)  # (1, 2, 3, 4, 5, 6)

# Repetition
repeated = (1, 2) * 3
print(repeated)  # (1, 2, 1, 2, 1, 2)

# Unpacking
x, y, z = (1, 2, 3)
print(x, y, z)  # 1 2 3

# Tuple methods
numbers = (1, 2, 2, 3, 2, 4)
print(numbers.count(2))  # 3
print(numbers.index(3))  # 3

# When to use tuples
# 1. Data that shouldn't change
coordinates = (10.5, 20.3)

# 2. Dictionary keys (lists can't be keys)
locations = {
    (0, 0): "origin",
    (1, 0): "east",
    (0, 1): "north"
}

# 3. Multiple return values
def get_user():
    return ("Alice", 30, "alice@example.com")

name, age, email = get_user()
```

### Sets

Sets are unordered collections of unique elements.

```python
# Creating sets
empty_set = set()  # Note: {} creates empty dict
numbers = {1, 2, 3, 4, 5}
mixed = {1, "hello", 3.14}

# Sets remove duplicates
numbers = {1, 2, 2, 3, 3, 3}
print(numbers)  # {1, 2, 3}

# Convert list to set (remove duplicates)
numbers = [1, 2, 2, 3, 3, 3]
unique = set(numbers)
print(unique)  # {1, 2, 3}

# Set methods
numbers = {1, 2, 3}

# add - add element
numbers.add(4)
print(numbers)  # {1, 2, 3, 4}

# remove - remove element (error if not found)
numbers.remove(2)
print(numbers)  # {1, 3, 4}

# discard - remove element (no error if not found)
numbers.discard(10)  # No error

# pop - remove and return arbitrary element
element = numbers.pop()
print(element)

# clear - remove all
numbers.clear()
print(numbers)  # set()

# Set operations
set1 = {1, 2, 3, 4}
set2 = {3, 4, 5, 6}

# Union - all elements from both
print(set1 | set2)  # {1, 2, 3, 4, 5, 6}
print(set1.union(set2))

# Intersection - common elements
print(set1 & set2)  # {3, 4}
print(set1.intersection(set2))

# Difference - in first but not second
print(set1 - set2)  # {1, 2}
print(set1.difference(set2))

# Symmetric difference - in either but not both
print(set1 ^ set2)  # {1, 2, 5, 6}
print(set1.symmetric_difference(set2))

# Subset / Superset
set1 = {1, 2}
set2 = {1, 2, 3, 4}
print(set1.issubset(set2))     # True
print(set2.issuperset(set1))   # True

# Membership testing (very fast)
numbers = {1, 2, 3, 4, 5}
print(3 in numbers)  # True

# Use cases for sets
# 1. Remove duplicates
numbers = [1, 2, 2, 3, 3, 3]
unique = list(set(numbers))

# 2. Fast membership testing
valid_users = {"alice", "bob", "charlie"}
if "alice" in valid_users:
    print("Valid user")

# 3. Set operations
users_today = {"alice", "bob", "charlie"}
users_yesterday = {"bob", "charlie", "dave"}

# New users
new_users = users_today - users_yesterday
print(new_users)  # {'alice'}

# Users both days
both_days = users_today & users_yesterday
print(both_days)  # {'bob', 'charlie'}
```

### Dictionaries

Dictionaries are key-value pairs (hash maps).

```python
# Creating dictionaries
empty_dict = {}
person = {
    "name": "Alice",
    "age": 30,
    "city": "NYC"
}

# Also using dict()
person = dict(name="Alice", age=30, city="NYC")

# Accessing values
print(person["name"])  # "Alice"
print(person.get("age"))  # 30

# get() with default
print(person.get("country", "Unknown"))  # "Unknown"

# Adding/modifying
person["email"] = "alice@example.com"  # Add new key
person["age"] = 31  # Modify existing key

# Dictionary methods
person = {"name": "Alice", "age": 30}

# keys() - get all keys
print(person.keys())  # dict_keys(['name', 'age'])
print(list(person.keys()))  # ['name', 'age']

# values() - get all values
print(person.values())  # dict_values(['Alice', 30])

# items() - get key-value pairs
print(person.items())  # dict_items([('name', 'Alice'), ('age', 30)])

# update() - merge dictionaries
person.update({"city": "NYC", "country": "USA"})
print(person)

# pop() - remove and return value
age = person.pop("age")
print(age)  # 30
print(person)  # {'name': 'Alice', 'city': 'NYC', 'country': 'USA'}

# popitem() - remove and return last item
item = person.popitem()
print(item)  # ('country', 'USA')

# setdefault() - get value or set default
person = {"name": "Alice"}
age = person.setdefault("age", 30)
print(age)  # 30
print(person)  # {'name': 'Alice', 'age': 30}

# clear() - remove all items
person.clear()
print(person)  # {}

# Iterating over dictionary
person = {"name": "Alice", "age": 30, "city": "NYC"}

# Keys only
for key in person:
    print(key)

# Values only
for value in person.values():
    print(value)

# Keys and values
for key, value in person.items():
    print(f"{key}: {value}")

# Dictionary comprehension (covered later)
squares = {x: x**2 for x in range(5)}
print(squares)  # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

# Nested dictionaries
users = {
    "user1": {"name": "Alice", "age": 30},
    "user2": {"name": "Bob", "age": 25}
}
print(users["user1"]["name"])  # "Alice"

# Checking for keys
if "name" in person:
    print("Name exists")

# Use cases
# 1. Configuration
config = {
    "host": "localhost",
    "port": 8000,
    "debug": True
}

# 2. Counting
text = "hello world"
char_count = {}
for char in text:
    char_count[char] = char_count.get(char, 0) + 1
print(char_count)

# 3. Grouping
students = [
    {"name": "Alice", "grade": "A"},
    {"name": "Bob", "grade": "B"},
    {"name": "Charlie", "grade": "A"}
]
by_grade = {}
for student in students:
    grade = student["grade"]
    if grade not in by_grade:
        by_grade[grade] = []
    by_grade[grade].append(student["name"])
print(by_grade)  # {'A': ['Alice', 'Charlie'], 'B': ['Bob']}
```

---

## String Operations

### String Methods

```python
text = "Python Programming"

# Case conversion
print(text.lower())       # "python programming"
print(text.upper())       # "PYTHON PROGRAMMING"
print(text.capitalize())  # "Python programming"
print(text.title())       # "Python Programming"
print(text.swapcase())    # "pYTHON pROGRAMMING"

# Checking string content
print("hello".isalpha())      # True (all alphabetic)
print("hello123".isalnum())   # True (alphanumeric)
print("123".isdigit())        # True (all digits)
print("   ".isspace())        # True (all whitespace)
print("Hello".istitle())      # True (title case)
print("HELLO".isupper())      # True (all uppercase)
print("hello".islower())      # True (all lowercase)

# Searching
text = "Hello World"
print(text.find("World"))      # 6 (index of first occurrence)
print(text.find("Python"))     # -1 (not found)
print(text.index("World"))     # 6 (raises error if not found)
print(text.count("l"))         # 3 (count occurrences)
print(text.startswith("Hello"))  # True
print(text.endswith("World"))    # True

# Replacing
text = "Hello World"
print(text.replace("World", "Python"))  # "Hello Python"
print(text.replace("l", "L"))           # "HeLLo WorLd"
print(text.replace("l", "L", 2))        # "HeLLo World" (replace 2 times)

# Splitting and joining
text = "apple,banana,cherry"
fruits = text.split(",")
print(fruits)  # ['apple', 'banana', 'cherry']

text = "Hello World Python"
words = text.split()  # Split by whitespace
print(words)  # ['Hello', 'World', 'Python']

# Join
fruits = ["apple", "banana", "cherry"]
text = ", ".join(fruits)
print(text)  # "apple, banana, cherry"

words = ["Hello", "World"]
sentence = " ".join(words)
print(sentence)  # "Hello World"

# Stripping whitespace
text = "  Python  "
print(text.strip())   # "Python" (both sides)
print(text.lstrip())  # "Python  " (left side)
print(text.rstrip())  # "  Python" (right side)

# Strip specific characters
text = "***Python***"
print(text.strip("*"))  # "Python"

# Padding
text = "Python"
print(text.center(20))      # "       Python       "
print(text.center(20, "-")) # "-------Python-------"
print(text.ljust(20))       # "Python              "
print(text.rjust(20))       # "              Python"
print(text.zfill(10))       # "0000Python"

# Splitting lines
text = "Line 1\nLine 2\nLine 3"
lines = text.splitlines()
print(lines)  # ['Line 1', 'Line 2', 'Line 3']
```

### String Formatting

```python
name = "Alice"
age = 30
price = 19.99

# f-strings (Python 3.6+) - RECOMMENDED
message = f"My name is {name} and I'm {age} years old"
print(message)

# Expressions in f-strings
print(f"Next year I'll be {age + 1}")
print(f"5 * 3 = {5 * 3}")

# Format specifiers
print(f"Price: ${price:.2f}")  # 2 decimal places: $19.99
print(f"Price: ${price:.0f}")  # No decimals: $20

# Padding and alignment
print(f"{name:>10}")   # Right align: "     Alice"
print(f"{name:<10}")   # Left align: "Alice     "
print(f"{name:^10}")   # Center: "  Alice   "
print(f"{name:*^10}")  # Center with fill: "**Alice***"

# format() method
message = "My name is {} and I'm {} years old".format(name, age)
message = "My name is {0} and I'm {1} years old".format(name, age)
message = "My name is {n} and I'm {a} years old".format(n=name, a=age)

# Old % formatting (avoid)
message = "My name is %s and I'm %d years old" % (name, age)
```

---

## File Operations

### Reading Files

```python
# Method 1: Using with (recommended - auto closes file)
with open("file.txt", "r") as file:
    content = file.read()
    print(content)
# File automatically closed here

# Read line by line
with open("file.txt", "r") as file:
    for line in file:
        print(line.strip())  # strip() removes newline

# Read all lines into list
with open("file.txt", "r") as file:
    lines = file.readlines()
    for line in lines:
        print(line.strip())

# Read specific number of characters
with open("file.txt", "r") as file:
    chunk = file.read(100)  # Read first 100 characters
    print(chunk)

# Method 2: Manual close (not recommended)
file = open("file.txt", "r")
content = file.read()
file.close()
```

### Writing Files

```python
# Write (overwrites existing content)
with open("output.txt", "w") as file:
    file.write("Hello, World!\n")
    file.write("Second line\n")

# Write multiple lines
lines = ["Line 1\n", "Line 2\n", "Line 3\n"]
with open("output.txt", "w") as file:
    file.writelines(lines)

# Append (adds to existing content)
with open("output.txt", "a") as file:
    file.write("Appended line\n")
```

### File Modes

```python
# "r"  - Read (default)
# "w"  - Write (overwrites)
# "a"  - Append
# "x"  - Exclusive create (fails if exists)
# "b"  - Binary mode
# "t"  - Text mode (default)
# "+"  - Read and write

# Examples
with open("file.txt", "r") as f:   # Read text
    pass

with open("file.txt", "w") as f:   # Write text
    pass

with open("file.bin", "rb") as f:  # Read binary
    pass

with open("file.txt", "r+") as f:  # Read and write
    pass
```

### File Operations

```python
import os

# Check if file exists
if os.path.exists("file.txt"):
    print("File exists")

# Get file size
size = os.path.getsize("file.txt")
print(f"File size: {size} bytes")

# Rename file
os.rename("old_name.txt", "new_name.txt")

# Delete file
if os.path.exists("file.txt"):
    os.remove("file.txt")

# Create directory
os.mkdir("new_folder")

# Create nested directories
os.makedirs("parent/child/grandchild")

# List directory contents
files = os.listdir(".")
for file in files:
    print(file)

# Get current directory
current_dir = os.getcwd()
print(current_dir)

# Change directory
os.chdir("/path/to/directory")

# Join paths (cross-platform)
path = os.path.join("folder", "subfolder", "file.txt")
print(path)
```

---

## Error Handling

### Try-Except Blocks

```python
# Basic try-except
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")

# Multiple exceptions
try:
    number = int(input("Enter a number: "))
    result = 10 / number
except ValueError:
    print("Invalid input!")
except ZeroDivisionError:
    print("Cannot divide by zero!")

# Catch multiple exceptions together
try:
    # Some code
    pass
except (ValueError, TypeError):
    print("Value or Type error!")

# Catch any exception
try:
    # Some code
    pass
except Exception as e:
    print(f"An error occurred: {e}")

# else clause (executes if no exception)
try:
    number = int("42")
except ValueError:
    print("Invalid number")
else:
    print("Success!")  # Executes only if try succeeds

# finally clause (always executes)
try:
    file = open("file.txt", "r")
    content = file.read()
except FileNotFoundError:
    print("File not found")
finally:
    print("Cleanup code here")  # Always runs
```

### Common Exceptions

```python
# ValueError - Invalid value
try:
    int("abc")
except ValueError:
    print("Cannot convert to int")

# TypeError - Wrong type
try:
    "hello" + 5
except TypeError:
    print("Cannot add string and int")

# KeyError - Dictionary key doesn't exist
try:
    person = {"name": "Alice"}
    print(person["age"])
except KeyError:
    print("Key doesn't exist")

# IndexError - Index out of range
try:
    numbers = [1, 2, 3]
    print(numbers[10])
except IndexError:
    print("Index out of range")

# FileNotFoundError - File doesn't exist
try:
    with open("nonexistent.txt") as f:
        pass
except FileNotFoundError:
    print("File not found")

# AttributeError - Attribute doesn't exist
try:
    numbers = [1, 2, 3]
    numbers.push(4)  # lists don't have push
except AttributeError:
    print("Attribute doesn't exist")
```

### Raising Exceptions

```python
# Raise exception
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

try:
    result = divide(10, 0)
except ValueError as e:
    print(e)

# Re-raise exception
try:
    # Some code
    raise ValueError("Error!")
except ValueError:
    print("Handling error")
    raise  # Re-raise the same exception

# Custom exceptions
class InvalidAgeError(Exception):
    pass

def set_age(age):
    if age < 0 or age > 150:
        raise InvalidAgeError("Age must be between 0 and 150")
    return age

try:
    set_age(200)
except InvalidAgeError as e:
    print(e)
```

---

## Modules and Imports

### Importing Modules

```python
# Import entire module
import math
print(math.pi)
print(math.sqrt(16))

# Import specific items
from math import pi, sqrt
print(pi)
print(sqrt(16))

# Import with alias
import math as m
print(m.pi)

from math import sqrt as square_root
print(square_root(16))

# Import all (not recommended)
from math import *
print(pi)
print(sqrt(16))

# Common standard library modules
import os        # Operating system interface
import sys       # System-specific parameters
import datetime  # Date and time
import random    # Random number generation
import json      # JSON encoding/decoding
import re        # Regular expressions
import collections  # Specialized container datatypes
```

### Creating Modules

```python
# File: mymodule.py
def greet(name):
    return f"Hello, {name}!"

def add(a, b):
    return a + b

PI = 3.14159

# File: main.py
import mymodule

print(mymodule.greet("Alice"))
print(mymodule.add(5, 3))
print(mymodule.PI)

# Or
from mymodule import greet, add
print(greet("Bob"))
print(add(2, 3))
```

### Useful Standard Library Modules

```python
# datetime
from datetime import datetime, timedelta

now = datetime.now()
print(now)
print(now.strftime("%Y-%m-%d %H:%M:%S"))

tomorrow = now + timedelta(days=1)
print(tomorrow)

# random
import random

print(random.randint(1, 10))  # Random integer
print(random.random())  # Random float 0-1
print(random.choice(["apple", "banana", "cherry"]))
numbers = [1, 2, 3, 4, 5]
random.shuffle(numbers)

# json
import json

# Python dict to JSON string
data = {"name": "Alice", "age": 30}
json_string = json.dumps(data)
print(json_string)

# JSON string to Python dict
json_string = '{"name": "Bob", "age": 25}'
data = json.loads(json_string)
print(data["name"])

# collections
from collections import Counter, defaultdict, namedtuple

# Counter - count elements
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
count = Counter(words)
print(count)  # Counter({'apple': 3, 'banana': 2, 'cherry': 1})
print(count.most_common(2))  # [('apple', 3), ('banana', 2)]

# defaultdict - dict with default values
word_dict = defaultdict(list)
word_dict["fruits"].append("apple")
print(word_dict)  # {'fruits': ['apple']}

# namedtuple - tuple with named fields
Point = namedtuple('Point', ['x', 'y'])
p = Point(10, 20)
print(p.x, p.y)  # 10 20
```

---

## List Comprehensions

### Basic List Comprehension

```python
# Traditional way
squares = []
for x in range(10):
    squares.append(x ** 2)

# List comprehension
squares = [x ** 2 for x in range(10)]
print(squares)  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# With condition
evens = [x for x in range(10) if x % 2 == 0]
print(evens)  # [0, 2, 4, 6, 8]

# Transform and filter
words = ["hello", "world", "python", "hi"]
long_words = [word.upper() for word in words if len(word) > 3]
print(long_words)  # ['HELLO', 'WORLD', 'PYTHON']
```

### Nested List Comprehension

```python
# Create matrix
matrix = [[i * j for j in range(3)] for i in range(3)]
print(matrix)  # [[0, 0, 0], [0, 1, 2], [0, 2, 4]]

# Flatten matrix
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flat = [num for row in matrix for num in row]
print(flat)  # [1, 2, 3, 4, 5, 6, 7, 8, 9]

# Multiple conditions
numbers = [x for x in range(50) if x % 2 == 0 if x % 5 == 0]
print(numbers)  # [0, 10, 20, 30, 40]
```

### Dictionary Comprehension

```python
# Basic
squares = {x: x ** 2 for x in range(5)}
print(squares)  # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

# From lists
keys = ["a", "b", "c"]
values = [1, 2, 3]
dictionary = {k: v for k, v in zip(keys, values)}
print(dictionary)  # {'a': 1, 'b': 2, 'c': 3}

# With condition
numbers = {x: x ** 2 for x in range(10) if x % 2 == 0}
print(numbers)  # {0: 0, 2: 4, 4: 16, 6: 36, 8: 64}

# Swap keys and values
original = {"a": 1, "b": 2, "c": 3}
swapped = {v: k for k, v in original.items()}
print(swapped)  # {1: 'a', 2: 'b', 3: 'c'}
```

### Set Comprehension

```python
# Basic
squares = {x ** 2 for x in range(10)}
print(squares)  # {0, 1, 4, 9, 16, 25, 36, 49, 64, 81}

# With condition
evens = {x for x in range(20) if x % 2 == 0}
print(evens)  # {0, 2, 4, 6, 8, 10, 12, 14, 16, 18}
```

---

## Classes and Objects

### Basic Class

```python
# Define a class
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def greet(self):
        return f"Hello, I'm {self.name}"
    
    def birthday(self):
        self.age += 1

# Create objects
person1 = Person("Alice", 30)
person2 = Person("Bob", 25)

# Access attributes
print(person1.name)  # Alice
print(person2.age)   # 25

# Call methods
print(person1.greet())  # Hello, I'm Alice
person1.birthday()
print(person1.age)  # 31
```

### Class Attributes vs Instance Attributes

```python
class Dog:
    # Class attribute (shared by all instances)
    species = "Canis familiaris"
    
    def __init__(self, name, age):
        # Instance attributes (unique to each instance)
        self.name = name
        self.age = age

dog1 = Dog("Buddy", 3)
dog2 = Dog("Max", 5)

print(dog1.species)  # Canis familiaris
print(dog2.species)  # Canis familiaris
print(dog1.name)     # Buddy
print(dog2.name)     # Max

# Modify class attribute
Dog.species = "Dog"
print(dog1.species)  # Dog (affects all instances)
```

### Methods

```python
class Calculator:
    def __init__(self, value=0):
        self.value = value
    
    # Instance method
    def add(self, x):
        self.value += x
        return self.value
    
    # Class method
    @classmethod
    def from_string(cls, string):
        value = int(string)
        return cls(value)
    
    # Static method (doesn't use class or instance)
    @staticmethod
    def is_positive(x):
        return x > 0

# Instance method
calc = Calculator(10)
calc.add(5)
print(calc.value)  # 15

# Class method
calc2 = Calculator.from_string("20")
print(calc2.value)  # 20

# Static method
print(Calculator.is_positive(5))  # True
print(Calculator.is_positive(-3))  # False
```

### Inheritance

```python
# Parent class
class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        return "Some sound"

# Child class
class Dog(Animal):
    def speak(self):
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

# Usage
dog = Dog("Buddy")
cat = Cat("Whiskers")

print(dog.name)    # Buddy (inherited)
print(dog.speak())  # Woof! (overridden)
print(cat.speak())  # Meow!

# Check inheritance
print(isinstance(dog, Dog))     # True
print(isinstance(dog, Animal))  # True
print(issubclass(Dog, Animal))  # True
```

### Special Methods (Magic Methods)

```python
class Book:
    def __init__(self, title, author, pages):
        self.title = title
        self.author = author
        self.pages = pages
    
    # String representation
    def __str__(self):
        return f"{self.title} by {self.author}"
    
    # Detailed representation
    def __repr__(self):
        return f"Book('{self.title}', '{self.author}', {self.pages})"
    
    # Length
    def __len__(self):
        return self.pages
    
    # Comparison
    def __eq__(self, other):
        return self.pages == other.pages
    
    def __lt__(self, other):
        return self.pages < other.pages

book1 = Book("Python Basics", "John Doe", 300)
book2 = Book("Advanced Python", "Jane Smith", 450)

print(str(book1))    # Python Basics by John Doe
print(repr(book1))   # Book('Python Basics', 'John Doe', 300)
print(len(book1))    # 300
print(book1 == book2)  # False
print(book1 < book2)   # True
```

---

## Common Built-in Functions

### Utility Functions

```python
# len() - length
print(len([1, 2, 3]))       # 3
print(len("hello"))         # 5
print(len({"a": 1, "b": 2}))  # 2

# type() - get type
print(type(42))        # <class 'int'>
print(type("hello"))   # <class 'str'>
print(type([1, 2]))    # <class 'list'>

# isinstance() - check type
print(isinstance(42, int))     # True
print(isinstance("hi", str))   # True
print(isinstance([1], list))   # True

# min(), max(), sum()
numbers = [1, 2, 3, 4, 5]
print(min(numbers))  # 1
print(max(numbers))  # 5
print(sum(numbers))  # 15

# abs() - absolute value
print(abs(-5))   # 5
print(abs(3.14))  # 3.14

# round() - round number
print(round(3.7))      # 4
print(round(3.14159, 2))  # 3.14

# pow() - power
print(pow(2, 3))    # 8
print(pow(2, 3, 5))  # 3 (2^3 % 5)
```

### Conversion Functions

```python
# int(), float(), str()
print(int("42"))       # 42
print(int(3.14))       # 3
print(float("3.14"))   # 3.14
print(str(42))         # "42"

# bool() - convert to boolean
print(bool(1))     # True
print(bool(0))     # False
print(bool(""))    # False
print(bool("hi"))  # True
print(bool([]))    # False
print(bool([1]))   # True

# list(), tuple(), set()
print(list("hello"))        # ['h', 'e', 'l', 'l', 'o']
print(tuple([1, 2, 3]))     # (1, 2, 3)
print(set([1, 2, 2, 3]))    # {1, 2, 3}

# dict() - create dictionary
print(dict(name="Alice", age=30))  # {'name': 'Alice', 'age': 30}
print(dict([("a", 1), ("b", 2)]))  # {'a': 1, 'b': 2}
```

### Iteration Functions

```python
# range() - sequence of numbers
print(list(range(5)))        # [0, 1, 2, 3, 4]
print(list(range(2, 8)))     # [2, 3, 4, 5, 6, 7]
print(list(range(0, 10, 2))) # [0, 2, 4, 6, 8]

# enumerate() - index and value
fruits = ["apple", "banana", "cherry"]
for index, fruit in enumerate(fruits):
    print(f"{index}: {fruit}")

for index, fruit in enumerate(fruits, start=1):
    print(f"{index}: {fruit}")

# zip() - combine iterables
names = ["Alice", "Bob", "Charlie"]
ages = [30, 25, 35]
for name, age in zip(names, ages):
    print(f"{name} is {age} years old")

# Create dictionary from zip
person_dict = dict(zip(names, ages))
print(person_dict)

# reversed() - reverse iterator
numbers = [1, 2, 3, 4, 5]
for num in reversed(numbers):
    print(num)  # 5, 4, 3, 2, 1

# sorted() - return sorted list
numbers = [3, 1, 4, 1, 5]
print(sorted(numbers))  # [1, 1, 3, 4, 5]
print(sorted(numbers, reverse=True))  # [5, 4, 3, 1, 1]

people = [{"name": "Bob", "age": 30}, {"name": "Alice", "age": 25}]
print(sorted(people, key=lambda x: x["age"]))
```

### Functional Programming

```python
# map() - apply function to all items
numbers = [1, 2, 3, 4, 5]
squared = list(map(lambda x: x ** 2, numbers))
print(squared)  # [1, 4, 9, 16, 25]

# Multiple iterables
a = [1, 2, 3]
b = [10, 20, 30]
result = list(map(lambda x, y: x + y, a, b))
print(result)  # [11, 22, 33]

# filter() - keep items matching condition
numbers = [1, 2, 3, 4, 5, 6]
evens = list(filter(lambda x: x % 2 == 0, numbers))
print(evens)  # [2, 4, 6]

# all() - True if all are True
print(all([True, True, True]))   # True
print(all([True, False, True]))  # False
print(all([]))  # True (empty is True)

numbers = [2, 4, 6, 8]
print(all(x % 2 == 0 for x in numbers))  # True

# any() - True if any is True
print(any([False, False, True]))  # True
print(any([False, False, False]))  # False
print(any([]))  # False (empty is False)

numbers = [1, 3, 5, 6]
print(any(x % 2 == 0 for x in numbers))  # True
```

### Input/Output

```python
# print()
print("Hello")
print("Hello", "World")
print("Hello", "World", sep=", ")  # Hello, World
print("Hello", end=" ")  # No newline
print("World")  # Hello World

# input()
name = input("Enter your name: ")
print(f"Hello, {name}")

age = int(input("Enter your age: "))  # Convert to int
print(f"You are {age} years old")
```

---

## Python Style Guide (PEP 8)

### Naming Conventions

```python
# Variables and functions: lowercase with underscores
my_variable = 10
def my_function():
    pass

# Constants: UPPERCASE with underscores
MAX_SIZE = 100
PI = 3.14159

# Classes: PascalCase
class MyClass:
    pass

# Private/internal: leading underscore
_internal_variable = 5
def _internal_function():
    pass

# Avoid single character names except in loops
# Good
for index in range(10):
    pass

# OK for short loops
for i in range(10):
    pass
```

### Code Layout

```python
# Indentation: 4 spaces (not tabs)
def my_function():
    if True:
        print("Hello")

# Maximum line length: 79 characters
# Break long lines
result = some_function(argument1, argument2,
                      argument3, argument4)

# Blank lines
# 2 blank lines before class and top-level function
class MyClass:
    pass


def my_function():
    pass


# 1 blank line between methods
class MyClass:
    def method1(self):
        pass
    
    def method2(self):
        pass
```

### Imports

```python
# Order: standard library, third-party, local
import os
import sys

import numpy
import pandas

import mymodule

# Each import on separate line
# Good
import os
import sys

# Bad
import os, sys

# From imports can be on same line if short
from math import pi, sqrt
```

### Whitespace

```python
# Spaces around operators
x = 5 + 3  # Good
x=5+3      # Bad

# No spaces around = in keyword arguments
def function(arg1, arg2=None):  # Good
    pass

def function(arg1, arg2 = None):  # Bad
    pass

# Spaces after commas
my_list = [1, 2, 3]  # Good
my_list = [1,2,3]    # Bad

# No trailing whitespace
```

### Comments

```python
# Comments should be complete sentences
# First word should be capitalized

# Inline comments separated by two spaces
x = 5  # This is an inline comment

# Block comments for complex sections
# This section handles the complex calculation
# using the Smith-Jones algorithm
result = complex_calculation()

# Docstrings for functions and classes
def my_function(arg1, arg2):
    """
    Brief description of function.
    
    Longer description if needed.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
    
    Returns:
        Description of return value
    """
    pass
```

---

## Quick Reference Examples

### Common Patterns

```python
# Swap variables
a, b = b, a

# Check multiple conditions
if x > 0 and x < 10:
    pass
# Better
if 0 < x < 10:
    pass

# Check if variable is one of many values
if x in (1, 2, 3, 4, 5):
    pass

# Default value for dict
value = my_dict.get(key, default_value)

# Merge dictionaries (Python 3.9+)
dict1 = {"a": 1, "b": 2}
dict2 = {"c": 3, "d": 4}
merged = dict1 | dict2

# Python 3.5-3.8
merged = {**dict1, **dict2}

# Remove duplicates from list
unique_list = list(set(my_list))

# Count occurrences
from collections import Counter
counts = Counter(my_list)

# Sort dictionary by value
sorted_dict = dict(sorted(my_dict.items(), key=lambda x: x[1]))

# Create list of squares
squares = [x**2 for x in range(10)]

# Filter list
evens = [x for x in numbers if x % 2 == 0]

# Flatten nested list
flat_list = [item for sublist in nested_list for item in sublist]

# Read file lines
with open("file.txt") as f:
    lines = f.read().splitlines()

# Try-except-else-finally
try:
    result = risky_operation()
except Exception as e:
    handle_error(e)
else:
    handle_success(result)
finally:
    cleanup()
```

---

## Practice Exercises

Now that you've learned the basics, try these exercises:

1. **FizzBuzz**: Print numbers 1-100, but print "Fizz" for multiples of 3, "Buzz" for multiples of 5, and "FizzBuzz" for multiples of both.

2. **Palindrome Checker**: Write a function that checks if a string is a palindrome.

3. **Word Counter**: Count word frequency in a text file.

4. **Temperature Converter**: Convert between Celsius and Fahrenheit.

5. **Todo List Manager**: Create a simple todo list with add, remove, and list functions.

6. **Grade Calculator**: Calculate average grade and letter grade from a list of scores.

7. **Simple Calculator**: Build a calculator that can add, subtract, multiply, and divide.

8. **Password Validator**: Check if a password meets certain criteria (length, special characters, etc.).

---

## Next Steps

After mastering these fundamentals, you're ready for:
- **Week 1**: Decorators, Context Managers, Generators
- **Week 2**: Async/Await, Type Hints, Pydantic

**Remember**: Programming is learned by doing. Practice these concepts by writing code!

---

**Happy Learning!** 🐍

# Day 0: Python Fundamentals - Exercises

**Topic**: Python Basics - Complete Foundation  
**Difficulty**: Beginner to Intermediate  
**Total Exercises**: 15 (Progressive difficulty)  
**Estimated Time**: 3-5 hours

---

## Instructions

- Solve each exercise in a separate Python file (exercise_1.py, exercise_2.py, etc.)
- Test your solutions by running the files
- Don't look at solutions immediately - try to solve yourself first!
- If stuck, review the relevant section in day-0-python-fundamentals.md
- These exercises cover ALL the concepts from Day 0

---

## Exercise 1: FizzBuzz

**Difficulty**: Easy  
**File**: `exercise_1.py`

Write a program that prints numbers from 1 to 100, but:
- For multiples of 3, print "Fizz" instead of the number
- For multiples of 5, print "Buzz" instead of the number
- For multiples of both 3 and 5, print "FizzBuzz"

**Expected Output (first 15 lines)**:
```
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

**Bonus**: Make it work for any range, not just 1-100

---

## Exercise 2: Palindrome Checker

**Difficulty**: Easy  
**File**: `exercise_2.py`

Create a function that checks if a string is a palindrome (reads the same forwards and backwards).

**Requirements**:
- Ignore case (e.g., "Racecar" should be True)
- Ignore spaces and punctuation (e.g., "A man a plan a canal Panama" should be True)
- Return True or False

**Test Cases**:
```python
is_palindrome("racecar")  # True
is_palindrome("hello")    # False
is_palindrome("A man a plan a canal Panama")  # True
is_palindrome("Was it a car or a cat I saw?")  # True
is_palindrome("Python")   # False
```

**Hints**:
- Convert to lowercase first
- Remove spaces and punctuation
- Compare string with its reverse

---

## Exercise 3: Word Frequency Counter

**Difficulty**: Easy-Medium  
**File**: `exercise_3.py`

Write a program that counts the frequency of each word in a text.

**Requirements**:
- Read text from a string (or file if you want bonus points)
- Count how many times each word appears
- Print results sorted by frequency (most common first)
- Case-insensitive (e.g., "The" and "the" are the same)

**Example Input**:
```
"The quick brown fox jumps over the lazy dog. The dog was sleeping."
```

**Expected Output**:
```
the: 3
dog: 2
quick: 1
brown: 1
fox: 1
jumps: 1
over: 1
lazy: 1
was: 1
sleeping: 1
```

**Hints**:
- Use a dictionary to store counts
- Use .lower() for case-insensitive counting
- Use .split() to split into words
- Consider removing punctuation

---

## Exercise 4: Temperature Converter

**Difficulty**: Easy  
**File**: `exercise_4.py`

Create a temperature converter that converts between Celsius and Fahrenheit.

**Requirements**:
- Function: `celsius_to_fahrenheit(celsius)` 
- Function: `fahrenheit_to_celsius(fahrenheit)`
- Function: `convert_temperature(value, from_unit, to_unit)`
- Support both 'C' and 'F' as units
- Round to 2 decimal places

**Formulas**:
- Celsius to Fahrenheit: (C × 9/5) + 32
- Fahrenheit to Celsius: (F - 32) × 5/9

**Test Cases**:
```python
celsius_to_fahrenheit(0)    # 32.0
celsius_to_fahrenheit(100)  # 212.0
fahrenheit_to_celsius(32)   # 0.0
fahrenheit_to_celsius(212)  # 100.0
convert_temperature(25, 'C', 'F')  # 77.0
convert_temperature(77, 'F', 'C')  # 25.0
```

---

## Exercise 5: List Operations

**Difficulty**: Easy-Medium  
**File**: `exercise_5.py`

Implement the following functions that work with lists:

**Requirements**:
1. `remove_duplicates(lst)` - Remove duplicates while preserving order
2. `find_common_elements(list1, list2)` - Find elements in both lists
3. `flatten_list(nested_list)` - Flatten a nested list
4. `chunk_list(lst, chunk_size)` - Split list into chunks

**Test Cases**:
```python
remove_duplicates([1, 2, 2, 3, 3, 3, 4])
# Returns: [1, 2, 3, 4]

find_common_elements([1, 2, 3, 4], [3, 4, 5, 6])
# Returns: [3, 4]

flatten_list([[1, 2], [3, 4], [5, 6]])
# Returns: [1, 2, 3, 4, 5, 6]

chunk_list([1, 2, 3, 4, 5, 6, 7], 3)
# Returns: [[1, 2, 3], [4, 5, 6], [7]]
```

---

## Exercise 6: Dictionary Operations

**Difficulty**: Medium  
**File**: `exercise_6.py`

Create functions that manipulate dictionaries:

**Requirements**:
1. `merge_dicts(*dicts)` - Merge multiple dictionaries (later values override)
2. `invert_dict(d)` - Swap keys and values
3. `filter_dict(d, keys)` - Keep only specified keys
4. `dict_to_list(d)` - Convert dict to list of (key, value) tuples sorted by key

**Test Cases**:
```python
merge_dicts({"a": 1, "b": 2}, {"b": 3, "c": 4})
# Returns: {"a": 1, "b": 3, "c": 4}

invert_dict({"a": 1, "b": 2, "c": 3})
# Returns: {1: "a", 2: "b", 3: "c"}

filter_dict({"a": 1, "b": 2, "c": 3}, ["a", "c"])
# Returns: {"a": 1, "c": 3}

dict_to_list({"b": 2, "a": 1, "c": 3})
# Returns: [("a", 1), ("b", 2), ("c", 3)]
```

---

## Exercise 7: String Manipulation

**Difficulty**: Medium  
**File**: `exercise_7.py`

Implement various string manipulation functions:

**Requirements**:
1. `reverse_words(sentence)` - Reverse order of words
2. `is_anagram(str1, str2)` - Check if two strings are anagrams
3. `title_case(sentence)` - Convert to title case (capitalize first letter of each word)
4. `compress_string(s)` - Compress repeated characters (e.g., "aaabb" → "a3b2")

**Test Cases**:
```python
reverse_words("Hello World Python")
# Returns: "Python World Hello"

is_anagram("listen", "silent")
# Returns: True

is_anagram("hello", "world")
# Returns: False

title_case("hello world from python")
# Returns: "Hello World From Python"

compress_string("aaabbcccc")
# Returns: "a3b2c4"

compress_string("abc")
# Returns: "abc" (no compression if not shorter)
```

---

## Exercise 8: Number Operations

**Difficulty**: Medium  
**File**: `exercise_8.py`

Create functions for number operations:

**Requirements**:
1. `is_prime(n)` - Check if number is prime
2. `get_primes(n)` - Return all prime numbers up to n
3. `fibonacci(n)` - Return first n Fibonacci numbers
4. `factorial(n)` - Calculate factorial (use both loop and recursion)
5. `gcd(a, b)` - Find greatest common divisor

**Test Cases**:
```python
is_prime(17)  # True
is_prime(18)  # False

get_primes(20)
# Returns: [2, 3, 5, 7, 11, 13, 17, 19]

fibonacci(8)
# Returns: [0, 1, 1, 2, 3, 5, 8, 13]

factorial(5)  # 120
factorial(0)  # 1

gcd(48, 18)  # 6
gcd(17, 13)  # 1
```

---

## Exercise 9: File Operations

**Difficulty**: Medium  
**File**: `exercise_9.py`

Create a log file analyzer:

**Requirements**:
1. Create a function that reads a log file
2. Count occurrences of different log levels (INFO, WARNING, ERROR)
3. Find the most common error message
4. Write summary to a new file

**Sample Log Format** (create sample_log.txt):
```
2024-01-01 10:00:00 INFO User logged in
2024-01-01 10:05:00 ERROR Database connection failed
2024-01-01 10:10:00 WARNING High memory usage
2024-01-01 10:15:00 ERROR Database connection failed
2024-01-01 10:20:00 INFO User logged out
```

**Functions to Implement**:
```python
def parse_log_file(filename):
    # Return dict with log level counts
    pass

def get_most_common_error(filename):
    # Return the most common error message
    pass

def write_summary(filename, output_filename):
    # Write analysis to output file
    pass
```

---

## Exercise 10: Contact Book (Class-based)

**Difficulty**: Medium  
**File**: `exercise_10.py`

Create a contact book using classes:

**Requirements**:
- `Contact` class with name, phone, email
- `ContactBook` class to manage contacts
- Methods: add_contact, remove_contact, find_contact, list_all
- Save/load contacts from JSON file

**Example Usage**:
```python
book = ContactBook()
book.add_contact("Alice", "123-456-7890", "alice@example.com")
book.add_contact("Bob", "098-765-4321", "bob@example.com")

contact = book.find_contact("Alice")
print(contact.phone)  # 123-456-7890

book.list_all()  # Print all contacts

book.save_to_file("contacts.json")
book.load_from_file("contacts.json")
```

**Hints**:
- Use the `json` module for saving/loading
- Handle cases where contact doesn't exist
- Make phone and email optional fields

---

## Exercise 11: Data Validator

**Difficulty**: Medium  
**File**: `exercise_11.py`

Create validators for common data types:

**Requirements**:
1. `is_valid_email(email)` - Validate email format
2. `is_valid_phone(phone)` - Validate phone number (US format)
3. `is_valid_url(url)` - Validate URL format
4. `is_valid_password(password)` - Check password strength

**Password Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*)

**Test Cases**:
```python
is_valid_email("user@example.com")  # True
is_valid_email("invalid.email")     # False

is_valid_phone("123-456-7890")  # True
is_valid_phone("1234567890")    # True
is_valid_phone("123-45-6789")   # False

is_valid_url("https://example.com")  # True
is_valid_url("not-a-url")            # False

is_valid_password("Pass123!")   # True
is_valid_password("weak")       # False
```

---

## Exercise 12: Shopping Cart

**Difficulty**: Medium-Hard  
**File**: `exercise_12.py`

Create a shopping cart system:

**Requirements**:
- `Item` class with name, price, quantity
- `ShoppingCart` class
- Methods: add_item, remove_item, update_quantity, get_total, apply_discount
- Handle tax calculation (provide tax rate)
- Generate receipt

**Example Usage**:
```python
cart = ShoppingCart(tax_rate=0.08)  # 8% tax

cart.add_item("Apple", 1.50, 5)
cart.add_item("Banana", 0.75, 10)
cart.add_item("Orange", 2.00, 3)

cart.update_quantity("Apple", 3)
cart.remove_item("Banana")

cart.apply_discount(10)  # 10% discount

print(cart.get_subtotal())
print(cart.get_tax())
print(cart.get_total())

cart.print_receipt()
```

**Expected Receipt Format**:
```
===== RECEIPT =====
Apple         x3    $4.50
Orange        x3    $6.00
-------------------
Subtotal:          $10.50
Discount (10%):    -$1.05
Tax (8%):          $0.76
-------------------
TOTAL:             $10.21
```

---

## Exercise 13: Text Analysis

**Difficulty**: Medium-Hard  
**File**: `exercise_13.py`

Create a comprehensive text analyzer:

**Requirements**:
1. Count total words, sentences, paragraphs
2. Calculate average word length
3. Find most common words (exclude common words like "the", "a", "is")
4. Calculate readability score (simplified)
5. Find longest and shortest sentences

**Functions to Implement**:
```python
def analyze_text(text):
    return {
        "word_count": ...,
        "sentence_count": ...,
        "paragraph_count": ...,
        "avg_word_length": ...,
        "most_common_words": [...],
        "longest_sentence": "...",
        "shortest_sentence": "..."
    }
```

**Test with this text**:
```
Python is a high-level programming language. It's known for its simplicity and readability.
Python is widely used in web development, data science, and automation. Many developers love Python.

Learning Python is fun and rewarding. The community is very supportive.
```

---

## Exercise 14: Data Structure Converter

**Difficulty**: Hard  
**File**: `exercise_14.py`

Create functions that convert between different data structures:

**Requirements**:
1. `csv_to_dict(csv_string)` - Parse CSV to list of dicts
2. `dict_to_csv(dict_list)` - Convert list of dicts to CSV string
3. `nested_dict_to_flat(nested)` - Flatten nested dict with dot notation
4. `flat_dict_to_nested(flat)` - Convert flat dict back to nested

**Test Cases**:
```python
csv_string = """name,age,city
Alice,30,NYC
Bob,25,LA
Charlie,35,Chicago"""

csv_to_dict(csv_string)
# Returns: [
#   {"name": "Alice", "age": "30", "city": "NYC"},
#   {"name": "Bob", "age": "25", "city": "LA"},
#   {"name": "Charlie", "age": "35", "city": "Chicago"}
# ]

nested = {
    "user": {
        "name": "Alice",
        "address": {
            "city": "NYC",
            "zip": "10001"
        }
    }
}

nested_dict_to_flat(nested)
# Returns: {
#   "user.name": "Alice",
#   "user.address.city": "NYC",
#   "user.address.zip": "10001"
# }
```

---

## Exercise 15: Mini Project - Todo List Manager

**Difficulty**: Hard  
**File**: `exercise_15.py`

Create a complete command-line todo list application:

**Requirements**:
1. Add tasks with priority (High, Medium, Low) and due date
2. Mark tasks as complete
3. List all tasks (filter by priority, completion status)
4. Edit task details
5. Delete tasks
6. Save/load from JSON file
7. Show statistics (total tasks, completed, overdue)

**Features to Implement**:
- Task class with id, title, description, priority, due_date, completed
- TodoManager class to manage all tasks
- Command-line interface

**Example Usage**:
```python
manager = TodoManager()

# Add tasks
manager.add_task(
    title="Buy groceries",
    description="Milk, bread, eggs",
    priority="High",
    due_date="2024-01-15"
)

# List tasks
manager.list_tasks(filter_by="priority", value="High")

# Mark complete
manager.complete_task(task_id=1)

# Statistics
stats = manager.get_statistics()
print(f"Total: {stats['total']}, Completed: {stats['completed']}")

# Save
manager.save_to_file("todos.json")
```

**Bonus Features**:
- Search tasks by keyword
- Sort tasks by due date or priority
- Archive completed tasks
- Undo last operation

---

## Testing Your Solutions

### Basic Testing
```bash
# Run each exercise
python exercise_1.py
python exercise_2.py
# etc.
```

### Create Test Cases
For each exercise, create a test file:
```python
# test_exercise_1.py
from exercise_1 import fizzbuzz

def test_fizzbuzz():
    # Your test cases
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(5) == "Buzz"
    assert fizzbuzz(15) == "FizzBuzz"
    print("All tests passed!")

test_fizzbuzz()
```

---

## Submission Checklist

Before moving to Week 1, ensure you can:
- [ ] Complete at least 10 out of 15 exercises
- [ ] Exercises 1-8 completed (fundamentals)
- [ ] At least 2 medium-hard exercises completed
- [ ] Code follows PEP 8 style guide
- [ ] Functions have docstrings
- [ ] Code handles edge cases and errors
- [ ] All code runs without errors

---

## Self-Assessment

After completing these exercises, you should be comfortable with:
- ✅ Variables, data types, operators
- ✅ Control flow (if/else, loops)
- ✅ Functions (including *args, **kwargs)
- ✅ Data structures (lists, dicts, sets, tuples)
- ✅ String operations
- ✅ File operations
- ✅ Error handling
- ✅ Classes and OOP basics
- ✅ List comprehensions
- ✅ Built-in functions

If you're struggling with any of these, review the corresponding section in `day-0-python-fundamentals.md` before moving to Week 1.

---

## Tips for Success

1. **Start Simple**: Begin with exercises 1-5, they're foundational
2. **Read Error Messages**: Python's error messages are helpful
3. **Test As You Go**: Don't write everything at once
4. **Use Print Statements**: Debug with strategic print statements
5. **Refactor**: First make it work, then make it better
6. **Don't Copy**: Type out the code yourself, muscle memory helps
7. **Experiment**: Modify examples and see what happens
8. **Ask Questions**: Use the Python REPL to test small snippets

---

## Bonus Challenges

If you finish all 15 exercises and want more:

1. **Combine exercises**: Create a text analysis tool that works on files (Ex 9 + 13)
2. **Add GUI**: Use tkinter to add a GUI to any exercise
3. **Web scraper**: Use `requests` and `BeautifulSoup` to scrape data
4. **API client**: Create a client for a public API (weather, news, etc.)
5. **Game**: Create a simple game (guess the number, hangman, etc.)

---

## Resources

- [Python Official Tutorial](https://docs.python.org/3/tutorial/)
- [Python Practice Problems](https://www.practicepython.org/)
- [LeetCode Easy Problems](https://leetcode.com/problemset/all/)
- [Real Python](https://realpython.com/)

---

**Good luck!** Remember: The goal is to practice, not to be perfect. Make mistakes, learn from them, and keep coding! 🐍

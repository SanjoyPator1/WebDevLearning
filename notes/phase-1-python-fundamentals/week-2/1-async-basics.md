# Day 5: Async/Await - Fundamentals

**Date**: Week 1, Day 5  
**Phase**: 1 - Python Fundamentals  
**Topic**: Asynchronous Programming with async/await

---

## Learning Objectives

- Understand what asynchronous programming is and when to use it
- Master the async/await syntax
- Understand the event loop and how it works
- Learn to run multiple tasks concurrently
- Use async context managers and iterators
- Avoid common async pitfalls
- Apply async patterns in real-world scenarios

---

## What is Asynchronous Programming?

Asynchronous programming allows your code to **start an operation, pause it while waiting, and continue doing other work**, all within a **single thread**. Instead of blocking the program until a task finishes, async lets the program **make progress elsewhere**.

The key idea is **non-blocking execution**:

- Start a task
- If it needs to wait (network, disk, DB), _yield control_
- Resume the task later when it's ready

This is typically managed by an **event loop**, which decides _what runs next_.

---

### Synchronous vs Asynchronous (Intuition)

**Synchronous (Blocking) (Traditional)**

```
Chef starts cooking Order 1
  ↓
Waits for Order 1 to finish (10 minutes)
  ↓
Starts cooking Order 2
  ↓
Waits for Order 2 to finish (10 minutes)

Total time: 20 minutes for 2 orders
```

- One task blocks everything else
- Simple but inefficient when waiting is involved
- CPU stays idle during waits

### Synchronous Code example

```python
#synchronous example - operations run one after another
def sync_task(name: str, delay: int) -> str:
    """Simulate a blocking operation"""
    print(f"[Sync] {name}: Starting (will take {delay}s)")
    time.sleep(delay)   # Blocks the entire program
    print(f"[Sync] {name}: Done")
    return f"{name} completed"

# Run synchronously
start = time.time()

result1 = sync_task("Task 1", 2)
result2 = sync_task("Task 2", 2)
result3 = sync_task("Task 3", 2)

elapsed = time.time() - start
print(f"\n⏱️ Total time (synchronously): {elapsed:.2f}s")
```

#### Explanation: Synchronous Tasks Running Sequentially

This example demonstrates **synchronous (blocking) execution**, where each task must **fully complete before the next one starts**.

---

#### What `sync_task` Does

```python
def sync_task(name: str, delay: int) -> str:

```

- Defines a **normal synchronous function**
- Executes immediately when called
- Blocks program execution until it finishes

```python
time.sleep(delay)

```

- This is a **blocking call**
- The entire program is paused during the sleep
- No other work can happen while waiting

---

#### How the Tasks Execute

```python
result1 = sync_task("Task 1", 2)
result2 = sync_task("Task 2", 2)
result3 = sync_task("Task 3", 2)

```

Execution flow:

1.  Task 1 starts
2.  Program waits 2 seconds
3.  Task 1 finishes
4.  Task 2 starts
5.  Program waits another 2 seconds
6.  Task 2 finishes
7.  Task 3 starts
8.  Program waits another 2 seconds
9.  Task 3 finishes

Each task **must wait** for the previous one to complete.

---

#### Total Execution Time

```python
elapsed = time.time() - start

```

- Each task takes **2 seconds**
- Total time = `2 + 2 + 2 = 6 seconds`

```
⏱️ Total time (synchronously): ~6.00s

```

---

#### Why This Is Slow for I/O-Bound Work

- The program spends most of its time **waiting**
- While waiting, the CPU sits idle
- No opportunity to overlap work

This approach is simple and predictable, but inefficient when tasks involve **network calls, file access, or delays**.

---

#### Key Characteristics of Synchronous Execution

- Tasks run **one after another**
- Each task **blocks** the program
- Total time = **sum of all task durations**
- Best suited for **small, fast, CPU-bound tasks**

This example clearly contrasts with the asynchronous version, where waiting time is shared instead of wasted.

**Asynchronous (Modern)**

```
Chef starts cooking Order 1
  ↓
While Order 1 is cooking, starts Order 2
  ↓
Both cook simultaneously
  ↓
Both finish around the same time

Total time: ~10 minutes for 2 orders
```

- Tasks **pause and resume**
- Waiting time is reused
- CPU stays productive

### Asynchronous Code example

```python
# Asynchronous example - operations run concurrently
async def async_task(name: str, delay: int) -> str:
    """Simulate a non-blocking operation"""
    print(f"[Async] {name}: starting (will take {delay}s)")
    await asyncio.sleep(delay)  # Non-blocking
    print(f"[Async] {name}: Done")
    return f"{name} completed"

async def run_async_tasks():
    """Run multiple tasks concurrently"""
    start = time.time()

    # Run all tasks concurrently
    results = await asyncio.gather(
        async_task("Task 1", 1),
        async_task("Task 2", 3),
        async_task("Task 3", 2)
    )

    elapsed = time.time() - start
    print(f"\n⏱️ Total time (asynchronous): {elapsed:.2f}s")
    return results

# Run the async function
await run_async_tasks()
```

#### Explanation: Asynchronous Tasks Running Concurrently

This example demonstrates **concurrency using `async` and `await`**.  
Although multiple tasks are started together, they **do not run in parallel**. Instead, they **share a single thread** and cooperate by yielding control whenever they are waiting.

---

#### What `async_task` Does

```python
async def async_task(name: str, delay: int) -> str:

```

- Declares an **asynchronous function**
- It does not execute immediately; it returns a **coroutine object**
- Execution starts only when the event loop schedules it

```python
await asyncio.sleep(delay)

```

- This is a **non-blocking sleep**
- The task **pauses itself** and gives control back to the event loop
- While waiting, **other async tasks can run**

This is the key difference from `time.sleep()`.

---

#### What `run_async_tasks` Does

```python
results = await asyncio.gather(...)

```

- `asyncio.gather`:

  - Schedules **all tasks at once**
  - Runs them **concurrently**
  - Waits until **all tasks finish**
  - Returns results in the same order they were passed

```python
start = time.time()
...
elapsed = time.time() - start

```

- Measures total execution time
- Shows that concurrent tasks complete **faster than sequential ones**

---

#### Different Completion Times

Changing delays makes the concurrency more visible.

```python
async def run_async_tasks():
    start = time.time()

    results = await asyncio.gather(
        async_task("Task 1", 1),
        async_task("Task 2", 3),
        async_task("Task 3", 2)
    )

    elapsed = time.time() - start
    print(f"\n⏱️ Total time (asynchronous): {elapsed:.2f}s")
    return results

await run_async_tasks()

```

---

#### What You’ll Observe Now

```
[Async] Task 1: starting (1s)
[Async] Task 2: starting (3s)
[Async] Task 3: starting (2s)

[Async] Task 1: Done
[Async] Task 3: Done
[Async] Task 2: Done

⏱️ Total time (asynchronous): ~3.00s

```

**Important observations:**

- Tasks finish in **order of their delays**, not start order
- Total time equals the **longest task**, not the sum
- Confirms **concurrency, not parallelism**

---

#### Key Takeaways

- `async` allows multiple tasks to **make progress together**
- `await` lets a task **pause without blocking**
- `asyncio.gather` runs coroutines concurrently
- Async is ideal for **I/O-bound work**
- Execution time = **max(delay)**, not sum of delays

This example is a **perfect demonstration of concurrency in action**.

---

#### What Is a Coroutine?

A **coroutine** is a special type of function that can **pause its execution**, give control back to the caller, and **resume later from the same point**.

In Python, coroutines are the fundamental building blocks of **asynchronous programming**.

---

#### How Coroutines Are Different from Normal Functions

A normal function:

- Runs from start to finish
- Cannot pause in the middle
- Blocks the program while executing

A coroutine:

- Can pause at specific points (`await`)
- Allows other coroutines to run while it is waiting
- Resumes execution exactly where it paused

---

#### Coroutines in Python

In Python, a function becomes a coroutine when it is defined using `async def`:

```python
async def fetch_data():
    await asyncio.sleep(1)
    return "data"
```

Calling this function **does not execute it immediately**:

```python
coro = fetch_data()
```

- `coro` is a **coroutine object**
- Execution starts only when the coroutine is **awaited** or scheduled by the event loop

---

#### What `await` Does Inside a Coroutine

When a coroutine encounters `await`:

- It **pauses execution**
- It tells the event loop: “I am waiting for something”
- Control is returned to the event loop
- Other coroutines can run during this time

Once the awaited operation completes, the coroutine **resumes from the same line**.

---

#### Why Coroutines Are Important

Coroutines allow:

- Efficient handling of many I/O-bound tasks
- Non-blocking execution
- High-performance networking and servers
- Writing concurrent code without threads

They make it possible to scale programs to handle **thousands of simultaneous operations** using a single thread.

---

#### Key Points to Remember

- Coroutines are defined using `async def`
- They can pause and resume execution
- `await` is the point where execution is suspended
- Coroutines are managed by the **event loop**
- They are the foundation of `asyncio` and async/await in Python

---

### Concurrency vs Parallelism

**Concurrency and Parallelism solve different problems.**  
They are often confused, but they answer **two different questions**:

- **Concurrency** → _How tasks are structured_
- **Parallelism** → _How tasks are executed_

**These are NOT the same thing!**

---

#### Concurrency (Async / Await)

**Definition:**  
Concurrency means **handling multiple tasks at the same time**, even if only **one task is actually running at any given moment**.

```
CONCURRENCY (Async/Await)
─────────────────────────
Single chef switching between tasks

Time ──────────────────────────────>
Chef: [Order1] [Order2] [Order1] [Order2]
      └───switch─┘ └─switch─┘

✓ One thing at a time
✓ Fast switching creates illusion of simultaneity
✓ Perfect for I/O-bound tasks (waiting)
```

**What's happening:**

- Only **one task executes at a time**
- Tasks **pause and resume**
- Switching happens when a task is **waiting** (I/O)

**Key idea:**

> Tasks _make progress together_, not run simultaneously.

**Why it works:**

- While one task waits (network, disk), another task runs
- No CPU time is wasted waiting

**Real-world analogy:**

- One chef cooking multiple dishes
- While one dish is baking, the chef chops vegetables for another

**Best for:**

- Network requests
- Database queries
- File I/O
- Web servers

---

#### Parallelism (Threads / Processes)

**Definition:**  
Parallelism means **multiple tasks running at the exact same time** using **multiple CPU cores**.

```
PARALLELISM (Threading/Multiprocessing)
────────────────────────────────────────
Multiple chefs working simultaneously

Time ──────────────────────────────>
Chef1: [Order1──────────────────]
Chef2: [Order2──────────────────]

✓ Multiple things truly at once
✓ Perfect for CPU-bound tasks (computation)
```

**What's happening:**

- Tasks execute **simultaneously**
- Each task gets its own CPU core
- No switching needed for speed

**Key idea:**

> Tasks run _at the same time_, not just make progress together.

**Real-world analogy:**

- Multiple chefs cooking different dishes simultaneously

**Best for:**

- Heavy computation
- Image/video processing
- Data analysis
- Machine learning workloads

---

#### Side-by-Side Comparison

| Aspect                 | Concurrency              | Parallelism                    |
| ---------------------- | ------------------------ | ------------------------------ |
| Core idea              | Task switching           | Simultaneous execution         |
| CPU cores              | Single core              | Multiple cores                 |
| Tasks run at same time | No                       | Yes                            |
| Ideal for              | I/O-bound work           | CPU-bound work                 |
| Python tools           | `asyncio`, `async/await` | `threading`, `multiprocessing` |

---

#### Critical Insight (Very Important)

- **Async ≠ Parallel**
- Async improves **efficiency**, not **raw speed**
- Parallelism improves **raw performance**

You can have:

- Concurrency without parallelism (async on one core)
- Parallelism without concurrency (multiple CPUs, one task each)
- Both together (advanced systems)

**One-Line Summary:**

- **Concurrency**: _Dealing with many things at once_
- **Parallelism**: _Doing many things at once_

This distinction is the foundation of understanding **why async exists and when to use it**.

---

### I/O-Bound vs CPU-Bound Tasks

Understanding this distinction is **critical** for knowing when to use async.

#### I/O-Bound Tasks (Use Async)

Tasks that spend most of their time **waiting** for external operations:

- **Network requests** (API calls, downloading files)
- **Database queries** (waiting for database response)
- **File operations** (reading/writing to disk)
- **User input** (waiting for user to type)

```python
# I/O-Bound Example
async def fetch_user_data(user_id):
    # Program waits here for network response
    response = await http_client.get(f"/users/{user_id}")
    return response.json()

# While waiting for response, event loop can do other work!
```

**What happens internally:**

1. Request is sent
2. Task pauses at `await`
3. Event loop runs other tasks
4. Task resumes when response arrives

**Why async works well here:**

- Waiting time is unavoidable
- Async reuses that waiting time efficiently
- No extra threads needed

---

#### CPU-Bound Tasks (Don't Use Async)

Tasks that spend most of their time **computing**:

- **Mathematical calculations**
- **Image/video processing**
- **Data encryption/decryption**
- **Machine learning inference**

```python
# CPU-Bound Example (async won't help here!)
async def calculate_prime(n):
    # CPU is constantly working, no waiting
    for i in range(2, n):
        if n % i == 0:
            return False
    return True

# Event loop is blocked during computation - async provides NO benefit!
```

**Why async doesn't help:**

- No waiting points
- Event loop cannot switch tasks
- Entire program stalls during computation

**Correct solution:**

- Use multiprocessing
- Use native extensions (NumPy, C/C++)
- Offload work to worker processes

---

### Why Async Is Not "Faster Code"

Async does **not**:

- Make CPU operations faster
- Use multiple cores automatically
- Replace threads or processes

Async **does**:

- Improve throughput
- Reduce idle time
- Scale I/O-heavy workloads efficiently

---

### When to Use Async: Decision Tree

```
                    Start
                      |
                      ↓
        Does task involve waiting?
        (network, database, files)
                    /   \
                  NO     YES
                  /       \
                 ↓         ↓
        Use normal      How many
        synchronous     operations?
          code            /    \
                       1-10   10+
                        /       \
                       ↓         ↓
                  Consider   Definitely
                    async    use async!
```

**Quick Rules:**

- Use async for: API calls, database queries, file I/O, web scraping
- Don't use async for: Math calculations, data processing, image manipulation
- Mixed workload? Use async for I/O parts, normal code for CPU parts

---

## The Event Loop

The **event loop** is the heart of async programming in Python. It manages and schedules all async operations.

### What is an Event Loop?

The event loop is a **task manager** that:

1. Keeps track of all pending tasks
2. Runs tasks one at a time
3. Switches to another task when one is waiting
4. Continues until all tasks are complete

Think of it as a supervisor managing workers. When one worker is waiting for materials (I/O), the supervisor assigns other work to keep productivity high.

```
Event Loop Visualization
─────────────────────────

    ┌─────────────────┐
    │   Event Loop    │
    │   (Manager)     │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │   Task Queue    │
    ├─────────────────┤
    │ Task A: wait... │
    │ Task B: running │ ← Currently executing
    │ Task C: wait... │
    │ Task D: ready   │
    └─────────────────┘
```

**When Task B hits 'await':**

- Event loop switches to Task D
- Task B goes to "waiting" state
- When Task B's I/O completes, it becomes "ready"
- Event loop resumes Task B when possible

---

### How the Event Loop Works (Step-by-Step)

Let's trace execution with a concrete example:

```python
import asyncio

async def task1():
    print("Task 1: Start")
    await asyncio.sleep(2)  # Simulate I/O
    print("Task 1: Done")

async def task2():
    print("Task 2: Start")
    await asyncio.sleep(1)  # Simulate I/O
    print("Task 2: Done")

async def main():
    await asyncio.gather(task1(), task2())

asyncio.run(main())
```

**Execution Timeline:**

```
Time (seconds)
─────────────────────────────────────>

0.0s  │ Event loop starts
      │ main() creates task1() and task2()
      │
0.0s  │ task1: "Task 1: Start" printed
      │ task1: hits await sleep(2) → goes to waiting
      │
0.0s  │ task2: "Task 2: Start" printed
      │ task2: hits await sleep(1) → goes to waiting
      │
      │ [Both tasks waiting, event loop is idle]
      │
1.0s  │ task2's sleep(1) completes
      │ task2: "Task 2: Done" printed
      │ task2 is finished
      │
      │ [task1 still waiting]
      │
2.0s  │ task1's sleep(2) completes
      │ task1: "Task 1: Done" printed
      │ task1 is finished
      │
      │ All tasks complete, event loop exits
```

**Output:**

```
Task 1: Start
Task 2: Start
Task 2: Done    ← After 1 second
Task 1: Done    ← After 2 seconds
```

**Key Insight:** Both tasks ran concurrently. Total time was 2 seconds (not 3).

---

### Running the Event Loop

Python provides `asyncio.run()` to start the event loop:

```python
import asyncio

async def hello():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

# Start the event loop
asyncio.run(hello())
```

**What `asyncio.run()` does:**

1. Creates a new event loop
2. Runs the coroutine until completion
3. Closes the event loop
4. Cleans up resources

**Important Rule:**

Only call `asyncio.run()` **once** at the top level of your program.

```python
# DON'T DO THIS - Wrong!
async def bad_example():
    asyncio.run(another_async_function())  # Error!

# DO THIS - Correct!
async def good_example():
    await another_async_function()  # Correct!
```

---

### Manual Event Loop Control (Advanced)

For more control, you can manage the loop manually:

```python
import asyncio

async def my_coroutine():
    print("Running")

# Get or create event loop
loop = asyncio.get_event_loop()

# Schedule and run coroutine
loop.run_until_complete(my_coroutine())

# Close loop when done
loop.close()
```

**When to use manual control:**

- Custom loop configurations
- Integration with other async libraries
- Advanced scheduling needs

**For most cases, use `asyncio.run()` - it's simpler and safer.**

---

## Basic Async/Await Syntax

The async/await syntax is how you write asynchronous code in Python.

### Defining Async Functions (Coroutines)

Use `async def` to define a coroutine:

```python
# Regular function
def regular_function():
    return "Hello"

# Async function (coroutine)
async def async_function():
    return "Hello"
```

**Key Difference:**

When you call these functions, they behave differently:

```python
# Regular function - executes immediately, returns result
result = regular_function()
print(result)  # "Hello"

# Async function - returns a coroutine object, doesn't execute yet
coro = async_function()
print(coro)  # <coroutine object async_function at 0x...>
```

**To execute a coroutine:**

```python
# Use await (inside another async function)
async def main():
    result = await async_function()
    print(result)  # "Hello"

# Or use asyncio.run() (at top level)
result = asyncio.run(async_function())
print(result)  # "Hello"
```

---

### The `await` Keyword

`await` does three things:

1. **Pauses** the current coroutine
2. **Waits** for the awaited operation to complete
3. **Returns** the result

**Example:**

```python
import asyncio

async def fetch_data():
    print("Fetching...")
    await asyncio.sleep(2)  # Pause here for 2 seconds
    print("Fetched!")
    return "data"

async def main():
    # Wait for fetch_data() to complete
    result = await fetch_data()
    print(f"Got: {result}")

asyncio.run(main())
```

**Output:**

```
Fetching...
[2 second pause]
Fetched!
Got: data
```

**What happened:**

1. `fetch_data()` starts executing
2. Hits `await asyncio.sleep(2)` - pauses for 2 seconds
3. Event loop waits (could run other tasks if available)
4. After 2 seconds, resumes execution
5. Returns "data"
6. `main()` receives the result

---

### What Can You `await`?

You can only `await` **awaitable** objects:

**Valid awaitable objects:**

```python
# Coroutine functions
await async_function()

# Coroutines from asyncio
await asyncio.sleep(1)

# Tasks
await asyncio.create_task(coro)

# Futures
await asyncio.gather(coro1, coro2)
```

**NOT awaitable (will cause SyntaxError):**

```python
await regular_function()  # SyntaxError - not a coroutine
await "hello"            # SyntaxError - not awaitable
await 42                 # SyntaxError - not awaitable
```

---

### Common Mistake: Forgetting `await`

This is a **silent bug** that's easy to make and hard to catch:

```python
import asyncio

async def get_data():
    await asyncio.sleep(1)
    return "data"

async def main():
    # WRONG - Forgot await!
    result = get_data()
    print(result)  # <coroutine object get_data at 0x...>

    # CORRECT - Using await
    result = await get_data()
    print(result)  # "data"

asyncio.run(main())
```

**Python Warning:**

If you forget `await`, Python will show:

```
RuntimeWarning: coroutine 'get_data' was never awaited
```

**Always watch for this warning!** It means you forgot to `await` a coroutine.

---

### Step-by-Step Execution Example

Let's trace a complete async program:

```python
import asyncio

async def step1():
    print("Step 1: Start")
    await asyncio.sleep(1)
    print("Step 1: Done")
    return "Result 1"

async def step2():
    print("Step 2: Start")
    await asyncio.sleep(1)
    print("Step 2: Done")
    return "Result 2"

async def main():
    print("Main: Start")
    result1 = await step1()
    result2 = await step2()
    print(f"Main: Got {result1} and {result2}")

asyncio.run(main())
```

**Execution Timeline:**

```
0.0s │ main() starts
     │ Print: "Main: Start"
     │ Call step1()
     │
0.0s │ step1() starts
     │ Print: "Step 1: Start"
     │ Hit await sleep(1) → pause
     │
1.0s │ step1() resumes
     │ Print: "Step 1: Done"
     │ Return "Result 1"
     │
1.0s │ main() resumes with result1
     │ Call step2()
     │
1.0s │ step2() starts
     │ Print: "Step 2: Start"
     │ Hit await sleep(1) → pause
     │
2.0s │ step2() resumes
     │ Print: "Step 2: Done"
     │ Return "Result 2"
     │
2.0s │ main() resumes with result2
     │ Print: "Main: Got Result 1 and Result 2"
```

**Output:**

```
Main: Start
Step 1: Start
Step 1: Done
Step 2: Start
Step 2: Done
Main: Got Result 1 and Result 2
```

**Total time: 2 seconds** (because steps ran sequentially)

Notice that we're not taking advantage of concurrency here yet. Both steps could run at the same time, but we're using `await` sequentially. We'll fix this next.

---

## Running Multiple Tasks Concurrently

The real power of async comes from running **multiple operations at the same time**.

### Sequential vs Concurrent Execution

#### Sequential (One After Another)

```python
import asyncio
import time

async def task(name, delay):
    print(f"{name}: Start")
    await asyncio.sleep(delay)
    print(f"{name}: Done")

async def sequential():
    start = time.time()

    await task("Task 1", 2)  # Wait for Task 1
    await task("Task 2", 2)  # Then wait for Task 2
    await task("Task 3", 2)  # Then wait for Task 3

    print(f"Total time: {time.time() - start:.1f}s")

asyncio.run(sequential())
```

**Output:**

```
Task 1: Start
Task 1: Done
Task 2: Start
Task 2: Done
Task 3: Start
Task 3: Done
Total time: 6.0s
```

**Problem:** Tasks run one after another. Total time = sum of all delays.

This is inefficient because we're not utilizing async's ability to handle multiple tasks concurrently.

---

#### Concurrent (All at Once)

```python
import asyncio
import time

async def task(name, delay):
    print(f"{name}: Start")
    await asyncio.sleep(delay)
    print(f"{name}: Done")
    return f"{name} result"

async def concurrent():
    start = time.time()

    # Run all tasks concurrently!
    results = await asyncio.gather(
        task("Task 1", 2),
        task("Task 2", 2),
        task("Task 3", 2)
    )

    print(f"Results: {results}")
    print(f"Total time: {time.time() - start:.1f}s")

asyncio.run(concurrent())
```

**Output:**

```
Task 1: Start
Task 2: Start
Task 3: Start
Task 1: Done
Task 2: Done
Task 3: Done
Results: ['Task 1 result', 'Task 2 result', 'Task 3 result']
Total time: 2.0s
```

**Success!** All tasks ran concurrently. Total time = longest delay (2s), not the sum (6s).

This is the power of async - we reduced execution time by 3x simply by running tasks concurrently.

---

### `asyncio.gather()` - Wait for All Tasks

`gather()` runs multiple coroutines concurrently and waits for all to complete.

**Basic usage:**

```python
import asyncio

async def fetch_user(user_id):
    await asyncio.sleep(1)  # Simulate API call
    return f"User {user_id}"

async def main():
    # Fetch 5 users concurrently
    users = await asyncio.gather(
        fetch_user(1),
        fetch_user(2),
        fetch_user(3),
        fetch_user(4),
        fetch_user(5)
    )

    print(users)
    # ['User 1', 'User 2', 'User 3', 'User 4', 'User 5']

asyncio.run(main())
```

**Key characteristics of `gather()`:**

- Returns results in the **same order** as input (not completion order)
- If any task fails by default, `gather()` raises the exception
- Total time ≈ longest task (not sum of all tasks)
- All tasks start immediately

**Important behavior:**

The order of results matches the order of input coroutines, **not** the order of completion:

```python
async def task(name, delay):
    await asyncio.sleep(delay)
    return f"{name} (took {delay}s)"

# Task 3 finishes first, but results maintain input order
results = await asyncio.gather(
    task("Task 1", 3),
    task("Task 2", 2),
    task("Task 3", 1)
)

print(results)
# ['Task 1 (took 3s)', 'Task 2 (took 2s)', 'Task 3 (took 1s)']
```

---

### Error Handling in `gather()`

By default, `gather()` stops on first error:

```python
import asyncio

async def task(n):
    if n == 2:
        raise ValueError("Task 2 failed!")
    await asyncio.sleep(1)
    return f"Task {n}"

async def main():
    try:
        results = await asyncio.gather(
            task(1),
            task(2),  # This will fail
            task(3)
        )
    except ValueError as e:
        print(f"Error: {e}")

asyncio.run(main())
```

**Output:**

```
Error: Task 2 failed!
```

**What happens:**

- Task 1 and 3 are started
- Task 2 raises an exception
- The exception propagates to the caller
- Results from Task 1 and 3 are lost

---

**Continuing Despite Errors** (return_exceptions=True):

```python
async def main():
    results = await asyncio.gather(
        task(1),
        task(2),  # This will fail
        task(3),
        return_exceptions=True  # Don't stop on errors
    )

    print(results)
    # ['Task 1', ValueError('Task 2 failed!'), 'Task 3']

asyncio.run(main())
```

**What happens:**

- All tasks run to completion
- Exceptions are returned as results instead of being raised
- You can check which tasks failed by inspecting results

**Processing results with exceptions:**

```python
for i, result in enumerate(results, 1):
    if isinstance(result, Exception):
        print(f"Task {i} failed: {result}")
    else:
        print(f"Task {i} succeeded: {result}")
```

---

### `asyncio.create_task()` - Fire and Forget

Sometimes you want to start a task but not wait for it immediately.

**Example:**

```python
import asyncio

async def background_work():
    print("Background: Starting")
    await asyncio.sleep(2)
    print("Background: Done")

async def main():
    # Start task but don't wait
    task = asyncio.create_task(background_work())

    print("Main: Doing other work")
    await asyncio.sleep(1)
    print("Main: Still working")

    # Now wait for background task
    await task
    print("Main: All done")

asyncio.run(main())
```

**Output:**

```
Background: Starting
Main: Doing other work
Main: Still working
Background: Done
Main: All done
```

**What happened:**

1. `create_task()` schedules `background_work()` to run
2. `main()` continues immediately (doesn't wait)
3. Both `main()` and `background_work()` run concurrently
4. At the end, `await task` waits for background work to complete

**Key Insight:** The background task runs **while** main() does other work.

**Important:** Always `await` tasks eventually, otherwise they may be cancelled when the program exits:

```python
# BAD - task might not complete
async def bad():
    task = asyncio.create_task(some_work())
    # Function ends, task might be cancelled!

# GOOD - ensure task completes
async def good():
    task = asyncio.create_task(some_work())
    # Do other work...
    await task  # Wait for completion
```

---

### `asyncio.wait()` - Advanced Control

For more control over task completion, use `wait()`:

```python
import asyncio

async def task(name, delay):
    await asyncio.sleep(delay)
    return f"{name} done"

async def main():
    tasks = [
        asyncio.create_task(task("A", 1)),
        asyncio.create_task(task("B", 2)),
        asyncio.create_task(task("C", 3))
    ]

    # Wait for FIRST task to complete
    done, pending = await asyncio.wait(
        tasks,
        return_when=asyncio.FIRST_COMPLETED
    )

    print(f"First completed: {done.pop().result()}")
    print(f"Still pending: {len(pending)} tasks")

    # Wait for rest
    await asyncio.wait(pending)

asyncio.run(main())
```

**Output:**

```
First completed: A done
Still pending: 2 tasks
```

**`return_when` options:**

- `FIRST_COMPLETED` - Return when any task completes
- `FIRST_EXCEPTION` - Return when any task raises exception
- `ALL_COMPLETED` - Return when all tasks complete (default)

**When to use `wait()` vs `gather()`:**

- Use `gather()` when you want all results in order
- Use `wait()` when you need fine-grained control over completion

---

### Performance Comparison

Let's measure the actual time savings:

```python
import asyncio
import time

async def api_call(n):
    """Simulate API call (1 second)"""
    await asyncio.sleep(1)
    return n * 2

async def sequential_approach():
    """Run 10 API calls sequentially"""
    start = time.time()
    results = []

    for i in range(10):
        result = await api_call(i)
        results.append(result)

    elapsed = time.time() - start
    print(f"Sequential: {elapsed:.1f}s")
    return results

async def concurrent_approach():
    """Run 10 API calls concurrently"""
    start = time.time()

    results = await asyncio.gather(*[
        api_call(i) for i in range(10)
    ])

    elapsed = time.time() - start
    print(f"Concurrent: {elapsed:.1f}s")
    return results

async def compare():
    await sequential_approach()
    await concurrent_approach()

asyncio.run(compare())
```

**Output:**

```
Sequential: 10.0s
Concurrent: 1.0s
```

**10x speedup** from using async concurrency!

This demonstrates why async is so powerful for I/O-bound operations - we can handle multiple operations in the time it takes to complete one.

---

## Async Context Managers

Async context managers handle resources that need async setup or cleanup.

### The `async with` Syntax

Just like regular `with`, but for async operations:

```python
import asyncio

class AsyncResource:
    async def __aenter__(self):
        print("Acquiring resource...")
        await asyncio.sleep(1)
        print("Resource acquired")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("Releasing resource...")
        await asyncio.sleep(1)
        print("Resource released")

async def main():
    async with AsyncResource() as resource:
        print("Using resource")
        await asyncio.sleep(0.5)

asyncio.run(main())
```

**Output:**

```
Acquiring resource...
Resource acquired
Using resource
Releasing resource...
Resource released
```

**How it works:**

1. `__aenter__()` is called when entering the context
2. The returned value is assigned to the variable after `as`
3. The indented block executes
4. `__aexit__()` is called when leaving the context (even on errors)

---

### Real Example: HTTP Session

```python
import aiohttp
import asyncio

async def fetch_data():
    # Async context manager for HTTP session
    async with aiohttp.ClientSession() as session:
        # Async context manager for HTTP response
        async with session.get('https://api.example.com/data') as response:
            data = await response.json()
            return data

# Session is automatically closed when exiting context
```

**What's happening:**

- `ClientSession()` creates a connection pool (async operation)
- `session.get()` makes the request (async operation)
- Both are automatically cleaned up when exiting their contexts
- Connection pooling is handled automatically
- Even if an error occurs, cleanup happens correctly

**Why this matters:**

Without async context managers, you'd need to manually manage cleanup:

```python
# Manual cleanup (error-prone)
session = await create_session()
try:
    response = await session.get(url)
    try:
        data = await response.json()
    finally:
        await response.close()
finally:
    await session.close()

# With async context managers (clean and safe)
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()
```

---

### Real Example: Database Connection

```python
import asyncpg
import asyncio

async def get_users():
    # Async context manager for database connection pool
    async with asyncpg.create_pool(
        'postgresql://user:pass@localhost/db'
    ) as pool:
        # Get connection from pool
        async with pool.acquire() as connection:
            # Execute query
            users = await connection.fetch('SELECT * FROM users')
            return users

# Connection automatically returned to pool
# Pool automatically closed
```

**Benefits:**

- Connections are properly managed
- Pool is automatically closed
- Works correctly even if exceptions occur
- No resource leaks

---

### Creating Custom Async Context Managers

**Method 1: Using the class protocol:**

```python
class DatabaseConnection:
    async def __aenter__(self):
        print("Opening database connection...")
        await asyncio.sleep(0.5)
        self.connection = "Connected"
        return self.connection

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("Closing database connection...")
        await asyncio.sleep(0.5)
        self.connection = None
```

**Method 2: Using `@asynccontextmanager` decorator (simpler):**

```python
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def database_connection():
    # Setup code
    print("Connecting to database...")
    await asyncio.sleep(1)
    connection = {"db": "connected"}

    try:
        yield connection  # Provide resource
    finally:
        # Cleanup code (always runs)
        print("Closing connection...")
        await asyncio.sleep(1)

async def main():
    async with database_connection() as db:
        print(f"Using {db}")

asyncio.run(main())
```

**Output:**

```
Connecting to database...
Using {'db': 'connected'}
Closing connection...
```

**Why use `@asynccontextmanager`:**

- Less boilerplate code
- Clearer separation of setup/cleanup
- Automatically handles exceptions
- More Pythonic

---

## Async Iterators

Async iterators let you iterate over data that arrives asynchronously.

### The `async for` Syntax

**Regular for loop** - synchronous iteration:

```python
for item in [1, 2, 3]:
    print(item)
```

**Async for loop** - asynchronous iteration:

```python
async for item in async_iterator:
    print(item)
```

**Example: Custom async iterator:**

```python
import asyncio

class AsyncCounter:
    def __init__(self, stop):
        self.current = 0
        self.stop = stop

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.current >= self.stop:
            raise StopAsyncIteration

        await asyncio.sleep(0.5)  # Simulate async operation
        self.current += 1
        return self.current

async def main():
    async for num in AsyncCounter(5):
        print(num)

asyncio.run(main())
```

**Output:**

```
1
2
3
4
5
```

Each number appears after a 0.5s delay.

**How it works:**

1. `__aiter__()` returns the iterator object
2. `__anext__()` is called for each iteration
3. It performs async operations (like waiting for data)
4. Returns the next value
5. Raises `StopAsyncIteration` when done

---

### Async Generators

Combining `async def` with `yield` creates an async generator (simpler than the class approach):

```python
import asyncio

async def fetch_pages(num_pages):
    """Async generator that fetches pages one at a time"""
    for page in range(1, num_pages + 1):
        # Simulate fetching a page
        await asyncio.sleep(1)
        yield f"Page {page} content"

async def main():
    async for page_content in fetch_pages(3):
        print(f"Processing: {page_content}")

asyncio.run(main())
```

**Output:**

```
Processing: Page 1 content
Processing: Page 2 content
Processing: Page 3 content
```

**Why use async generators:**

- Simpler syntax than async iterator classes
- Can `yield` values from within async operations
- Memory efficient (values produced on demand)
- Perfect for streaming data

---

### Real Example: Streaming API Data

```python
import asyncio
import aiohttp

async def stream_tweets(query, limit=10):
    """Stream tweets matching query"""
    async with aiohttp.ClientSession() as session:
        url = f"https://api.twitter.com/stream?q={query}"

        async with session.get(url) as response:
            count = 0
            async for line in response.content:
                if count >= limit:
                    break

                # Process line
                tweet = parse_tweet(line)
                yield tweet
                count += 1

async def main():
    async for tweet in stream_tweets("python", limit=5):
        print(f"New tweet: {tweet}")
```

**Benefits:**

- Process data as it arrives (no need to wait for all)
- Memory efficient (don't store all tweets)
- Can handle infinite streams
- Natural way to handle streaming APIs

---

### Real Example: Processing Large Files

```python
import asyncio
import aiofiles

async def process_large_file(filename):
    """Read and process file line by line asynchronously"""
    async with aiofiles.open(filename, 'r') as f:
        async for line in f:
            # Process each line asynchronously
            processed = await process_line(line)
            yield processed

async def process_line(line):
    # Simulate some async processing
    await asyncio.sleep(0.01)
    return line.upper()

async def main():
    async for result in process_large_file('huge_file.txt'):
        print(result)
```

**Why this is efficient:**

- Only one line in memory at a time
- Can process files larger than available RAM
- Other tasks can run while processing
- Clean, readable code

---

## Error Handling in Async Code

Errors in async code work similarly to synchronous code, with some nuances.

### Try/Except in Async Functions

Basic error handling works the same:

```python
import asyncio

async def risky_operation():
    await asyncio.sleep(1)
    raise ValueError("Something went wrong!")

async def main():
    try:
        await risky_operation()
    except ValueError as e:
        print(f"Caught error: {e}")

asyncio.run(main())
```

**Output:**

```
Caught error: Something went wrong!
```

**Important:** The exception is raised at the `await` point, not when the coroutine is created:

```python
async def main():
    # Exception NOT raised here
    coro = risky_operation()

    # Exception IS raised here
    await coro  # ValueError raised
```

---

### Handling Errors in Concurrent Operations

When running multiple tasks concurrently, error handling becomes more complex.

**Default behavior with `gather()` - stops on first error:**

```python
import asyncio

async def task(n):
    await asyncio.sleep(1)
    if n == 2:
        raise ValueError(f"Task {n} failed")
    return f"Task {n} success"

async def main():
    try:
        results = await asyncio.gather(
            task(1),
            task(2),  # This fails
            task(3)
        )
    except ValueError as e:
        print(f"Error: {e}")
        # Tasks 1 and 3 results are lost!

asyncio.run(main())
```

**Output:**

```
Error: Task 2 failed
```

**Problem:** When one task fails, we lose all results.

---

**Better approach - collect all results including errors:**

```python
async def main():
    results = await asyncio.gather(
        task(1),
        task(2),  # This fails
        task(3),
        return_exceptions=True  # Return exceptions instead of raising
    )

    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            print(f"Task {i} failed: {result}")
        else:
            print(f"Task {i} succeeded: {result}")

asyncio.run(main())
```

**Output:**

```
Task 1 succeeded: Task 1 success
Task 2 failed: Task 2 failed
Task 3 succeeded: Task 3 success
```

**Benefit:** We get results from all tasks, even if some failed.

---

### Timeouts with `asyncio.wait_for()`

Prevent operations from hanging forever:

```python
import asyncio

async def slow_operation():
    print("Starting slow operation...")
    await asyncio.sleep(10)  # Takes 10 seconds
    return "Done"

async def main():
    try:
        result = await asyncio.wait_for(
            slow_operation(),
            timeout=2  # Wait maximum 2 seconds
        )
        print(result)
    except asyncio.TimeoutError:
        print("Operation timed out!")

asyncio.run(main())
```

**Output:**

```
Starting slow operation...
Operation timed out!
```

**Why this is critical:**

External operations (network, database) can hang indefinitely. Always set timeouts:

```python
# BAD - no timeout, might hang forever
async def bad():
    result = await external_api_call()

# GOOD - timeout prevents hanging
async def good():
    try:
        result = await asyncio.wait_for(
            external_api_call(),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        # Handle timeout
        result = None
```

---

### Cancellation and Cleanup

Tasks can be cancelled, and you should handle cleanup properly:

```python
import asyncio

async def long_task():
    try:
        print("Task: Starting")
        await asyncio.sleep(10)
        print("Task: Completed")
    except asyncio.CancelledError:
        print("Task: Cancelled! Cleaning up...")
        # Perform cleanup here
        raise  # Re-raise to mark as cancelled

async def main():
    task = asyncio.create_task(long_task())

    await asyncio.sleep(2)
    task.cancel()  # Cancel after 2 seconds

    try:
        await task
    except asyncio.CancelledError:
        print("Main: Task was cancelled")

asyncio.run(main())
```

**Output:**

```
Task: Starting
Task: Cancelled! Cleaning up...
Main: Task was cancelled
```

**Best practice for cleanup:**

```python
async def task_with_cleanup():
    resource = None
    try:
        resource = await acquire_resource()
        await do_work(resource)
    except asyncio.CancelledError:
        # Handle cancellation
        raise
    finally:
        # Cleanup always runs
        if resource:
            await release_resource(resource)
```

---

## Common Pitfalls and How to Avoid Them

### 1. Blocking the Event Loop (CRITICAL)

**This is the biggest mistake in async programming.**

The problem:

```python
import asyncio
import time

async def bad_blocking():
    print("Start")
    time.sleep(5)  # BLOCKS THE ENTIRE EVENT LOOP!
    print("End")

async def good_async():
    print("Start")
    await asyncio.sleep(5)  # Allows other tasks to run
    print("End")
```

**Why it's bad:**

- `time.sleep()` blocks the entire event loop
- No other tasks can run during the sleep
- Defeats the entire purpose of async
- Your concurrent code becomes sequential

**Common blocking operations to avoid:**

```
BLOCKING OPERATIONS          USE INSTEAD
────────────────────────    ─────────────────────────
time.sleep()             →  await asyncio.sleep()
requests.get()           →  async with aiohttp.get()
open().read()            →  async with aiofiles.open()
psycopg2.connect()       →  await asyncpg.connect()
Any CPU-intensive work   →  await loop.run_in_executor()
```

**Example - fixing blocking code:**

```python
# BAD - blocks event loop
import requests

async def fetch_bad(url):
    response = requests.get(url)  # Blocking!
    return response.text

# GOOD - async version
import aiohttp

async def fetch_good(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

---

### 2. Forgetting `await` (Silent Bug)

**This creates silent bugs that are hard to catch:**

```python
import asyncio

async def get_data():
    await asyncio.sleep(1)
    return "data"

async def main():
    # WRONG - Returns coroutine object, not result
    result = get_data()
    print(result)  # <coroutine object get_data>
    print(type(result))  # <class 'coroutine'>

    # CORRECT
    result = await get_data()
    print(result)  # "data"

asyncio.run(main())
```

**Python will warn you:**

```
RuntimeWarning: coroutine 'get_data' was never awaited
```

**Always look for this warning!** It's your first line of defense against this bug.

**How to avoid:**

- Always use `await` with coroutine functions
- Set up your IDE to highlight unawaited coroutines
- Run with warnings enabled during development
- Use type checkers (mypy can catch this)

---

### 3. Mixing Sync and Async Code

**The problem:**

```python
import asyncio

def blocking_function():
    import time
    time.sleep(5)
    return "result"

async def bad_example():
    result = blocking_function()  # Blocks event loop!
    await async_function()
```

**What happens:**

- `blocking_function()` blocks the entire event loop
- No other tasks can run for 5 seconds
- Async advantage is lost

**Solution - run blocking code in executor:**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

def blocking_operation():
    import time
    time.sleep(5)
    return "Done"

async def good_example():
    loop = asyncio.get_running_loop()

    # Run blocking operation in thread pool
    result = await loop.run_in_executor(
        None,  # Use default executor
        blocking_operation
    )

    print(result)

asyncio.run(good_example())
```

**What this does:**

- Runs the blocking code in a separate thread
- Event loop remains responsive
- Other async tasks can run
- Result is awaited properly

**Understanding executors:**

When you pass `None` to `run_in_executor()`, Python uses a default `ThreadPoolExecutor` with a limited number of threads. For more control, you can create your own:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

def cpu_bound_task(n):
    """Simulate CPU-intensive work"""
    total = sum(i * i for i in range(n))
    return total

def io_bound_task():
    """Simulate I/O operation (e.g., file read, API call)"""
    import time
    time.sleep(2)
    return "IO Complete"

async def with_custom_executor():
    loop = asyncio.get_running_loop()

    # Create custom executor with specific thread count
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Run multiple blocking tasks concurrently
        results = await asyncio.gather(
            loop.run_in_executor(executor, cpu_bound_task, 1000000),
            loop.run_in_executor(executor, io_bound_task),
            loop.run_in_executor(executor, io_bound_task),
        )

        print(f"Results: {results}")

asyncio.run(with_custom_executor())
```

**When to use custom ThreadPoolExecutor:**

- **Use `None` (default):** For occasional blocking operations, simple use cases
- **Use custom executor:** When you need:
  - Control over the number of worker threads
  - Multiple blocking operations running concurrently
  - Resource management (limit thread count)
  - Better performance tuning

**Real-world example - API with blocking database:**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

def blocking_db_query(user_id: int):
    """Simulate blocking database call"""
    import time
    time.sleep(1)  # Simulates DB query time
    return f"User data for {user_id}"

async def fetch_multiple_users(user_ids: List[int]):
    """Fetch multiple users concurrently using executor"""
    loop = asyncio.get_running_loop()

    # Create executor for DB operations
    with ThreadPoolExecutor(max_workers=10) as db_executor:
        # Run all DB queries concurrently
        tasks = [
            loop.run_in_executor(db_executor, blocking_db_query, user_id)
            for user_id in user_ids
        ]

        results = await asyncio.gather(*tasks)
        return results

async def main():
    user_ids = [1, 2, 3, 4, 5]

    # Fetch all users concurrently
    users = await fetch_multiple_users(user_ids)

    for user in users:
        print(user)

asyncio.run(main())
```

**Key differences:**

| Aspect              | `None` (Default)           | Custom `ThreadPoolExecutor`    |
| ------------------- | -------------------------- | ------------------------------ |
| Setup               | Automatic                  | Manual creation                |
| Thread count        | Limited (system-dependent) | You specify (`max_workers`)    |
| Control             | Minimal                    | Full control                   |
| Use case            | Simple blocking calls      | Multiple concurrent operations |
| Resource management | Automatic                  | Manual (use context manager)   |

---

### 4. Creating Too Many Tasks

**The problem:**

```python
import asyncio

async def fetch(i):
    await asyncio.sleep(0.1)
    return i

async def bad():
    # Creates 1 million tasks at once!
    tasks = [asyncio.create_task(fetch(i)) for i in range(1_000_000)]
    await asyncio.gather(*tasks)
```

**What happens:**

- Too much memory used
- Event loop overwhelmed
- System might crash

**Solution - limit concurrent tasks with semaphore:**

```python
import asyncio

async def fetch(i):
    await asyncio.sleep(0.1)
    return i

async def good():
    semaphore = asyncio.Semaphore(100)  # Max 100 concurrent

    async def limited_fetch(i):
        async with semaphore:
            return await fetch(i)

    tasks = [asyncio.create_task(limited_fetch(i)) for i in range(1_000_000)]
    await asyncio.gather(*tasks)
```

**What this does:**

- Maximum 100 tasks run concurrently
- Tasks wait for semaphore before starting
- Memory usage controlled
- System remains stable

**Alternative - process in batches:**

```python
async def process_in_batches(items, batch_size=100):
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results = await asyncio.gather(*[fetch(item) for item in batch])
        # Process results...
```

---

### 5. Not Handling Cancellation

**The problem:**

```python
import asyncio

async def bad_cleanup():
    file = await open_file()
    await process_file(file)
    await close_file(file)  # Might not run if cancelled!
```

**What happens:**

- If the task is cancelled during `process_file()`
- `close_file()` never runs
- Resource leak!

**Solution - use try/finally:**

```python
async def good_cleanup():
    file = await open_file()
    try:
        await process_file(file)
    finally:
        await close_file(file)  # Always runs!
```

**Even better - use async context managers:**

```python
async def best_cleanup():
    async with open_file() as file:
        await process_file(file)
    # File automatically closed even on cancellation
```

---

### 6. Misunderstanding Coroutine Lifecycle

**The problem:**

```python
import asyncio

async def task():
    print("Task running")
    await asyncio.sleep(1)
    return "done"

async def bad():
    # Creates coroutine but doesn't schedule it
    coro = task()
    # coro is never executed!

asyncio.run(bad())
```

**Output:**

```
RuntimeWarning: coroutine 'task' was never awaited
```

**The coroutine was created but never executed.**

**Solution - schedule or await the coroutine:**

```python
async def good():
    # Option 1: Await it
    result = await task()

    # Option 2: Create a task
    task_obj = asyncio.create_task(task())
    result = await task_obj
```

---

## Real-World Examples

### Example 1: Concurrent API Calls

Fetching data from multiple APIs simultaneously:

```python
import asyncio
import aiohttp
import time

async def fetch_github_user(session, username):
    """Fetch GitHub user data"""
    url = f"https://api.github.com/users/{username}"
    async with session.get(url) as response:
        return await response.json()

async def fetch_multiple_users(usernames):
    """Fetch multiple GitHub users concurrently"""
    async with aiohttp.ClientSession() as session:
        # Create tasks for all users
        tasks = [
            fetch_github_user(session, username)
            for username in usernames
        ]

        # Wait for all to complete
        users = await asyncio.gather(*tasks)
        return users

async def main():
    usernames = ["guido", "gvanrossum", "tiangolo", "kennethreitz", "nvie"]

    start = time.time()
    users = await fetch_multiple_users(usernames)
    elapsed = time.time() - start

    for user in users:
        print(f"{user['login']}: {user['public_repos']} repos")

    print(f"\nFetched {len(users)} users in {elapsed:.2f}s")

asyncio.run(main())
```

**Output:**

```
guido: 54 repos
gvanrossum: 18 repos
tiangolo: 84 repos
kennethreitz: 246 repos
nvie: 102 repos

Fetched 5 users in 0.87s
```

**If done sequentially:** ~5 seconds  
**With async:** <1 second

**Why it's faster:**

- All 5 requests sent simultaneously
- Wait for all responses concurrently
- Total time = longest response time, not sum

---

### Example 2: Database Queries with Connection Pool

```python
import asyncio
import asyncpg

async def get_user(pool, user_id):
    """Get user from database"""
    async with pool.acquire() as connection:
        user = await connection.fetchrow(
            'SELECT * FROM users WHERE id = $1',
            user_id
        )
        return user

async def get_multiple_users(user_ids):
    """Get multiple users concurrently"""
    # Create connection pool
    pool = await asyncpg.create_pool(
        host='localhost',
        database='mydb',
        user='user',
        password='password',
        min_size=10,
        max_size=20
    )

    try:
        # Fetch all users concurrently
        tasks = [get_user(pool, user_id) for user_id in user_ids]
        users = await asyncio.gather(*tasks)
        return users
    finally:
        await pool.close()

async def main():
    user_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    users = await get_multiple_users(user_ids)

    for user in users:
        print(f"User {user['id']}: {user['name']}")

asyncio.run(main())
```

**Benefits:**

- Connection pooling (reuse connections)
- Concurrent queries (multiple at once)
- Automatic connection cleanup
- Efficient resource usage

**How it works:**

1. Pool creates multiple connections upfront
2. Each task acquires a connection from pool
3. Queries run concurrently (up to pool size)
4. Connections returned to pool after use
5. Pool closed when done

---

### Example 3: Web Scraping with Rate Limiting

```python
import asyncio
import aiohttp
from datetime import datetime

class RateLimiter:
    """Rate limiter using semaphore and delays"""

    def __init__(self, rate_per_second):
        self.rate_per_second = rate_per_second
        self.min_interval = 1.0 / rate_per_second
        self.last_call = 0

    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_call

        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)

        self.last_call = asyncio.get_event_loop().time()

async def scrape_url(session, url, rate_limiter):
    """Scrape URL with rate limiting"""
    await rate_limiter.acquire()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scraping: {url}")

    async with session.get(url) as response:
        return await response.text()

async def scrape_multiple_urls(urls, rate_limit=5):
    """Scrape multiple URLs respecting rate limit"""
    rate_limiter = RateLimiter(rate_limit)

    async with aiohttp.ClientSession() as session:
        tasks = [
            scrape_url(session, url, rate_limiter)
            for url in urls
        ]

        results = await asyncio.gather(*tasks)
        return results

async def main():
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
        "https://example.com/page4",
        "https://example.com/page5",
    ]

    # Scrape max 2 URLs per second
    results = await scrape_multiple_urls(urls, rate_limit=2)
    print(f"Scraped {len(results)} URLs")

asyncio.run(main())
```

**Output:**

```
[14:30:00] Scraping: https://example.com/page1
[14:30:00] Scraping: https://example.com/page2
[14:30:01] Scraping: https://example.com/page3
[14:30:01] Scraping: https://example.com/page4
[14:30:02] Scraping: https://example.com/page5
Scraped 5 URLs
```

Notice the 0.5s delay between requests (2 per second)!

**Why rate limiting matters:**

- Prevents overwhelming servers
- Avoids getting banned
- Respectful scraping
- Required by most APIs

---

## Performance Considerations

### When Async is Faster

```python
import asyncio
import aiohttp
import requests
import time

def sync_fetch(urls):
    """Synchronous version"""
    start = time.time()
    results = []

    for url in urls:
        response = requests.get(url)
        results.append(response.text)

    return time.time() - start

async def async_fetch(urls):
    """Asynchronous version"""
    start = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        results = [await r.text() for r in responses]

    return time.time() - start

urls = ["https://httpbin.org/delay/1"] * 10

sync_time = sync_fetch(urls)
async_time = asyncio.run(async_fetch(urls))

print(f"Sync:  {sync_time:.1f}s")
print(f"Async: {async_time:.1f}s")
print(f"Speedup: {sync_time / async_time:.1f}x")
```

**Output:**

```
Sync:  10.2s
Async: 1.1s
Speedup: 9.3x
```

**9x faster** with async for I/O-bound operations!

---

### When Async is NOT Faster

```python
import asyncio
import time

def cpu_bound_sync(n):
    """CPU-intensive calculation"""
    start = time.time()
    total = 0
    for i in range(n):
        total += i ** 2
    return time.time() - start

async def cpu_bound_async(n):
    """Same calculation, but marked as 'async'"""
    start = time.time()
    total = 0
    for i in range(n):
        total += i ** 2
    return time.time() - start

n = 10_000_000

sync_time = cpu_bound_sync(n)
async_time = asyncio.run(cpu_bound_async(n))

print(f"Sync:  {sync_time:.3f}s")
print(f"Async: {async_time:.3f}s")
```

**Output:**

```
Sync:  0.623s
Async: 0.625s
```

**No benefit** - async doesn't help CPU-bound tasks!

**Why:**

- CPU is constantly busy
- No waiting time to utilize
- Event loop can't switch tasks
- Adding `async` just adds overhead

**Correct solution for CPU-bound work:**

- Use multiprocessing
- Use native extensions (C, Rust)
- Use specialized libraries (NumPy, pandas)

---

### Memory Usage

Async is also memory efficient:

```python
import asyncio
import sys

def sync_range(n):
    """Synchronous - stores all results"""
    return [i for i in range(n)]

async def async_range(n):
    """Asynchronous generator - yields one at a time"""
    for i in range(n):
        yield i
        await asyncio.sleep(0)

# Compare memory
sync_list = sync_range(1_000_000)
print(f"Sync list size: {sys.getsizeof(sync_list):,} bytes")

async_gen = async_range(1_000_000)
print(f"Async gen size: {sys.getsizeof(async_gen):,} bytes")
```

**Output:**

```
Sync list size: 8,000,056 bytes
Async gen size: 184 bytes
```

**Async generator uses 43,000x less memory!**

This is because:

- Sync list stores all values in memory
- Async generator only stores current state
- Perfect for processing large datasets

---

## Best Practices Summary

### DO

**1. Use async for I/O-bound tasks**

```python
# Good use cases
async def fetch_data(url):
    async with aiohttp.get(url) as response:
        return await response.json()

async def query_database(user_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
```

**2. Always `await` coroutines**

```python
# Correct
result = await async_function()

# Wrong
result = async_function()  # Returns coroutine object!
```

**3. Use `async with` for resources**

```python
# Correct
async with aiohttp.ClientSession() as session:
    # Use session

# Wrong
session = aiohttp.ClientSession()
# Manual cleanup needed
```

**4. Handle cancellation with try/finally**

```python
async def task():
    resource = None
    try:
        resource = await acquire_resource()
        await do_work(resource)
    finally:
        if resource:
            await release_resource(resource)
```

**5. Set timeouts on external operations**

```python
try:
    result = await asyncio.wait_for(
        external_call(),
        timeout=5.0
    )
except asyncio.TimeoutError:
    # Handle timeout
    pass
```

**6. Limit concurrency with semaphores**

```python
semaphore = asyncio.Semaphore(100)

async def limited_task():
    async with semaphore:
        await do_work()
```

**7. Use connection pools for databases**

```python
pool = await asyncpg.create_pool(...)
async with pool.acquire() as conn:
    # Use connection
```

**8. Profile and measure performance**

```python
import time

start = time.time()
result = await async_operation()
elapsed = time.time() - start
print(f"Took {elapsed:.2f}s")
```

---

### DON'T

**1. Don't block the event loop**

```python
# Wrong
async def bad():
    time.sleep(5)  # Blocks event loop!

# Right
async def good():
    await asyncio.sleep(5)  # Non-blocking
```

**2. Don't use async for CPU-bound tasks**

```python
# Wrong - async doesn't help here
async def bad():
    result = sum(range(10_000_000))

# Right - use multiprocessing or run in executor
async def good():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, compute_heavy_task)
```

**3. Don't create unlimited tasks**

```python
# Wrong - might exhaust memory
tasks = [asyncio.create_task(fetch(i)) for i in range(1_000_000)]

# Right - use semaphore to limit
semaphore = asyncio.Semaphore(100)
async def limited_fetch(i):
    async with semaphore:
        return await fetch(i)
```

**4. Don't ignore coroutine warnings**

```
RuntimeWarning: coroutine 'function' was never awaited
```

This means you forgot `await` - fix it immediately!

**5. Don't mix sync and async randomly**

```python
# Wrong
async def bad():
    result = blocking_sync_function()  # Blocks loop!

# Right
async def good():
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, blocking_sync_function)
```

**6. Don't call `asyncio.run()` inside async functions**

```python
# Wrong
async def bad():
    asyncio.run(another_async_function())  # Error!

# Right
async def good():
    await another_async_function()
```

---

## Key Takeaways

1. **Async enables concurrency, not parallelism** - Tasks make progress together on one CPU core

2. **The event loop manages task scheduling** - Switches between tasks when they're waiting

3. **`async def` creates coroutines, `await` pauses them** - Always await your coroutines!

4. **Use `asyncio.gather()` for concurrent operations** - Run multiple tasks at once

5. **`async with` and `async for`** - For async context managers and iterators

6. **Always set timeouts** - External operations can hang forever

7. **Don't block the event loop** - Use async versions of I/O operations

8. **Async shines for I/O, not CPU work** - Network, database, files = good; math, processing = bad

9. **Measure performance** - Async isn't always faster, verify it helps

10. **Watch for coroutine warnings** - "coroutine was never awaited" means you forgot `await`

---

## Practice Exercises

**Exercise 1: Basic Async**  
Create an async function that fetches data from 3 URLs concurrently and returns all results.

**Exercise 2: Async File Processing**  
Read a large file line by line asynchronously using `aiofiles` and process each line.

**Exercise 3: Rate-Limited API Calls**  
Make 100 API calls with a maximum of 10 concurrent requests using a semaphore.

**Exercise 4: Database Queries**  
Query 50 records from a database concurrently using connection pooling.

**Exercise 5: Error Handling**  
Handle errors in concurrent operations gracefully using `return_exceptions=True`.

See: `exercises/python-fundamentals/async/EXERCISES.md`

---

## Code Examples

- Notebooks: `notebooks/05-async-await.ipynb`
- All runnable code: `code-examples/05_async_await.py`

---

## Next Steps

**Tomorrow**: Day 6 - Type Hints and Static Type Checking

**Resources:**

- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Real Python - Async IO](https://realpython.com/async-io-python/)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)

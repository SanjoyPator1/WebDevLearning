# Day 5: Async/Await - Basics

**Topic**: Introduction to Asynchronous Programming
**Focus**: Understanding `async/await`, event loops, and basic concurrency

## Key Concepts

### What is Async Programming?
- Run multiple operations concurrently without threads
- Perfect for I/O-bound tasks (network, file operations)
- Uses event loop to manage execution

### Basic Syntax

```python
import asyncio

async def fetch_data():
    print("Start fetching")
    await asyncio.sleep(1)  # Simulates I/O operation
    print("Done fetching")
    return "data"

# Run async function
asyncio.run(fetch_data())
```

### Multiple Async Operations

```python
async def task1():
    await asyncio.sleep(1)
    return "Task 1 done"

async def task2():
    await asyncio.sleep(2)
    return "Task 2 done"

async def main():
    # Run concurrently
    results = await asyncio.gather(task1(), task2())
    print(results)

asyncio.run(main())
```

## Code Examples: `code-examples/05_async_basics.py`

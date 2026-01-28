# Python Fundamentals - Async/Await Exercises

**Topic**: Async/Await (Days 1-3)  
**Difficulty**: Beginner to Advanced  
**Total Exercises**: 8

---

## Exercise 1: Concurrent File Downloads

**Difficulty**: Easy  
**File**: `exercise_1.py`

Create an async function that downloads multiple files concurrently.

**Requirements**:
- Use `aiohttp` to fetch URLs
- Download at least 5 URLs concurrently using `asyncio.gather()`
- Measure total time taken
- Return list of results

**Example Usage**:
```python
urls = [
    'https://jsonplaceholder.typicode.com/posts/1',
    'https://jsonplaceholder.typicode.com/posts/2',
    # ... more URLs
]
results = await download_all(urls)
```

---

## Exercise 2: Async Rate Limiter

**Difficulty**: Medium  
**File**: `exercise_2.py`

Implement an async rate limiter class that limits function calls.

**Requirements**:
- Limit to N calls per time window
- Use asyncio.Semaphore or custom implementation
- Track call timestamps
- Block when limit exceeded until window resets

**Example Usage**:
```python
limiter = AsyncRateLimiter(max_calls=5, period=1.0)

async def api_call():
    await limiter.acquire()
    return "API called"
```

---

## Exercise 3: Async Producer-Consumer

**Difficulty**: Medium  
**File**: `exercise_3.py`

Implement producer-consumer pattern using asyncio.Queue.

**Requirements**:
- Multiple producers adding items to queue
- Multiple consumers processing items
- Graceful shutdown when producers done
- Track items processed

---

## Exercise 4: Async Retry with Exponential Backoff

**Difficulty**: Medium  
**File**: `exercise_4.py`

Create an async retry decorator with exponential backoff.

**Requirements**:
- Configurable max attempts
- Exponential backoff: delay * (2 ** attempt)
- Handle specific exceptions
- Return result or raise after max attempts

---

## Exercise 5: Async Semaphore for Concurrency Control

**Difficulty**: Medium  
**File**: `exercise_5.py`

Limit concurrent API calls using semaphore.

**Requirements**:
- Process 100 items
- Only 10 concurrent operations at a time
- Use asyncio.Semaphore
- Track completion progress

---

## Exercise 6: Async Context Manager for Database

**Difficulty**: Medium-Hard  
**File**: `exercise_6.py`

Create an async context manager for database connections.

**Requirements**:
- Implement `__aenter__` and `__aexit__`
- Handle connection errors
- Ensure cleanup on exit
- Support transaction rollback

---

## Exercise 7: Async Task Cancellation

**Difficulty**: Hard  
**File**: `exercise_7.py`

Implement graceful task cancellation.

**Requirements**:
- Start long-running async task
- Cancel after timeout
- Cleanup resources properly
- Handle CancelledError

---

## Exercise 8: Async Batch Processor

**Difficulty**: Hard  
**File**: `exercise_8.py`

Process items in batches concurrently.

**Requirements**:
- Process 1000 items
- Batch size of 50
- Max 5 concurrent batches
- Error handling for individual items
- Return successful and failed items

---

## Testing Your Solutions

```bash
# Install dependencies
pip install aiohttp aiofiles

# Run solutions
python exercise_1.py
```

---

## Resources

- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [aiohttp Documentation](https://docs.aiohttp.org/)
- [Real Python - Async IO](https://realpython.com/async-io-python/)

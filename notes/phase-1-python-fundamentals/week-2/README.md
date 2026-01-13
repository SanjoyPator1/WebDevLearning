# Week 2: Python Fundamentals - Async, Type Hints, Pydantic

**Duration**: 7 days  
**Focus**: Asynchronous programming, type annotations, and data validation

---

## Daily Breakdown

### Day 1: Async/Await - Basics
- **File**: `day-1-async-basics.md`
- **Topics**: Event loops, coroutines, asyncio.gather(), asyncio.create_task()
- **Exercises**: `exercises/01-python-fundamentals/02-async/` (Ex 1-3)

### Day 2: Async/Await - Advanced
- **File**: `day-2-async-advanced.md`
- **Topics**: asyncio.wait(), Semaphores, Locks, Queues, Cancellation

### Day 3: Async/Await - Patterns
- **File**: `day-3-async-patterns.md`
- **Topics**: Rate limiting, retries, batch processing, real-world patterns

### Day 4: Type Hints - Basics
- **File**: `day-4-type-hints-basics.md`
- **Topics**: Basic annotations, collections, Optional, Union, mypy

### Day 5: Type Hints - Advanced
- **File**: `day-5-type-hints-advanced.md`
- **Topics**: TypeVar, Callable, Protocol, Literal, TypedDict
- **Exercises**: `exercises/01-python-fundamentals/03-type-hints/`

### Day 6: Pydantic - Basics
- **File**: `day-6-pydantic-basics.md`
- **Topics**: BaseModel, Field validation, custom validators

### Day 7: Pydantic - Advanced
- **File**: `day-7-pydantic-advanced.md`
- **Topics**: Nested models, computed fields, settings management
- **Exercises**: `exercises/01-python-fundamentals/04-pydantic/`

---

## How to Use This Week's Materials

### 1. Install Dependencies

```bash
# Create/activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install aiohttp aiofiles mypy pydantic pydantic-settings
```

### 2. Read Daily Notes

Start each day by reading the markdown file:
```bash
cat day-1-async-basics.md
# or open in your editor
```

### 3. Run Code Examples (when available)

```bash
cd code-examples/
python 01_async_basics.py
```

### 4. Complete Exercises

```bash
cd ../../exercises/01-python-fundamentals/02-async/
# Read EXERCISES.md
# Complete exercise files
python exercise_1.py
```

### 5. Check Your Types

```bash
# For type hints exercises
mypy exercise_1.py
mypy --strict exercise_1.py
```

---

## Week 2 Goals

By the end of this week, you should be able to:
- [ ] Write async functions and understand event loops
- [ ] Use asyncio.gather() and create_task() effectively
- [ ] Implement rate limiting and retry patterns
- [ ] Add comprehensive type hints to your code
- [ ] Use mypy for static type checking
- [ ] Create Pydantic models for data validation
- [ ] Use Pydantic for settings management

---

## Key Concepts

### Async/Await
- **Concurrency ≠ Parallelism**: Async handles I/O-bound tasks
- **Event Loop**: Manages task execution
- **Coroutines**: Functions defined with `async def`
- **await**: Pauses execution, yields control

### Type Hints
- **Static typing**: Catch errors before runtime
- **Documentation**: Types as documentation
- **IDE support**: Better autocomplete and refactoring
- **Optional**: Types don't affect runtime

### Pydantic
- **Runtime validation**: Validates data at runtime
- **Type coercion**: Converts compatible types
- **Serialization**: Easy JSON conversion
- **FastAPI integration**: Core of FastAPI

---

## Common Pitfalls

### Async
1. Forgetting `await` - coroutine won't execute
2. Using `time.sleep()` instead of `await asyncio.sleep()`
3. Not handling `CancelledError`
4. Running CPU-bound tasks in async code

### Type Hints
1. Not running mypy to check types
2. Using `Any` everywhere (defeats the purpose)
3. Forgetting to annotate return types
4. Not using `Optional` for nullable values

### Pydantic
1. Not handling `ValidationError`
2. Forgetting `Field()` for constraints
3. Using mutable defaults (like lists)
4. Not using `model_dump()` for serialization

---

## Troubleshooting

### Async Issues

**Problem**: "coroutine was never awaited"  
**Solution**: Add `await` before the coroutine call

**Problem**: "RuntimeError: no running event loop"  
**Solution**: Use `asyncio.run()` for top-level code

### Type Checking Issues

**Problem**: mypy errors everywhere  
**Solution**: Start with basic types, gradually add more

**Problem**: "Incompatible types in assignment"  
**Solution**: Check your type annotations match actual types

### Pydantic Issues

**Problem**: ValidationError  
**Solution**: Check your data matches model schema

**Problem**: Field not serializing  
**Solution**: Use `model_dump()` instead of `dict()`

---

## Practice Projects

After completing Week 2, try building:

1. **Async Web Scraper**
   - Fetch multiple URLs concurrently
   - Rate limit requests
   - Validate data with Pydantic

2. **Configuration Manager**
   - Load settings from .env
   - Validate with Pydantic
   - Type hints throughout

3. **Async API Client**
   - Multiple concurrent requests
   - Retry logic
   - Type-safe responses with Pydantic

---

## Next Week Preview

**Week 3**: FastAPI fundamentals - routes, requests, responses

---

## Resources

### Async
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [Real Python - Async IO](https://realpython.com/async-io-python/)
- [aiohttp Documentation](https://docs.aiohttp.org/)

### Type Hints
- [Python Typing Module](https://docs.python.org/3/library/typing.html)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)

### Pydantic
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pydantic V2 Guide](https://docs.pydantic.dev/latest/)
- [FastAPI with Pydantic](https://fastapi.tiangolo.com/tutorial/body/)

---

**Remember**: Async programming and type hints are skills that improve with practice. Don't get discouraged if they feel challenging at first!

Good luck with Week 2! 🚀

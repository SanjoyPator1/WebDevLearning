import time
from fastapi import FastAPI, Depends, Query

app = FastAPI()

# --- Cached Dependency ---
def expensive_computation(q: str = Query("default")):
    """
    Simulates heavy logic. 
    FastAPI will run this ONCE per request, even if called multiple times.
    """
    print(f"Running expensive computation for query: {q}")
    time.sleep(0.5) 
    return f"Computed result for {q}"

@app.get("/cached")
async def test_caching(
    res1: str = Depends(expensive_computation),
    res2: str = Depends(expensive_computation)
):
    """
    Check your console. You will see "Running expensive computation..." ONLY ONCE.
    res1 and res2 will hold the exact same object.
    """
    return {"result_1": res1, "result_2": res2, "is_same_object": res1 is res2}


# --- Disabled Cache ---
def get_timestamp():
    return time.time()

@app.get("/no-cache")
async def test_no_cache(
    t1: float = Depends(get_timestamp, use_cache=False),
    t2: float = Depends(get_timestamp, use_cache=False)
):
    """
    With use_cache=False, the dependency runs every time it's injected.
    t1 and t2 will be slightly different.
    """
    return {"t1": t1, "t2": t2, "is_equal": t1 == t2}
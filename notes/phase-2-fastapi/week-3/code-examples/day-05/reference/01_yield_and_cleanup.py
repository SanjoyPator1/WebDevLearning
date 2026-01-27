import time
from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

# --- 1. Basic Yield (Database Simulation) ---
class MockDB:
    def __init__(self):
        self.status = "disconnected"

    def connect(self):
        self.status = "connected"
        print(">>> DB: Connected")

    def close(self):
        self.status = "closed"
        print(">>> DB: Closed")

def get_db():
    """
    Simulates a database session.
    Code before yield = Setup
    Code after yield = Teardown (Finally)
    """
    db = MockDB()
    db.connect()
    try:
        yield db
    finally:
        # This always runs, even if the handler errors!
        db.close()

@app.get("/db-items")
async def read_db_items(db=Depends(get_db)):
    print(f"Handler using DB: {db.status}")
    return {"db_status": db.status}

@app.get("/db-error")
async def trigger_error(db=Depends(get_db)):
    print("Handler about to raise error...")
    raise HTTPException(status_code=500, detail="Something went wrong")
    # Check console: ">>> DB: Closed" will still print!


# --- 2. Side-Effect Dependency (Timing) ---
async def log_timing():
    """
    Tracks how long a request takes.
    Does not return a value to the handler, just performs logging.
    """
    start = time.time()
    try:
        yield # Control passes to the handler here
    finally:
        process_time = time.time() - start
        print(f"Request took: {process_time:.4f} seconds")

@app.get("/slow-process", dependencies=[Depends(log_timing)])
async def slow_process():
    time.sleep(1) # Simulate work
    return {"message": "Process finished"}
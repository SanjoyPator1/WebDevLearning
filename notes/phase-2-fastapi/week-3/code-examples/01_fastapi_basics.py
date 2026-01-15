"""
Week 3, Day 1: FastAPI Basics
Run with: uvicorn 01_fastapi_basics:app --reload
Visit: http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="FastAPI Basics")

# In-memory storage
items = {}

class Item(BaseModel):
    name: str
    price: float

@app.get("/")
async def root():
    return {"message": "Hello FastAPI"}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(404, "Not found")
    return items[item_id]

@app.post("/items")
async def create_item(item: Item):
    item_id = len(items) + 1
    items[item_id] = item.model_dump()
    return {"id": item_id, **items[item_id]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

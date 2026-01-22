from fastapi import FastAPI
from enum import Enum
from typing import Dict, Union

# setup and configuration
app = FastAPI(
    title="Day 1 FastAPI basics",
    description="A playground to practice Path Operations and Type Hints.",
    version="0.1.0"
)

# in-memory database
# we use this to simulate a real database for our CRUD operations
fake_items_db: Dict[int, dict] = {
    1: {
        "id": 1,
        "name": "Hammer",
        "type": "tool"
    },
    2: {
        "id": 2,
        "name": "Laptop",
        "type": "electronics"
    },
    3: {
        "id": 3,
        "name": "Notebook",
        "type": "stationery"
    }
}

# 1. Basic Hello World
@app.get("/")
async def root():
    """
    Root Endpoint.
    Returns a JSON welcome message
    """
    return {
        "message": "Welcome to the Day 1 of API Playground"
    }

# 2. Path parameters and type conversion
@app.get("/item/{item_id}")
async def read_item(item_id: int):
    """
    Try passing 'abc' instead of a number in the URL to see
    FastAPI's automatic error handling in action.
    """
    if item_id in fake_items_db:
        return {
            "item": fake_items_db[item_id]
        }
    
    return {
        "error": "Item not found"
    }

@app.get("/user/{user_name}")
async def read_user(username: str):
    """
    accept any string for username
    """

    return {
        "user_name": username,
        "message": "You fetched a string parameter"
    }

# 3. ENUMS (Predefined values)
class ItemType(str, Enum):
    tool = "tool"
    electronics = "electronics"
    stationery = "stationery"

@app.get("/items/type/{item_type}")
async def get_items_by_type(item_type: ItemType):
    """
    This endpoint ONLY accepts: 'tool', 'electronics', or 'stationery'.
    Try sending 'food' and watch it fail.
    """
    filtered_items = [
        item for item in fake_items_db.values()
        if item["type"] == item_type
    ]

    return {
        "type": item_type,
        "items": filtered_items 
    }

# 4. Route ordering matters
# CORRECT: Specific route first
@app.get("/users/me")
async def read_current_user():
    return {
        "user_id": "current_user",
        "is_admin": True
    }

# GENERIC: Catch-all route second
@app.get("/users/{user_id}")
async def read_user_by_id(user_id: int):
    return {
        "user_id": user_id,
        "is_admin": False
    }

# 5. CRUD OPERATIONS (HTTP METHODS)
# Note: Since we haven't learned Request Body (JSON) yet,
# we are using path parameters to simulate adding data.

# GET - read
@app.get("/items")
async def get_items():
    """
    Read the complete item list
    """
    return {
        "message": "Successfully fetched complete items list",
        "items" : fake_items_db
    }

# POST - Create
@app.post("/items/create/{name}")
async def create_item(name: str):
    """
    Creates a new item with a generated ID.
    Note: Usually we send data in the Body, but for Day 1 we use Path.
    """
    new_id = len(fake_items_db) + 1
    new_item = {
        "id": new_id,
        "name": name,
        "type": "general"
    }
    fake_items_db[new_id] = new_item

    return {
        "message": "Item created",
        "item": new_item
    }

# PUT - Update (Full Replacement)
@app.put("/items/{item_id}/{new_name}")
async def update_item(item_id: int, new_name: str):
    if item_id not in fake_items_db:
        return {
            "error": "Item not found"
        }
    
    # Update the name
    fake_items_db[item_id]["name"] = new_name
    return {
        "message": "Item updated",
        "item": fake_items_db[item_id]
    }

# DELETE - Remove
@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    if item_id in fake_items_db:
        del fake_items_db[item_id]
        return {
            "message": f"Item {item_id} deleted"
        }
    
    return {
        "message": "Item not found"
    }

# 6. FILE PATHS
@app.get("/files/{file_path: path}")
async def read_file(file_path: str):
    return {
        "file_path": file_path
    }

# you can simply run the above code app using the below command
# uvicorn main:app --reload

# since our python file name is different we need to run this command
# uvicorn 02_fastapi_basics:app --reload

# to directly run this python file for fastapi backend use this
# python 02_fastapi_basics.py 

if __name__ == "__main__":
    import uvicorn
    # CHANGE: "main:app" -> "02_fastapi_basics:app"
    # This tells uvicorn: look in file "02_fastapi_basics.py" for the object "app"
    uvicorn.run("02_fastapi_basics:app", host="127.0.0.1", port=8000, reload=True)
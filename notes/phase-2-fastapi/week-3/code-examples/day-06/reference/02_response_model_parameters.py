from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: float = 10.5
    tags: list[str] = []

# --- Data ---
items_db = {
    "foo": {"name": "Foo", "price": 50.2},
    "bar": {"name": "Bar", "description": "The bartenders", "price": 62, "tax": 20.2},
    "baz": {"name": "Baz", "description": None, "price": 50.2, "tax": 10.5, "tags": []},
}

# --- Endpoints ---

@app.get("/items/{item_id}", response_model=Item, response_model_exclude_unset=True)
async def read_item(item_id: str):
    """
    response_model_exclude_unset=True
    Only fields that were explicitly set when creating the model are returned.
    Default values are not sent to save bandwidth.
    """
    return items_db[item_id]

@app.get("/items/{item_id}/no-none", response_model=Item, response_model_exclude_none=True)
async def read_item_no_none(item_id: str):
    """
    response_model_exclude_none=True
    Fields with 'null' (None) values will be completely removed from the JSON.
    Cleaner API responses.
    """
    # For 'baz', description is None, so it won't appear in the JSON at all.
    return items_db[item_id]

@app.get("/items/{item_id}/public", 
         response_model=Item, 
         response_model_include={"name", "price"})
async def read_item_public(item_id: str):
    """
    response_model_include={"name", "price"}
    Strict whitelist. Only 'name' and 'price' will be returned.
    """
    return items_db[item_id]
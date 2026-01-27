from fastapi import FastAPI
from pydantic import BaseModel
from typing import Union, List

app = FastAPI()

class BaseItem(BaseModel):
    description: str
    type: str

class CarItem(BaseItem):
    type: str = "car"
    wheels: int = 4

class PlaneItem(BaseItem):
    type: str = "plane"
    wingspan: int

# --- Union Response Model ---

items = {
    "item1": {"description": "Tesla Model S", "type": "car", "wheels": 4},
    "item2": {"description": "Boeing 747", "type": "plane", "wingspan": 64},
}

@app.get("/items/{item_id}", response_model=Union[PlaneItem, CarItem, BaseItem])
async def read_item(item_id: str):
    """
    FastAPI will check the data against the models in order.
    If it matches PlaneItem, it returns that structure.
    If it matches CarItem, it returns that.
    """
    return items[item_id]


# --- Documenting Error Responses ---

class ErrorMessage(BaseModel):
    message: str
    code: int

@app.get("/search", 
         response_model=List[str],
         responses={
             404: {"model": ErrorMessage, "description": "The item was not found"},
             200: {"description": "A list of found items"}
         })
async def search(query: str):
    if query == "fail":
        # This structure matches ErrorMessage
        return JSONResponse(
            status_code=404, 
            content={"message": "Not found", "code": 1001}
        )
    return ["item A", "item B"]
    
from fastapi.responses import JSONResponse
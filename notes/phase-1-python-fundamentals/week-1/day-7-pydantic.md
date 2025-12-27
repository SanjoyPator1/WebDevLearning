# Day 7: Pydantic Basics

**Topic**: Data Validation with Pydantic
**Focus**: BaseModel, validators, settings management

## Key Concepts

### Basic Pydantic Model

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int = Field(ge=0, le=150)  # 0 <= age <= 150

user = User(id=1, name="Alice", email="alice@example.com", age=30)
print(user.model_dump())  # Convert to dict
print(user.model_dump_json())  # Convert to JSON
```

### Custom Validators

```python
from pydantic import BaseModel, field_validator

class Product(BaseModel):
    name: str
    price: float
    
    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v
```

### Settings Management

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Code Examples: `code-examples/07_pydantic.py`

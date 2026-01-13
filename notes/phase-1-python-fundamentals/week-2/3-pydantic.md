# Day 7: Pydantic - Data Validation & Settings Management

**Date**: Week 1, Day 7  
**Phase**: 1 - Python Fundamentals  
**Topic**: Data Validation, Serialization, and Settings Management with Pydantic

---

## Learning Objectives

- Understand what Pydantic is and why it's essential for modern Python
- Master BaseModel for data validation and serialization
- Use Field for advanced field configuration
- Create custom validators for complex validation logic
- Handle nested models and complex data structures
- Manage application settings with BaseSettings
- Serialize and deserialize data (dict, JSON, objects)
- Apply Pydantic in real-world scenarios

---

## What is Pydantic?

Pydantic is a **data validation library** that uses Python type hints to validate, parse, and serialize data.

Think of Pydantic as a combination of:

- Type checking (like mypy)
- Data validation (checking values are correct)
- Data parsing (converting types automatically)
- Data serialization (converting to dict/JSON)

### The Problem: Manual Validation is Tedious

Without Pydantic, validation requires lots of manual code:

```python
# Manual validation - tedious and error-prone
def create_user(data: dict) -> dict:
    # Check required fields
    if "name" not in data:
        raise ValueError("name is required")
    if "email" not in data:
        raise ValueError("email is required")
    if "age" not in data:
        raise ValueError("age is required")

    # Validate types
    if not isinstance(data["name"], str):
        raise TypeError("name must be string")
    if not isinstance(data["email"], str):
        raise TypeError("email must be string")
    if not isinstance(data["age"], int):
        raise TypeError("age must be integer")

    # Validate values
    if data["age"] < 0:
        raise ValueError("age must be positive")
    if data["age"] > 150:
        raise ValueError("age must be <= 150")
    if "@" not in data["email"]:
        raise ValueError("email must be valid")

    return data
```

**Problems with this approach:**

- Lots of boilerplate code
- Easy to forget validation
- Hard to maintain
- No automatic type conversion
- Difficult to test

---

### Solution: Pydantic Does It Automatically

With Pydantic, the same validation is simple and declarative:

```python
from pydantic import BaseModel, Field, EmailStr

class User(BaseModel):
    name: str
    email: EmailStr
    age: int = Field(ge=0, le=150)

# Automatic validation
user = User(name="Alice", email="alice@example.com", age=30)

# Invalid data raises clear errors
try:
    User(name="Bob", email="invalid", age=-5)
except ValueError as e:
    print(e)
    # 2 validation errors for User
    # email: value is not a valid email address
    # age: Input should be greater than or equal to 0
```

**What Pydantic provides:**

- Automatic type validation
- Automatic type conversion
- Clear error messages
- Data serialization (to dict/JSON)
- No boilerplate code
- Runtime validation using type hints

---

### Why Use Pydantic?

**1. Type Safety at Runtime**

Unlike mypy (which only checks at development time), Pydantic validates types at runtime:

```python
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float

# Valid - correct types
product = Product(name="Widget", price=19.99)

# Invalid - wrong types, caught immediately
try:
    Product(name=123, price="expensive")
except ValueError as e:
    print(e)
    # 2 validation errors for Product
    # name: Input should be a valid string
    # price: Input should be a valid number
```

---

**2. Automatic Type Conversion**

Pydantic converts compatible types automatically:

```python
from pydantic import BaseModel

class Item(BaseModel):
    quantity: int
    price: float
    active: bool

# Strings are converted automatically
item = Item(
    quantity="10",      # str → int
    price="19.99",      # str → float
    active="yes"        # str → bool
)

print(item.quantity)  # 10 (int, not str)
print(item.price)     # 19.99 (float, not str)
print(item.active)    # True (bool, not str)
```

**What gets converted:**

- Strings to numbers
- Strings to booleans ("yes", "true", "1" → True)
- Numbers to strings
- Compatible types are coerced intelligently

---

**3. Better than Dataclasses**

Pydantic vs standard dataclasses:

```python
from dataclasses import dataclass
from pydantic import BaseModel

# Dataclass - no validation
@dataclass
class DataUser:
    name: str
    age: int

# This works but shouldn't!
bad_user = DataUser(name=123, age="invalid")
print(bad_user.age + 1)  # Error at runtime!

# Pydantic - validates automatically
class PydanticUser(BaseModel):
    name: str
    age: int

# This raises validation error immediately
try:
    PydanticUser(name=123, age="invalid")
except ValueError:
    print("Validation failed - data is incorrect")
```

**Key differences:**

| Feature          | dataclass | Pydantic  |
| ---------------- | --------- | --------- |
| Type validation  | No        | Yes       |
| Type conversion  | No        | Yes       |
| Value validation | No        | Yes       |
| Serialization    | Manual    | Automatic |
| JSON support     | Manual    | Built-in  |
| Error messages   | Generic   | Detailed  |

---

**4. Perfect for APIs**

Pydantic is the foundation of FastAPI and is ideal for API development:

```python
from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    # Note: password NOT included in response!

# FastAPI uses these models for automatic validation
# and documentation generation
```

---

## Installing Pydantic

```bash
# Install Pydantic v2
pip install pydantic

# Install with email validation support
pip install pydantic[email]
```

**Pydantic versions:**

- Pydantic v1: Older version, still widely used
- Pydantic v2: Current version, much faster, some API changes

This guide covers **Pydantic v2** syntax.

---

## BaseModel Fundamentals

`BaseModel` is the foundation of Pydantic. All models inherit from it.

### Creating a Basic Model

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int
    is_active: bool = True  # Default value

# Create instance
user = User(
    id=1,
    name="Alice",
    email="alice@example.com",
    age=30
)

print(user.id)         # 1
print(user.name)       # Alice
print(user.is_active)  # True (default value)
```

**How BaseModel works:**

1. You define fields with type hints
2. Pydantic validates data when creating instance
3. Invalid data raises `ValidationError`
4. Valid data creates a validated object

---

### Required vs Optional Fields

```python
from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    # Required fields (no default value)
    name: str
    price: float

    # Optional field with default value
    description: str = "No description"

    # Optional field that can be None
    discount: Optional[float] = None

# Valid - all required fields provided
product1 = Product(name="Widget", price=19.99)

# Valid - optional fields provided
product2 = Product(
    name="Gadget",
    price=29.99,
    description="A useful gadget",
    discount=0.15
)

# Invalid - missing required field 'price'
try:
    Product(name="Item")
except ValueError as e:
    print(e)
    # 1 validation error for Product
    # price: Field required
```

**Rules:**

- Fields without default values are required
- Fields with default values are optional
- `Optional[Type]` or `Type | None` allows None

---

### Model Methods

Pydantic models have several useful built-in methods:

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

user = User(id=1, name="Alice", email="alice@example.com")

# Convert to dictionary
user_dict = user.model_dump()
print(user_dict)
# {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}

# Convert to JSON string
user_json = user.model_dump_json()
print(user_json)
# '{"id":1,"name":"Alice","email":"alice@example.com"}'

# Create from dictionary
data = {"id": 2, "name": "Bob", "email": "bob@example.com"}
user2 = User(**data)

# Create from JSON string
json_str = '{"id": 3, "name": "Charlie", "email": "charlie@example.com"}'
user3 = User.model_validate_json(json_str)

# Copy with changes
user_copy = user.model_copy(update={"name": "Alice Smith"})
print(user_copy.name)  # "Alice Smith"
```

**Common methods:**

- `model_dump()` → Convert to dict
- `model_dump_json()` → Convert to JSON string
- `model_validate()` → Validate dict and create instance
- `model_validate_json()` → Parse JSON and create instance
- `model_copy()` → Create a copy (optionally with updates)

---

### Accessing Field Values

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

user = User(id=1, name="Alice", email="alice@example.com")

# Access as attributes
print(user.name)   # Alice
print(user.email)  # alice@example.com

# Access as dictionary
user_dict = user.model_dump()
print(user_dict["name"])   # Alice
print(user_dict["email"])  # alice@example.com

# Iterate over fields
for field_name, field_value in user:
    print(f"{field_name}: {field_value}")
# id: 1
# name: Alice
# email: alice@example.com
```

---

## Field Configuration with Field()

`Field()` provides advanced configuration for model fields.

### Basic Field Usage

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int = Field(description="Unique user identifier")
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: int = Field(ge=0, le=150)  # 0 <= age <= 150
    score: float = Field(gt=0, lt=100)  # 0 < score < 100

# Valid user
user = User(
    id=1,
    name="Alice",
    email="alice@example.com",
    age=30,
    score=85.5
)

# Invalid - name too short
try:
    User(id=2, name="", email="test@example.com", age=25, score=80)
except ValueError as e:
    print(e)
    # name: String should have at least 1 character
```

**Field validation parameters:**

| Parameter     | Type        | Description                  |
| ------------- | ----------- | ---------------------------- |
| `ge`          | number      | Greater than or equal        |
| `gt`          | number      | Greater than                 |
| `le`          | number      | Less than or equal           |
| `lt`          | number      | Less than                    |
| `min_length`  | string/list | Minimum length               |
| `max_length`  | string/list | Maximum length               |
| `pattern`     | string      | Regex pattern                |
| `description` | string      | Field description (for docs) |

---

### Default Values and Factories

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Article(BaseModel):
    title: str
    content: str

    # Static default value
    published: bool = False

    # Default factory (called each time)
    created_at: datetime = Field(default_factory=datetime.now)
    tags: list[str] = Field(default_factory=list)

    # Optional with None default
    author: Optional[str] = None

# Each instance gets unique created_at and tags list
article1 = Article(title="First", content="Content 1")
article2 = Article(title="Second", content="Content 2")

print(article1.created_at == article2.created_at)  # False
print(article1.tags is article2.tags)  # False
```

**When to use `default_factory`:**

- When default value should be different for each instance
- For mutable defaults (list, dict, set)
- For computed defaults (datetime.now(), uuid.uuid4())

---

### Field Aliases

Use aliases when JSON/dict keys don't match Python field names:

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str
    email_address: str = Field(alias="email")

# Create with alias
user = User(id=1, name="Alice", email="alice@example.com")

# Access with Python name
print(user.email_address)  # alice@example.com

# Serialize with alias
print(user.model_dump(by_alias=True))
# {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}
```

**When to use aliases:**

- API responses use different field names
- Working with camelCase JSON (JavaScript)
- Database columns have different names

> Alias is important when you have to respond in camel case for the api e.g firstName is alias for first_name

---

## Custom Validators (Pydantic v2)

Validators let you **enforce business rules and transform data**, not just check types. They run automatically when a model is created.

---

## Field Validators

Field validators validate **individual fields**.

```python
from pydantic import BaseModel, field_validator

class Product(BaseModel):
    name: str
    price: float
    quantity: int

    @field_validator('price')
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

    @field_validator('quantity')
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Quantity cannot be negative')
        return v

    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

---

## Why `cls` is the First Argument

Field validators **must be class methods**, so their signature always starts with `cls`.

### What `cls` means

- `cls` refers to the **model class itself** (`Product`, `User`, etc.)
- Similar to how `self` refers to an instance
- Provided by Python automatically because of `@classmethod`

### Why Pydantic requires `@classmethod`

1. Validators run **before an instance fully exists**
2. Pydantic may reuse the validator logic across model creation
3. Using `cls` allows:

   - Access to model-level configuration
   - Reusability in subclasses
   - Consistent lifecycle control

Even if you don’t use `cls`, it **must be present**.

```python
@field_validator('price')
@classmethod
def validate_price(cls, v):  # cls is required
    return v
```

---

## How Field Validators Work (Execution Flow)

1. Input data is received
2. Type coercion happens (`"10"` → `10`)
3. Field validator runs
4. If invalid → raises `ValueError`
5. If valid → returned value is stored in the model

Validators **must always return a value**.

---

## Valid vs Invalid Example

```python
Product(name="Widget", price=19.99, quantity=10)   # valid
Product(name="Item", price=-5, quantity=10)        # raises error
```

---

## Validating Multiple Fields with One Validator

You can reuse the same logic across fields.

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    username: str
    email: str
    password: str

    @field_validator('username', 'email', 'password')
    @classmethod
    def fields_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty')
        return v.strip()
```

Use this when:

- Validation logic is identical
- Fields share the same constraints

---

## Model Validators

Model validators validate the **entire object**, not just one field.

```python
from pydantic import BaseModel, model_validator

class DateRange(BaseModel):
    start_date: str
    end_date: str

    @model_validator(mode='after')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValueError('start_date must be before end_date')
        return self
```

---

## Why Model Validators Use `self` Instead of `cls`

- Model validators run **after the model instance exists**
- `self` gives access to **all validated fields**
- Used for cross-field rules

Use model validators when:

- One field depends on another
- You need the full object state

---

## Model Validator Modes

### `mode='before'`

- Runs **before field validation**
- Receives raw input data (usually a `dict`)
- Useful for reshaping input

```python
@model_validator(mode='before')
@classmethod
def preprocess_input(cls, data):
    data['email'] = data['email'].lower()
    return data
```

### `mode='after'`

- Runs **after all fields are validated**
- Receives the model instance (`self`)
- Most common and safest option

```python
@model_validator(mode='after')
def check_dates(self):
    if self.start_date > self.end_date:
        raise ValueError('start_date must be before end_date')
    return self
```

---

## Transforming Values with Validators

Validators are allowed to **modify data**.

```python
from pydantic import BaseModel, field_validator

class User(BaseModel):
    username: str
    email: str

    @field_validator('username')
    @classmethod
    def username_to_lowercase(cls, v):
        return v.lower()

    @field_validator('email')
    @classmethod
    def email_to_lowercase(cls, v):
        return v.lower().strip()
```

```python
user = User(username="ALICE", email=" BOB@EXAMPLE.COM ")
print(user.username)  # alice
print(user.email)     # bob@example.com
```

---

## When to Use What

| Use Case                   | Validator Type                      |
| -------------------------- | ----------------------------------- |
| Single-field rules         | `field_validator`                   |
| Shared logic across fields | `field_validator` (multiple fields) |
| Cross-field dependency     | `model_validator(mode='after')`     |
| Raw input cleanup          | `model_validator(mode='before')`    |
| Data normalization         | Field validator                     |

---

## Common Mistakes

- Forgetting `@classmethod` on field validators
- Not returning a value from a validator
- Using field validators for cross-field logic
- Raising generic `Exception` instead of `ValueError`

---

## Mental Model

- **Field validator** → “Is this value valid?”
- **Model validator** → “Does this object make sense as a whole?”
- **`cls`** → model-level context (before instance exists)
- **`self`** → instance-level validation (after creation)

This structure keeps validation predictable, explicit, and maintainable.

## Nested Models

Models can contain other models for complex data structures.

### Basic Nested Models

```python
from pydantic import BaseModel

class Address(BaseModel):
    street: str
    city: str
    country: str
    postal_code: str

class User(BaseModel):
    name: str
    email: str
    address: Address

# Create with nested data
user = User(
    name="Alice",
    email="alice@example.com",
    address={
        "street": "123 Main St",
        "city": "Springfield",
        "country": "USA",
        "postal_code": "12345"
    }
)

# Access nested fields
print(user.address.city)      # Springfield
print(user.address.country)   # USA

# Serialize to dict (includes nested models)
user_dict = user.model_dump()
print(user_dict["address"]["city"])  # Springfield
```

**How nested models work:**

- Nested dict is automatically validated and converted to model
- Nested model can be accessed as attribute
- Serialization includes nested models

---

### Lists of Models

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    quantity: int

class Order(BaseModel):
    order_id: int
    customer_name: str
    items: list[Item]

# Create with list of items
order = Order(
    order_id=1,
    customer_name="Alice",
    items=[
        {"name": "Widget", "price": 19.99, "quantity": 2},
        {"name": "Gadget", "price": 29.99, "quantity": 1}
    ]
)

# Access items
for item in order.items:
    print(f"{item.name}: ${item.price} x {item.quantity}")
# Widget: $19.99 x 2
# Gadget: $29.99 x 1

# Calculate total
total = sum(item.price * item.quantity for item in order.items)
print(f"Total: ${total}")  # Total: $69.97
```

---

### Optional Nested Models

```python
from pydantic import BaseModel
from typing import Optional

class Company(BaseModel):
    name: str
    website: str

class User(BaseModel):
    name: str
    email: str
    company: Optional[Company] = None

# User without company
user1 = User(name="Alice", email="alice@example.com")
print(user1.company)  # None

# User with company
user2 = User(
    name="Bob",
    email="bob@example.com",
    company={"name": "Acme Corp", "website": "acme.com"}
)
print(user2.company.name)  # Acme Corp
```

---

### Deeply Nested Models

```python
from pydantic import BaseModel

class Image(BaseModel):
    url: str
    width: int
    height: int

class Comment(BaseModel):
    user: str
    text: str
    timestamp: str

class Post(BaseModel):
    title: str
    content: str
    author: str
    images: list[Image]
    comments: list[Comment]

# Create deeply nested structure
post = Post(
    title="My Post",
    content="Post content",
    author="Alice",
    images=[
        {"url": "image1.jpg", "width": 800, "height": 600},
        {"url": "image2.jpg", "width": 1024, "height": 768}
    ],
    comments=[
        {"user": "Bob", "text": "Great post!", "timestamp": "2024-01-01"},
        {"user": "Charlie", "text": "Thanks!", "timestamp": "2024-01-02"}
    ]
)

# All nested models are validated
print(post.images[0].width)      # 800
print(post.comments[0].user)     # Bob
```

---

## Settings Management with `BaseSettings`

`BaseSettings` is a specialized form of `BaseModel` used for **application configuration**.
It automatically loads values from environment variables and `.env` files and validates them using type hints.

---

### Why `BaseSettings` Exists

Without structured settings management:

- Configuration values are scattered across the codebase
- `os.getenv()` calls are untyped and unvalidated
- Missing or invalid configuration fails at runtime
- Secrets are easy to leak accidentally

`BaseSettings` solves this by combining:

- Environment variable loading
- Type validation
- Default values
- Centralized configuration

---

### Basic Settings Definition

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    app_name: str = "My App"
    debug: bool = False

    # Database settings
    database_url: str
    database_pool_size: int = 10

    # API settings
    api_key: str
    api_timeout: int = 30

settings = Settings()
```

---

### How Value Resolution Works

For each field, Pydantic follows this order:

1. Environment variable
2. Value from `.env` file (if configured)
3. Default value defined in the class
4. Error if no value is found for a required field

Field names are matched to environment variables in a **case-insensitive** manner.

```bash
DATABASE_URL=postgresql://localhost/db
API_KEY=secret
```

---

### Loading from `.env` Files

Create a `.env` file:

```bash
APP_NAME=Production App
DEBUG=false
DATABASE_URL=postgresql://localhost/mydb
API_KEY=secret-key-12345
```

Configure the settings class:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str
    debug: bool
    database_url: str
    api_key: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

settings = Settings()
```

---

### Environment-Specific Settings

Different environments often require different configurations.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    app_name: str
    debug: bool
    database_url: str

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('ENV', 'development')}"
    )
```

```bash
# .env.development
DEBUG=true
DATABASE_URL=sqlite:///dev.db

# .env.production
DEBUG=false
DATABASE_URL=postgresql://prod-server/db
```

---

### Nested Settings (Structured Configuration)

Large applications benefit from grouping related settings.

```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    username: str
    password: str
    database: str

class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379

class Settings(BaseSettings):
    app_name: str
    database: DatabaseSettings
    redis: RedisSettings

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__"
    )
```

Environment variables map using the nested delimiter:

```bash
DATABASE__HOST=db-server
DATABASE__USERNAME=admin
DATABASE__PASSWORD=secret
REDIS__HOST=cache-server
```

---

### Secret Values with `SecretStr`

Sensitive configuration values should not appear in logs or error messages.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    app_name: str
    debug: bool = False

    database_password: SecretStr
    api_key: SecretStr

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

```python
print(settings.api_key)
# **********

real_key = settings.api_key.get_secret_value()
```

`SecretStr` masks values in representations while still allowing explicit access when needed.

---

### Practical Guidelines

- Keep all configuration in a single `Settings` class
- Use defaults for non-critical values
- Use `.env` files for local development only
- Use real environment variables in production
- Avoid calling `os.getenv()` directly in application code

---

### Conceptual Summary

- `BaseModel` validates **data**
- `BaseSettings` validates **configuration**
- Environment variables have highest priority
- Defaults provide safe fallbacks
- Secrets should always use `SecretStr`

---

## Common Patterns and Best Practices (Pydantic)

---

## Pattern 1: Request / Response Models (API Boundary Models)

This pattern separates **what the client sends**, **what the server stores**, and **what the server returns**.

```python
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
```

```python
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    created_at: datetime
    is_active: bool
```

```python
class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None
```

### Why this separation matters

**Create model**

- Represents incoming request data
- Contains fields required to create a resource
- May include sensitive fields (e.g. password)
- Does not include server-generated fields (id, timestamps)

**Response model**

- Represents outgoing API data
- Excludes sensitive fields
- Includes server-controlled fields
- Acts as a contract for API consumers

**Update model**

- Represents partial updates
- All fields optional
- Explicitly restricts which fields can change

### Key idea

One database entity ≠ one API schema
Each interaction has its own validated shape.

---

## Pattern 2: Configuration Validation (Fail Fast)

Configuration errors should fail **at startup**, not at runtime.

```python
class ServerConfig(BaseModel):
    host: str
    port: int
    workers: int
    timeout: int
    max_requests: int
```

### What this pattern solves

- Invalid ports (e.g. 70000)
- Impossible worker counts
- Misconfigured timeouts
- Typos in environment variables

### Why validators are used here

Configuration often has:

- Ranges (port numbers, timeouts)
- Domain rules (allowed hosts)
- Cross-field constraints

Using validation ensures:

- Application crashes early
- Errors are explicit and actionable
- Production misconfiguration is caught immediately

### Design principle

Configuration is **data**, not logic
Validate it like user input.

---

## Pattern 3: Data Transfer Objects (DTOs)

DTOs define **how data moves between layers** of the system.

```python
class CreateOrderDTO(BaseModel):
    customer_id: int
    items: list[dict]
    shipping_address: str
    billing_address: str
```

```python
class OrderDTO(BaseModel):
    order_id: int
    customer_id: int
    total_amount: float
    status: str
    created_at: str
```

### What a DTO is

A DTO is:

- A plain data container
- Validated and typed
- Free of business logic
- Used to move data across boundaries

### Where DTOs are used

- API → Service layer
- Service → Repository
- Service → API response
- Microservice → Microservice

### Why not pass ORM models directly

- ORM models leak persistence concerns
- Tight coupling between layers
- Harder to evolve APIs
- Increased security risk

### Key idea

DTOs protect your architecture boundaries.

---

## Pattern 4: Immutable Models (Read-Only Data)

Immutable models prevent accidental mutation.

```python
class ImmutableUser(BaseModel):
    id: int
    username: str
    email: str

    model_config = ConfigDict(frozen=True)
```

### What immutability guarantees

- Once created, data cannot change
- No accidental state corruption
- Easier reasoning and debugging
- Safe to share across threads or layers

### When to use immutable models

- Configuration objects
- API response models
- Value objects (Money, Coordinates, IDs)
- Cached data

### When not to use them

- Forms or request models
- Objects that evolve during processing
- Aggregates under construction

---

## Architectural Mapping

| Pattern          | Purpose                       |
| ---------------- | ----------------------------- |
| Request Models   | Validate incoming data        |
| Response Models  | Control outgoing data         |
| DTOs             | Transfer data between layers  |
| Config Models    | Validate system configuration |
| Immutable Models | Enforce read-only guarantees  |

---

## Core Design Principles Reinforced

- Explicit schemas prevent implicit bugs
- Different responsibilities need different models
- Validation belongs at system boundaries
- Data shape is part of your API contract
- Immutability is a safety tool, not a default

---

## Serialization and Deserialization

### Converting to Dictionary

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True

user = User(id=1, name="Alice", email="alice@example.com")

# Full dict
user_dict = user.model_dump()
print(user_dict)
# {'id': 1, 'name': 'Alice', 'email': 'alice@example.com', 'is_active': True}

# Exclude fields
user_dict = user.model_dump(exclude={'email'})
print(user_dict)
# {'id': 1, 'name': 'Alice', 'is_active': True}

# Include only specific fields
user_dict = user.model_dump(include={'id', 'name'})
print(user_dict)
# {'id': 1, 'name': 'Alice'}

# Exclude unset fields (use defaults)
user_dict = user.model_dump(exclude_unset=True)
```

---

### Converting to JSON

```python
from pydantic import BaseModel
from datetime import datetime

class Event(BaseModel):
    name: str
    timestamp: datetime
    attendees: list[str]

event = Event(
    name="Conference",
    timestamp=datetime(2024, 1, 15, 10, 0),
    attendees=["Alice", "Bob", "Charlie"]
)

# Convert to JSON string
json_str = event.model_dump_json()
print(json_str)
# {"name":"Conference","timestamp":"2024-01-15T10:00:00","attendees":["Alice","Bob","Charlie"]}

# Pretty JSON
json_str = event.model_dump_json(indent=2)
print(json_str)
# {
#   "name": "Conference",
#   "timestamp": "2024-01-15T10:00:00",
#   "attendees": [
#     "Alice",
#     "Bob",
#     "Charlie"
#   ]
# }
```

---

### Parsing from Dictionary

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

# From dict
data = {"id": 1, "name": "Alice", "email": "alice@example.com"}
user = User(**data)

# Or use model_validate
user = User.model_validate(data)

# Extra fields are ignored by default
data_with_extra = {
    "id": 2,
    "name": "Bob",
    "email": "bob@example.com",
    "age": 30,  # Not in model
    "city": "NYC"  # Not in model
}
user = User(**data_with_extra)  # Works fine, extra fields ignored
```

---

### Parsing from JSON

```python
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float
    in_stock: bool

# Parse JSON string
json_str = '{"name": "Widget", "price": 19.99, "in_stock": true}'
product = Product.model_validate_json(json_str)

print(product.name)      # Widget
print(product.price)     # 19.99
print(product.in_stock)  # True
```

---

## Error Handling (Pydantic)

---

## Validation Errors

Pydantic raises a single `ValidationError` that can contain **multiple field-level errors**.

```python
try:
    User(name="", age="invalid", email="not-an-email")
except ValidationError as e:
    print(e)
```

**What happens internally**

- All fields are validated
- Errors are collected (not fail-fast)
- A structured error report is raised
- One exception may represent many problems

This makes validation feedback complete and user-friendly.

---

## Understanding the Error Structure

Each validation error is represented as a structured dictionary.

```python
try:
    User(name="Alice", age=-5, email="alice@example.com")
except ValidationError as e:
    for error in e.errors():
        print(error)
```

**Common fields in `error`**

- `loc` – Location of the error (field path)
- `msg` – Human-readable message
- `type` – Error category (useful for programmatic handling)
- `input` – The invalid value (in some cases)

Example interpretation:

- `loc = ('age',)` → error occurred in `age`
- `msg = 'Input should be greater than or equal to 0'`
- `type = 'greater_than_equal'`

---

## Custom Error Messages

Use validators when built-in constraints are not expressive enough.

```python
class User(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    age: int = Field(ge=0, le=150)

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError(
                "Username must contain only letters and numbers"
            )
        return v
```

**Why custom messages matter**

- Clear feedback for API consumers
- Better UX in forms and clients
- Domain-specific rules are explicit
- Errors describe intent, not implementation

---

## Built-in vs Custom Validation

**Prefer built-in validation when possible**

```python
age: int = Field(ge=0, le=150)
```

**Use validators when**

- Validation logic is conditional
- Rules depend on business logic
- Data needs normalization or transformation
- Error messages must be domain-specific

---

## Handling Errors Programmatically

Validation errors are designed to be machine-readable.

```python
try:
    User(username="ab", age=200)
except ValidationError as e:
    errors = e.errors()
```

**Common use cases**

- Mapping errors to HTTP responses
- Returning structured API error payloads
- Logging validation failures
- Displaying field-level errors in UI forms

---

## Key Design Principles

- Validation errors are data, not just exceptions
- One model validation can produce many errors
- Error structure is stable and predictable
- Custom errors should explain _why_, not just _what_

---

## Practical Guideline

- Let Pydantic handle syntax and type errors
- Add custom validators only for business rules
- Never silence `ValidationError`
- Always validate at system boundaries (API, config, user input)

---

## Real-World Example: Complete API Models

```python
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional

# User models
class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str = Field(min_length=8)

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        return v

class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

# Post models
class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str
    published: bool = False

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: int
    author_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Using the models
def create_user(user_data: UserCreate) -> UserResponse:
    """Create a new user - input is validated automatically"""
    # Input is guaranteed to be valid
    # Create user in database
    # Return validated response
    pass

def create_post(post_data: PostCreate, author_id: int) -> PostResponse:
    """Create a new post - input is validated automatically"""
    # Input is guaranteed to be valid
    pass
```

---

## Best Practices (Pydantic Models)

---

## DO

### 1. Use precise field types

Choose the most specific type available instead of generic primitives.

```python
class User(BaseModel):
    email: EmailStr
    website: HttpUrl
    age: int
```

**Why this matters**

- Built-in validation comes for free
- Invalid data is rejected early
- Intent is explicit in the model definition
- Reduces the need for custom validators

---

### 2. Express constraints at the field level

Use `Field` for simple, declarative validation rules.

```python
class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    quantity: int = Field(ge=0)
```

**When to prefer `Field` over validators**

- Range checks
- Length limits
- Numeric boundaries
- Basic format constraints

This keeps validation readable and centralized.

---

### 3. Use validators only for cross-field or domain rules

Validators are best suited for logic that involves multiple fields or business rules.

```python
class User(BaseModel):
    password: str
    password_confirm: str

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self
```

**Key guideline**

- Field constraints → `Field`
- Single-field transformation → `field_validator`
- Cross-field logic → `model_validator`

---

### 4. Separate models by responsibility

Different operations require different data shapes.

```python
class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
```

**Benefits**

- Prevents accidental data leaks
- Makes API intent explicit
- Allows models to evolve independently
- Aligns with REST and clean architecture

---

## DON'T

### 1. Don’t rely on `Any`

Using `Any` removes almost all benefits of validation and typing.

```python
class User(BaseModel):
    data: Any
```

**Why this is harmful**

- No validation
- No editor assistance
- Errors move to runtime
- Hidden bugs propagate across layers

---

### 2. Don’t bypass validation

Disabling validation defeats the purpose of using Pydantic.

```python
class User(BaseModel):
    model_config = ConfigDict(validate_assignment=False)
```

**Use cases are rare**

Only disable validation when:

- You fully control all assignments
- Performance profiling proves it necessary
- You understand the trade-offs

---

### 3. Don’t use mutable default values

Mutable defaults are shared across instances.

```python
class User(BaseModel):
    tags: list = []
```

**Correct approach**

```python
class User(BaseModel):
    tags: list = Field(default_factory=list)
```

**Why this matters**

- Prevents state leakage between objects
- Avoids subtle and hard-to-debug bugs
- Aligns with Python’s object model

---

## Mental Checklist When Designing a Model

- Are field types as specific as possible?
- Can this rule be expressed declaratively with `Field`?
- Does this model represent input, output, or transfer?
- Should this data be mutable or immutable?
- Is validation happening at the boundary?

---

## Key Takeaways

1. **Pydantic validates data at runtime** - Unlike mypy, Pydantic checks types when code runs

2. **BaseModel is the foundation** - All Pydantic models inherit from BaseModel

3. **Field() adds constraints** - Use for validation rules like min/max, length, patterns

4. **Validators enable custom logic** - Use `@field_validator` for complex validation

5. **Automatic type conversion** - Pydantic converts compatible types (str → int, etc.)

6. **Built-in serialization** - Easy conversion to dict/JSON with `model_dump()` and `model_dump_json()`

7. **BaseSettings for configuration** - Load settings from environment variables and .env files

8. **Nested models for complex data** - Models can contain other models

9. **Clear error messages** - ValidationError provides detailed information

10. **Perfect for APIs** - FastAPI uses Pydantic for automatic request/response validation

---

## Practice Exercises

**Exercise 1: Basic Models**  
Create a Book model with title, author, ISBN, price, and publication year. Add appropriate field constraints.

**Exercise 2: Custom Validators**  
Create a Password model with validation for minimum length, uppercase, lowercase, digit, and special character requirements.

**Exercise 3: Nested Models**  
Create an Order model containing Customer, list of OrderItems, and ShippingAddress as nested models.

**Exercise 4: Settings Management**  
Create a Settings class that loads database, Redis, and API configuration from environment variables.

**Exercise 5: Request/Response Models**  
Create UserCreate, UserResponse, and UserUpdate models for a user management API.

See: `exercises/python-fundamentals/pydantic/EXERCISES.md`

---

## Code Examples

- Notebooks: `notebooks/07-pydantic.ipynb`
- All runnable code: `code-examples/07_pydantic.py`

---

## Next Steps

**Congratulations!** You've completed Week 1 - Python Fundamentals!

**What you've learned:**

- Generators (memory-efficient iteration)
- Async/Await (concurrent programming)
- Type Hints (static type checking)
- Pydantic (data validation)

**Week 2 Preview**: FastAPI Fundamentals - Building production APIs

**Resources:**

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pydantic GitHub](https://github.com/pydantic/pydantic)
- [FastAPI and Pydantic](https://fastapi.tiangolo.com/tutorial/body/)

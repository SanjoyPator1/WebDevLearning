# Python Fundamentals - Pydantic Exercises

**Topic**: Pydantic (Days 6-7)  
**Difficulty**: Beginner to Intermediate  
**Total Exercises**: 6

---

## Exercise 1: Basic User Model

**Difficulty**: Easy  
**File**: `exercise_1.py`

Create a User model with validation.

**Requirements**:
- Fields: id, username, email, age
- Username: alphanumeric, 3-20 chars
- Email: valid email format
- Age: 13-120
- Use Field validators

---

## Exercise 2: E-commerce Product Model

**Difficulty**: Medium  
**File**: `exercise_2.py`

Create Product model with nested Category.

**Requirements**:
- Product: name, price, quantity, category
- Category: id, name, description (optional)
- Price must be positive
- Quantity must be non-negative
- Discount price (computed field)

---

## Exercise 3: Custom Validators

**Difficulty**: Medium  
**File**: `exercise_3.py`

Implement custom validators for password strength.

**Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Custom error messages

---

## Exercise 4: Settings from Environment

**Difficulty**: Medium  
**File**: `exercise_4.py`

Create Settings class loading from .env file.

**Requirements**:
- Use BaseSettings
- Load DATABASE_URL, API_KEY, DEBUG
- Provide defaults for optional settings
- Validate URL format
- Create .env.example

---

## Exercise 5: Model Serialization

**Difficulty**: Medium  
**File**: `exercise_5.py`

Practice model serialization/deserialization.

**Requirements**:
- Create complex nested model
- Convert to dict with custom field names
- Serialize to JSON
- Deserialize from JSON
- Handle optional fields

---

## Exercise 6: API Response Models

**Difficulty**: Medium-Hard  
**File**: `exercise_6.py`

Create Pydantic models for API responses.

**Requirements**:
- Success and Error response models
- Generic response wrapper
- Pagination model
- Validation for status codes
- JSON serialization with snake_case

**Example Structure**:
```python
class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int

class SuccessResponse(BaseModel):
    status: Literal["success"]
    data: Any
    pagination: PaginationInfo | None = None

class ErrorResponse(BaseModel):
    status: Literal["error"]
    message: str
    error_code: str
```

---

## Testing

```bash
# Install pydantic
pip install pydantic pydantic-settings

# Run your solutions
python exercise_1.py
```

---

## Resources

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [FastAPI with Pydantic](https://fastapi.tiangolo.com/tutorial/body/)

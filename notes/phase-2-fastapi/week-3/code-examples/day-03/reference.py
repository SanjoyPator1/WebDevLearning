"""
Day 3: Data Validation & Exception Handling - Practical Examples
================================================================

This module demonstrates:
1. Field() constraints for different data types
2. Custom field validators
3. Model-level validators
4. Exception handling patterns
5. Real-world validation scenarios

Run this file directly to see examples, or import models for your own use.
"""

from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr


app = FastAPI(
    title="Day 3: Validation Examples",
    description="Comprehensive validation and error handling demonstrations"
)


# ============================================================================
# SECTION 1: Field() Constraints - Different Data Types
# ============================================================================

class ProductCreate(BaseModel):
    """
    Demonstrates numeric and string Field() constraints.
    
    Real-world use case: E-commerce product creation
    """
    
    # String constraints
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Product name",
        examples=["Wireless Mouse", "Gaming Keyboard"]
    )
    
    # Numeric constraints - price must be positive
    price: float = Field(
        ...,
        gt=0,  # Greater than 0 (cannot be free)
        le=1_000_000,  # Less than or equal to 1 million
        description="Product price in USD",
        examples=[29.99, 149.99]
    )
    
    # Integer with range - stock can be zero
    stock: int = Field(
        ...,
        ge=0,  # Greater than or equal to 0
        le=10_000,
        description="Available stock quantity"
    )
    
    # Optional field with default
    description: str = Field(
        "No description available",
        max_length=500,
        description="Product description"
    )
    
    # Optional field that can be None
    category: str | None = Field(
        None,
        min_length=2,
        max_length=50,
        description="Product category"
    )
    
    # List with constraints
    tags: list[str] = Field(
        default_factory=list,  # IMPORTANT: Use default_factory for mutable defaults
        max_length=5,
        description="Product tags (max 5)"
    )
    
    # Multiple of constraint
    quantity_per_pack: int = Field(
        ...,
        multiple_of=5,
        ge=5,
        description="Items per pack (must be multiple of 5)"
    )


# ============================================================================
# SECTION 2: Custom Field Validators - Single Field Logic
# ============================================================================

class UserRegistration(BaseModel):
    """
    Demonstrates field validators for business logic.
    
    Real-world use case: User registration with validation
    """
    
    # Basic fields with Field() constraints
    username: str = Field(..., min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(..., min_length=12)
    age: int = Field(..., ge=13, le=120)
    
    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        Custom validator for username format.
        
        Why this is needed:
        - Field() can check length, but not character composition
        - Business rule: usernames must be alphanumeric
        - Normalization: convert to lowercase for consistency
        
        Args:
            cls: The model class (UserRegistration)
            v: The username value to validate
            
        Returns:
            str: The validated (and normalized) username
            
        Raises:
            ValueError: If username contains non-alphanumeric characters
        """
        if not v.isalnum():
            raise ValueError(
                "Username must contain only letters and numbers (no spaces or special characters)"
            )
        
        # Normalize to lowercase for consistent storage
        return v.lower()
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Enforce strong password requirements.
        
        Security considerations:
        - Length is checked by Field() (min 12 characters)
        - This validator checks character variety
        - Prevents common weak passwords
        
        Requirements:
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        
        Args:
            cls: The model class
            v: The password to validate
            
        Returns:
            str: The validated password (unchanged)
            
        Raises:
            ValueError: If password doesn't meet strength requirements
        """
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError(
                f"Password must contain at least one special character: {special_chars}"
            )
        
        # Password is strong enough
        return v


class BlogPostCreate(BaseModel):
    """
    Demonstrates data normalization with validators.
    
    Real-world use case: Blog post creation with automatic formatting
    """
    
    title: str = Field(..., min_length=5, max_length=200)
    content: str = Field(..., min_length=50)
    tags: list[str] = Field(default_factory=list, max_length=10)
    
    @field_validator("title")
    @classmethod
    def normalize_title(cls, v: str) -> str:
        """
        Normalize title format.
        
        Why normalize:
        - Consistent capitalization for display
        - Remove extra whitespace
        - Professional appearance
        
        Transformations:
        - Strip leading/trailing whitespace
        - Title case (Each Word Capitalized)
        """
        return v.strip().title()
    
    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        """
        Normalize and deduplicate tags.
        
        Business logic:
        - Tags should be lowercase for consistency
        - Remove duplicates
        - Strip whitespace
        - Remove empty tags
        
        Example:
            Input: ["Python", "python ", "PYTHON", "", "FastAPI"]
            Output: ["python", "fastapi"]
        """
        # Process each tag
        normalized = []
        seen = set()
        
        for tag in v:
            # Normalize: lowercase and strip
            clean_tag = tag.strip().lower()
            
            # Skip empty tags
            if not clean_tag:
                continue
            
            # Skip duplicates
            if clean_tag in seen:
                continue
            
            normalized.append(clean_tag)
            seen.add(clean_tag)
        
        return normalized


# ============================================================================
# SECTION 3: Model Validators - Cross-Field Logic
# ============================================================================

class PasswordReset(BaseModel):
    """
    Demonstrates model validator for cross-field validation.
    
    Real-world use case: Password reset confirmation
    """
    
    new_password: str = Field(..., min_length=12)
    confirm_password: str = Field(..., min_length=12)
    
    @model_validator(mode="after")
    def passwords_must_match(self) -> "PasswordReset":
        """
        Verify password confirmation matches.
        
        Why use model_validator instead of field_validator:
        - Need to compare TWO fields
        - Field validators only see ONE field
        - Model validators see the entire object (self)
        
        Args:
            self: The entire PasswordReset model instance
            
        Returns:
            PasswordReset: The validated model
            
        Raises:
            ValueError: If passwords don't match
        """
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        
        return self


class PaymentRequest(BaseModel):
    """
    Demonstrates conditional validation based on another field.
    
    Real-world use case: Payment processing with multiple methods
    """
    
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., description="'card' or 'bank_transfer'")
    
    # Card payment fields (optional)
    card_number: str | None = Field(None, min_length=13, max_length=19)
    card_expiry: str | None = Field(None, regex=r"^\d{2}/\d{2}$")
    cvv: str | None = Field(None, min_length=3, max_length=4)
    
    # Bank transfer fields (optional)
    bank_account: str | None = Field(None, min_length=8, max_length=20)
    routing_number: str | None = Field(None, min_length=9, max_length=9)
    
    @model_validator(mode="after")
    def validate_payment_details(self) -> "PaymentRequest":
        """
        Validate that required fields are provided based on payment method.
        
        Business logic:
        - If payment_method is 'card', card details are required
        - If payment_method is 'bank_transfer', bank details are required
        - Fields can be optional, but become required conditionally
        
        This pattern is common in:
        - Multi-step forms
        - Conditional business logic
        - Polymorphic data structures
        """
        if self.payment_method == "card":
            # Card payment requires card details
            if not self.card_number:
                raise ValueError("card_number is required for card payments")
            if not self.card_expiry:
                raise ValueError("card_expiry is required for card payments")
            if not self.cvv:
                raise ValueError("cvv is required for card payments")
        
        elif self.payment_method == "bank_transfer":
            # Bank transfer requires bank details
            if not self.bank_account:
                raise ValueError("bank_account is required for bank transfers")
            if not self.routing_number:
                raise ValueError("routing_number is required for bank transfers")
        
        else:
            # Invalid payment method
            raise ValueError(
                f"Invalid payment_method: {self.payment_method}. "
                "Must be 'card' or 'bank_transfer'"
            )
        
        return self


class DateRangeQuery(BaseModel):
    """
    Demonstrates validation of logical relationships.
    
    Real-world use case: Date range filtering in queries
    """
    
    start_date: datetime
    end_date: datetime
    
    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeQuery":
        """
        Ensure end_date is after start_date.
        
        Why this matters:
        - Prevents nonsensical queries
        - Catches user errors early
        - Database queries would return empty results anyway
        - Better UX with clear error message
        """
        if self.end_date <= self.start_date:
            raise ValueError(
                f"end_date ({self.end_date}) must be after start_date ({self.start_date})"
            )
        
        return self


# ============================================================================
# SECTION 4: Exception Handling Patterns
# ============================================================================

class OrderCreate(BaseModel):
    """Model for creating orders (for exception handling examples)."""
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., ge=1, le=100)
    customer_email: EmailStr


# Simulated database for demonstration
fake_products_db = {
    1: {"name": "Laptop", "stock": 10, "price": 999.99},
    2: {"name": "Mouse", "stock": 50, "price": 29.99},
    3: {"name": "Keyboard", "stock": 0, "price": 79.99},  # Out of stock
}


@app.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate):
    """
    Demonstrates exception handling in route logic.
    
    Exception handling patterns demonstrated:
    1. Not found (404) - Resource doesn't exist
    2. Conflict (409) - Business rule violation
    3. Bad request (400) - Invalid operation
    
    Note: Validation errors (422) are handled automatically by FastAPI
    """
    
    # Check if product exists
    product = fake_products_db.get(order.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {order.product_id} not found"
        )
    
    # Check stock availability
    if product["stock"] < order.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Insufficient stock",
                "requested": order.quantity,
                "available": product["stock"],
                "product_name": product["name"]
            }
        )
    
    # Business logic would go here
    # For demonstration, we'll just return success
    
    return {
        "order_id": 12345,
        "product": product["name"],
        "quantity": order.quantity,
        "total": product["price"] * order.quantity,
        "message": "Order created successfully"
    }


# ============================================================================
# SECTION 5: FastAPI Routes - Testing the Models
# ============================================================================

@app.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate):
    """
    Test endpoint for ProductCreate model.
    
    Try different validation scenarios:
    
    Valid request:
        {
            "name": "Wireless Mouse",
            "price": 29.99,
            "stock": 50,
            "quantity_per_pack": 10,
            "category": "Electronics",
            "tags": ["wireless", "mouse"]
        }
    
    Invalid scenarios to test:
    - name too short: "ab"
    - price negative: -10
    - price zero: 0
    - stock negative: -5
    - quantity_per_pack not multiple of 5: 7
    - too many tags: ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
    """
    return {
        "message": "Product created successfully",
        "product": product.model_dump()
    }


@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserRegistration):
    """
    Test endpoint for UserRegistration model.
    
    Try different validation scenarios:
    
    Valid request:
        {
            "username": "john123",
            "email": "john@example.com",
            "password": "StrongPass123!",
            "age": 25
        }
    
    Invalid scenarios to test:
    - username with spaces: "john doe"
    - username with special chars: "john@123"
    - weak password (no uppercase): "weakpassword123!"
    - weak password (no digit): "WeakPassword!"
    - weak password (no special): "WeakPassword123"
    - age too young: 12
    - age too old: 150
    """
    return {
        "message": "User registered successfully",
        "username": user.username,  # Will be lowercase
        "email": user.email
    }


@app.post("/blog/posts", status_code=status.HTTP_201_CREATED)
async def create_blog_post(post: BlogPostCreate):
    """
    Test endpoint for BlogPostCreate model.
    
    Test data normalization:
    
    Input:
        {
            "title": "  my first BLOG post  ",
            "content": "This is a long enough content for a blog post...",
            "tags": ["Python", "python ", "PYTHON", "", "FastAPI", "fastapi"]
        }
    
    Expected normalization:
    - title: "My First Blog Post" (title case, trimmed)
    - tags: ["python", "fastapi"] (lowercase, deduplicated, no empty)
    """
    return {
        "message": "Blog post created successfully",
        "post": post.model_dump()
    }


@app.post("/auth/reset-password")
async def reset_password(reset: PasswordReset):
    """
    Test endpoint for PasswordReset model.
    
    Valid request:
        {
            "new_password": "NewStrongPass123!",
            "confirm_password": "NewStrongPass123!"
        }
    
    Invalid scenario:
        {
            "new_password": "NewStrongPass123!",
            "confirm_password": "DifferentPass123!"
        }
    
    Should return: "Passwords do not match"
    """
    return {"message": "Password reset successfully"}


@app.post("/payments")
async def process_payment(payment: PaymentRequest):
    """
    Test endpoint for PaymentRequest model.
    
    Valid card payment:
        {
            "amount": 99.99,
            "payment_method": "card",
            "card_number": "4111111111111111",
            "card_expiry": "12/25",
            "cvv": "123"
        }
    
    Valid bank transfer:
        {
            "amount": 99.99,
            "payment_method": "bank_transfer",
            "bank_account": "123456789",
            "routing_number": "987654321"
        }
    
    Invalid scenarios:
    - Card payment without card_number
    - Bank transfer without routing_number
    - Invalid payment_method: "paypal"
    """
    return {
        "message": "Payment processed successfully",
        "amount": payment.amount,
        "method": payment.payment_method
    }


@app.post("/reports/date-range")
async def get_date_range_report(query: DateRangeQuery):
    """
    Test endpoint for DateRangeQuery model.
    
    Valid request:
        {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-12-31T23:59:59"
        }
    
    Invalid scenario (end before start):
        {
            "start_date": "2024-12-31T00:00:00",
            "end_date": "2024-01-01T00:00:00"
        }
    """
    return {
        "start_date": query.start_date,
        "end_date": query.end_date,
        "message": "Report generated successfully"
    }


# ============================================================================
# SECTION 6: Testing Examples
# ============================================================================

def demonstrate_validation():
    """
    Run this function to see validation in action.
    
    This demonstrates validation outside of FastAPI routes,
    showing how Pydantic models work independently.
    """
    print("\n" + "="*70)
    print("VALIDATION DEMONSTRATIONS")
    print("="*70)
    
    # Example 1: Successful validation
    print("\n1. SUCCESSFUL PRODUCT CREATION")
    print("-" * 70)
    try:
        product = ProductCreate(
            name="Wireless Mouse",
            price=29.99,
            stock=50,
            quantity_per_pack=10,
            category="Electronics",
            tags=["wireless", "mouse"]
        )
        print("✅ Product created successfully!")
        print(f"   Name: {product.name}")
        print(f"   Price: ${product.price}")
        print(f"   Stock: {product.stock}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 2: Invalid price (negative)
    print("\n2. INVALID PRICE (NEGATIVE)")
    print("-" * 70)
    try:
        product = ProductCreate(
            name="Invalid Product",
            price=-10.00,  # Invalid!
            stock=50,
            quantity_per_pack=10
        )
        print("✅ Product created")
    except Exception as e:
        print(f"❌ Validation failed (expected): {e}")
    
    # Example 3: Username validation and normalization
    print("\n3. USERNAME NORMALIZATION")
    print("-" * 70)
    try:
        user = UserRegistration(
            username="JohnDoe123",  # Mixed case
            email="john@example.com",
            password="StrongPass123!",
            age=25
        )
        print("✅ User created successfully!")
        print(f"   Input username: JohnDoe123")
        print(f"   Stored username: {user.username}")  # Will be lowercase
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 4: Weak password
    print("\n4. WEAK PASSWORD VALIDATION")
    print("-" * 70)
    try:
        user = UserRegistration(
            username="johndoe",
            email="john@example.com",
            password="weakpassword123",  # No uppercase, no special char
            age=25
        )
        print("✅ User created")
    except Exception as e:
        print(f"❌ Validation failed (expected): {e}")
    
    # Example 5: Tag normalization
    print("\n5. TAG NORMALIZATION AND DEDUPLICATION")
    print("-" * 70)
    try:
        post = BlogPostCreate(
            title="  my awesome POST  ",
            content="This is a long enough content for the blog post to be valid and meet minimum requirements.",
            tags=["Python", "python ", "PYTHON", "", "FastAPI", "fastapi"]
        )
        print("✅ Blog post created successfully!")
        print(f"   Original title: '  my awesome POST  '")
        print(f"   Normalized title: '{post.title}'")
        print(f"   Original tags: ['Python', 'python ', 'PYTHON', '', 'FastAPI', 'fastapi']")
        print(f"   Normalized tags: {post.tags}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Example 6: Password mismatch
    print("\n6. PASSWORD CONFIRMATION MISMATCH")
    print("-" * 70)
    try:
        reset = PasswordReset(
            new_password="StrongPass123!",
            confirm_password="DifferentPass123!"
        )
        print("✅ Password reset created")
    except Exception as e:
        print(f"❌ Validation failed (expected): {e}")
    
    # Example 7: Conditional validation
    print("\n7. CONDITIONAL VALIDATION (PAYMENT METHOD)")
    print("-" * 70)
    try:
        # This should fail - card payment without card details
        payment = PaymentRequest(
            amount=99.99,
            payment_method="card"
            # Missing card_number, card_expiry, cvv
        )
        print("✅ Payment created")
    except Exception as e:
        print(f"❌ Validation failed (expected): {e}")
    
    print("\n" + "="*70)
    print("DEMONSTRATIONS COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║         Day 3: Data Validation & Exception Handling              ║
    ║                    Practical Examples                            ║
    ╚══════════════════════════════════════════════════════════════════╝
    
    This file contains comprehensive examples for Day 3 topics:
    
    📚 WHAT'S INCLUDED:
    
    1️⃣  Field() Constraints (ProductCreate)
       - Numeric constraints (gt, ge, lt, le)
       - String constraints (min_length, max_length)
       - List constraints
       - Multiple of constraints
    
    2️⃣  Custom Field Validators
       - Username validation (UserRegistration)
       - Password strength (UserRegistration)
       - Data normalization (BlogPostCreate)
    
    3️⃣  Model Validators
       - Password confirmation (PasswordReset)
       - Conditional validation (PaymentRequest)
       - Date range validation (DateRangeQuery)
    
    4️⃣  Exception Handling
       - HTTPException patterns (create_order)
       - Status codes (404, 409, 422)
       - Error details
    
    🚀 HOW TO USE:
    
    Option 1 - Run demonstrations:
        python day3_validation_examples.py
    
    Option 2 - Start FastAPI server:
        uvicorn day3_validation_examples:app --reload
        
        Then visit:
        - http://localhost:8000/docs (Interactive API docs)
        - Test each endpoint with valid/invalid data
    
    Option 3 - Import for your own code:
        from day3_validation_examples import ProductCreate, UserRegistration
    
    📖 LEARNING PATH:
    
    1. Read the docstrings in each model
    2. Run the demonstrations to see validation in action
    3. Start the API and test with different inputs
    4. Try breaking each validator to understand constraints
    5. Modify validators to add your own business logic
    
    💡 KEY CONCEPTS TO UNDERSTAND:
    
    - Field() defines constraints (static rules)
    - @field_validator handles business logic (dynamic rules)
    - @model_validator handles cross-field logic
    - Validators run BEFORE route logic
    - FastAPI returns 422 for validation errors automatically
    - Always return the value from validators
    
    """)
    
    # Run demonstrations
    demonstrate_validation()
    
    print("""
    🎯 NEXT STEPS:
    
    1. Start the API server:
       uvicorn day3_validation_examples:app --reload
    
    2. Visit http://localhost:8000/docs
    
    3. Test each endpoint with:
       ✅ Valid data (should succeed)
       ❌ Invalid data (should fail with clear errors)
    
    4. Study the error responses - notice how detailed they are
    
    5. Try adding your own validators based on your needs
    
    Happy learning! 🚀
    """)
"""
Form Data - Complete Guide
===========================

Topics covered:
1. What form data is (backend perspective)
2. Basic form handling with Form()
3. Multiple form fields
4. Form validation
5. Optional form fields
6. Form data vs JSON comparison
7. When to use forms
8. Real-world form examples

Run: uvicorn 06_form_data:app --reload
Test: http://localhost:8000/docs
Test with client: Open clients/test_forms.html in browser

Important: Requires python-multipart
Install: pip install python-multipart
"""

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from typing import Optional

app = FastAPI(
    title="Form Data Guide",
    description="Complete guide to handling form data in FastAPI",
    version="1.0.0"
)

# =============================================================================
# 1. WHAT FORM DATA IS (Backend Perspective)
# =============================================================================
"""
Form data is used when clients submit data using HTML forms or systems
that do not send JSON.

Encoding types:
- application/x-www-form-urlencoded (default for forms)
  Format: key1=value1&key2=value2&key3=value3
  
- multipart/form-data (used when files are included)
  Format: Multi-part message with boundaries

Key points:
- Data is sent as KEY-VALUE pairs
- Values are always received as STRINGS first
- FastAPI converts them to target Python types
- Validation happens the same way as JSON

Typical sources:
- Browser <form> submissions
- Server-rendered apps
- Legacy systems
- OAuth / login callbacks
- File uploads + metadata
"""


# =============================================================================
# 2. BASIC FORM HANDLING
# =============================================================================

@app.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Basic form data handling.
    
    Expected Content-Type: application/x-www-form-urlencoded
    
    Example body:
    username=alice&password=secret
    
    How it works:
    - Form(...) marks parameter as coming from request body
    - ... means the field is required
    - Without Form, FastAPI treats it as query parameter
    
    Test with curl:
    curl -X POST http://localhost:8000/login \
      -d "username=alice&password=secret"
    
    Or with HTML form (see clients/test_forms.html)
    """
    # Validate credentials (simplified)
    if username == "alice" and password == "secret":
        return {
            "message": "Login successful",
            "username": username
        }
    
    return {
        "error": "Invalid credentials",
        "username": username
    }


@app.post("/contact")
async def contact_form(
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...)
):
    """
    Simple contact form.
    
    All fields are required (Form(...)).
    
    Test with curl:
    curl -X POST http://localhost:8000/contact \
      -d "name=Alice&email=alice@example.com&message=Hello"
    """
    return {
        "message": "Contact form submitted successfully",
        "data": {
            "name": name,
            "email": email,
            "message": message
        }
    }


# =============================================================================
# 3. MULTIPLE FORM FIELDS WITH VALIDATION
# =============================================================================

@app.post("/users/register")
async def register_user(
    username: str = Form(..., min_length=3, max_length=20),
    email: str = Form(...),
    password: str = Form(..., min_length=8),
    full_name: str = Form(...),
    age: int = Form(..., ge=18),
    terms_accepted: bool = Form(...)
):
    """
    Registration form with comprehensive validation.
    
    Validation rules:
    - username: 3-20 characters
    - email: Required (format not validated here, use Pydantic EmailStr for that)
    - password: Minimum 8 characters
    - full_name: Required
    - age: At least 18
    - terms_accepted: Required boolean
    
    All values arrive as strings → converted automatically.
    
    Boolean conversion:
    - "true", "on", "1" → True
    - "false", "off", "0" → False
    
    Test with curl:
    curl -X POST http://localhost:8000/users/register \
      -d "username=alice" \
      -d "email=alice@example.com" \
      -d "password=securepass123" \
      -d "full_name=Alice Smith" \
      -d "age=25" \
      -d "terms_accepted=true"
    """
    # In real app: hash password, store in database
    
    return {
        "message": "User registered successfully",
        "user": {
            "username": username,
            "email": email,
            "full_name": full_name,
            "age": age,
            "terms_accepted": terms_accepted
        },
        "note": "Password not returned for security"
    }


# =============================================================================
# 4. OPTIONAL FORM FIELDS
# =============================================================================

@app.post("/contact/advanced")
async def advanced_contact_form(
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form("General Inquiry"),  # Optional with default
    message: str = Form(...),
    phone: str | None = Form(None),  # Optional, no default
    newsletter: bool = Form(False)  # Optional boolean with default
):
    """
    Contact form with optional fields.
    
    Mix of required and optional:
    - name: Required
    - email: Required
    - subject: Optional with default "General Inquiry"
    - message: Required
    - phone: Optional, None if not provided
    - newsletter: Optional boolean, defaults to False
    
    Test with curl (minimal):
    curl -X POST http://localhost:8000/contact/advanced \
      -d "name=Alice" \
      -d "email=alice@example.com" \
      -d "message=Need help"
    
    Test with curl (full):
    curl -X POST http://localhost:8000/contact/advanced \
      -d "name=Alice" \
      -d "email=alice@example.com" \
      -d "subject=Support Request" \
      -d "message=Need help" \
      -d "phone=555-1234" \
      -d "newsletter=true"
    """
    contact_data = {
        "name": name,
        "email": email,
        "subject": subject,
        "message": message
    }
    
    # Only include optional fields if provided
    if phone:
        contact_data["phone"] = phone
    
    contact_data["newsletter_signup"] = newsletter
    
    return {
        "message": "Contact form submitted",
        "data": contact_data
    }


# =============================================================================
# 5. FORM DATA VS JSON COMPARISON
# =============================================================================

from pydantic import BaseModel

class UserJSON(BaseModel):
    """Pydantic model for JSON requests"""
    username: str
    email: str
    full_name: str


@app.post("/users/json")
async def create_user_json(user: UserJSON):
    """
    JSON request (typical for APIs).
    
    Content-Type: application/json
    
    Body:
    {
        "username": "alice",
        "email": "alice@example.com",
        "full_name": "Alice Smith"
    }
    
    Advantages:
    - Structured data
    - Supports nested objects
    - Preferred for APIs
    - Used by frontend frameworks
    """
    return {
        "message": "User created (JSON)",
        "user": user
    }


@app.post("/users/form")
async def create_user_form(
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...)
):
    """
    Form data request (typical for HTML forms).
    
    Content-Type: application/x-www-form-urlencoded
    
    Body:
    username=alice&email=alice@example.com&full_name=Alice Smith
    
    Advantages:
    - Works with HTML forms
    - Simpler for server-rendered apps
    - Handles file uploads (with multipart/form-data)
    - Legacy system compatibility
    
    Disadvantages:
    - Flat structure (no nesting)
    - Less expressive than JSON
    """
    return {
        "message": "User created (Form)",
        "user": {
            "username": username,
            "email": email,
            "full_name": full_name
        }
    }


# =============================================================================
# 6. WHEN TO USE FORMS
# =============================================================================
"""
Use FORM DATA when:
- Accepting data from <form> submissions
- Supporting server-rendered apps
- Handling file uploads
- Integrating with legacy systems
- OAuth callbacks

Use JSON when:
- Building APIs
- Using React / Vue / mobile clients
- Sending nested or complex data
- Versioning request schemas

Backend rule: Prefer JSON unless you explicitly need form support.
"""


# =============================================================================
# 7. REAL-WORLD FORM EXAMPLES
# =============================================================================

@app.post("/feedback")
async def submit_feedback(
    rating: int = Form(..., ge=1, le=5),
    category: str = Form(...),
    comment: str = Form(..., min_length=10, max_length=500),
    email: str | None = Form(None),
    follow_up: bool = Form(False)
):
    """
    Product feedback form.
    
    Real-world validation:
    - rating: 1-5 stars
    - category: Required
    - comment: 10-500 characters
    - email: Optional (for follow-up)
    - follow_up: Whether user wants follow-up
    
    Test with curl:
    curl -X POST http://localhost:8000/feedback \
      -d "rating=5" \
      -d "category=Product Quality" \
      -d "comment=Great product, very satisfied with the purchase" \
      -d "email=alice@example.com" \
      -d "follow_up=true"
    """
    feedback = {
        "rating": rating,
        "category": category,
        "comment": comment,
        "follow_up": follow_up
    }
    
    if email:
        feedback["email"] = email
    
    return {
        "message": "Feedback submitted successfully",
        "feedback": feedback,
        "note": "Thank you for your feedback!"
    }


@app.post("/newsletter/subscribe")
async def subscribe_newsletter(
    email: str = Form(...),
    name: str = Form(...),
    interests: str = Form("general"),  # Comma-separated interests
    frequency: str = Form("weekly")
):
    """
    Newsletter subscription form.
    
    Test with curl:
    curl -X POST http://localhost:8000/newsletter/subscribe \
      -d "email=alice@example.com" \
      -d "name=Alice" \
      -d "interests=tech,news" \
      -d "frequency=daily"
    """
    # Parse interests (in real app, use proper list handling)
    interest_list = [i.strip() for i in interests.split(",")]
    
    return {
        "message": "Subscribed to newsletter",
        "subscription": {
            "email": email,
            "name": name,
            "interests": interest_list,
            "frequency": frequency
        }
    }


@app.post("/job/apply")
async def apply_for_job(
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    position: str = Form(...),
    experience_years: int = Form(..., ge=0),
    cover_letter: str = Form(..., min_length=50),
    linkedin_url: str | None = Form(None),
    available_start: str | None = Form(None)
):
    """
    Job application form.
    
    Real-world scenario: Job application without resume upload
    (see 07_file_uploads.py for version with file upload)
    
    Test with curl:
    curl -X POST http://localhost:8000/job/apply \
      -d "full_name=Alice Smith" \
      -d "email=alice@example.com" \
      -d "phone=555-1234" \
      -d "position=Backend Developer" \
      -d "experience_years=5" \
      -d "cover_letter=I am excited to apply for this position because..." \
      -d "linkedin_url=https://linkedin.com/in/alice" \
      -d "available_start=2025-02-01"
    """
    application = {
        "applicant": {
            "full_name": full_name,
            "email": email,
            "phone": phone
        },
        "position": position,
        "experience_years": experience_years,
        "cover_letter": cover_letter,
        "linkedin_url": linkedin_url,
        "available_start": available_start
    }
    
    return {
        "message": "Application submitted successfully",
        "application": application,
        "next_steps": "We will review your application and contact you soon"
    }


# =============================================================================
# 8. TESTING INTERFACE
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    HTML interface for testing forms.
    
    Opens in browser at http://localhost:8000/
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Form Testing</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            form { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
            label { display: block; margin: 10px 0 5px 0; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 8px; margin-bottom: 10px; }
            button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .output { background: #fff; padding: 15px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
            pre { background: #f8f8f8; padding: 10px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Form Testing Interface</h1>
        
        <h2>Login Form</h2>
        <form id="loginForm">
            <label>Username:</label>
            <input type="text" name="username" required>
            
            <label>Password:</label>
            <input type="password" name="password" required>
            
            <button type="submit">Login</button>
        </form>
        
        <h2>Registration Form</h2>
        <form id="registerForm">
            <label>Username:</label>
            <input type="text" name="username" minlength="3" required>
            
            <label>Email:</label>
            <input type="email" name="email" required>
            
            <label>Password:</label>
            <input type="password" name="password" minlength="8" required>
            
            <label>Full Name:</label>
            <input type="text" name="full_name" required>
            
            <label>Age:</label>
            <input type="number" name="age" min="18" required>
            
            <label>
                <input type="checkbox" name="terms_accepted" value="true" required>
                I accept the terms and conditions
            </label>
            
            <button type="submit">Register</button>
        </form>
        
        <h2>Contact Form</h2>
        <form id="contactForm">
            <label>Name:</label>
            <input type="text" name="name" required>
            
            <label>Email:</label>
            <input type="email" name="email" required>
            
            <label>Subject:</label>
            <input type="text" name="subject" value="General Inquiry">
            
            <label>Message:</label>
            <textarea name="message" rows="5" required></textarea>
            
            <label>Phone (optional):</label>
            <input type="tel" name="phone">
            
            <label>
                <input type="checkbox" name="newsletter" value="true">
                Subscribe to newsletter
            </label>
            
            <button type="submit">Submit</button>
        </form>
        
        <div class="output" id="output">
            <p>Submit a form above to see the response</p>
        </div>
        
        <script>
            const output = document.getElementById('output');
            
            // Login form
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/login', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                output.innerHTML = `<h3>Login Response:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
            
            // Register form
            document.getElementById('registerForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/users/register', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                output.innerHTML = `<h3>Registration Response:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
            
            // Contact form
            document.getElementById('contactForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const response = await fetch('/contact/advanced', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                output.innerHTML = `<h3>Contact Response:</h3><pre>${JSON.stringify(data, null, 2)}</pre>`;
            });
        </script>
    </body>
    </html>
    """


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing Form Data:

1. Using Browser:
   - Visit http://localhost:8000/
   - Use built-in HTML forms
   - See form submission and validation

2. Using curl:
   curl -X POST http://localhost:8000/endpoint \
     -d "field1=value1" \
     -d "field2=value2"
   
   # Or URL-encoded in one line
   curl -X POST http://localhost:8000/endpoint \
     -d "field1=value1&field2=value2"

3. Using httpie:
   http --form POST localhost:8000/endpoint \
     field1=value1 \
     field2=value2

4. Using Python requests:
   response = requests.post(
       "http://localhost:8000/endpoint",
       data={"field1": "value1", "field2": "value2"}
   )

Common Mistakes:
- Forgetting Form() → becomes query parameter
- Using Form with GET requests
- Expecting nested data (forms are flat)
- Not installing python-multipart

Backend Best Practices:
- Use Form() explicitly
- Install python-multipart
- Validate aggressively (lengths, ranges, patterns)
- Prefer JSON for APIs
- Use forms for HTML form submissions
- Treat form input as untrusted user data
- Sanitize and validate everything
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

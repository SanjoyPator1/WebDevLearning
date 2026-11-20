# Day 2: Advanced Security Headers & CORS

**Date**: Week 4, Day 2  
**Phase**: 2 - FastAPI Mastery  
**Topic**: Advanced Security Headers and Cross-Origin Resource Sharing

---

## Table of Contents

1. [Advanced Security Headers](#advanced-security-headers)
2. [Implementing All Security Headers in FastAPI](#implementing-all-security-headers-in-fastapi)
3. [CORS (Cross-Origin Resource Sharing)](#cors-cross-origin-resource-sharing)
4. [CORS Request Flow](#cors-request-flow)
5. [CORS Headers Explained](#cors-headers-explained)
6. [CORS Middleware in FastAPI](#cors-middleware-in-fastapi)
7. [CORS Common Scenarios](#cors-common-scenarios)
8. [CORS Troubleshooting](#cors-troubleshooting)
9. [Complete Practical Example](#complete-practical-example)
10. [Security Headers Testing Tools](#security-headers-testing-tools)
11. [Common Pitfalls](#common-pitfalls)
12. [Key Takeaways](#key-takeaways)
13. [Practice Exercises](#practice-exercises)

---

## Advanced Security Headers

Yesterday we covered the basics of Content-Security-Policy, X-Frame-Options, and X-Content-Type-Options. Today we'll explore additional security headers that provide even more protection against various attack vectors.

### Strict-Transport-Security (HSTS)

#### What is HSTS?

HTTP Strict Transport Security (HSTS) is a security mechanism that tells browsers to only communicate with your site over HTTPS, never HTTP. Once a browser sees the HSTS header, it will refuse to connect via HTTP for the specified duration, even if the user types `http://` in the address bar.

**The problem HSTS solves:**

```python
# Scenario without HSTS:
# 1. User types: example.com (no protocol)
# 2. Browser tries: http://example.com
# 3. Attacker intercepts HTTP request (man-in-the-middle)
# 4. Attacker serves fake page or steals credentials
# 5. Even with redirect to HTTPS, damage is done in first request

# With HSTS:
# 1. User types: example.com
# 2. Browser remembers HSTS policy from previous visit
# 3. Browser automatically uses: https://example.com
# 4. No HTTP request is ever made
# 5. Attacker cannot intercept
```

#### HSTS Directives

The HSTS header has three directives:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**1. max-age (required)**

Specifies how long (in seconds) the browser should remember to only use HTTPS.

```python
# One year (recommended)
max-age=31536000  # 365 days * 24 hours * 60 minutes * 60 seconds

# Two years (for preload list)
max-age=63072000  # 730 days

# Six months
max-age=15768000  # 182.5 days
```

**Choosing max-age:**

- Start with short duration during testing (e.g., 300 seconds = 5 minutes)
- Increase gradually (1 day → 1 week → 1 month)
- Production: 1-2 years
- Preload requirement: minimum 1 year (31536000)

**What happens during max-age:**

```python
# Day 1: Browser receives HSTS header
# Browser stores: "example.com must use HTTPS until Dec 31, 2025"

# Day 100: User types http://example.com
# Browser: "I remember HSTS policy, automatically use HTTPS"
# Result: https://example.com (no HTTP request made)

# After max-age expires (Dec 31, 2025):
# Browser: "HSTS policy expired, need to check again"
# Allows HTTP request (to get new HSTS header)
```

**2. includeSubDomains (optional)**

Applies the HSTS policy to all subdomains.

```python
# Without includeSubDomains:
# example.com → HTTPS only
# api.example.com → Can use HTTP (not protected)
# www.example.com → Can use HTTP (not protected)

# With includeSubDomains:
# example.com → HTTPS only
# api.example.com → HTTPS only
# www.example.com → HTTPS only
# any.subdomain.example.com → HTTPS only
```

**Warning about includeSubDomains:**

```python
# Before enabling, ensure ALL subdomains support HTTPS:
# ✓ https://www.example.com - works
# ✓ https://api.example.com - works
# ✗ http://old.example.com - BROKEN (doesn't have SSL)

# If old.example.com doesn't have SSL certificate:
# Users cannot access it after includeSubDomains is enabled
# They'll see: "This site can't provide a secure connection"
```

**3. preload (optional)**

Signals that you want to be included in the browser's HSTS preload list.

```python
# Normal HSTS: Protection starts AFTER first visit
# Visit 1: http://example.com → Could be intercepted
# Visit 2+: https://example.com → Protected

# HSTS Preload: Protection from FIRST visit
# Visit 1: https://example.com → Protected (browser has hardcoded list)
# All visits: https://example.com → Protected
```

#### HSTS Preload List

The HSTS preload list is a list of sites hardcoded into browsers. Sites on this list are automatically accessed via HTTPS, even on the first visit.

**How to get on the preload list:**

1. Serve a valid certificate
2. Redirect from HTTP to HTTPS (same host)
3. Serve HSTS header on base domain with:
   - `max-age` of at least 31536000 (1 year)
   - `includeSubDomains` directive
   - `preload` directive
4. Submit your domain at: https://hstspreload.org/

**Checking preload status:**

```bash
# Check if domain is preloaded
curl -I https://example.com | grep -i strict-transport

# Expected:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

**Warning about preload:**

```python
# HSTS preload is essentially permanent
# Removal from preload list takes months
# Only enable if you're 100% certain about HTTPS on ALL subdomains

# Scenario to avoid:
# Day 1: Submit example.com to preload list
# Day 30: Realize internal.example.com cannot get SSL certificate
# Day 60: Want to remove from preload
# Day 365+: Still in browsers (preload lists update slowly)
```

#### HSTS Implementation

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class HSTSMiddleware(BaseHTTPMiddleware):
    """
    HTTP Strict Transport Security middleware.

    Forces browsers to only communicate via HTTPS for specified duration.
    Once set, browsers will refuse HTTP connections even if user types http://
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Only set HSTS on HTTPS connections
        # Setting HSTS over HTTP is ignored by browsers
        if request.url.scheme == "https" or \
           request.headers.get("x-forwarded-proto") == "https":

            # Production configuration
            response.headers["Strict-Transport-Security"] = \
                "max-age=31536000; includeSubDomains; preload"

            # Development configuration (shorter duration)
            # response.headers["Strict-Transport-Security"] = "max-age=300"

        return response

app.add_middleware(HSTSMiddleware)
```

**Progressive rollout strategy:**

```python
# Week 1: Test with short duration
"Strict-Transport-Security": "max-age=300"  # 5 minutes

# Week 2: Increase to 1 day
"Strict-Transport-Security": "max-age=86400"  # 24 hours

# Week 3: Increase to 1 week
"Strict-Transport-Security": "max-age=604800"  # 7 days

# Week 4: Increase to 1 month
"Strict-Transport-Security": "max-age=2592000"  # 30 days

# Production: 1 year
"Strict-Transport-Security": "max-age=31536000"

# Production with subdomains: 1 year + includeSubDomains
"Strict-Transport-Security": "max-age=31536000; includeSubDomains"

# Submit to preload list: Add preload directive
"Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload"
```

### Referrer-Policy

#### What is Referrer Policy?

When a user clicks a link or loads a resource, browsers send a `Referer` header (note the misspelling - it's in the HTTP spec) that tells the destination site where the user came from. Referrer-Policy controls how much information is included in this header.

**The referer header:**

```python
# User is on: https://example.com/account/settings?user=alice
# User clicks link to: https://othersite.com/article

# Without Referrer-Policy:
# Browser sends:
# Referer: https://example.com/account/settings?user=alice
# ^ Full URL including path and query parameters

# Problem: Sensitive information leaked!
# - User is on account settings page
# - Username in URL
# - Other site now knows this
```

#### Referrer-Policy Values

```python
# 1. no-referrer
# Never send referer header
Referer: (not sent)

# 2. no-referrer-when-downgrade (default)
# Send referer to same security level or higher
# HTTPS → HTTPS: Send full URL
# HTTP → HTTP: Send full URL
# HTTPS → HTTP: Don't send (downgrade)
Referer: https://example.com/page

# 3. origin
# Send only origin (protocol + domain)
Referer: https://example.com

# 4. origin-when-cross-origin
# Same origin: Send full URL
# Cross origin: Send only origin
Same origin: Referer: https://example.com/page/article
Cross origin: Referer: https://example.com

# 5. same-origin
# Only send referer for same-origin requests
Same origin: Referer: https://example.com/page
Cross origin: (not sent)

# 6. strict-origin
# Send origin, but not on HTTPS → HTTP downgrade
HTTPS → HTTPS: Referer: https://example.com
HTTPS → HTTP: (not sent)

# 7. strict-origin-when-cross-origin (recommended)
# Same origin: Send full URL
# Cross origin HTTPS: Send origin only
# HTTPS → HTTP: Don't send
Same origin: Referer: https://example.com/page
Cross origin: Referer: https://example.com
Downgrade: (not sent)

# 8. unsafe-url (not recommended)
# Always send full URL (even on downgrades)
Referer: https://example.com/page?secret=123
```

#### Choosing the Right Policy

```python
# Best for privacy (strict)
"Referrer-Policy": "no-referrer"
# Pros: Maximum privacy
# Cons: Breaks analytics, anti-fraud

# Recommended for most sites
"Referrer-Policy": "strict-origin-when-cross-origin"
# Pros: Good privacy, maintains analytics
# Cons: Some information shared

# For internal APIs
"Referrer-Policy": "same-origin"
# Pros: No external leakage
# Cons: Blocks legitimate cross-origin requests

# Avoid
"Referrer-Policy": "unsafe-url"
# Shares full URL including query params
# Can leak sensitive data
```

#### Real-world Example

```python
# Scenario: Banking site
# URL: https://bank.com/transfer?amount=10000&to=account123

# With no policy (default):
# User clicks external link
# External site receives: Referer: https://bank.com/transfer?amount=10000&to=account123
# ^ Sensitive transaction data leaked!

# With strict-origin-when-cross-origin:
# User clicks external link
# External site receives: Referer: https://bank.com
# ^ Only domain leaked, transaction data protected

# With no-referrer:
# User clicks external link
# External site receives: (no referer)
# ^ Complete privacy, but analytics don't work
```

#### Implementation

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class ReferrerPolicyMiddleware(BaseHTTPMiddleware):
    """
    Referrer Policy middleware.

    Controls what information is sent in the Referer header when
    users navigate away from your site or load external resources.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Recommended: Balance privacy and functionality
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Alternative options:
        # response.headers["Referrer-Policy"] = "no-referrer"  # Maximum privacy
        # response.headers["Referrer-Policy"] = "same-origin"  # Internal only

        return response

app.add_middleware(ReferrerPolicyMiddleware)
```

### Permissions-Policy (formerly Feature-Policy)

#### What is Permissions Policy?

Permissions-Policy controls which browser features and APIs can be used by your site and embedded iframes. This prevents malicious or compromised third-party scripts from accessing powerful browser features.

**The problem it solves:**

```python
# Scenario: You embed a third-party widget
<iframe src="https://widget.com/chat"></iframe>

# Without Permissions-Policy:
# widget.com can:
# - Access camera (if user grants)
# - Access microphone
# - Get geolocation
# - Use payment APIs
# - Access USB devices
# - And more...

# With Permissions-Policy:
# You specify: "This iframe can only use X, Y, Z"
# Everything else is blocked
```

#### Permission Directives

```python
# Syntax:
# Permissions-Policy: feature=(allowlist)

# Common features:
camera           # Camera access
microphone       # Microphone access
geolocation      # Location API
payment          # Payment Request API
usb              # WebUSB API
accelerometer    # Accelerometer
gyroscope        # Gyroscope
magnetometer     # Magnetometer
fullscreen       # Fullscreen API
picture-in-picture  # PiP API
```

#### Allowlist Values

```python
# self - Allow for same origin only
"Permissions-Policy": "camera=(self)"
# Your domain can use camera, iframes cannot

# src - Allow for iframe's own origin
"Permissions-Policy": "camera=(src)"
# Iframe can use camera for its own origin

# none - Block completely
"Permissions-Policy": "camera=()"
# No one can use camera

# Specific origins
"Permissions-Policy": "camera=(self \"https://trusted.com\")"
# You and trusted.com can use camera

# All origins (not recommended)
"Permissions-Policy": "camera=*"
# Anyone can use camera
```

#### Common Configurations

```python
# Strict policy (recommended for most sites)
permissions_policy = (
    "camera=(), "           # Block camera
    "microphone=(), "       # Block microphone
    "geolocation=(), "      # Block geolocation
    "payment=()"            # Block payment API
)

# Allow camera/mic for video chat feature
permissions_policy = (
    "camera=(self), "       # Allow for your site
    "microphone=(self), "   # Allow for your site
    "geolocation=(), "      # Block geolocation
    "payment=()"            # Block payment
)

# Allow geolocation for maps
permissions_policy = (
    "camera=(), "
    "microphone=(), "
    "geolocation=(self \"https://maps.googleapis.com\"), "
    "payment=()"
)

# Allow everything (not recommended)
permissions_policy = (
    "camera=*, "
    "microphone=*, "
    "geolocation=*, "
    "payment=*"
)
```

#### Implementation

```python
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

class PermissionsPolicyMiddleware(BaseHTTPMiddleware):
    """
    Permissions Policy middleware.

    Controls which browser features and APIs can be used by your site
    and any embedded content (iframes).
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Restrictive policy (recommended)
        permissions_policy = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=(), "
            "usb=(), "
            "accelerometer=(), "
            "gyroscope=(), "
            "magnetometer=()"
        )

        response.headers["Permissions-Policy"] = permissions_policy

        return response

app.add_middleware(PermissionsPolicyMiddleware)
```

#### Real-world Example

```python
# Video conferencing site
# Needs: camera, microphone
# Doesn't need: geolocation, payment, USB

permissions_policy = (
    "camera=(self), "        # Allow camera for video
    "microphone=(self), "    # Allow microphone for audio
    "geolocation=(), "       # Block location (not needed)
    "payment=(), "           # Block payment (not needed)
    "usb=()"                 # Block USB (security risk)
)

# E-commerce site
# Needs: payment
# Doesn't need: camera, microphone, geolocation

permissions_policy = (
    "camera=(), "            # Block camera (not needed)
    "microphone=(), "        # Block microphone (not needed)
    "geolocation=(), "       # Block location (not needed)
    "payment=(self)"         # Allow payment API
)

# News/blog site
# Doesn't need any special permissions

permissions_policy = (
    "camera=(), "            # Block everything
    "microphone=(), "
    "geolocation=(), "
    "payment=(), "
    "usb=()"
)
```

### X-XSS-Protection

#### What is X-XSS-Protection?

X-XSS-Protection was a header that enabled browser's built-in XSS filter. However, it's now **deprecated** and should not be used.

**Historical context:**

```python
# Old approach (deprecated):
"X-XSS-Protection": "1; mode=block"

# Modern approach (use instead):
"Content-Security-Policy": "default-src 'self'"
```

**Why it's deprecated:**

1. Can introduce security vulnerabilities
2. Inconsistent across browsers
3. CSP provides better protection
4. Can be bypassed easily

**What to do instead:**

```python
# Don't use X-XSS-Protection
# response.headers["X-XSS-Protection"] = "1; mode=block"  # Deprecated

# Use Content-Security-Policy instead
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self'; "
    "object-src 'none'"
)
```

**For completeness (if you must):**

```python
# If you need to support very old browsers:
"X-XSS-Protection": "0"  # Disable the filter (prevents vulnerabilities)

# Never use:
# "X-XSS-Protection": "1; mode=block"  # Can introduce vulnerabilities
```

---

## Implementing All Security Headers in FastAPI

Now let's combine all security headers into a comprehensive middleware that provides defense-in-depth.

### Comprehensive Security Middleware

```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import os

app = FastAPI(
    title="Secure FastAPI Application",
    description="Production-ready security headers",
    version="1.0.0"
)

class ComprehensiveSecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security headers middleware.

    Implements multiple layers of security headers to protect against:
    - XSS (Cross-Site Scripting)
    - Clickjacking
    - MIME sniffing
    - Information leakage
    - Unauthorized feature access

    Best Practices:
    - Start with restrictive policies
    - Test thoroughly before production
    - Monitor for CSP violations
    - Update regularly
    """

    def __init__(self, app, environment: str = "production"):
        super().__init__(app)
        self.environment = environment
        self.is_production = environment == "production"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ):
        response = await call_next(request)

        # Only set HSTS on HTTPS connections
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https"
        )

        # Strict-Transport-Security (HSTS)
        # Forces HTTPS for all future requests
        if is_https:
            if self.is_production:
                # Production: 1 year with subdomains
                response.headers["Strict-Transport-Security"] = \
                    "max-age=31536000; includeSubDomains; preload"
            else:
                # Development: 5 minutes (easy to undo)
                response.headers["Strict-Transport-Security"] = \
                    "max-age=300"

        # Content-Security-Policy
        # Restricts resource loading to prevent XSS
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com",
            "font-src 'self' fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' api.example.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "object-src 'none'",
            "upgrade-insecure-requests"
        ]

        # Different CSP for development (more permissive)
        if not self.is_production:
            csp_directives = [
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "img-src * data:",
                "frame-ancestors 'none'"
            ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # X-Frame-Options
        # Prevents clickjacking by blocking iframes
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        # Prevents MIME sniffing attacks
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy
        # Controls information sent in Referer header
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        # Restricts access to browser features
        permissions = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "payment=()",
            "usb=()",
            "accelerometer=()",
            "gyroscope=()",
            "magnetometer=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)

        # Remove server header (don't reveal technology)
        response.headers["Server"] = "Secure"

        # X-Content-Type-Options
        # Prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Cache-Control for sensitive data
        # Prevent caching of sensitive responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = \
                "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

# Initialize with environment
environment = os.getenv("ENVIRONMENT", "development")
app.add_middleware(ComprehensiveSecurityMiddleware, environment=environment)

@app.get("/")
async def root():
    """Root endpoint with full security headers"""
    return {
        "message": "Secure API",
        "security": {
            "headers": "enabled",
            "hsts": "active",
            "csp": "enforced"
        }
    }

@app.get("/headers")
async def show_headers(request: Request):
    """Display security headers for debugging"""
    return {
        "request_headers": dict(request.headers),
        "security_status": {
            "https": request.url.scheme == "https" or
                     request.headers.get("x-forwarded-proto") == "https",
            "environment": environment
        }
    }
```

### Configuration-Based Approach

For more flexibility, use a configuration-based approach:

```python
from pydantic import BaseModel
from typing import List, Optional

class SecurityConfig(BaseModel):
    """
    Security headers configuration.

    Allows customization of security headers per environment
    or deployment scenario.
    """

    # HSTS Configuration
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False

    # CSP Configuration
    csp_default_src: List[str] = ["'self'"]
    csp_script_src: List[str] = ["'self'"]
    csp_style_src: List[str] = ["'self'"]
    csp_img_src: List[str] = ["'self'", "data:", "https:"]
    csp_font_src: List[str] = ["'self'"]
    csp_connect_src: List[str] = ["'self'"]
    csp_frame_ancestors: List[str] = ["'none'"]

    # Frame Options
    x_frame_options: str = "DENY"  # or "SAMEORIGIN"

    # Referrer Policy
    referrer_policy: str = "strict-origin-when-cross-origin"

    # Permissions Policy
    camera_policy: str = "()"
    microphone_policy: str = "()"
    geolocation_policy: str = "()"
    payment_policy: str = "()"

# Development configuration
dev_config = SecurityConfig(
    hsts_max_age=300,  # 5 minutes
    hsts_include_subdomains=False,
    csp_script_src=["'self'", "'unsafe-inline'", "'unsafe-eval'"],
    csp_style_src=["'self'", "'unsafe-inline'"]
)

# Production configuration
prod_config = SecurityConfig(
    hsts_max_age=31536000,  # 1 year
    hsts_include_subdomains=True,
    hsts_preload=True,
    csp_script_src=["'self'", "cdn.jsdelivr.net"],
    csp_style_src=["'self'", "fonts.googleapis.com"]
)

class ConfigurableSecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware with configuration support"""

    def __init__(self, app, config: SecurityConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Build HSTS header from config
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https"
        )

        if is_https:
            hsts_parts = [f"max-age={self.config.hsts_max_age}"]
            if self.config.hsts_include_subdomains:
                hsts_parts.append("includeSubDomains")
            if self.config.hsts_preload:
                hsts_parts.append("preload")

            response.headers["Strict-Transport-Security"] = "; ".join(hsts_parts)

        # Build CSP header from config
        csp_parts = [
            f"default-src {' '.join(self.config.csp_default_src)}",
            f"script-src {' '.join(self.config.csp_script_src)}",
            f"style-src {' '.join(self.config.csp_style_src)}",
            f"img-src {' '.join(self.config.csp_img_src)}",
            f"font-src {' '.join(self.config.csp_font_src)}",
            f"connect-src {' '.join(self.config.csp_connect_src)}",
            f"frame-ancestors {' '.join(self.config.csp_frame_ancestors)}"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_parts)

        # Other headers from config
        response.headers["X-Frame-Options"] = self.config.x_frame_options
        response.headers["Referrer-Policy"] = self.config.referrer_policy

        permissions = [
            f"camera={self.config.camera_policy}",
            f"microphone={self.config.microphone_policy}",
            f"geolocation={self.config.geolocation_policy}",
            f"payment={self.config.payment_policy}"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)

        # Standard headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Server"] = "Secure"

        return response

# Use appropriate config based on environment
config = prod_config if os.getenv("ENVIRONMENT") == "production" else dev_config
app.add_middleware(ConfigurableSecurityMiddleware, config=config)
```

---

## CORS (Cross-Origin Resource Sharing)

CORS is one of the most important and frequently misunderstood security mechanisms in web development. Let's explore it in depth.

### What is CORS?

CORS (Cross-Origin Resource Sharing) is a security feature implemented by web browsers that controls how web pages from one origin can request resources from another origin.

**Why CORS exists:**

```python
# Without CORS:
# Evil.com could do this:
<script>
fetch('https://yourbank.com/api/balance')
  .then(response => response.json())
  .then(data => {
    // Evil.com now has your bank balance!
    sendToAttacker(data);
  });
</script>

# With CORS:
# Browser blocks the request because yourbank.com and evil.com
# are different origins, and yourbank.com hasn't given permission
```

### Understanding Origins

An origin consists of three parts:

```python
https://api.example.com:443/path
│      │   │          │    │
scheme  │   domain     port  path (not part of origin)
        │
    subdomain

# Same Origin Examples:
origin1 = "https://example.com:443"
origin2 = "https://example.com:443"  # Same origin ✓

# Different Origin Examples (any difference = different origin):
origin1 = "https://example.com"
origin2 = "http://example.com"      # Different scheme ✗
origin3 = "https://api.example.com"  # Different subdomain ✗
origin4 = "https://example.com:8000" # Different port ✗
origin5 = "https://example.org"      # Different domain ✗
```

### Same-Origin Policy

The Same-Origin Policy (SOP) is a critical security mechanism that restricts how documents or scripts from one origin can interact with resources from another origin.

```python
# Page loaded from: https://example.com

# Same-origin requests (allowed by default):
fetch('https://example.com/api/data')           # ✓ Same origin
fetch('https://example.com:443/api/data')       # ✓ Same origin (443 is default)
fetch('https://example.com/different/path')     # ✓ Path doesn't matter

# Cross-origin requests (blocked by default):
fetch('http://example.com/api/data')            # ✗ Different scheme
fetch('https://api.example.com/data')           # ✗ Different subdomain
fetch('https://example.com:8000/data')          # ✗ Different port
fetch('https://other.com/data')                 # ✗ Different domain
```

**What SOP blocks:**

```python
# JavaScript running on https://example.com cannot:
# 1. Read responses from other origins
fetch('https://other.com/api/data')  # Blocked

# 2. Read cookies from other origins
document.cookie  # Can only see same-origin cookies

# 3. Access DOM of other origins
let iframe = document.getElementById('other-site-frame');
iframe.contentDocument  # Blocked if different origin

# 4. Make AJAX requests to other origins (without CORS)
$.ajax({url: 'https://other.com/api'})  # Blocked
```

**What SOP allows:**

```python
# These are allowed (but limited):
# 1. Images
<img src="https://other.com/image.jpg">  # Allowed (but can't read pixels)

# 2. Scripts
<script src="https://cdn.com/lib.js"></script>  # Allowed (executes in your context)

# 3. Stylesheets
<link rel="stylesheet" href="https://other.com/style.css">  # Allowed

# 4. Iframes (with restrictions)
<iframe src="https://other.com"></iframe>  # Allowed (but can't access content)

# 5. Forms
<form action="https://other.com/submit" method="POST">  # Allowed
```

### CORS Purpose

CORS provides a controlled way to relax the Same-Origin Policy, allowing legitimate cross-origin requests while maintaining security.

```python
# Without CORS:
# Frontend: https://myapp.com
# API: https://api.myapp.com
# Result: Frontend can't call API (different subdomain)

# With CORS:
# API sends: Access-Control-Allow-Origin: https://myapp.com
# Result: Browser allows the request
```

---

## CORS Request Flow

CORS requests come in two types: simple requests and preflight requests.

### Simple Requests

Simple requests are sent directly without a preflight check.

**Requirements for a simple request:**

1. **Method** must be one of:

   - GET
   - HEAD
   - POST

2. **Headers** can only be:

   - Accept
   - Accept-Language
   - Content-Language
   - Content-Type (with limitations)
   - Range (simple range)

3. **Content-Type** (if present) must be one of:
   - application/x-www-form-urlencoded
   - multipart/form-data
   - text/plain

```python
# Example: Simple GET request
fetch('https://api.example.com/data', {
    method: 'GET',
    headers: {
        'Accept': 'application/json'  # Only simple headers
    }
})

# Browser sends:
GET /data HTTP/1.1
Host: api.example.com
Origin: https://myapp.com
Accept: application/json

# Server responds:
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://myapp.com
Content-Type: application/json

{"data": "value"}

# Browser checks: Does Access-Control-Allow-Origin match?
# Yes → Allow JavaScript to read response
# No → Block JavaScript from reading response
```

**Simple request flow diagram:**

```mermaid
sequenceDiagram
    participant JS as JavaScript<br/>(myapp.com)
    participant Browser
    participant API as API Server<br/>(api.example.com)

    Note over JS,API: Simple CORS Request Flow

    JS->>Browser: fetch('api.example.com/data')

    Browser->>API: GET /data<br/>Origin: https://myapp.com

    API->>Browser: 200 OK<br/>Access-Control-Allow-Origin: https://myapp.com<br/>Data: {...}

    Browser->>Browser: Check CORS policy<br/>Origin matches? ✓

    Browser->>JS: Response accessible<br/>data = {...}

    Note over Browser: If origin didn't match,<br/>browser blocks JavaScript access

    classDef jsStyle fill:#6B8DBE,stroke:#6B8DBE,color:#FFFFFF
    classDef browserStyle fill:#C2A25F,stroke:#C2A25F,color:#FFFFFF
    classDef apiStyle fill:#6FAFA3,stroke:#6FAFA3,color:#FFFFFF

    class JS jsStyle
    class Browser browserStyle
    class API apiStyle
```

### Preflight Requests

Preflight requests are sent before the actual request to check if the CORS protocol is understood and if the request is permitted.

**When preflight is triggered:**

```python
# Preflight happens when:
# 1. Method is NOT GET, HEAD, or POST
fetch('https://api.example.com/data', {
    method: 'DELETE'  # Triggers preflight
})

# 2. Custom headers are used
fetch('https://api.example.com/data', {
    headers: {
        'X-Custom-Header': 'value',  # Triggers preflight
        'Authorization': 'Bearer token'  # Triggers preflight
    }
})

# 3. Content-Type is NOT simple
fetch('https://api.example.com/data', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'  # Triggers preflight
    },
    body: JSON.stringify({data: 'value'})
})
```

**Preflight request flow:**

```python
# Step 1: Browser sends OPTIONS request (preflight)
OPTIONS /data HTTP/1.1
Host: api.example.com
Origin: https://myapp.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type, authorization

# Step 2: Server responds with permissions
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://myapp.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: content-type, authorization
Access-Control-Max-Age: 86400

# Step 3: If preflight succeeds, browser sends actual request
POST /data HTTP/1.1
Host: api.example.com
Origin: https://myapp.com
Content-Type: application/json
Authorization: Bearer token

{"data": "value"}

# Step 4: Server responds to actual request
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://myapp.com
Content-Type: application/json

{"result": "success"}
```

**Preflight flow diagram:**

```mermaid
sequenceDiagram
    participant JS as JavaScript<br/>(myapp.com)
    participant Browser
    participant API as API Server<br/>(api.example.com)

    Note over JS,API: Preflight CORS Request Flow

    JS->>Browser: fetch() with custom headers<br/>or non-simple method

    Browser->>Browser: Detect: Needs preflight

    Browser->>API: OPTIONS /data<br/>Origin: myapp.com<br/>Request-Method: POST<br/>Request-Headers: authorization

    Note over API: Check CORS policy:<br/>Is myapp.com allowed?<br/>Is POST allowed?<br/>Is authorization header allowed?

    API->>Browser: 204 No Content<br/>Allow-Origin: myapp.com<br/>Allow-Methods: POST<br/>Allow-Headers: authorization<br/>Max-Age: 86400

    Browser->>Browser: Preflight succeeded ✓<br/>Cache for 86400 seconds

    Browser->>API: POST /data<br/>Origin: myapp.com<br/>Authorization: Bearer token<br/>Body: {...}

    API->>Browser: 200 OK<br/>Allow-Origin: myapp.com<br/>Data: {...}

    Browser->>JS: Response accessible

    classDef jsStyle fill:#6B8DBE,stroke:#6B8DBE,color:#FFFFFF
    classDef browserStyle fill:#C2A25F,stroke:#C2A25F,color:#FFFFFF
    classDef apiStyle fill:#6FAFA3,stroke:#6FAFA3,color:#FFFFFF

    class JS jsStyle
    class Browser browserStyle
    class API apiStyle
```

### Preflight Caching

Preflight requests can be cached to improve performance:

```python
# Server sends:
Access-Control-Max-Age: 86400  # Cache for 24 hours

# Result:
# First request: Preflight + Actual request (2 HTTP requests)
# Subsequent requests (within 24 hours): Only actual request (1 HTTP request)

# After 24 hours:
# Preflight is sent again
```

**Optimizing preflight:**

```python
# Short cache (development)
"Access-Control-Max-Age": "300"  # 5 minutes

# Medium cache (staging)
"Access-Control-Max-Age": "3600"  # 1 hour

# Long cache (production)
"Access-Control-Max-Age": "86400"  # 24 hours

# Maximum cache (if CORS policy rarely changes)
"Access-Control-Max-Age": "604800"  # 7 days
```

---

## CORS Headers Explained

Let's examine each CORS header in detail.

### Access-Control-Allow-Origin

Controls which origins can access the resource.

```python
# Single origin (specific)
"Access-Control-Allow-Origin": "https://myapp.com"
# Only myapp.com can access

# Wildcard (all origins)
"Access-Control-Allow-Origin": "*"
# Any origin can access

# Multiple origins (not supported directly)
# Must be set dynamically based on Origin header
```

**Important rules:**

```python
# Rule 1: Can only specify ONE origin or wildcard
"Access-Control-Allow-Origin": "https://app1.com, https://app2.com"  # ✗ Invalid

# Rule 2: Wildcard cannot be used with credentials
"Access-Control-Allow-Origin": "*"
"Access-Control-Allow-Credentials": "true"
# ✗ This combination is forbidden

# Rule 3: Must be exact match (no partial matching)
"Access-Control-Allow-Origin": "https://*.example.com"  # ✗ Invalid
"Access-Control-Allow-Origin": "https://example.com:*"  # ✗ Invalid
```

**Dynamic origin handling:**

```python
from fastapi import FastAPI, Request

app = FastAPI()

ALLOWED_ORIGINS = [
    "https://myapp.com",
    "https://www.myapp.com",
    "https://admin.myapp.com"
]

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    origin = request.headers.get("origin")

    response = await call_next(request)

    # Check if origin is in allowed list
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin

    return response
```

### Access-Control-Allow-Methods

Specifies which HTTP methods are allowed.

```python
# Single method
"Access-Control-Allow-Methods": "GET"

# Multiple methods
"Access-Control-Allow-Methods": "GET, POST, PUT, DELETE"

# Common pattern (REST API)
"Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS"

# Read-only API
"Access-Control-Allow-Methods": "GET, OPTIONS"
```

**Method security:**

```python
# Conservative (read-only)
"Access-Control-Allow-Methods": "GET, HEAD, OPTIONS"

# Standard (most APIs)
"Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS"

# Permissive (careful with this)
"Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD"

# Never include methods you don't implement:
# If your API doesn't have DELETE endpoints, don't include DELETE
```

### Access-Control-Allow-Headers

Specifies which headers can be used in the actual request.

```python
# Common headers
"Access-Control-Allow-Headers": "Content-Type, Authorization"

# Extended set
"Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With"

# API with custom headers
"Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key, X-Request-ID"
```

**Header security:**

```python
# Minimal (most secure)
"Access-Control-Allow-Headers": "Content-Type"

# Standard (for most APIs with auth)
"Access-Control-Allow-Headers": "Content-Type, Authorization"

# Extended (for complex APIs)
"Access-Control-Allow-Headers": "Content-Type, Authorization, X-Custom-Header"

# Permissive (avoid if possible)
"Access-Control-Allow-Headers": "*"  # Allows any header
```

### Access-Control-Allow-Credentials

Controls whether credentials (cookies, authorization headers) can be sent.

```python
# Allow credentials
"Access-Control-Allow-Credentials": "true"

# Default (credentials not allowed)
# Don't send this header, or:
"Access-Control-Allow-Credentials": "false"
```

**Critical rules for credentials:**

```python
# Rule 1: Cannot use wildcard origin with credentials
"Access-Control-Allow-Origin": "*"  # ✗
"Access-Control-Allow-Credentials": "true"
# This combination is FORBIDDEN by browsers

# Rule 2: Must specify exact origin
"Access-Control-Allow-Origin": "https://myapp.com"  # ✓
"Access-Control-Allow-Credentials": "true"
# This combination is allowed

# Rule 3: Client must also opt-in
fetch('https://api.example.com/data', {
    credentials: 'include'  # Client must include this
})
```

**When to use credentials:**

```python
# Scenario 1: Cookie-based authentication
# Frontend: https://myapp.com
# API: https://api.myapp.com
# Cookies need to be sent → Use credentials: true

# Scenario 2: Token in Authorization header
# Frontend stores token in localStorage
# Sends: Authorization: Bearer token
# Doesn't need credentials: true (header sent regardless)

# Scenario 3: Public API
# No authentication needed
# Don't use credentials: true
```

### Access-Control-Expose-Headers

Controls which headers JavaScript can access in the response.

```python
# By default, JavaScript can only access these headers:
# - Cache-Control
# - Content-Language
# - Content-Type
# - Expires
# - Last-Modified
# - Pragma

# To expose additional headers:
"Access-Control-Expose-Headers": "X-Custom-Header, X-Request-ID"

# Expose multiple headers
"Access-Control-Expose-Headers": "X-Request-ID, X-Rate-Limit-Remaining, X-Rate-Limit-Reset"
```

**Example use case:**

```python
# API response includes pagination info in headers
HTTP/1.1 200 OK
X-Total-Count: 1000
X-Page: 1
X-Per-Page: 50
Access-Control-Expose-Headers: X-Total-Count, X-Page, X-Per-Page

# JavaScript can now access these:
fetch('https://api.example.com/items')
  .then(response => {
    const total = response.headers.get('X-Total-Count');  # Accessible
    const page = response.headers.get('X-Page');          # Accessible
    return response.json();
  })
```

### Access-Control-Max-Age

Specifies how long preflight results can be cached.

```python
# 24 hours (recommended for production)
"Access-Control-Max-Age": "86400"

# 1 hour (for frequently changing CORS policies)
"Access-Control-Max-Age": "3600"

# 5 minutes (for development/testing)
"Access-Control-Max-Age": "300"

# 7 days (maximum for most browsers)
"Access-Control-Max-Age": "604800"
```

**Caching behavior:**

```python
# Without Access-Control-Max-Age:
# Every non-simple request triggers preflight
# Request 1: OPTIONS + GET (2 requests)
# Request 2: OPTIONS + GET (2 requests)
# Request 3: OPTIONS + GET (2 requests)

# With Access-Control-Max-Age: 86400:
# Preflight cached for 24 hours
# Request 1: OPTIONS + GET (2 requests)
# Request 2: GET (1 request) - uses cache
# Request 3: GET (1 request) - uses cache
# After 24 hours: OPTIONS + GET (2 requests) - cache expired
```

---

## CORS Middleware in FastAPI

FastAPI provides built-in CORS middleware that handles all the complexity for you.

### Basic CORS Configuration

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],  # Allowed origins
    allow_credentials=True,                # Allow cookies
    allow_methods=["*"],                   # Allowed HTTP methods
    allow_headers=["*"],                   # Allowed headers
)

@app.get("/api/data")
async def get_data():
    return {"data": "value"}
```

### CORS Configuration Options

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,

    # Origins
    allow_origins=[
        "https://myapp.com",
        "https://www.myapp.com",
        "https://admin.myapp.com"
    ],
    # Or use wildcard (not recommended with credentials):
    # allow_origins=["*"],

    # Origin patterns (regex)
    allow_origin_regex="https://.*\.myapp\.com",

    # Credentials (cookies, authorization headers)
    allow_credentials=True,

    # Methods
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    # Or allow all:
    # allow_methods=["*"],

    # Headers
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    # Or allow all:
    # allow_headers=["*"],

    # Expose additional headers to JavaScript
    expose_headers=["X-Request-ID", "X-Total-Count"],

    # Preflight cache duration (seconds)
    max_age=600,  # 10 minutes
)
```

### Environment-Based CORS Configuration

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Development configuration
if os.getenv("ENVIRONMENT") == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],              # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],              # Allow all methods
        allow_headers=["*"],              # Allow all headers
        max_age=300,                      # Short cache
    )
# Production configuration
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://myapp.com",
            "https://www.myapp.com",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=86400,  # 24 hours
    )
```

### Custom CORS with Multiple Configurations

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Public API endpoints (lenient CORS)
public_app = FastAPI()
public_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)

# Private API endpoints (strict CORS)
private_app = FastAPI()
private_app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://admin.myapp.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Mount sub-applications
app.mount("/public", public_app)
app.mount("/private", private_app)

@public_app.get("/data")
async def public_data():
    return {"data": "public"}

@private_app.get("/data")
async def private_data():
    return {"data": "private"}
```

### Dynamic Origin Validation

```python
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List
import re

app = FastAPI()

class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware with dynamic origin validation.

    Allows fine-grained control over which origins are allowed
    based on patterns, database lookups, or custom logic.
    """

    def __init__(
        self,
        app,
        allowed_origins: List[str] = None,
        allowed_patterns: List[str] = None
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins or []
        self.allowed_patterns = [
            re.compile(pattern) for pattern in (allowed_patterns or [])
        ]

    def is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed"""

        # Check exact matches
        if origin in self.allowed_origins:
            return True

        # Check regex patterns
        for pattern in self.allowed_patterns:
            if pattern.match(origin):
                return True

        # Could add database lookup here
        # if self.check_origin_in_database(origin):
        #     return True

        return False

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            if origin and self.is_allowed_origin(origin):
                return self.create_preflight_response(origin)
            else:
                return HTTPException(status_code=403, detail="Origin not allowed")

        # Handle actual requests
        response = await call_next(request)

        if origin and self.is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response

    def create_preflight_response(self, origin: str):
        """Create response for OPTIONS preflight request"""
        from fastapi.responses import Response

        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "86400",
            }
        )

# Use custom middleware
app.add_middleware(
    DynamicCORSMiddleware,
    allowed_origins=[
        "https://myapp.com",
        "https://www.myapp.com"
    ],
    allowed_patterns=[
        r"https://.*\.myapp\.com",      # All subdomains
        r"https://preview-.*\.netlify\.app"  # Preview deployments
    ]
)
```

---

## CORS Common Scenarios

Let's explore real-world CORS scenarios and solutions.

### Scenario 1: Frontend and API on Different Subdomains

```python
# Frontend: https://app.example.com
# API: https://api.example.com

# Problem: Different subdomains = different origins
# Solution: Configure CORS on API

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.example.com",
        "https://www.example.com"
    ],
    allow_credentials=True,  # For cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

### Scenario 2: Development on Different Port

```python
# Frontend dev server: http://localhost:3000
# API dev server: http://localhost:8000

# Problem: Different ports = different origins
# Solution: Allow localhost with different ports

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Scenario 3: Multiple Frontend Domains

```python
# Scenario:
# - Main site: https://example.com
# - Admin panel: https://admin.example.com
# - Mobile app: https://mobile.example.com

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://example.com",
        "https://www.example.com",
        "https://admin.example.com",
        "https://mobile.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

### Scenario 4: Public API (No Authentication)

```python
# Public API - anyone can access
# No credentials needed

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin
    allow_credentials=False,  # No credentials
    allow_methods=["GET"],  # Read-only
    allow_headers=["Content-Type"],
)
```

### Scenario 5: Preview/Staging Environments

```python
# Support dynamic preview URLs (Netlify, Vercel, etc.)
# Pattern: https://preview-abc123.netlify.app

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://preview-.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

### Scenario 6: Mobile App with Web View

```python
# Mobile apps often use special origins
# iOS: capacitor://localhost or ionic://localhost
# Android: http://localhost

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "capacitor://localhost",
        "ionic://localhost",
        "http://localhost",
        "https://example.com"  # Web version
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## CORS Troubleshooting

CORS errors are common. Let's learn how to debug and fix them.

### Common CORS Errors

#### Error 1: "No 'Access-Control-Allow-Origin' header"

```
Access to fetch at 'https://api.example.com/data' from origin
'https://myapp.com' has been blocked by CORS policy: No
'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Cause**: API didn't send CORS headers

**Solution**:

```python
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Error 2: "Origin not allowed"

```
Access to fetch at 'https://api.example.com/data' from origin
'https://myapp.com' has been blocked by CORS policy: The
'Access-Control-Allow-Origin' header has a value 'https://other.com'
that is not equal to the supplied origin.
```

**Cause**: Origin not in allowed list

**Solution**:

```python
# Add your origin to allowed list
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://myapp.com",  # Add this
        "https://other.com"
    ],
)
```

#### Error 3: "Credentials mode with wildcard"

```
Access to fetch at 'https://api.example.com/data' from origin
'https://myapp.com' has been blocked by CORS policy: The value of
the 'Access-Control-Allow-Origin' header in the response must not
be the wildcard '*' when the request's credentials mode is 'include'.
```

**Cause**: Cannot use `*` with credentials

**Solution**:

```python
# Change from wildcard to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],  # Specific origin
    allow_credentials=True,
)
```

#### Error 4: "Method not allowed in preflight"

```
Access to fetch at 'https://api.example.com/data' from origin
'https://myapp.com' has been blocked by CORS policy: Method DELETE
is not allowed by Access-Control-Allow-Methods in preflight response.
```

**Cause**: Method not in allowed methods

**Solution**:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Add DELETE
)
```

#### Error 5: "Header not allowed in preflight"

```
Access to fetch at 'https://api.example.com/data' from origin
'https://myapp.com' has been blocked by CORS policy: Request header
field authorization is not allowed by Access-Control-Allow-Headers
in preflight response.
```

**Cause**: Header not in allowed headers

**Solution**:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_headers=["Content-Type", "Authorization"],  # Add Authorization
)
```

### Debugging CORS Issues

#### 1. Check Browser Console

```javascript
// Look for CORS error messages
// They tell you exactly what's wrong
```

#### 2. Inspect Network Tab

```python
# Look at preflight request (OPTIONS)
# Check response headers:
# - Access-Control-Allow-Origin
# - Access-Control-Allow-Methods
# - Access-Control-Allow-Headers
# - Access-Control-Max-Age
```

#### 3. Test with curl

```bash
# Test actual request
curl -H "Origin: https://myapp.com" \
     -H "Content-Type: application/json" \
     -X GET \
     https://api.example.com/data \
     -v

# Look for Access-Control-Allow-Origin in response

# Test preflight request
curl -H "Origin: https://myapp.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type" \
     -X OPTIONS \
     https://api.example.com/data \
     -v

# Check preflight response headers
```

#### 4. Create Test Endpoint

```python
@app.get("/cors-test")
async def cors_test(request: Request):
    """Debug endpoint to check CORS configuration"""
    return {
        "origin": request.headers.get("origin"),
        "method": request.method,
        "headers": dict(request.headers),
        "cors_configured": True
    }
```

#### 5. Temporary Fix for Development

```python
# ONLY FOR DEVELOPMENT
# Allow everything temporarily to verify CORS is the issue

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# If this fixes the issue, the problem is definitely CORS
# Then narrow down to specific origins/methods/headers
```

### CORS Checklist

When debugging CORS issues:

- [ ] Is CORS middleware added to the app?
- [ ] Is the origin in the `allow_origins` list?
- [ ] If using credentials, is origin specific (not `*`)?
- [ ] Is the HTTP method in `allow_methods`?
- [ ] Are custom headers in `allow_headers`?
- [ ] Is the request actually cross-origin?
- [ ] Is the preflight request succeeding?
- [ ] Are response headers being set correctly?
- [ ] Is there an error handler interfering?
- [ ] Is middleware order correct?

---

## Complete Practical Example

Let's build a complete application with comprehensive security headers and properly configured CORS.

```python
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import os
from datetime import datetime

app = FastAPI(
    title="Secure API with CORS",
    description="Production-ready security configuration",
    version="1.0.0"
)

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# CORS Configuration
if IS_PRODUCTION:
    # Production: Specific origins only
    ALLOWED_ORIGINS = [
        "https://myapp.com",
        "https://www.myapp.com",
        "https://admin.myapp.com"
    ]
else:
    # Development: Local development servers
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Total-Count"],
    max_age=86400 if IS_PRODUCTION else 300,
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ):
        response = await call_next(request)

        is_https = (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https"
        )

        # HSTS
        if is_https:
            if IS_PRODUCTION:
                response.headers["Strict-Transport-Security"] = \
                    "max-age=31536000; includeSubDomains; preload"
            else:
                response.headers["Strict-Transport-Security"] = \
                    "max-age=300"

        # CSP
        csp = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self' " + " ".join(ALLOWED_ORIGINS),
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp)

        # Other security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = \
            "camera=(), microphone=(), geolocation=(), payment=()"
        response.headers["Server"] = "Secure"

        # Add request ID for tracking
        request_id = request.headers.get("x-request-id", "no-id")
        response.headers["X-Request-ID"] = request_id

        return response

app.add_middleware(SecurityHeadersMiddleware)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging"""
    start_time = datetime.now()

    # Log request
    print(f"[{start_time}] {request.method} {request.url.path}")
    print(f"Origin: {request.headers.get('origin', 'None')}")

    response = await call_next(request)

    # Log response
    duration = (datetime.now() - start_time).total_seconds()
    print(f"Status: {response.status_code} Duration: {duration:.3f}s")

    return response

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Secure API",
        "environment": ENVIRONMENT,
        "security": {
            "https": "enforced" if IS_PRODUCTION else "optional",
            "cors": "configured",
            "headers": "enabled"
        }
    }

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# CORS test endpoint
@app.get("/cors-test")
async def cors_test(request: Request):
    """Test CORS configuration"""
    return {
        "origin": request.headers.get("origin"),
        "cors_configured": True,
        "allowed_origins": ALLOWED_ORIGINS,
        "environment": ENVIRONMENT
    }

# Protected endpoint example
@app.get("/api/data")
async def get_data(request: Request):
    """Example protected endpoint"""

    # Check authorization (simplified)
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {
        "data": [
            {"id": 1, "value": "Item 1"},
            {"id": 2, "value": "Item 2"},
            {"id": 3, "value": "Item 3"}
        ],
        "total": 3
    }

# Error handler for CORS errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom error handler that maintains CORS headers"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*")
        }
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=not IS_PRODUCTION
    )
```

### Frontend Test Client

```html
<!DOCTYPE html>
<html>
  <head>
    <title>CORS Test Client</title>
  </head>
  <body>
    <h1>CORS Test Client</h1>
    <button onclick="testSimpleRequest()">Test Simple Request (GET)</button>
    <button onclick="testPreflightRequest()">
      Test Preflight Request (POST with auth)
    </button>
    <button onclick="testWithCredentials()">Test With Credentials</button>
    <pre id="output"></pre>

    <script>
      const API_URL = "http://localhost:8000";
      const output = document.getElementById("output");

      function log(message) {
        output.textContent += message + "\n";
      }

      async function testSimpleRequest() {
        log("\n--- Testing Simple Request ---");
        try {
          const response = await fetch(`${API_URL}/cors-test`);
          const data = await response.json();
          log("Success: " + JSON.stringify(data, null, 2));
        } catch (error) {
          log("Error: " + error.message);
        }
      }

      async function testPreflightRequest() {
        log("\n--- Testing Preflight Request ---");
        try {
          const response = await fetch(`${API_URL}/api/data`, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              Authorization: "Bearer test-token",
            },
          });
          const data = await response.json();
          log("Success: " + JSON.stringify(data, null, 2));
        } catch (error) {
          log("Error: " + error.message);
        }
      }

      async function testWithCredentials() {
        log("\n--- Testing With Credentials ---");
        try {
          const response = await fetch(`${API_URL}/cors-test`, {
            credentials: "include", // Send cookies
          });
          const data = await response.json();
          log("Success: " + JSON.stringify(data, null, 2));
        } catch (error) {
          log("Error: " + error.message);
        }
      }
    </script>
  </body>
</html>
```

---

## Security Headers Testing Tools

### Online Tools

1. **Security Headers** (https://securityheaders.com/)

   - Comprehensive security header checker
   - Provides grade (A+ to F)
   - Explains missing headers

2. **Mozilla Observatory** (https://observatory.mozilla.org/)

   - Security and configuration scanner
   - Detailed recommendations
   - Historical tracking

3. **SSL Labs** (https://www.ssllabs.com/ssltest/)
   - SSL/TLS configuration test
   - Certificate validation
   - Protocol and cipher analysis

### Command Line Testing

```bash
# Test security headers
curl -I https://example.com

# Test specific header
curl -I https://example.com | grep -i "strict-transport-security"

# Test CORS (simple request)
curl -H "Origin: https://myapp.com" \
     -I https://api.example.com/data

# Test CORS (preflight)
curl -H "Origin: https://myapp.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: authorization" \
     -X OPTIONS \
     -I https://api.example.com/data

# Verbose output (see full headers)
curl -v https://example.com
```

### Python Testing Script

```python
import requests

def test_security_headers(url: str):
    """
    Test security headers on a URL.

    Checks for presence and correctness of security headers.
    """

    response = requests.get(url)
    headers = response.headers

    checks = {
        "Strict-Transport-Security": {
            "present": "Strict-Transport-Security" in headers,
            "value": headers.get("Strict-Transport-Security", "Not set"),
            "recommendation": "max-age=31536000; includeSubDomains; preload"
        },
        "Content-Security-Policy": {
            "present": "Content-Security-Policy" in headers,
            "value": headers.get("Content-Security-Policy", "Not set")[:100] + "...",
            "recommendation": "Restrictive policy based on needs"
        },
        "X-Frame-Options": {
            "present": "X-Frame-Options" in headers,
            "value": headers.get("X-Frame-Options", "Not set"),
            "recommendation": "DENY or SAMEORIGIN"
        },
        "X-Content-Type-Options": {
            "present": "X-Content-Type-Options" in headers,
            "value": headers.get("X-Content-Type-Options", "Not set"),
            "recommendation": "nosniff"
        },
        "Referrer-Policy": {
            "present": "Referrer-Policy" in headers,
            "value": headers.get("Referrer-Policy", "Not set"),
            "recommendation": "strict-origin-when-cross-origin"
        }
    }

    print(f"\n=== Security Headers Test for {url} ===\n")

    score = 0
    total = len(checks)

    for header, check in checks.items():
        status = "✓" if check["present"] else "✗"
        if check["present"]:
            score += 1

        print(f"{status} {header}")
        print(f"  Present: {check['present']}")
        print(f"  Value: {check['value']}")
        print(f"  Recommended: {check['recommendation']}")
        print()

    grade = "A+" if score == total else \
            "A" if score >= total - 1 else \
            "B" if score >= total - 2 else \
            "C" if score >= total - 3 else "F"

    print(f"Score: {score}/{total} - Grade: {grade}")

def test_cors(api_url: str, origin: str):
    """
    Test CORS configuration.

    Sends request with Origin header and checks CORS response.
    """

    headers = {"Origin": origin}
    response = requests.get(api_url, headers=headers)

    print(f"\n=== CORS Test ===")
    print(f"API URL: {api_url}")
    print(f"Origin: {origin}\n")

    cors_headers = {
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
        "Access-Control-Expose-Headers"
    }

    print("CORS Response Headers:")
    for header in cors_headers:
        value = response.headers.get(header, "Not set")
        print(f"  {header}: {value}")

    allowed_origin = response.headers.get("Access-Control-Allow-Origin")
    if allowed_origin == origin or allowed_origin == "*":
        print("\n✓ CORS Configured - Origin Allowed")
    else:
        print("\n✗ CORS Not Configured Properly")

# Test your site
test_security_headers("https://example.com")
test_cors("https://api.example.com/data", "https://myapp.com")
```

---

## Common Pitfalls

### 1. Forgetting CORS Middleware

```python
# ✗ BAD: No CORS configuration
app = FastAPI()

@app.get("/api/data")
async def get_data():
    return {"data": "value"}

# Browser blocks cross-origin requests

# ✓ GOOD: Add CORS middleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Using Wildcard with Credentials

```python
# ✗ BAD: Cannot use * with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # FORBIDDEN combination
)

# ✓ GOOD: Specific origins with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_credentials=True,
)
```

### 3. Not Including OPTIONS Method

```python
# ✗ BAD: Missing OPTIONS for preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_methods=["GET", "POST"],  # No OPTIONS
)

# ✓ GOOD: Include OPTIONS or use *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://myapp.com"],
    allow_methods=["GET", "POST", "OPTIONS"],
    # Or:
    # allow_methods=["*"],
)
```

### 4. Incorrect HSTS Configuration

```python
# ✗ BAD: HSTS on HTTP
if request.url.scheme == "http":
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
# HSTS over HTTP is ignored by browsers

# ✓ GOOD: HSTS only on HTTPS
if request.url.scheme == "https":
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
```

### 5. Overly Permissive CSP

```python
# ✗ BAD: Defeats purpose of CSP
"Content-Security-Policy": "default-src * 'unsafe-inline' 'unsafe-eval'"

# ✓ GOOD: Restrictive policy
"Content-Security-Policy": "default-src 'self'; script-src 'self'"
```

### 6. Not Testing in Production-Like Environment

```python
# Development works (localhost)
# Production fails (different origin)

# Always test with actual domains before deploying
```

### 7. Middleware Order Matters

```python
# ✗ BAD: CORS after other middleware that returns responses
app.add_middleware(SomeMiddleware)  # Returns response
app.add_middleware(CORSMiddleware)  # Never reached

# ✓ GOOD: CORS first
app.add_middleware(CORSMiddleware)
app.add_middleware(SomeMiddleware)
```

---

## Key Takeaways

### Security Headers

1. **HSTS forces HTTPS**

   - Prevents protocol downgrade attacks
   - Set long max-age in production
   - Use includeSubDomains carefully
   - Consider preload list for maximum protection

2. **Referrer-Policy controls information leakage**

   - Default behavior can leak sensitive URLs
   - strict-origin-when-cross-origin is good balance
   - no-referrer for maximum privacy

3. **Permissions-Policy restricts feature access**

   - Block unused browser features
   - Especially important for embedded content
   - Reduces attack surface

4. **CSP is the strongest XSS protection**
   - Replaces X-XSS-Protection
   - Start restrictive, relax as needed
   - Monitor CSP violations

### CORS

5. **CORS is a browser security feature**

   - Protects users, not servers
   - Server opts-in to cross-origin requests
   - Cannot be bypassed from browser

6. **Origins are protocol + domain + port**

   - Any difference = different origin
   - Subdomains are different origins
   - Different ports are different origins

7. **Simple requests vs preflight requests**

   - Simple: GET/POST with basic headers
   - Preflight: OPTIONS request first
   - Custom headers trigger preflight

8. **Credentials require specific origin**

   - Cannot use wildcard (\*) with credentials
   - Must specify exact origin
   - Both server and client must opt-in

9. **CORS errors are client-side**

   - Server might respond successfully
   - Browser blocks JavaScript access
   - Check browser console for details

10. **Test CORS configuration thoroughly**
    - Test from actual frontend domain
    - Test both simple and preflight requests
    - Test with and without credentials
    - Test error cases

---

## Practice Exercises

### Exercise 1: Configure HSTS

Implement HSTS middleware with progressive rollout:

- Start with 5-minute max-age
- Increase to 1 day
- Increase to 1 year
- Add includeSubDomains
- Add preload

**Test**: Verify with curl and browser

### Exercise 2: Implement CSP

Create Content-Security-Policy that:

- Allows scripts only from your domain and CDN
- Allows styles from your domain and Google Fonts
- Blocks all iframes
- Allows images from anywhere (data: and https:)

**Test**: Try to load blocked resources

### Exercise 3: CORS Configuration

Configure CORS for:

- Frontend: https://app.example.com
- API: https://api.example.com
- Allow credentials
- Allow GET, POST, PUT, DELETE
- Allow Content-Type and Authorization headers

**Test**: Make requests from frontend

### Exercise 4: Dynamic CORS

Implement middleware that:

- Reads allowed origins from environment variable
- Supports regex patterns
- Validates origin on each request
- Logs rejected origins

**Test**: Try various origins

### Exercise 5: CORS Debugging

Given a CORS error, identify and fix:

1. Missing CORS middleware
2. Wrong origin in allowed list
3. Wildcard with credentials
4. Missing header in allowed headers
5. Missing method in allowed methods

**Test**: Verify fixes work

---

## What's Next?

**Tomorrow (Day 3)**: Input Sanitization & Attack Prevention

We'll cover:

1. SQL Injection prevention
2. XSS (Cross-Site Scripting) prevention
3. Path Traversal prevention
4. File Upload validation
5. Input validation with Pydantic
6. Security testing

Get ready for a deep dive into protecting your API from common attacks!

---

## Additional Resources

### Official Documentation

- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [MDN: CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)

### Security Resources

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [Security Headers Guide](https://securityheaders.com/)
- [Mozilla Web Security](https://infosec.mozilla.org/guidelines/web_security)

### Tools

- [Security Headers Checker](https://securityheaders.com/)
- [Mozilla Observatory](https://observatory.mozilla.org/)
- [CORS Tester](https://www.test-cors.org/)

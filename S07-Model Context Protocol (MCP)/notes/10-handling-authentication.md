# 10 — Handling Authentication

> **Phase:** Advanced  
> **Goal:** Learn how to securely pass API keys and credentials to MCP servers — and understand the OAuth flow for remote servers.

---

## Table of Contents
1. [Why Auth in MCP is Different](#1-why-auth-in-mcp-is-different)
2. [The Golden Rule: Environment Variables](#2-the-golden-rule-environment-variables)
3. [Passing Env Vars via Config](#3-passing-env-vars-via-config)
4. [Accessing Env Vars in Your Server](#4-accessing-env-vars-in-your-server)
5. [Full Example: Python Server with API Key](#5-full-example-python-server-with-api-key)
6. [OAuth 2.0 for Remote Servers](#6-oauth-20-for-remote-servers)
7. [Security Best Practices Checklist](#7-security-best-practices-checklist)
8. [Common Security Mistakes](#8-common-security-mistakes)

---

## 1. Why Auth in MCP is Different

In a traditional web app, auth is between a **user's browser** and a **server**. In MCP, the picture is more complex:

```
MCP Auth Landscape
────────────────────────────────────────────────────────────

  Scenario A: Local stdio server (most common)
  ─────────────────────────────────────────────
  Claude Desktop ──► Your Python Server ──► External API
                     (trusted local process)   (needs API key)

  The "auth" here is between YOUR SERVER and the EXTERNAL API.
  Claude Desktop trusts your server implicitly (it spawned it).
  Solution: Pass API keys as environment variables.

  Scenario B: Remote HTTP+SSE server
  ────────────────────────────────────
  Claude Desktop ──► Remote MCP Server ──► External API
  (over the internet)

  Now YOU need to authenticate Claude to your server too.
  Solution: OAuth 2.0 or bearer tokens.
```

---

## 2. The Golden Rule: Environment Variables

**Never hardcode API keys, tokens, or secrets in your server code.**

```
Why Not Hardcode?
────────────────────────────────────────────────────────────

  ❌ Hardcoded secret:
  ┌─────────────────────────────────────────────────────┐
  │ API_KEY = "sk-abc123..."  # in server.py            │
  │                                                     │
  │ Problems:                                           │
  │ ├── Accidentally committed to git                   │
  │ ├── Shared with everyone who sees the code          │
  │ ├── Hard to rotate (change the key)                 │
  │ └── Different keys for dev/prod require code change │
  └─────────────────────────────────────────────────────┘

  ✅ Environment variable:
  ┌─────────────────────────────────────────────────────┐
  │ API_KEY = os.environ["WEATHER_API_KEY"]             │
  │                                                     │
  │ Benefits:                                           │
  │ ├── Not in source code → safe to commit             │
  │ ├── Set per-environment (dev vs prod)               │
  │ ├── Easy to rotate without code changes             │
  │ └── Each user sets their own value                  │
  └─────────────────────────────────────────────────────┘
```

---

## 3. Passing Env Vars via Config

In Claude Desktop and Cursor, use the `env` field in your MCP config:

```json
// claude_desktop_config.json or .cursor/mcp.json

{
  "mcpServers": {
    "weather-server": {
      "command": "python3",
      "args": ["/Users/yourname/mcp/weather/server.py"],
      "env": {
        "WEATHER_API_KEY": "your-actual-api-key-here",
        "WEATHER_BASE_URL": "https://api.openweathermap.org/data/2.5",
        "LOG_LEVEL": "info"
      }
    },
    "github-server": {
      "command": "node",
      "args": ["/Users/yourname/mcp/github/dist/server.js"],
      "env": {
        "GITHUB_TOKEN": "ghp_yourtokenhere"
      }
    }
  }
}
```

The env vars in the `env` object are **merged with the system environment** and injected into the server process. Your server can read them like any other env var.

> ⚠️ The config file itself should be protected. On macOS, the `~/Library` folder is not readable by other users, but don't share this file.

---

## 4. Accessing Env Vars in Your Server

### Python

```python
import os

# Required — raises KeyError if not set (fails fast with a clear error)
api_key = os.environ["WEATHER_API_KEY"]

# Optional with a default value
log_level = os.environ.get("LOG_LEVEL", "info")

# Validate at startup (not inside the tool handler)
def validate_config():
    required = ["WEATHER_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: Missing required env vars: {missing}", file=sys.stderr)
        sys.exit(1)   # fail fast with a clear message

validate_config()  # call this at module load time
```

### TypeScript

```typescript
// Required — throw if not set
const apiKey = process.env.WEATHER_API_KEY;
if (!apiKey) {
  console.error("ERROR: WEATHER_API_KEY environment variable is required");
  process.exit(1);
}

// Optional with default
const logLevel = process.env.LOG_LEVEL ?? "info";
```

---

## 5. Full Example: Python Server with API Key

A complete, runnable server that uses a real API key securely:

```python
# secure_weather_server.py

import asyncio
import os
import sys
import urllib.request
import urllib.error
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

# ── Validate config at startup ─────────────────────────────
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
if not WEATHER_API_KEY:
    print(
        "ERROR: WEATHER_API_KEY environment variable is not set.\n"
        "Add it to your claude_desktop_config.json under 'env'.",
        file=sys.stderr
    )
    sys.exit(1)

BASE_URL = "https://api.openweathermap.org/data/2.5"

app = Server("secure-weather-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(
        name="get_weather",
        description=(
            "Get real-time weather for a city using OpenWeatherMap. "
            "Returns temperature, description, humidity, and wind. "
            "Use when user asks about current weather anywhere in the world."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'Paris'"},
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial"],
                    "default": "metric",
                    "description": "metric=Celsius, imperial=Fahrenheit"
                }
            },
            "required": ["city"]
        }
    )]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name != "get_weather":
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True
        )

    city = arguments.get("city", "").strip()
    units = arguments.get("units", "metric")

    if not city:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: city is required")],
            isError=True
        )

    # Build request URL — API key comes from env var, never hardcoded
    url = (
        f"{BASE_URL}/weather"
        f"?q={urllib.parse.quote(city)}"
        f"&units={units}"
        f"&appid={WEATHER_API_KEY}"   # <-- env var used here
    )

    try:
        import urllib.parse
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read())

        unit_symbol = "°C" if units == "metric" else "°F"
        speed_unit  = "m/s" if units == "metric" else "mph"

        result = (
            f"Weather in {data['name']}, {data['sys']['country']}:\n"
            f"  Temperature: {data['main']['temp']}{unit_symbol} "
            f"(feels like {data['main']['feels_like']}{unit_symbol})\n"
            f"  Conditions:  {data['weather'][0]['description'].title()}\n"
            f"  Humidity:    {data['main']['humidity']}%\n"
            f"  Wind:        {data['wind']['speed']} {speed_unit}"
        )
        return CallToolResult(content=[TextContent(type="text", text=result)])

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return CallToolResult(
                content=[TextContent(type="text", text=f"City '{city}' not found.")],
                isError=True
            )
        if e.code == 401:
            return CallToolResult(
                content=[TextContent(type="text", text="Invalid API key. Check WEATHER_API_KEY.")],
                isError=True
            )
        return CallToolResult(
            content=[TextContent(type="text", text=f"API error: HTTP {e.code}")],
            isError=True
        )
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unexpected error: {str(e)}")],
            isError=True
        )


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

**Config to use this server:**
```json
{
  "mcpServers": {
    "weather": {
      "command": "python3",
      "args": ["/path/to/secure_weather_server.py"],
      "env": {
        "WEATHER_API_KEY": "your_openweathermap_api_key"
      }
    }
  }
}
```

---

## 6. OAuth 2.0 for Remote Servers

For remote HTTP+SSE servers, you need users to authenticate with your server. MCP supports the **OAuth 2.0 Authorization Code flow**.

```
OAuth Flow for Remote MCP Servers
────────────────────────────────────────────────────────────

  MCP Client                 Your MCP Server            OAuth Provider
  (Claude Desktop)           (remote HTTP)              (GitHub, Google...)
       │                          │                            │
       │── connects to server ───►│                            │
       │                          │                            │
       │◄── 401 Unauthorized ─────│                            │
       │◄── WWW-Authenticate:     │                            │
       │    resource_metadata URL │                            │
       │                          │                            │
       │── fetch /.well-known/    │                            │
       │   oauth-protected-       │                            │
       │   resource-metadata ────►│                            │
       │◄── returns auth server   │                            │
       │    info ─────────────────│                            │
       │                          │                            │
       │── redirect user ────────────────────────────────────►│
       │                                                       │ user logs in
       │◄─────────────── callback with auth code ─────────────│
       │                          │                            │
       │── exchange code ────────►│                            │
       │◄── access token ─────────│                            │
       │                          │                            │
       │── reconnect with token ─►│                            │
       │                          │ validates token            │
       │◄── MCP connection OK ────│                            │
```

> **For local stdio servers:** OAuth is not needed — the host trusts the locally spawned server implicitly.

---

## 7. Security Best Practices Checklist

```
Security Checklist for MCP Servers
────────────────────────────────────────────────────────────

  Secrets & Credentials
  □ API keys only in environment variables, never in code
  □ Config files not committed to git (.gitignore them!)
  □ .env files used for local dev, never for production

  Input Validation
  □ Validate all tool inputs before using them
  □ Sanitize file paths (prevent directory traversal)
  □ Validate URLs before making requests to them
  □ Set timeouts on all external API calls

  Access Control
  □ Tools only access resources they need (principle of least privilege)
  □ File resource servers are scoped to a specific directory
  □ DB servers use read-only credentials where possible

  Remote Servers
  □ Always use HTTPS (never HTTP) for remote servers
  □ Implement OAuth or bearer token auth
  □ Rate limit your endpoints
  □ Log auth failures for monitoring
```

---

## 8. Common Security Mistakes

| Mistake | Risk | Fix |
|---|---|---|
| Hardcoded API keys | Key leaked if code is shared | Use `os.environ["KEY"]` |
| Committing config with keys | Key leaked via git history | Add config to `.gitignore` |
| No path sanitization in file tools | Directory traversal attack | Resolve and validate paths |
| Accepting any URL in tools | SSRF attacks | Whitelist allowed domains |
| No timeout on API calls | Tools hang indefinitely | Always set `timeout=10` |
| Logging full API responses | Leaks sensitive data | Log only metadata, not payloads |
| Broad file system access | LLM reads sensitive files | Scope to a specific directory |

---

> **Previous Note ←** `09-debugging-mcp.md`  
> **Next Note →** `11-pagination-and-large-data.md` — Handling large datasets and the cursor-based pagination pattern.

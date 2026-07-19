# 05 — Exposing Resources

> **Series:** S07 — Model Context Protocol (MCP)
> **Previous:** [04 — Server Setup & SDKs](./04-server-setup-and-sdks.md)
> **Next:** [06 — Creating Tools](./06-creating-tools.md)

---

## Table of Contents

1. [What Makes a Good Resource?](#1-what-makes-a-good-resource)
2. [How Resources Flow Through MCP](#2-how-resources-flow-through-mcp)
3. [Implementing listResources](#3-implementing-listresources)
   - 3.1 [What it Returns](#31-what-it-returns)
   - 3.2 [The Resource Object Fields](#32-the-resource-object-fields)
4. [Implementing readResource](#4-implementing-readresource)
   - 4.1 [How to Serve Content](#41-how-to-serve-content)
   - 4.2 [Content Type Reference](#42-content-type-reference)
5. [Full Python Example: Exposing Markdown Files](#5-full-python-example-exposing-markdown-files)
6. [Full TypeScript Example: Exposing Markdown Files](#6-full-typescript-example-exposing-markdown-files)
7. [Resource Templates (Dynamic URIs)](#7-resource-templates-dynamic-uris)
   - 7.1 [URI Template Syntax](#71-uri-template-syntax)
   - 7.2 [Python Implementation](#72-python-implementation)
   - 7.3 [TypeScript Implementation](#73-typescript-implementation)
8. [Common Pitfalls & How to Avoid Them](#8-common-pitfalls--how-to-avoid-them)
9. [Mental Model Summary](#9-mental-model-summary)

---

## 1. What Makes a Good Resource?

Resources in MCP represent **data that can be read**. Think of them as the server's "filesystem" — a collection of addressable, readable pieces of content that an AI client can pull in to gain context.

The golden rules of a well-designed resource:

```
┌─────────────────────────────────────────────────────────────────┐
│  Properties of a Good MCP Resource                             │
│                                                                 │
│  ✅ Read-only                                                   │
│     Resources should NEVER have side effects when read.        │
│     Mutations belong in Tools, not Resources.                   │
│     (Reading a file? Resource. Deleting it? Tool.)             │
│                                                                 │
│  ✅ Stable, predictable URIs                                    │
│     URIs should be guessable / documented.                     │
│     Good:  notes://intro.md                                     │
│            db://users/schema                                    │
│     Bad:   resource://a1b2c3d4  (opaque IDs)                   │
│                                                                 │
│  ✅ Focused on context, not action                              │
│     Resources give the model information to reason about.      │
│     A resource might be: a file, a DB row, an API response,    │
│     a config, a schema, a screenshot, a log excerpt.           │
│                                                                 │
│  ✅ Reasonable in size                                          │
│     Don't return 50 MB files. Resources flow into the model's  │
│     context window — keep them focused and reasonably sized.   │
│     Truncate, paginate, or summarize if needed.                │
│                                                                 │
│  ✅ Correct MIME type                                           │
│     Always declare the content's MIME type. The client uses    │
│     it to decide how to render or process the content.         │
└─────────────────────────────────────────────────────────────────┘
```

**Resource vs Tool — the key distinction:**

| Scenario | Use Resource | Use Tool |
|----------|-------------|----------|
| Read a config file | ✅ | ❌ |
| Read a database row | ✅ | ❌ |
| Fetch a public API response | ✅ | ❌ |
| Write to a file | ❌ | ✅ |
| Execute a shell command | ❌ | ✅ |
| Search a database (returns results) | Either* | ✅ (preferred) |
| Send an email | ❌ | ✅ |

> *Search with no side effects could be a resource template, but tools are more idiomatic for parameterized lookups.

---

## 2. How Resources Flow Through MCP

Here is the complete request/response lifecycle for resources:

```
AI Client (e.g., Claude)                    Your MCP Server
         │                                        │
         │  1. ── resources/list ──────────────► │
         │                                        │  list_resources()
         │  2. ◄── [Resource, Resource, ...] ──── │  returns list
         │                                        │
         │  (Claude decides which resource to read)
         │                                        │
         │  3. ── resources/read ──────────────► │
         │         { uri: "notes://intro.md" }    │  read_resource(uri)
         │                                        │
         │  4. ◄── { contents: [               ── │  returns content
         │            { uri: ...,               │
         │              mimeType: "text/plain", │
         │              text: "# Introduction"  │
         │            }                         │
         │           ] }                        │
         │                                        │
         │  (Claude uses the content as context)  │
```

The two handlers you must implement are:
- **`list_resources`** → answers "what resources do you have?"
- **`read_resource`** → answers "give me the content of this specific resource"

---

## 3. Implementing listResources

### 3.1 What it Returns

`list_resources` must return a list of `Resource` objects. Each object is a **description** of a resource — it tells the client the resource exists and how to fetch it, but does NOT include the content itself.

```
resources/list response
┌────────────────────────────────────────────────────┐
│  {                                                 │
│    "resources": [                                  │
│      {                                             │
│        "uri":         "notes://intro.md",    ──► Unique address │
│        "name":        "Introduction to MCP", ──► Human label    │
│        "description": "Overview and goals",  ──► Optional hint  │
│        "mimeType":    "text/markdown"         ──► Content type  │
│      },                                            │
│      {                                             │
│        "uri":         "notes://advanced.md",       │
│        "name":        "Advanced Patterns",         │
│        "mimeType":    "text/markdown"              │
│      }                                             │
│    ]                                               │
│  }                                                 │
└────────────────────────────────────────────────────┘
```

### 3.2 The Resource Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uri` | string | ✅ | Unique identifier for the resource. Client uses this in `read_resource`. Must be a valid URI. |
| `name` | string | ✅ | Human-readable display name shown in UIs and to the model. |
| `description` | string | ❌ | Optional one-line description. Helps the model decide whether to read it. |
| `mimeType` | string | ❌ | MIME type of the content. Strongly recommended — omit only if unknown. |

**URI Scheme Design:**  
You can use any URI scheme you invent — there is no global registry for MCP URIs. Common patterns:

```
Custom scheme examples:
  notes://filename.md          ← scheme: "notes"
  db://tablename/record-id     ← scheme: "db"
  config://app/settings        ← scheme: "config"
  file:///absolute/path        ← uses real "file" scheme

Stick to one scheme per server for clarity.
```

---

## 4. Implementing readResource

### 4.1 How to Serve Content

`read_resource` receives the URI the client wants to read, and must return the actual content.

```
resources/read response
┌──────────────────────────────────────────────────────────┐
│  {                                                       │
│    "contents": [                                         │
│      {                                                   │
│        "uri":      "notes://intro.md",   ◄── echo back  │
│        "mimeType": "text/markdown",                      │
│                                                          │
│        ── For text content ──────────────────────────    │
│        "text": "# Introduction\n\nThis is..."            │
│                                                          │
│        ── For binary content ────────────────────────    │
│        "blob": "<base64-encoded-bytes>"                  │
│      }                                                   │
│    ]                                                     │
│  }                                                       │
└──────────────────────────────────────────────────────────┘
```

**Rules:**
- Use `text` for anything text-based (markdown, JSON, CSV, HTML, code)
- Use `blob` (base64-encoded) for binary content (images, PDFs, audio)
- You MUST raise an error (not return empty content) if the URI is not found
- The `contents` array almost always has exactly one item — but the spec allows multiple for split content

### 4.2 Content Type Reference

| Content | MIME Type | Field to use |
|---------|-----------|--------------|
| Plain text | `text/plain` | `text` |
| Markdown | `text/markdown` | `text` |
| JSON | `application/json` | `text` |
| HTML | `text/html` | `text` |
| CSV | `text/csv` | `text` |
| Python source | `text/x-python` | `text` |
| JavaScript | `application/javascript` | `text` |
| TypeScript | `application/typescript` | `text` |
| PNG image | `image/png` | `blob` (base64) |
| JPEG image | `image/jpeg` | `blob` (base64) |
| PDF | `application/pdf` | `blob` (base64) |
| Any binary | `application/octet-stream` | `blob` (base64) |

> **Tip:** When serving code files, use the language-specific MIME type (e.g., `text/x-python`) rather than `text/plain`. Some clients use MIME types to apply syntax highlighting or special handling.

---

## 5. Full Python Example: Exposing Markdown Files

This is a **complete, runnable** Python MCP server that scans a `./data/notes/` directory and exposes every `.md` file as a readable resource.

```python
# server.py
# ─────────────────────────────────────────────────────────────────
# MCP Server: Expose local Markdown files as resources
#
# Directory structure assumed:
#   server.py
#   data/
#     notes/
#       intro.md
#       advanced.md
#       getting-started.md
#
# Usage:
#   pip install mcp
#   python3 server.py
#   # Then open: mcp dev server.py
# ─────────────────────────────────────────────────────────────────

import asyncio
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types  # All MCP types (Resource, TextContent, etc.)

# ── Configuration ─────────────────────────────────────────────────
# Resolve the path to the notes directory relative to this file.
# Using Path(__file__).parent makes the path work regardless of
# which directory you run the script from.
NOTES_DIR = Path(__file__).parent / "data" / "notes"

# The URI scheme we'll use for our resources.
# "notes://" is a custom scheme — we own and define its meaning.
URI_SCHEME = "notes"

# ── Server Initialization ─────────────────────────────────────────
app = Server("markdown-notes-server")


# ── Helper: URI ↔ Path conversion ────────────────────────────────
def filename_to_uri(filename: str) -> str:
    """Convert a filename like 'intro.md' to 'notes://intro.md'"""
    return f"{URI_SCHEME}://{filename}"

def uri_to_path(uri: str) -> Path:
    """
    Convert a URI like 'notes://intro.md' to an absolute Path.
    
    We strip the scheme prefix to get just the filename,
    then resolve it against our NOTES_DIR.
    
    Security note: We use .resolve() and check that the resulting
    path is still inside NOTES_DIR. This prevents path traversal
    attacks (e.g., uri = "notes://../../etc/passwd").
    """
    # Strip "notes://" → "intro.md"
    filename = uri.removeprefix(f"{URI_SCHEME}://")
    
    # Build the full path and resolve symlinks / ".." components
    full_path = (NOTES_DIR / filename).resolve()
    
    # Security: ensure the resolved path is inside NOTES_DIR
    try:
        full_path.relative_to(NOTES_DIR.resolve())
    except ValueError:
        # Path traversal detected — act as if file not found
        raise FileNotFoundError(f"Access denied: {uri}")
    
    return full_path


# ── Handler 1: list_resources ────────────────────────────────────
@app.list_resources()
async def list_resources() -> list[types.Resource]:
    """
    Scan NOTES_DIR for .md files and return a Resource descriptor
    for each one.
    
    Called by the client when it wants to know what resources exist.
    Does NOT return content — just metadata.
    """
    resources = []
    
    # Ensure the directory exists; if not, return empty list gracefully
    if not NOTES_DIR.exists():
        return resources
    
    # Iterate over all .md files in the directory (non-recursive)
    # Path.glob("*.md") yields Path objects for each matching file
    for md_file in sorted(NOTES_DIR.glob("*.md")):
        # Build a human-readable name from the filename
        # e.g., "getting-started.md" → "Getting Started"
        display_name = md_file.stem.replace("-", " ").replace("_", " ").title()
        
        resources.append(
            types.Resource(
                # URI that clients will pass to read_resource
                uri=filename_to_uri(md_file.name),
                
                # Human-readable label shown in UIs
                name=display_name,
                
                # Optional but helpful: tell client this is Markdown
                mimeType="text/markdown",
                
                # Optional one-line description
                description=f"Markdown notes file: {md_file.name}",
            )
        )
    
    return resources


# ── Handler 2: read_resource ─────────────────────────────────────
@app.read_resource()
async def read_resource(uri: types.AnyUrl) -> str:
    """
    Read and return the content of the resource at `uri`.
    
    The `uri` parameter is the exact URI the client requested
    (e.g., "notes://intro.md"). We resolve it to a file path
    and return the file's text content.
    
    IMPORTANT: Raise an appropriate error if the resource is not
    found. Never return empty content for a missing resource —
    that silently misleads the model.
    """
    # Convert AnyUrl to string for processing
    uri_str = str(uri)
    
    # Validate URI scheme — reject URIs we don't own
    if not uri_str.startswith(f"{URI_SCHEME}://"):
        raise ValueError(f"Unsupported URI scheme: {uri_str}")
    
    # Resolve URI → file path (with security check inside)
    try:
        file_path = uri_to_path(uri_str)
    except FileNotFoundError as e:
        # Re-raise as a clear error message to the client
        raise ValueError(str(e))
    
    # Check that the file actually exists
    if not file_path.exists():
        raise FileNotFoundError(
            f"Resource not found: {uri_str}\n"
            f"Expected file at: {file_path}"
        )
    
    # Check it's actually a file (not a directory)
    if not file_path.is_file():
        raise ValueError(f"URI resolves to a directory, not a file: {uri_str}")
    
    # Read and return the raw text content.
    # The Python SDK automatically wraps this in the correct
    # TextContent envelope with the right mimeType.
    return file_path.read_text(encoding="utf-8")


# ── Entrypoint ───────────────────────────────────────────────────
async def main():
    # Announce startup to stderr (safe — won't corrupt JSON-RPC on stdout)
    import sys
    print(f"Starting markdown-notes-server", file=sys.stderr)
    print(f"Serving .md files from: {NOTES_DIR}", file=sys.stderr)
    
    # Wire up stdio transport and run the server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
```

**Testing it with the MCP Inspector:**

```bash
# 1. Create some test files
mkdir -p data/notes
echo "# Introduction\n\nWelcome to MCP!" > data/notes/intro.md
echo "# Advanced Patterns\n\nLet's go deeper." > data/notes/advanced.md

# 2. Install and run
pip install mcp
mcp dev server.py
# Opens http://localhost:5173

# 3. In the Inspector UI:
#    - Click "Resources" tab
#    - Click "List Resources" → see intro.md and advanced.md
#    - Click a resource → click "Read Resource" → see content
```

**What the response looks like (JSON):**

```json
// resources/list response
{
  "resources": [
    {
      "uri": "notes://advanced.md",
      "name": "Advanced",
      "mimeType": "text/markdown",
      "description": "Markdown notes file: advanced.md"
    },
    {
      "uri": "notes://intro.md",
      "name": "Intro",
      "mimeType": "text/markdown",
      "description": "Markdown notes file: intro.md"
    }
  ]
}

// resources/read response (for "notes://intro.md")
{
  "contents": [
    {
      "uri": "notes://intro.md",
      "mimeType": "text/markdown",
      "text": "# Introduction\n\nWelcome to MCP!"
    }
  ]
}
```

---

## 6. Full TypeScript Example: Exposing Markdown Files

The same concept in TypeScript. Note the differences in error handling and type system usage.

```typescript
// src/server.ts
// ─────────────────────────────────────────────────────────────────
// MCP Server: Expose local Markdown files as resources (TypeScript)
//
// Directory structure:
//   src/server.ts
//   data/notes/
//     intro.md
//     advanced.md
//
// Usage:
//   npm install @modelcontextprotocol/sdk
//   npm run build && npm start
//   # OR: npx @modelcontextprotocol/inspector node dist/server.js
// ─────────────────────────────────────────────────────────────────

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  McpError,
  ErrorCode,
} from "@modelcontextprotocol/sdk/types.js";

import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

// ── Path Setup ────────────────────────────────────────────────────
// In ESM modules, __dirname is not available. We reconstruct it
// using import.meta.url, which gives us the current file's URL.
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Resolve the notes directory relative to the compiled output.
// If dist/server.js is the entry point, go up one level to reach
// the project root, then into data/notes/.
const NOTES_DIR = path.resolve(__dirname, "..", "data", "notes");

// Our custom URI scheme
const URI_SCHEME = "notes";

// ── Helper Functions ──────────────────────────────────────────────
/** Convert a filename like "intro.md" to "notes://intro.md" */
function filenameToUri(filename: string): string {
  return `${URI_SCHEME}://${filename}`;
}

/**
 * Convert a URI like "notes://intro.md" to an absolute file path.
 * Includes a path traversal check.
 */
function uriToPath(uri: string): string {
  // Strip "notes://" to get the filename
  const filename = uri.replace(`${URI_SCHEME}://`, "");

  // Resolve against NOTES_DIR
  const resolvedPath = path.resolve(NOTES_DIR, filename);

  // Security: ensure resolved path stays inside NOTES_DIR
  if (!resolvedPath.startsWith(path.resolve(NOTES_DIR))) {
    throw new McpError(
      ErrorCode.InvalidParams,
      `Access denied: path traversal detected for URI: ${uri}`
    );
  }

  return resolvedPath;
}

// ── Server Setup ──────────────────────────────────────────────────
const server = new Server(
  {
    name: "markdown-notes-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      // Declare that we support resources.
      // Empty object = support listing and reading, no subscriptions.
      resources: {},
    },
  }
);

// ── Handler 1: resources/list ─────────────────────────────────────
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  // Ensure the notes directory exists
  if (!fs.existsSync(NOTES_DIR)) {
    // Return empty list gracefully — don't crash
    return { resources: [] };
  }

  // Read all entries in the directory
  const entries = fs.readdirSync(NOTES_DIR, { withFileTypes: true });

  // Filter to only .md files that are actual files (not directories)
  const mdFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".md"))
    .sort((a, b) => a.name.localeCompare(b.name)); // Sort alphabetically

  // Map each file to a Resource descriptor
  const resources = mdFiles.map((file) => {
    // Build display name: "getting-started.md" → "Getting Started"
    const displayName = file.name
      .replace(/\.md$/, "")                         // remove extension
      .replace(/[-_]/g, " ")                         // dashes/underscores → spaces
      .replace(/\b\w/g, (c) => c.toUpperCase());     // Title Case

    return {
      uri: filenameToUri(file.name),           // "notes://intro.md"
      name: displayName,                        // "Intro"
      mimeType: "text/markdown",
      description: `Markdown notes file: ${file.name}`,
    };
  });

  return { resources };
});

// ── Handler 2: resources/read ─────────────────────────────────────
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  // Extract the URI from the request parameters
  const uri = request.params.uri;

  // Validate the URI scheme
  if (!uri.startsWith(`${URI_SCHEME}://`)) {
    // McpError is the proper way to signal errors in MCP.
    // InvalidParams = the client sent a bad request.
    throw new McpError(
      ErrorCode.InvalidParams,
      `Unsupported URI scheme. Expected "${URI_SCHEME}://", got: ${uri}`
    );
  }

  // Resolve URI to a file path (with security check)
  let filePath: string;
  try {
    filePath = uriToPath(uri);
  } catch (error) {
    // Re-throw McpError as-is; wrap unexpected errors
    if (error instanceof McpError) throw error;
    throw new McpError(ErrorCode.InternalError, `Failed to resolve URI: ${uri}`);
  }

  // Check if the file exists
  if (!fs.existsSync(filePath)) {
    // InvalidRequest = the client asked for something that doesn't exist.
    throw new McpError(
      ErrorCode.InvalidRequest,
      `Resource not found: ${uri}\nExpected file at: ${filePath}`
    );
  }

  // Confirm it's a file, not a directory
  const stat = fs.statSync(filePath);
  if (!stat.isFile()) {
    throw new McpError(
      ErrorCode.InvalidParams,
      `URI resolves to a directory, not a file: ${uri}`
    );
  }

  // Read the file content as UTF-8 text
  const content = fs.readFileSync(filePath, "utf-8");

  // Return the content in the required shape:
  // { contents: [{ uri, mimeType, text }] }
  return {
    contents: [
      {
        uri,                          // Echo back the requested URI
        mimeType: "text/markdown",    // Tell client what type this is
        text: content,                // The actual file contents
      },
    ],
  };
});

// ── Entrypoint ────────────────────────────────────────────────────
async function main() {
  // Log startup info to stderr (never stdout — that's the JSON-RPC channel)
  console.error(`Starting markdown-notes-server`);
  console.error(`Serving .md files from: ${NOTES_DIR}`);

  // Create the stdio transport and connect the server to it
  const transport = new StdioServerTransport();
  await server.connect(transport);

  console.error("Server connected and running");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
```

**Key differences vs Python:**

| Aspect | Python SDK | TypeScript SDK |
|--------|-----------|----------------|
| Error type | `FileNotFoundError`, `ValueError` | `McpError(ErrorCode.X, ...)` |
| Handler style | Decorator (`@app.list_resources()`) | `setRequestHandler(Schema, fn)` |
| Request access | Handler gets args directly | Handler gets full `request` object |
| `__dirname` | Available natively | Must reconstruct from `import.meta.url` |
| Type safety | `types.Resource`, `types.AnyUrl` | Inferred from `RequestSchema` |

---

## 7. Resource Templates (Dynamic URIs)

Resource templates let you **declare a pattern of URIs** rather than listing every resource individually. They're perfect when resources are dynamic — for example, when a user can specify which file they want by name.

### 7.1 URI Template Syntax

MCP uses [RFC 6570](https://tools.ietf.org/html/rfc6570) URI Templates — the same standard used by OpenAPI and many REST frameworks:

```
Template:  notes://{filename}
                    ────────
                    Variable → client fills this in

Examples:
  notes://{filename}              → notes://intro.md
  db://users/{userId}/profile    → db://users/42/profile
  repo://{owner}/{repo}/file     → repo://octocat/Hello-World/README.md
```

**How templates appear in listResources:**

```json
{
  "resourceTemplates": [
    {
      "uriTemplate": "notes://{filename}",
      "name":        "Any Notes File",
      "description": "Read any .md file from the notes directory",
      "mimeType":    "text/markdown"
    }
  ]
}
```

The client can then construct URIs from the template and call `resources/read` directly — without waiting for you to list every possible file.

### 7.2 Python Implementation

```python
# Add this to your server.py alongside list_resources and read_resource

from mcp import types

@app.list_resource_templates()
async def list_resource_templates() -> list[types.ResourceTemplate]:
    """
    Expose a URI template so clients can dynamically request
    any .md file by name, without it appearing in list_resources().
    
    A single template can represent unlimited concrete resources.
    """
    return [
        types.ResourceTemplate(
            # The template pattern — {filename} is the variable part
            uriTemplate=f"{URI_SCHEME}://{{filename}}",
            
            # Human-readable name for the template
            name="Notes File (by name)",
            
            # Explanation for the model / developer
            description=(
                "Read any Markdown file from the notes directory. "
                "Replace {filename} with the actual filename, e.g. "
                "'notes://intro.md'."
            ),
            
            mimeType="text/markdown",
        )
    ]

# NOTE: read_resource() already handles dynamic URIs — no changes needed!
# When the client calls resources/read with "notes://any-file.md",
# the same read_resource handler fires and resolves the path.
```

### 7.3 TypeScript Implementation

```typescript
import {
  ListResourceTemplatesRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Add this handler alongside your other setRequestHandler calls

server.setRequestHandler(ListResourceTemplatesRequestSchema, async () => {
  return {
    resourceTemplates: [
      {
        // The URI template — curly braces denote variables
        uriTemplate: `${URI_SCHEME}://{filename}`,

        // Human-readable label
        name: "Notes File (by name)",

        // Descriptive hint for the model
        description:
          "Read any Markdown file from the notes directory. " +
          "Replace {filename} with the actual filename, e.g. 'notes://intro.md'.",

        mimeType: "text/markdown",
      },
    ],
  };
});

// ReadResourceRequestSchema handler stays unchanged —
// it already handles any URI matching our scheme.
```

**Templates vs Static Resources — when to use which:**

```
┌────────────────────────────────────────────────────────────────┐
│  Static Resources (list_resources)                            │
│  ─────────────────────────────────                            │
│  Use when:                                                    │
│  • Resources are finite and known at startup                  │
│  • You want the client to discover resources automatically    │
│  • Resources change infrequently                              │
│  Example: a fixed set of config files                        │
│                                                               │
│  Resource Templates (list_resource_templates)                 │
│  ────────────────────────────────────────────                 │
│  Use when:                                                     │
│  • Resources are infinite or user-specified                   │
│  • You want the user/model to request by parameter           │
│  • Resources are generated on-the-fly from inputs            │
│  Example: any file by name, DB row by ID, API by endpoint   │
│                                                               │
│  TIP: Use BOTH together for best coverage:                   │
│  • list_resources → "here are our featured resources"        │
│  • list_resource_templates → "you can also request anything" │
└────────────────────────────────────────────────────────────────┘
```

---

## 8. Common Pitfalls & How to Avoid Them

### Pitfall 1: Wrong MIME Types

```python
# ❌ Wrong — using text/plain for JSON
types.Resource(uri="db://schema", mimeType="text/plain")

# ✅ Correct — use the specific MIME type
types.Resource(uri="db://schema", mimeType="application/json")
```

Why it matters: Claude and other clients use MIME types to format content for display, apply syntax highlighting, and decide how to process the data. Using `text/plain` for JSON means the model may not recognize it as structured data.

---

### Pitfall 2: No Error Handling for File Not Found

```python
# ❌ Wrong — silently returns empty string or crashes with unhelpful error
@app.read_resource()
async def read_resource(uri):
    path = uri_to_path(str(uri))
    return open(path).read()   # Raises FileNotFoundError with no context

# ✅ Correct — explicit, helpful error message
@app.read_resource()
async def read_resource(uri):
    path = uri_to_path(str(uri))
    if not path.exists():
        raise FileNotFoundError(
            f"Resource not found: {uri}. "
            f"Available resources: {[f.name for f in NOTES_DIR.glob('*.md')]}"
        )
    return path.read_text(encoding="utf-8")
```

---

### Pitfall 3: Writing to stdout from the Server

```python
# ❌ Wrong — print() writes to stdout, corrupting the JSON-RPC stream
print("Server started!")                  # NEVER do this

# ✅ Correct — write to stderr
import sys
print("Server started!", file=sys.stderr) # Safe
```

```typescript
// ❌ Wrong
console.log("Server started!");           // Goes to stdout — NEVER do this

// ✅ Correct
console.error("Server started!");         // Goes to stderr — safe
```

---

### Pitfall 4: Returning URI in List but Not Handling It in Read

```python
# ❌ Wrong — listing a resource with URI "notes://secret.md"
# but read_resource only handles "file://" scheme URIs.
# Client will call read_resource("notes://secret.md") and get an error.

@app.list_resources()
async def list_resources():
    return [types.Resource(uri="notes://secret.md", name="Secret")]

@app.read_resource()
async def read_resource(uri):
    # BUG: Only handles file:// URIs — notes:// will silently fail
    if str(uri).startswith("file://"):
        ...

# ✅ Correct — handle exactly the scheme you advertise
@app.read_resource()
async def read_resource(uri):
    if str(uri).startswith("notes://"):
        ...
```

---

### Pitfall 5: Path Traversal Vulnerability

```python
# ❌ Dangerous — user can request "notes://../../../etc/passwd"
@app.read_resource()
async def read_resource(uri):
    filename = str(uri).removeprefix("notes://")
    path = NOTES_DIR / filename       # Allows path traversal!
    return path.read_text()

# ✅ Safe — resolve and verify the path stays inside NOTES_DIR
@app.read_resource()
async def read_resource(uri):
    filename = str(uri).removeprefix("notes://")
    resolved = (NOTES_DIR / filename).resolve()
    if not resolved.is_relative_to(NOTES_DIR.resolve()):
        raise ValueError("Access denied")
    return resolved.read_text()
```

---

### Pitfall 6: Returning Binary Content as `text`

```python
# ❌ Wrong — PNG files are binary; you can't return them as text
@app.read_resource()
async def read_resource(uri):
    return Path("image.png").read_text()   # Will raise UnicodeDecodeError

# ✅ Correct — base64-encode binary content
import base64
from mcp import types

@app.read_resource()
async def read_resource(uri):
    raw_bytes = Path("image.png").read_bytes()
    return types.BlobResourceContents(
        uri=str(uri),
        mimeType="image/png",
        blob=base64.b64encode(raw_bytes).decode("ascii")
    )
```

---

## 9. Mental Model Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  Resources — The Complete Mental Model                         │
│                                                                 │
│  WHAT:  Read-only, addressable pieces of data                  │
│  WHY:   Give the AI model context to reason with               │
│  HOW:   Two handlers — list (discovery) + read (content)       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  list_resources()                                       │   │
│  │  → returns [Resource metadata]                         │   │
│  │  → like ls: "here's what exists"                       │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │  (client picks a URI)               │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │  read_resource(uri)                                     │   │
│  │  → returns { text: "..." } or { blob: "base64..." }    │   │
│  │  → like cat: "here's the content"                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  KEY RULES:                                                     │
│  1. Resources are READ-ONLY. No mutations, no side effects.    │
│  2. URIs must be stable. Don't change them across restarts.   │
│  3. Always raise an error for unknown URIs.                    │
│  4. Never write to stdout — use stderr for logging.           │
│  5. Validate and sanitize file paths to prevent traversal.    │
│  6. Match MIME types precisely to content type.               │
└─────────────────────────────────────────────────────────────────┘
```

---

> **Next Note →** [06 — Creating Tools](./06-creating-tools.md)
> Learn how to implement `list_tools` and `call_tool` handlers to give the model the ability to perform actions — not just read data.

# ============================================================
#  P01 — Echo Server
#  The simplest possible MCP server.
#
#  What this server does:
#    - Exposes 2 tools:
#        echo        → returns whatever text you send it
#        reverse     → returns the text reversed
#    - Exposes 1 static resource:
#        info://server-info → a description of this server
#    - Exposes 1 prompt:
#        try-echo → a prompt that demos the echo tool
#
#  This project teaches:
#    - [x] MCP server initialization
#    - [x] Registering tool, resource, and prompt handlers
#    - [x] The isError response pattern
#    - [x] How to test with the MCP Inspector
#    - [x] How to connect to Claude Desktop
# ============================================================

import asyncio
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
    Resource,
    ReadResourceResult,
    TextResourceContents,
    Prompt,
    PromptArgument,
    GetPromptResult,
    PromptMessage,
)

# ── 1. Create the server ────────────────────────────────────
#
# The name you pass here shows up in Claude Desktop's UI
# and in the MCP Inspector tab.
#
app = Server("echo-server")


# ── 2. Tools ────────────────────────────────────────────────
#
# @app.list_tools() is called by the client once on connect
# to discover what tools this server provides.
#
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ── Tool 1: echo ──────────────────────────────────
        Tool(
            name="echo",
            description=(
                "Repeats the provided text back exactly as given. "
                "Use this to test that the MCP server is connected and responding. "
                "Returns the input text unchanged."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to echo back",
                    },
                    "repeat": {
                        "type": "integer",
                        "description": "How many times to repeat the text (default: 1)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 1,
                    },
                },
                "required": ["text"],
            },
        ),
        # ── Tool 2: reverse ───────────────────────────────
        Tool(
            name="reverse",
            description=(
                "Returns the provided text with its characters reversed. "
                "For example 'hello' becomes 'olleh'. "
                "Use to demonstrate that tools can transform their inputs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to reverse",
                    }
                },
                "required": ["text"],
            },
        ),
        # ── Tool 3: word_count ────────────────────────────
        Tool(
            name="word_count",
            description=(
                "Counts the number of words, characters, and lines in the provided text. "
                "Returns a summary with all three counts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to analyse",
                    }
                },
                "required": ["text"],
            },
        ),
    ]


# ── 3. Tool handler ─────────────────────────────────────────
#
# @app.call_tool() is called every time the LLM invokes a tool.
# name  → which tool was called
# arguments → the dict of inputs the LLM provided
#
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:

    # ── echo ──────────────────────────────────────────────
    if name == "echo":
        text = arguments.get("text", "")
        repeat = arguments.get("repeat", 1)

        # Validate: text must not be empty
        if not text.strip():
            return CallToolResult(
                content=[TextContent(type="text", text="Error: text cannot be empty.")],
                isError=True,
            )

        output = (text + "\n") * repeat
        return CallToolResult(
            content=[TextContent(type="text", text=output.rstrip())]
        )

    # ── reverse ───────────────────────────────────────────
    elif name == "reverse":
        text = arguments.get("text", "")

        if not text:
            return CallToolResult(
                content=[TextContent(type="text", text="Error: text cannot be empty.")],
                isError=True,
            )

        reversed_text = text[::-1]  # Python string reversal
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Original : {text}\nReversed : {reversed_text}",
                )
            ]
        )

    # ── word_count ────────────────────────────────────────
    elif name == "word_count":
        text = arguments.get("text", "")

        words = len(text.split())
        chars = len(text)
        chars_no_spaces = len(text.replace(" ", ""))
        lines = len(text.splitlines()) if text else 0

        result = (
            f"Text Analysis\n"
            f"─────────────────\n"
            f"Words      : {words}\n"
            f"Characters : {chars} (with spaces)\n"
            f"Characters : {chars_no_spaces} (without spaces)\n"
            f"Lines      : {lines}"
        )

        return CallToolResult(content=[TextContent(type="text", text=result)])

    # ── unknown tool ──────────────────────────────────────
    else:
        return CallToolResult(
            content=[
                TextContent(type="text", text=f"Unknown tool: '{name}'")
            ],
            isError=True,
        )


# ── 4. Resources ────────────────────────────────────────────
#
# Resources are read-only data that the LLM can access.
# Think of them like GET endpoints that return content.
#
@app.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="info://server-info",
            name="Echo Server Info",
            description="General information about this MCP server and its capabilities.",
            mimeType="text/plain",
        ),
        Resource(
            uri="info://how-to-use",
            name="How to Use",
            description="Instructions on how to use the echo server's tools.",
            mimeType="text/markdown",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:

    if uri == "info://server-info":
        content = (
            "Echo Server v1.0\n"
            "================\n"
            "A simple MCP server built for learning.\n\n"
            "Tools available:\n"
            "  - echo       : repeats text back\n"
            "  - reverse    : reverses the characters of text\n"
            "  - word_count : counts words, characters, and lines\n\n"
            "Resources available:\n"
            "  - info://server-info  : this file\n"
            "  - info://how-to-use   : usage instructions\n\n"
            "Transport: stdio (local subprocess)\n"
            "Protocol: MCP over JSON-RPC 2.0\n"
        )
        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=uri,
                    mimeType="text/plain",
                    text=content,
                )
            ]
        )

    elif uri == "info://how-to-use":
        content = (
            "# How to Use the Echo Server\n\n"
            "## Testing with MCP Inspector\n"
            "```bash\n"
            "npx @modelcontextprotocol/inspector python server.py\n"
            "```\n"
            "Then open the browser UI and:\n"
            "1. Click **Tools** → select `echo` → type any text → click **Call Tool**\n"
            "2. Click **Resources** → click `Echo Server Info` → see the content\n\n"
            "## Testing in Claude Desktop\n"
            "Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:\n"
            "```json\n"
            '{\n  "mcpServers": {\n    "echo-server": {\n'
            '      "command": "python3",\n'
            '      "args": ["/full/path/to/server.py"]\n'
            "    }\n  }\n}\n"
            "```\n"
            "Then ask Claude: *'Echo the phrase hello world back to me'*\n"
        )
        return ReadResourceResult(
            contents=[
                TextResourceContents(
                    uri=uri,
                    mimeType="text/markdown",
                    text=content,
                )
            ]
        )

    # Unknown URI
    raise ValueError(f"Resource not found: {uri}")


# ── 5. Prompts ──────────────────────────────────────────────
#
# Prompts are reusable conversation starters.
# Users can select them from the UI (e.g. the / menu in Claude Desktop).
#
@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="try-echo",
            description="A starter prompt that demonstrates all three echo server tools.",
            arguments=[
                PromptArgument(
                    name="your_name",
                    description="Your name, to personalise the demo",
                    required=False,
                )
            ],
        )
    ]


@app.get_prompt()
async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
    if name == "try-echo":
        your_name = arguments.get("your_name", "there")
        return GetPromptResult(
            description="Demo all three echo server tools",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            f"Hi {your_name}! Let's test the echo server.\n\n"
                            "Please do the following steps one by one:\n"
                            "1. Use the `echo` tool to echo the phrase 'MCP is awesome!' twice.\n"
                            "2. Use the `reverse` tool on the phrase 'Hello World'.\n"
                            "3. Use the `word_count` tool on this sentence: "
                            "'The quick brown fox jumps over the lazy dog.'\n"
                            "4. Read the resource at info://server-info and tell me what you find.\n\n"
                            "Show me the result of each step."
                        ),
                    ),
                )
            ],
        )

    raise ValueError(f"Unknown prompt: {name}")


# ── 6. Run ──────────────────────────────────────────────────
#
# stdio_server() manages the stdin/stdout streams for the
# MCP protocol. NEVER print to stdout below this point —
# use sys.stderr for any debug output.
#
async def main():
    print("Echo server starting...", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )

if __name__ == "__main__":
    asyncio.run(main())

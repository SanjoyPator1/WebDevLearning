# 06 — Creating Tools

> **Phase:** Building Your First MCP Server  
> **Goal:** Define tools that the LLM can call to take real actions, with full working examples in Python and TypeScript.

---

## Table of Contents
1. [Tools vs Resources — When to Use Which](#1-tools-vs-resources--when-to-use-which)
2. [Tool Anatomy Deep Dive](#2-tool-anatomy-deep-dive)
3. [Writing Great Tool Descriptions](#3-writing-great-tool-descriptions)
4. [JSON Schema for Tool Inputs](#4-json-schema-for-tool-inputs)
5. [Full Example: Python Weather Tool](#5-full-example-python-weather-tool)
6. [Full Example: TypeScript Calculator Tool](#6-full-example-typescript-calculator-tool)
7. [Returning Errors Gracefully](#7-returning-errors-gracefully)
8. [The Tool Call Flow (Diagram)](#8-the-tool-call-flow-diagram)
9. [Best Practices](#9-best-practices)

---

## 1. Tools vs Resources — When to Use Which

```
Quick Decision
────────────────────────────────────────────────────────────

  Question: What should this capability be?

  "Read data that exists at a known address"  ──►  Resource
  "Do something / fetch dynamic data"         ──►  Tool
  "Modify state, call an API, run code"       ──►  Tool (always)

  Examples:
  ├── Read a file at a known path         ──►  Resource
  ├── Search for files matching a query   ──►  Tool
  ├── Get the current weather             ──►  Tool
  ├── A database record by ID            ──►  Resource
  └── Run a SQL query                    ──►  Tool
```

---

## 2. Tool Anatomy Deep Dive

Every tool has four parts. The SDK + JSON Schema handles the wire format — you just define:

```
Tool Structure
────────────────────────────────────────────────────────────

  name         ──►  Unique identifier, snake_case
                    e.g. "get_weather", "create_issue", "send_email"

  description  ──►  Plain English explanation for the LLM
                    THIS IS WHAT THE MODEL READS TO DECIDE WHEN TO USE IT
                    Make it detailed and precise

  inputSchema  ──►  JSON Schema object describing all parameters
                    Defines what arguments the LLM must/can provide

  handler      ──►  Your async function that does the actual work
                    Receives validated arguments, returns a result
```

---

## 3. Writing Great Tool Descriptions

The description is **the most important field** in a tool definition. The LLM decides whether and when to call a tool based solely on its name and description.

```
Bad vs Good Descriptions
────────────────────────────────────────────────────────────

  ❌ BAD: "Gets weather"
     Problem: Too vague. When should the LLM call this?
              What does it return? What inputs does it need?

  ✅ GOOD: "Get the current weather conditions for a specified city.
            Returns the temperature in Celsius, a short conditions
            description (e.g. 'Partly Cloudy'), humidity percentage,
            and wind speed in km/h. Use this when the user asks about
            current weather, temperature, or conditions in any city."

  Tips:
  ├── Say WHAT it does
  ├── Say WHAT it returns
  ├── Say WHEN to use it (trigger phrases help the model)
  └── Mention any limitations (e.g. "only for current weather, not forecasts")
```

---

## 4. JSON Schema for Tool Inputs

Tools define their inputs using [JSON Schema](https://json-schema.org/). Here is a reference of common patterns:

```json
{
  "type": "object",
  "properties": {

    // Simple string
    "city": {
      "type": "string",
      "description": "Name of the city, e.g. 'London' or 'New York'"
    },

    // Enum — fixed list of allowed values
    "unit": {
      "type": "string",
      "enum": ["celsius", "fahrenheit"],
      "description": "Temperature unit to use",
      "default": "celsius"
    },

    // Integer with range constraint
    "days": {
      "type": "integer",
      "minimum": 1,
      "maximum": 7,
      "description": "Number of forecast days (1-7)"
    },

    // Boolean flag
    "include_humidity": {
      "type": "boolean",
      "description": "Whether to include humidity data",
      "default": false
    },

    // Array of strings
    "labels": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of labels to apply"
    }

  },
  "required": ["city"]  // only city is required; others are optional
}
```

---

## 5. Full Example: Python Weather Tool

A complete, runnable server with a `get_weather` tool that calls a mock weather API:

```python
# weather_server.py — Python MCP server with a weather tool

import asyncio
import json
import urllib.request
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

app = Server("weather-server")


# ── Tool Definition ────────────────────────────────────────
@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_weather",
            description=(
                "Get the current weather conditions for a city. "
                "Returns temperature in Celsius, weather description, "
                "humidity, and wind speed. Use when the user asks about "
                "weather, temperature, or conditions in any location."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'London' or 'Tokyo'"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                        "default": "celsius"
                    }
                },
                "required": ["city"]
            }
        )
    ]


# ── Tool Handler ───────────────────────────────────────────
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    if name == "get_weather":
        return await handle_get_weather(arguments)

    return CallToolResult(
        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
        isError=True
    )


async def handle_get_weather(arguments: dict) -> CallToolResult:
    city = arguments.get("city", "").strip()
    unit = arguments.get("unit", "celsius")

    if not city:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: city is required")],
            isError=True
        )

    # --- In a real server, call a weather API here ---
    # Example with Open-Meteo (free, no API key needed):
    # city_coords = get_coordinates(city)  # geocode the city
    # url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"

    # For this example, we use mock data:
    mock_data = {
        "london": {"temp_c": 15, "description": "Partly Cloudy", "humidity": 72, "wind_kph": 18},
        "tokyo":  {"temp_c": 22, "description": "Clear Sky",     "humidity": 58, "wind_kph": 10},
        "mumbai": {"temp_c": 34, "description": "Humid & Hazy",  "humidity": 88, "wind_kph": 12},
    }

    weather = mock_data.get(city.lower())
    if not weather:
        return CallToolResult(
            content=[TextContent(type="text", text=f"City '{city}' not found in weather database.")],
            isError=True
        )

    temp = weather["temp_c"]
    if unit == "fahrenheit":
        temp = round(temp * 9 / 5 + 32, 1)
        unit_symbol = "°F"
    else:
        unit_symbol = "°C"

    result = (
        f"Weather in {city.title()}:\n"
        f"  Temperature: {temp}{unit_symbol}\n"
        f"  Conditions:  {weather['description']}\n"
        f"  Humidity:    {weather['humidity']}%\n"
        f"  Wind Speed:  {weather['wind_kph']} km/h"
    )

    return CallToolResult(
        content=[TextContent(type="text", text=result)]
    )


# ── Main ───────────────────────────────────────────────────
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. Full Example: TypeScript Calculator Tool

```typescript
// calc-server.ts — TypeScript MCP server with a calculator tool

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const server = new Server(
  { name: "calculator-server", version: "0.1.0" },
  { capabilities: { tools: {} } }
);


// ── Tool Definition ────────────────────────────────────────
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "calculate",
      description:
        "Evaluate a mathematical expression and return the result. " +
        "Supports +, -, *, /, ** (power), and parentheses. " +
        "Use when the user asks for any mathematical calculation.",
      inputSchema: {
        type: "object",
        properties: {
          expression: {
            type: "string",
            description: "Math expression to evaluate, e.g. '(3 + 4) * 2' or '2 ** 10'",
          },
        },
        required: ["expression"],
      },
    },
  ],
}));


// ── Tool Handler ───────────────────────────────────────────
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "calculate") {
    const { expression } = request.params.arguments as { expression: string };

    // Safety: only allow safe math characters
    if (!/^[\d\s\+\-\*\/\(\)\.\*\*]+$/.test(expression)) {
      return {
        content: [{ type: "text", text: "Error: Invalid characters in expression." }],
        isError: true,
      };
    }

    try {
      // Note: In production, use a proper math parser library (e.g. mathjs)
      // eval() is used here for simplicity in a controlled context
      const result = Function(`"use strict"; return (${expression})`)();

      if (typeof result !== "number" || !isFinite(result)) {
        throw new Error("Result is not a valid number");
      }

      return {
        content: [
          { type: "text", text: `${expression} = ${result}` },
        ],
      };
    } catch (err) {
      return {
        content: [
          { type: "text", text: `Error evaluating expression: ${(err as Error).message}` },
        ],
        isError: true,
      };
    }
  }

  return {
    content: [{ type: "text", text: `Unknown tool: ${request.params.name}` }],
    isError: true,
  };
});


// ── Main ───────────────────────────────────────────────────
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Calculator MCP server started");
}

main().catch(console.error);
```

---

## 7. Returning Errors Gracefully

Always use `isError: true` instead of throwing exceptions from your tool handler:

```python
# ✅ Correct — structured error the LLM can understand and recover from
return CallToolResult(
    content=[TextContent(type="text", text="Error: API rate limit exceeded. Try again in 60s.")],
    isError=True
)

# ❌ Wrong — unhandled exception crashes the server process
raise RuntimeError("API rate limit exceeded")
```

The LLM receives the error message as content and can **tell the user what went wrong** gracefully, instead of the tool silently failing.

---

## 8. The Tool Call Flow (Diagram)

```
Full Tool Execution Flow
────────────────────────────────────────────────────────────

  User types a message
    │
    ▼
  LLM receives message + list of available tools
    │
    ├── Does any tool match the intent?
    │   └── Yes: LLM generates a tool_use block
    │       { name: "get_weather", input: { city: "London" } }
    │
    ▼
  Host/Client sends tools/call to MCP Server
    { method: "tools/call", params: { name: "get_weather", arguments: {...} } }
    │
    ▼
  Server's call_tool handler runs
    ├── Validates inputs
    ├── Executes logic (API call, file read, computation)
    └── Returns CallToolResult
    │
    ▼
  Client sends result back to LLM
    { content: [{ type: "text", text: "London: 15°C, Partly Cloudy" }] }
    │
    ▼
  LLM incorporates result into its response to the user
```

---

## 9. Best Practices

| Practice | Why it matters |
|---|---|
| Write detailed descriptions | The LLM uses them to decide when to call the tool |
| Use `required` in inputSchema | Prevents the LLM from omitting critical args |
| Always return `isError: true` for failures | LLM can handle errors gracefully |
| Validate inputs in your handler | Never trust that the LLM sent valid data |
| Keep tools focused and single-purpose | Easier for the LLM to choose the right tool |
| Use snake_case for tool names | Consistent convention across the MCP ecosystem |
| Never use `stdout` for logging | It corrupts the stdio transport |

---

> **Previous Note ←** `05-exposing-resources.md`  
> **Next Note →** `07-connecting-to-claude-desktop.md` — Wiring your server into Claude Desktop and testing it for real.

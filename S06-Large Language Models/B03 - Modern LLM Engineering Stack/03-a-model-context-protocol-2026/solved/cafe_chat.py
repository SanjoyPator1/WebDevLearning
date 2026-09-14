# ============================================================
# CAFÉ CHAT — terminal agentic chat over your MCP server
# RUN:
#   Terminal 1:  python solved/cafe_project.py
#   Terminal 2:  python solved/cafe_chat.py
#
# Providers (OpenAI-compatible API):
#   gemini  — https://generativelanguage.googleapis.com/v1beta/openai/
#             Needs GEMINI_API_KEY in .env
#   ollama  — http://localhost:11434/v1  (model: qwen3:8b)
#             Free, local, nothing leaves your machine
# ============================================================
#
# HOW THE AGENT LOOP WORKS
# ─────────────────────────
#  1. You type a message.
#  2. History (system + all past turns) + tool schemas → LLM
#  3. If LLM says "call a tool" → we call MCP server directly
#  4. If MCP returns input_required → we ask YOU in the terminal
#  5. Tool result is added to history → back to step 2
#  6. If LLM says "here is my answer" (no more tool calls) → print it
#  7. Wait for your next message (step 1)
# ============================================================

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx2 as httpx
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CAFE_URL          = f"http://127.0.0.1:{os.environ.get('CAFE_MCP_PORT', '3010')}/mcp"
PROTOCOL_VERSION  = "2026-07-28"

GEMINI_BASE_URL   = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL      = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

OLLAMA_BASE_URL   = "http://localhost:11434/v1"
OLLAMA_MODEL      = "qwen3:8b"

DEFAULT_PROVIDER  = "gemini"   # change to "ollama" to flip the default


# ─────────────────────────────────────────────
# TERMINAL COLOURS (no extra deps)
# ─────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[36m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    RED     = "\033[31m"
    WHITE   = "\033[97m"


def banner(text: str) -> None:
    width = 60
    print(f"\n{C.CYAN}{'─' * width}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}  {text}{C.RESET}")
    print(f"{C.CYAN}{'─' * width}{C.RESET}")


def step(icon: str, label: str, detail: str = "") -> None:
    print(f"  {C.DIM}{icon}{C.RESET} {C.BOLD}{label}{C.RESET}", end="")
    if detail:
        print(f"  {C.DIM}{detail}{C.RESET}", end="")
    print()


def mcp_req(method: str, args: dict) -> None:
    args_str = json.dumps(args, ensure_ascii=False)
    if len(args_str) > 80:
        args_str = args_str[:77] + "..."
    print(f"  {C.BLUE}→ MCP{C.RESET}  {C.BOLD}{method}{C.RESET}  {C.DIM}{args_str}{C.RESET}")


def mcp_res(summary: str, is_error: bool = False) -> None:
    colour = C.RED if is_error else C.GREEN
    icon   = "✗" if is_error else "✓"
    print(f"  {colour}← MCP{C.RESET}  {colour}{icon} {summary}{C.RESET}")


def llm_thinking(provider: str) -> None:
    print(f"  {C.MAGENTA}→ LLM{C.RESET}   calling {C.BOLD}{provider}{C.RESET} ...")


def llm_tool_call(name: str, args: dict) -> None:
    args_str = json.dumps(args, ensure_ascii=False)
    if len(args_str) > 80:
        args_str = args_str[:77] + "..."
    print(f"  {C.MAGENTA}← LLM{C.RESET}   wants tool {C.BOLD}{C.YELLOW}{name}{C.RESET}  {C.DIM}{args_str}{C.RESET}")


def llm_answer(text: str) -> None:
    print(f"\n{C.GREEN}{C.BOLD}Assistant:{C.RESET}")
    # Render standard Markdown beautifully in the terminal
    console = Console()
    console.print(Markdown(text))
    print()


def mrtr_prompt(message: str) -> None:
    print(f"\n  {C.YELLOW}⚠  MCP needs your input:{C.RESET}")
    print(f"  {C.YELLOW}   {message}{C.RESET}")


# ─────────────────────────────────────────────
# .ENV LOADER  (same pattern as agent_client.py)
# ─────────────────────────────────────────────
def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return


_load_dotenv()


# ─────────────────────────────────────────────
# LLM CLIENT  (OpenAI-compatible for both)
# ─────────────────────────────────────────────
def make_llm_client(provider: str) -> "tuple[OpenAI, str]":
    """Return (client, model_name) for the chosen provider."""
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print(f"{C.RED}ERROR: GEMINI_API_KEY not set in .env{C.RESET}")
            sys.exit(1)
        client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
        return client, GEMINI_MODEL
    elif provider == "ollama":
        client = OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL)
        return client, OLLAMA_MODEL
    else:
        print(f"{C.RED}ERROR: Unknown provider '{provider}'. Use 'gemini' or 'ollama'.{C.RESET}")
        sys.exit(1)


# ─────────────────────────────────────────────
# MCP RAW CLIENT  (follows raw_client.py patterns)
# ─────────────────────────────────────────────
_META: dict[str, Any] = {
    "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
    "io.modelcontextprotocol/clientInfo": {"name": "cafe-chat", "version": "1.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
}

_NAME_KEY: dict[str, str] = {
    "tools/call": "name",
    "prompts/get": "name",
    "resources/read": "uri",
}


def _mcp_post(method: str, params: dict[str, Any], req_id: int) -> dict:
    """Single synchronous JSON-RPC request to the MCP server."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    key = _NAME_KEY.get(method)
    if key and key in params:
        headers["Mcp-Name"] = params[key]

    body_params = {**params, "_meta": _META}
    body = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": body_params}

    response = httpx.post(CAFE_URL, headers=headers, json=body, timeout=30)
    ct = response.headers.get("content-type", "")
    if ct.startswith("text/event-stream"):
        for line in response.text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
        raise RuntimeError("SSE stream ended with no data: line")
    return response.json()


def mcp_list_tools() -> list[dict]:
    result = _mcp_post("tools/list", {}, 0)
    return result["result"]["tools"]


def mcp_call_tool(
    name: str,
    arguments: dict,
    req_id: int,
) -> dict:
    """
    Call a tool. Handles MRTR: if the server returns input_required,
    prompts the user in the terminal and retries automatically.
    Returns the final result dict (always resultType: "complete").
    """
    params: dict[str, Any] = {"name": name, "arguments": arguments}

    mcp_req(name, arguments)
    raw = _mcp_post("tools/call", params, req_id)
    result = raw.get("result") or raw.get("error", {})

    # MRTR loop: server may ask for human input before completing
    while result.get("resultType") == "input_required":
        request_state = result["requestState"]
        input_requests: dict = result.get("inputRequests", {})

        collected: dict[str, Any] = {}
        for field_name, field_spec in input_requests.items():
            msg = field_spec["params"].get("message", f"Please provide {field_name}:")
            schema = field_spec["params"].get("schema", {})
            props = schema.get("properties", {})

            mrtr_prompt(msg)
            collected_content: dict[str, Any] = {}
            for prop_name, prop_def in props.items():
                prop_type = prop_def.get("type", "string")
                if prop_type == "boolean":
                    raw_val = input(f"  {C.YELLOW}  {prop_name} [y/n]: {C.RESET}").strip().lower()
                    collected_content[prop_name] = raw_val in ("y", "yes", "true", "1")
                else:
                    raw_val = input(f"  {C.YELLOW}  {prop_name}: {C.RESET}").strip()
                    collected_content[prop_name] = raw_val
            collected[field_name] = {"action": "accept", "content": collected_content}

        mcp_req(f"{name} [round 2 — your answers sent]", arguments)
        raw = _mcp_post(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,   # UNCHANGED — protocol requires this
                "inputResponses": collected,
                "requestState": request_state,
            },
            req_id + 1000,
        )
        result = raw.get("result") or raw.get("error", {})

    is_error = result.get("isError", False)
    content = result.get("content", [])
    text_summary = content[0]["text"] if content else "(no content)"
    if len(text_summary) > 120:
        text_summary = text_summary[:117] + "..."
    mcp_res(text_summary, is_error=is_error)
    return result


# ─────────────────────────────────────────────
# TOOL SCHEMAS  (OpenAI function format)
# ─────────────────────────────────────────────
def build_tool_schemas(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tools/list entries into the OpenAI tools format."""
    schemas = []
    for t in mcp_tools:
        schemas.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        })
    return schemas


# ─────────────────────────────────────────────
# THE AGENTIC LOOP
# ─────────────────────────────────────────────
def run_agent_turn(
    history: list[dict],
    tool_schemas: list[dict],
    llm: OpenAI,
    model: str,
    provider: str,
) -> None:
    """
    Given the conversation history, call the LLM, execute any tool calls
    it wants, and loop until it produces a plain text answer.
    Mutates `history` in place.
    """
    req_id = 1

    while True:
        llm_thinking(provider)

        response = llm.chat.completions.create(
            model=model,
            messages=history,
            tools=tool_schemas,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        # ── LLM wants to call one or more tools ───────────────────────────
        if msg.tool_calls:
            # Use model_dump() to preserve ALL fields the API returned,
            # including `thought_signature` that Gemini thinking models
            # embed inside each function_call part. Rebuilding the dict
            # by hand drops that field and causes a 400 on the next turn.
            history.append(msg.model_dump(exclude_none=True))

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)

                llm_tool_call(fn_name, fn_args)

                result = mcp_call_tool(fn_name, fn_args, req_id)
                req_id += 1

                # Build a text representation to feed back into the LLM
                if result.get("structuredContent"):
                    result_text = json.dumps(result["structuredContent"], ensure_ascii=False)
                elif result.get("content"):
                    result_text = "\n".join(
                        c.get("text", "") for c in result["content"] if c.get("type") == "text"
                    )
                else:
                    result_text = json.dumps(result)

                history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text,
                })

            # Loop: let LLM decide what to do with the tool results
            continue

        # ── LLM has a plain text answer — done ────────────────────────────
        text = (msg.content or "").strip()
        history.append({"role": "assistant", "content": text})
        llm_answer(text)
        break


# ─────────────────────────────────────────────
# PROVIDER SELECTION
# ─────────────────────────────────────────────
def ask_provider() -> str:
    print(f"\n{C.BOLD}Choose your LLM provider:{C.RESET}")
    print(f"  {C.GREEN}1{C.RESET}  Gemini  (default) — cloud, needs GEMINI_API_KEY in .env")
    print(f"  {C.BLUE}2{C.RESET}  Ollama  (local)   — needs Ollama running with {OLLAMA_MODEL}")
    choice = input(f"\n{C.BOLD}Enter 1 or 2 (or press Enter for Gemini): {C.RESET}").strip()
    if choice == "2":
        return "ollama"
    return "gemini"


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main() -> None:
    print(f"\n{C.CYAN}{C.BOLD}")
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║          ☕  Café MCP  —  Terminal Chat              ║")
    print("  ║  Watch every LLM call, MCP request, and tool result ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(C.RESET)

    provider = ask_provider()
    llm, model = make_llm_client(provider)

    print(f"\n  {C.DIM}provider : {C.BOLD}{provider}{C.RESET}")
    print(f"  {C.DIM}model    : {C.BOLD}{model}{C.RESET}")
    print(f"  {C.DIM}server   : {C.BOLD}{CAFE_URL}{C.RESET}\n")

    step("⟳", "Fetching tool list from MCP server...")
    try:
        mcp_tools = mcp_list_tools()
    except Exception as e:
        print(f"\n{C.RED}Could not connect to MCP server at {CAFE_URL}{C.RESET}")
        print(f"{C.RED}Start it first:  python solved/cafe_project.py{C.RESET}")
        print(f"{C.RED}Error: {e}{C.RESET}")
        sys.exit(1)

    tool_schemas = build_tool_schemas(mcp_tools)
    names_preview = ", ".join(t["name"] for t in mcp_tools[:5])
    if len(mcp_tools) > 5:
        names_preview += f", ... (+{len(mcp_tools) - 5} more)"
    step("✓", f"Loaded {len(mcp_tools)} tools:", names_preview)

    history: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are a helpful barista assistant at Café MCP. "
                "Help the customer browse the menu, add items to their order, "
                "and place it. Always call list_drinks first before recommending "
                "anything unless the customer already named a specific drink. "
                "When placing an order, walk the customer through step by step. "
                "Be friendly and concise."
            ),
        }
    ]

    print(f"\n  {C.DIM}Type your order or question. Type 'quit' to exit.{C.RESET}")
    banner("Chat started — you are talking to the café ☕")

    while True:
        try:
            user_input = input(f"\n{C.WHITE}{C.BOLD}You ❯ {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n{C.DIM}Goodbye! ☕{C.RESET}\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print(f"\n{C.DIM}Goodbye! ☕{C.RESET}\n")
            break

        history.append({"role": "user", "content": user_input})

        banner("Agent loop")
        try:
            run_agent_turn(history, tool_schemas, llm, model, provider)
        except Exception as e:
            print(f"\n{C.RED}Agent error: {e}{C.RESET}")
            history.pop()   # remove the broken user message


if __name__ == "__main__":
    main()

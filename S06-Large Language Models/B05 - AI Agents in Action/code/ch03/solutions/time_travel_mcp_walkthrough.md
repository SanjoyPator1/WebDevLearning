# The Time-Travel Tracker: From a Plain Tool to an MCP Server

This walks through four files that all do the *same* thing — a journaling
agent that records time-travel events and can summarize them — but built
three different ways, so you can see exactly what changes when you move
tools out of your agent's own file and into a separate MCP server.

```text
05_time_travel_agent.py                    (BEFORE — no MCP at all)
        |
        |  the exact same two functions, moved into their own file
        v
06_mcp_time_travel_tracker.py              (the MCP SERVER)
        ^                              ^
        |  reached over STDIO         |  reached over Streamable HTTP
        |                              |
06_time_travel_agent_mcp_stdio.py    06_time_travel_agent_mcp_sse.py
   (the AGENT, path A)                  (the AGENT, path B)
```

All four files record the same three fake history events and then ask for
a summary. What differs is *where the journal-recording code lives* and
*how the agent reaches it*.

---

## Part 1 — The "before" picture: `05_time_travel_agent.py`

No MCP anywhere in this file. Everything lives in one process:

```python
_journal = []

@function_tool
def record_event(entry: str) -> dict:
    _journal.append(entry)
    ...

@function_tool
def load_journal() -> dict:
    ...

agent = Agent(..., tools=[record_event, load_journal])
```

`_journal` is just a plain Python list, sitting in memory, inside the same
process as the agent itself. `record_event` and `load_journal` are
`@function_tool`-decorated functions — the exact same pattern as
`get_research_sources` from chapter 2 — registered directly on the agent
via `tools=[...]`. When the agent decides to call `record_event`, it's
calling a Python function that lives two lines above it in the same file.
Nothing is separate here; this is the "control group" the other three
files get compared against.

---

## Part 2 — Turning it into an MCP server: `06_mcp_time_travel_tracker.py`

This file takes those exact same two functions and moves them into their
own standalone program — one that knows nothing about the agent that will
eventually call it.

**What actually changed, line by line:**

- `_journal = []` — same idea, but now this list lives inside a
  *separate* process. The agent can no longer reach into it directly the
  way it could in file 1; the only way in or out is through the two tools.
- `@function_tool` became `@mcp.tool()` — that's the *only* decorator
  change. The function bodies underneath didn't need to change at all.
- `print(f"Event recorded: {entry}")` became
  `print(f"Event recorded: {entry}", file=sys.stderr)`. This one matters a
  lot: when this server is reached over STDIO, its `stdout` **is** the
  actual message channel carrying MCP's protocol messages back and forth.
  A plain `print()` writes into that same channel and corrupts it — this
  was verified directly while building this file: it produces a real
  `"Failed to parse JSONRPC message from server"` error the moment the
  tool runs. Sending narration to `stderr` instead keeps it out of the
  protocol's way entirely.

**The bottom `if __name__ == "__main__":` block is the interesting part —
it's a two-way switch:**

```python
if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "streamable-http":
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8000, stateless_http=True)
    else:
        mcp.run(transport="stdio")
```

This one file can start up two completely different ways, depending on an
environment variable:

- **No `MCP_TRANSPORT` set** → starts over STDIO (talks over stdin/stdout
  to whatever process launched it).
- **`MCP_TRANSPORT=streamable-http`** → starts a real, always-listening
  HTTP server on port 8000 instead.

`stateless_http=True` is worth calling out on its own: it means this
server doesn't try to remember "who is currently connected" between
requests — every request to it stands completely on its own. That's the
whole point of the 2026-07-28 protocol update covered in the notes: no
handshake to set up first, no session to keep alive, just independent
request-in, response-out.

**One subtlety:** this `__main__` block only runs when you execute
`python 06_mcp_time_travel_tracker.py` yourself, directly. When the STDIO
agent file launches this server via `mcp run 06_mcp_time_travel_tracker.py`,
that command *imports this file as a module* and calls `.run()} on the
`mcp` object itself — it never reaches `__main__` at all, and it always
defaults to STDIO regardless of any environment variable.

---

## Part 3 — Reaching it over STDIO: `06_time_travel_agent_mcp_stdio.py`

```python
async with MCPServerStdio(
    name="Time Tracker Server",
    params=MCPServerStdioParams(command="mcp", args=["run", str(SCRIPT)]),
) as time_tracker_server:
```

This line is doing something important: it's telling Python to run the
shell command `mcp run 06_mcp_time_travel_tracker.py` **for you**, as a
background subprocess, the instant this line executes — and to shut that
subprocess down automatically once the `async with` block ends. You never
open a second terminal for this version. One command
(`python 06_time_travel_agent_mcp_stdio.py`) starts both the tracker *and*
the agent, because the agent script is the one doing the starting.

A consequence worth noticing: because a brand-new subprocess is spawned
every time you run this file, the journal starts **empty every single
run**. There's no way for a previous run's events to still be there —
the whole server process, `_journal` list included, is thrown away the
moment the script finishes.

---

## Part 4 — Reaching it over Streamable HTTP: `06_time_travel_agent_mcp_sse.py`

This is the one worth slowing down on, since it works meaningfully
differently from the STDIO version.

```python
async with MCPServerStreamableHttp(
    name="Time Tracker Server",
    params={"url": "http://127.0.0.1:8000/mcp"},
) as time_tracker_server:
```

Notice there's no `command` or `args` here at all — just a `url`. That's
the core difference: **this file does not start the tracker.** It assumes
the tracker is *already running somewhere else*, and just connects to it
the same way a web browser connects to a website — by hitting a URL.

That's why this only works with two terminals open at once:

```text
Terminal 1:  MCP_TRANSPORT=streamable-http python 06_mcp_time_travel_tracker.py
             (starts the tracker, leaves it running, listening on :8000)

Terminal 2:  python 06_time_travel_agent_mcp_sse.py
             (the agent connects to the already-running tracker over HTTP)
```

A few details worth understanding:

- **One URL, not two.** `http://127.0.0.1:8000/mcp` is a single address
  used for everything — sending a request and getting the response both
  go through it. The older SSE-based approach (what this file's name still
  references, even though the code inside no longer uses it) used two
  separate addresses, `/sse` and `/messages`, which turned out to be
  fragile whenever a connection dropped. Streamable HTTP folds both
  directions into the one endpoint.
- **`MCPServerStreamableHttp`, not `MCPServerSse`.** The class name
  itself tells you which transport era you're in.
- **Because the tracker in Terminal 1 keeps running on its own,** its
  `_journal` list survives across multiple runs of the agent script — run
  Terminal 2 twice in a row and the second run's summary will include
  events from the first. That's the opposite of the STDIO version, and
  it's a direct result of the server being a long-lived, shared process
  instead of a disposable subprocess.
- **`stateless_http=True` on the server side is what makes this safe to
  reach from more than one place at once.** Because the server doesn't
  hold onto any per-connection memory between requests, multiple agents
  (or multiple runs of the same agent) could talk to that one Terminal-1
  process simultaneously without stepping on each other's connection
  state — only the shared `_journal` list itself would be shared data,
  which is a deliberate, visible trade-off, not an accident.

---

## Side by side

| | STDIO version | Streamable HTTP version |
|---|---|---|
| File | `06_time_travel_agent_mcp_stdio.py` | `06_time_travel_agent_mcp_sse.py` |
| Class used | `MCPServerStdio` | `MCPServerStreamableHttp` |
| How the tracker starts | Automatically — this script launches it as a subprocess | Manually — you start it yourself, in a separate terminal, first |
| Terminals needed | 1 | 2 |
| Journal state across runs | Always starts empty (fresh subprocess every time) | Persists as long as the Terminal-1 server keeps running |
| Can several agents share one tracker at once? | No — each run gets its own private subprocess | Yes — the same running server can answer many callers |

---

## How to actually run each one

**STDIO (simplest, one command):**
```bash
python 06_time_travel_agent_mcp_stdio.py
```

**Streamable HTTP (two terminals):**
```bash
# Terminal 1 — start the tracker and leave it running
MCP_TRANSPORT=streamable-http python 06_mcp_time_travel_tracker.py

# Terminal 2 — run the agent against it
python 06_time_travel_agent_mcp_sse.py
```

**Plain, no-MCP version, for comparison:**
```bash
python 05_time_travel_agent.py
```

---

## The one thing worth remembering from all four files

The agent's *instructions* are identical in every version — "call
`load_journal` first, call `record_event` for new entries, summarize
when asked." What changes across files 1, 3, and 4 is never *what the
agent is told to do* — it's *how far away the tool's actual code lives*,
and *how the agent reaches it*. That gap — the agent only ever seeing a
tool's name, description, and return shape, never its implementation — is
the entire reason MCP tools are swappable: the tracker's `_journal` here
could just as easily be a database or a remote API, and neither agent
file would need to change a single line to notice.

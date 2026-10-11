# Chapter 3 -- Own Practice: Library Front Desk Agent

## How This Folder Is Different

Every file in `from_scratch/` came with a scaffold: a problem description, theory to read, a `template` stub, and a `solved` reference to check against. This folder has none of that on purpose. Below is a problem statement only -- a scenario, a checklist of required techniques, and an example of the expected shape. No file layout, no function signatures, no solved reference (yet). Design the server, the agent, and the control flow yourself. Write it in new files in this folder, e.g. `library_server.py` and `library_agent.py`.

The goal isn't a new concept -- it's using everything from chapter 3 together, unassisted, so you can tell for yourself whether it's internalized or you were still leaning on the scaffold. This uses a different scenario than the trip planner from chapter 2's own practice, on purpose, so you aren't just retyping a domain you already know by heart. The trip planner's tools are fair game to reuse here too if you'd rather reuse that domain -- the checklist below is about which techniques you use, not which story you tell.

## The Scenario

Build a front-desk agent for a small library. Given a request like "find me a mystery novel and check one out for me", it should:

1. Search the library's catalog for books in a genre, paging through results if there are more than one page.
2. Check out a book for the patron -- which requires confirming with the patron first, since a checkout can't be undone by the model alone.
3. Optionally scan a shelf (a slow operation) to verify what's physically there against what the catalog says, reporting progress as it goes.

All of this runs through a real MCP server you build with the `mcp` library, and a hand-written agent (no agents SDK) that talks to it, the same way `05_trip_agent.py` and `06_multi_server_agent.py` did.

The difference from most of `from_scratch`: the server runs the way you would deploy it for real, as its own long-lived **stateless Streamable HTTP** service. The agent does not start it. It connects to a URL, the same way `06_multi_server_agent.py` reached the trips server. STDIO is the right choice for a local tool that one client starts for itself; a library front desk is a shared service that many desks (clients) would talk to at once, which is exactly what HTTP is for.

## Required Techniques (the chapter 3 checklist)

Your implementation must use all of the following. Treat this as a checklist, not an ordered list of steps:

- **A stateless Streamable HTTP server.** Run it with `transport="streamable-http"`, a fixed host and port, and `stateless_http=True`, the same way `03_wire_server.py` and `04_cart_server.py` did. It is started on its own, in its own terminal, and keeps running between agent runs.
- **A real `MCPServer` using all three primitives**, not just tools:
  - A **tool** that searches the catalog by genre and pages through results 5 (or so) at a time, with an opaque cursor the client must copy back exactly -- the same shape as `07_bookstore_server.py`'s `search_books`. Hardcode a catalog of at least 25 books across 3-4 genres.
  - A **tool** that checks out a book, which must use MRTR: round 1 quotes which book and asks the patron to confirm (form-mode elicitation), round 2 reads the confirmation back and either books it or reports a decline as a normal outcome, the same shape as `08_flight_server.py`'s `book_flight`. Put something in `request_state` that is a fact from round 1 which is *not* an argument (for example: how many copies were available when quoted), and have round 2 reject the checkout if that fact has changed by round 2 (someone else checked out the last copy in between) -- the same idea as the flight's fare check.
  - A **tool** that scans a shelf, taking a few seconds (simulate with `asyncio.sleep` per item) and calling `ctx.report_progress` after each item, the same shape as `09_indexer_server.py`'s `index_folder`.
  - A **resource** for the library's hours or rules (a fixed address, `library://hours` or similar) that the app attaches to the system message before the loop starts -- the model never fetches it itself.
  - A **prompt** for the front-desk persona (`front_desk_persona()` or similar) that the app fetches and uses as the system message, the same pattern as `trip_planner_persona()`.
- **A hand-written agent, not the agents SDK.** Connect by URL with `Client("http://127.0.0.1:<port>/mcp", ...)` (no `StdioServerParameters`, no subprocess), build an `McpToolbox`-style class that turns the server's tools into OpenAI-shaped schemas and routes calls back through `call_tool`, and run your own reason-act-observe loop -- all of this should look like `05_trip_agent.py`, pointed at a new server.
- **The model paging through the catalog on its own.** Ask for something that needs more results than one page holds (e.g. "list every mystery book you have"), and don't hand-feed it the cursor -- it has to read `next_cursor` out of a tool result and call again, the way Problem 07's Part 3 worked.
- **A real elicitation round trip, driven by your own terminal input.** Write an `elicitation_callback` that prints the confirmation question and reads yes/no from the user with `await asyncio.to_thread(input, ...)`, pass it into `Client(...)`, and confirm the model only ever sees one tool call and one result for the checkout -- it should never see the question itself.
- **A real progress callback**, printing something as the shelf scan runs, not just a final result after a silent wait.
- **Prove the stock check works against a real second caller.** Because the server is shared over HTTP, you can test the "someone else took the last copy" case for real: while your agent is waiting at the confirmation prompt, check out the same book from a second terminal (a tiny script, or a second run of the agent). Round 2 of the first checkout should then be rejected.

## How to Run

```text
Terminal 1:  python library_server.py          (leave it running)
Terminal 2:  python library_agent.py
Terminal 3:  (optional) a second caller, for the last-copy test above
```

If Terminal 1 isn't running, the agent fails with a connection error from the HTTP client. That is the correct failure: start the server first.

## Gotchas Worth Remembering (you've met all of these already)

- **`stateless_http` defaults to `False`.** Forget `stateless_http=True` and a modern client gets HTTP 400 `"Bad Request: Missing session ID"`, which is confusing on brand-new software (Theory 03).
- **Stateless protocol does not mean stateless code.** Your copies-available counts live in the server process's memory. They survive between agent runs because the server keeps running, but a server restart wipes them, and a second server process would have its own separate copy (the naive cart from Problem 04). That is fine for this exercise; just know where the state lives.
- **Narration still goes to `sys.stderr` or a logger.** Over HTTP, stdout is not the protocol channel the way it is over STDIO, so a stray `print()` won't corrupt anything here. Keep the habit anyway: the moment someone runs your server over STDIO, that same `print()` breaks it.
- **Strict/native schema enforcement guarantees shape, not quantity or content** -- same lesson as chapter 2. If you ask the model to check out "a couple of books" nothing in the schema forces it to actually call the tool twice; the persona's wording does that work.
- **`tc.model_dump()`, not hand-picked fields**, when you rebuild the assistant's tool-call message for the next loop turn -- Gemini's `thought_signature` lives in an extra field and a multi-step loop fails on step 2 without it, the same bug from file 07's SDK client.
- **A bare `dict` or `list` return type on a tool doesn't get clean structured output** -- define a small Pydantic model for anything you want `structured_content` to carry cleanly, the same fix `04_cart_server.py` and `08_flight_server.py` both needed.
- **A plain `def` progress callback fails silently with noisy logs**, not a crash -- it has to be `async def`, or the SDK's `await` on its `None` return value raises inside the dispatcher while your output still looks fine.
- **The checkout confirmation is a normal outcome either way.** A decline is not an error -- the tool asked, and got an answer. Don't raise an exception for "the patron said no."
- **A tool handler should never crash on an input it didn't expect.** An unknown genre or an invalid cursor should come back as a clear, model-readable error (`ToolError`), not a stack trace.

## Example

**Input:** "Find me a mystery novel and check one out for me. My name is Priya."

**Expected console flow (shape, not exact wording):**
```
[agent] connecting to http://127.0.0.1:8020/mcp (stateless Streamable HTTP)
[agent] system prompt built from: prompt 'front_desk_persona' + resource 'library://hours'
[agent] tools from server: ['search_catalog', 'checkout_book', 'scan_shelf']

--- loop step 1 ---
  tool call: search_catalog({'genre': 'mystery'})
  tool result: {"books": [...], "next_cursor": null}

--- loop step 2 ---
  tool call: checkout_book({'book_id': '...', 'patron_name': 'Priya'})

  [server asks] Check out 'The Silent Patient' for Priya?
  Confirm? (y/n): y

  tool result: {"status": "checked_out", "due_date": "..."}

FINAL ANSWER
I found "The Silent Patient" and checked it out for you, Priya. It's due back on ...
```

Your actual catalog, book titles, and due-date logic can be whatever you hardcode -- what matters is that the checkout really went through a round-trip confirmation, the search really paged (if you ask for more than one page's worth), and the agent is one you wrote by hand against a real MCP server, not the agents SDK.

## Stretch Goals (optional, not required to call this done)

- Add a second server (a small "fines calculator" that looks up whether a patron owes anything) and connect to both at once with `AsyncExitStack`, prefixing tool names the way `06_multi_server_agent.py` did.
- **Cursor survives a restart.** Get page 1 of a search, restart the server, then ask for page 2 with the cursor you saved. It should still work, since the cursor carries everything it needs and the server remembers nothing about your search.
- **Two replicas, round 1 and round 2 on different ones.** Start two copies of the server on two ports. Drive a checkout's two rounds by hand (`client.session.call_tool(..., allow_input_required=True)`, as in Problem 08's stretch) and send round 2 to the *other* replica. The `request_state` part works, because everything round 2 needs travels with the request. Then notice what breaks: each replica has its own copies-available counts, so the stock check can disagree. Moving those counts into a shared store (a small SQLite file both replicas open) is the fix, with no change to the tool's MRTR logic.
- **Also support STDIO.** Pick the transport from an environment variable, the same way `05_trip_server.py` does, so the same server works as a local tool too.
- Run the whole thing against Ollama too (its OpenAI-compatible endpoint, same as chapter 2's file 09), and compare whether a smaller local model pages through the catalog as reliably as Gemini does.

## When You're Done

Run it, read through the trace output yourself, and check off the required-techniques list above against your own code before considering it finished. If you want a reference to compare against afterward, ask for one then -- not before, since seeing it first defeats the point of this folder.

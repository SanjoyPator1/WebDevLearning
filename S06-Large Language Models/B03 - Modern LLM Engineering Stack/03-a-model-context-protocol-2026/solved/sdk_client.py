# ============================================================
# THE PROJECT — the official SDK client, same sequence
# REF:   notes/15-the-project.md
# RUN:   python solved/cafe_project.py   (in one terminal)
#        python solved/sdk_client.py     (in another)
# ============================================================
#
# Identical sequence to `solved/raw_client.py`: list tools, read the menu,
# build a cart, place the order (an MRTR confirmation), brew it (a progress
# stream). Every step that raw_client.py built by hand — the `_meta`
# envelope, the `Mcp-Method`/`Mcp-Name` headers, plain-JSON-vs-SSE detection,
# and above all the two-round MRTR retry — `mcp.client.Client` does for you.
#
# The one thing you still supply: an `elicitation_callback`. The SDK will not
# invent an answer to "what name goes on the cup?" — it drives the ROUND TRIP
# automatically (reading requestState back, replaying the unchanged argument,
# building inputResponses in the exact wire shape) but the actual DECISION
# still has to come from somewhere. Without a callback, `call_tool` raises
# `MCPError: Elicitation not supported` the moment a tool returns
# `input_required` — verified directly; there is no silent default accept.

# --- Imports ---
import asyncio

import mcp_types as types
from mcp.client import Client

# --- Constants / Config ---
SERVER_URL = "http://127.0.0.1:3010/mcp"


async def auto_confirm(context, params: types.ElicitRequestParams) -> types.ElicitResult:
    """Stands in for a human. Round-trip mechanics (requestState, the
    unchanged order argument, the wire shape of inputResponses) are ALL
    handled by the SDK before this is even called — all this function does
    is answer the one question a machine cannot answer on its own."""
    print("   [elicitation_callback] server asked:", params.message)
    return types.ElicitResult(action="accept", content={"name": "Sanjoy", "confirm": True})


async def on_progress(progress: float, total: float | None, message: str | None) -> None:
    """The SDK has already parsed the SSE frame and pulled `progress`,
    `total`, and `message` out of it by the time this runs.

    Must be a coroutine function, not a plain one — `ProgressFnT` is awaited
    internally (wrapped in `_shielded_progress`, which swallows and logs any
    exception rather than letting a broken callback take down the dispatcher).
    A plain `def` here still gets CALLED and its prints still fire, but its
    `None` return value then fails to await, logging "progress callback
    raised" for every single event even though the callback itself "worked" —
    an easy, silent-looking mistake to make once, worth naming directly.
    """
    print(f"   progress {progress:g}/{total:g}: {message}")


async def main() -> None:
    print("=" * 68)
    print("SDK CLIENT — the same sequence, through mcp.client.Client")
    print("=" * 68)

    async with Client(SERVER_URL, elicitation_callback=auto_confirm) as client:
        print(
            f"\nconnected — protocol_version negotiated automatically: {client.protocol_version!r}"
        )
        print(f"server_info: {client.server_info.name} v{client.server_info.version}")

        print("\n--- list_tools ---")
        tools = await client.list_tools()
        print("  ", sorted(t.name for t in tools.tools))

        print("\n--- read cafe://menu ---")
        menu = await client.read_resource("cafe://menu")
        print(f"   {len(menu.contents[0].text)} characters of markdown")

        print("\n--- add_to_order(latte, M, 1) ---")
        added = await client.call_tool("add_to_order", {"slug": "latte", "size": "M", "qty": 1})
        order_token = added.structured_content["order"]
        print(f"   total so far: ${added.structured_content['total']}")

        print("\n--- place_order — ONE call, both MRTR rounds driven internally ---")
        placed = await client.call_tool("place_order", {"order": order_token})
        result = placed.structured_content["result"]
        print(f"   PLACED — ticket {result['ticket']}, total ${result['total']}")
        print("   (round 1's input_required, requestState, and round 2's retry")
        print("    never appeared in this script at all)")

        print("\n--- brew(order) — progress_callback, no manual SSE parsing ---")
        brewed = await client.call_tool(
            "brew", {"order": order_token}, progress_callback=on_progress
        )
        print("   brew result:", brewed.structured_content)

    print("\n" + "=" * 68)
    print("Same outcome as solved/raw_client.py. Compare the two files' line counts")
    print("for `place_order` and `brew` specifically — that gap IS what the SDK buys.")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(main())

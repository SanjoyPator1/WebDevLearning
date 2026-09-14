# ============================================================
# TOPIC: 05 — prompts, and completion/complete
# REF:   notes/05-prompts-and-completion.md
# RUN:   python solutions/t05_prompts.py
# ============================================================
#
# YOUR TURN. Seven TODOs. This finishes Part 2 and the whole protocol surface.
#
# Before you start, place a prompt in topic 04's control table from memory:
#
#     tool      ->  the ______ decides to use it
#     resource  ->  the ______ attaches it
#     prompt    ->  the ______ invokes it
#
# The third row is what this file is about, and it has a consequence worth noticing
# as you write: the USER supplies the arguments, but YOU supply the wording. Every
# sentence you put in a returned message steers the model, and the user never sees
# it. That is more power than it looks like.
#
# Prove it from outside:
#     bash curl/05_prompts_list.sh
#     bash curl/05_get_order_for_me.sh sleepy
#     bash curl/05_get_order_for_me.sh sleepy true
#     bash curl/05_get_order_for_me.sh grumpy       <- your error path
#     bash curl/05_complete_mood.sh s
#     bash curl/05_complete_template.sh c
#     bash curl/05_complete_with_context.sh         <- the one that matters

# --- Imports ---
import os
import sys
from typing import Annotated

from mcp import MCPError
from mcp.server import CacheHint, MCPServer
from mcp.server.mcpserver import Message, UserMessage
from mcp.server.mcpserver.exceptions import ResourceNotFoundError
from mcp_types import (
    INVALID_PARAMS,
    Completion,
    CompletionArgument,
    CompletionContext,
    PromptReference,
    ResourceTemplateReference,
)
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse

from cafe_mcp import menu, render

# --- Constants / Config ---
HOST = "127.0.0.1"
PORT = int(os.environ.get("CAFE_MCP_PORT", "3010"))

# TODO 1: Define the vocabulary `order_for_me` accepts.
#
#   A dict of mood -> what it means for a recommendation. Six or so.
#
#   Keep it as DATA, in one place. Both the prompt AND the completion handler need
#   this list, and if you hardcode it twice one copy will be wrong within a month.
MOODS: dict[str, str] = {
    "sleepy": "needs caffeine, the more the better",
    # ... add the rest
}


# --- The server ---
mcp = MCPServer(
    name="cafe-mcp",
    version="0.5.0",
    instructions=(
        "You are working the counter of a small coffee shop.\n\n"
        "Read `cafe://menu` once at the start of a conversation; use "
        "`cafe://menu/dairy-free` when the customer avoids dairy."
    ),
    cache_hints={
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        "resources/list": CacheHint(ttl_ms=600_000, scope="public"),
        "resources/templates/list": CacheHint(ttl_ms=600_000, scope="public"),
        "resources/read": CacheHint(ttl_ms=600_000, scope="public"),
        # TODO 2: One of prompts/list and prompts/get is cacheable and the other is
        # not. Add the one that is, and write a comment saying why the other cannot
        # be. Check against the SDK, do not guess:
        #   python -c "from mcp_types.methods import CACHEABLE_METHODS as C; print(sorted(C))"
    },
)


# --- Resources, carried forward from topic 04 ---
# Given to you, because the completion handler below completes the {slug} in this
# template and you cannot demonstrate that against a server with no template.
@mcp.resource("cafe://menu", name="menu", title="The café menu", mime_type="text/markdown")
def menu_document() -> str:
    """The full menu as a markdown table, including each drink's slug."""
    return render.menu_markdown()


@mcp.resource(
    "cafe://menu/dairy-free",
    name="dairy_free_menu",
    title="Dairy-free drinks",
    mime_type="text/markdown",
)
def dairy_free_document() -> str:
    """Only the dairy-free drinks."""
    return render.dairy_free_markdown()


@mcp.resource(
    "cafe://drinks/{slug}",
    name="drink_detail",
    title="One drink, in full",
    mime_type="application/json",
)
def drink_document(slug: str) -> str:
    """The full record for a single drink as JSON."""
    try:
        return render.drink_json(slug)
    except KeyError:
        raise ResourceNotFoundError(
            f"There is no drink with slug {slug!r}. Read `cafe://menu` for valid slugs."
        ) from None


# --- Prompts ---
# TODO 3: Write `order_for_me(mood, dairy_free=False)`.
#
#   Return a list of messages. Two of them:
#
#   (a) The relevant menu, as an EMBEDDED RESOURCE rather than pasted text:
#         {"role": "user",
#          "content": {"type": "resource",
#                      "resource": {"uri": ..., "mimeType": ..., "text": ...}}}
#       Pick cafe://menu or cafe://menu/dairy-free depending on dairy_free.
#       Why embedded rather than pasted? Answer that in a comment.
#
#   (b) A UserMessage with your instruction. THIS IS THE EXERCISE. Write a sentence
#       that constrains the answer: how many drinks, whether to include a size,
#       how much reasoning, whether to offer alternatives. A vague instruction here
#       produces a vague assistant, and the user has no way to fix it because they
#       never see this text.
#
#   Argument descriptions: use Annotated[..., Field(description=...)] on BOTH
#   arguments. Without them a host shows a bare argument name and the slash command
#   is unusable.
#
#   Note `dairy_free: bool` — prompt arguments arrive as STRINGS on the wire
#   ("true"/"false") and your type hint coerces them. Verify that actually works.
@mcp.prompt(name="order_for_me", title="Order something for me")
def order_for_me(mood: str, dairy_free: bool = False) -> list[Message]:
    """TODO: write this. When should a user invoke it?"""
    print(f"  [server] prompt order_for_me({mood!r}, {dairy_free})", file=sys.stderr)

    if mood not in MOODS:
        # TODO 4: Fail cleanly.
        #
        #   There is NO ToolError equivalent for prompts, and here is the trap:
        #   an ordinary exception from a prompt comes back as an opaque
        #       -32603 "Internal server error"
        #   — even a pydantic validation message gets swallowed. Try it: raise a
        #   ValueError here first, run 05_get_order_for_me.sh grumpy, and look.
        #
        #   Then find the escape hatch. `MCPServer.get_prompt` re-raises exactly one
        #   exception type untouched. Which one? (It is imported at the top of this
        #   file.) Use it with code=INVALID_PARAMS, a message naming the allowed
        #   values, and `data` identifying which argument was wrong.
        raise NotImplementedError  # replace

    ...  # replace: build and return the two messages


# TODO 5: Write `compare_drinks(first, second)`.
#
#   Two slug arguments, both required, both described. Validate that each exists and
#   that they differ — using the same clean-error mechanism as TODO 4.
#
#   Return one UserMessage that lays out both drinks (name, description, caffeine,
#   sizes) and asks for the single clearest difference plus who should pick which.
#
#   This prompt exists mainly so TODO 7 has something to demonstrate against.


# --- completion/complete ---
# TODO 6: Complete prompt arguments and template placeholders.
#
#   ONE handler serves the whole server. It receives:
#
#     ref       WHAT is being completed.
#                 PromptReference          -> has `.name`
#                 ResourceTemplateReference-> has `.uri`, which is the TEMPLATE
#                                             ("cafe://drinks/{slug}"), not a
#                                             resolved URI
#     argument  WHICH argument (`.name`) and what has been typed (`.value`)
#     context   previously resolved arguments, or None
#
#   Handle at least:
#     - PromptReference "order_for_me",   argument "mood"  -> the MOODS keys
#     - ResourceTemplateReference "cafe://drinks/{slug}", argument "slug" -> slugs
#     - PromptReference "compare_drinks", argument "first" -> slugs
#
#   Return None for anything you do not recognise. Do NOT guess — a wrong
#   suggestion is worse than no suggestion, and the SDK turns None into an empty
#   completion for you.
@mcp.completion()
async def complete(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    """Autocomplete prompt arguments and resource-template placeholders."""
    typed = argument.value or ""
    print(f"  [server] complete {argument.name}={typed!r}", file=sys.stderr)

    # TODO 7: Make `compare_drinks`'s `second` argument CONTEXT-AWARE.
    #
    #   Comparing a cortado with a cortado is nonsense. `context.arguments` holds
    #   what the user already filled in on this same prompt — so when completing
    #   `second`, exclude whatever `first` already is.
    #
    #   This is the difference between completion as a static enum and completion as
    #   a function of state. Prove it with:
    #       bash curl/05_complete_with_context.sh
    #   You should see 5 values become 4.

    return None  # replace


def _prefix(candidates: list[str], typed: str) -> Completion:
    """Filter candidates by prefix, and report total/has_more honestly.

    Being accurate about `has_more` matters: a client that believes it received the
    full list will stop asking.
    """
    matches = [candidate for candidate in candidates if candidate.startswith(typed)]
    return Completion(values=matches, total=len(matches), has_more=False)


# --- Health ---
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "05"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 05 — prompts and completion (your version)")
    print("-" * 68)
    print(f"  endpoint : http://{HOST}:{PORT}/mcp")
    print("-" * 68, flush=True)
    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()

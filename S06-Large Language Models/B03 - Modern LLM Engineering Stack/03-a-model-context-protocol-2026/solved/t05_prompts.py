# ============================================================
# TOPIC: 05 — prompts, and completion/complete
# REF:   notes/05-prompts-and-completion.md
# RUN:   python solved/t05_prompts.py
# ============================================================
#
# This finishes Part 2, and with it the whole protocol surface: `prompts/list`,
# `prompts/get` and `completion/complete` are the last three of the ten methods a
# client can send at 2026-07-28.
#
# PROMPTS are the third control case. Topic 04 built the table:
#
#     tool      ->  the MODEL decides to use it
#     resource  ->  the HOST or USER attaches it
#     prompt    ->  the USER invokes it        <-- this file
#
# A prompt is a message template the server owns and the user triggers, usually
# surfacing in a host as a slash command. The server supplies the WORDING; the user
# supplies the arguments. That means the server author gets to write the sentence
# that steers the model — which is a surprising amount of power to hold.
#
# COMPLETION closes the gap topic 04 opened. `resources/templates/list` told the
# client the shape `cafe://drinks/{slug}` and nothing about what {slug} may be.
# `completion/complete` is how a client asks.

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

# The vocabulary `order_for_me` understands. Kept as data so the completion handler
# and the prompt itself cannot drift apart — if you hardcode the list twice, one
# copy will be wrong within a month.
MOODS: dict[str, str] = {
    "sleepy": "needs caffeine, the more the better",
    "sweet-tooth": "wants something dessert-like",
    "sad": "wants comfort, warmth, not too bitter",
    "celebratory": "wants a treat, price is not the issue",
    "focused": "wants clean caffeine without sugar or heaviness",
    "cold": "wants something hot and enveloping",
}


# --- The server ---
mcp = MCPServer(
    name="cafe-mcp",
    version="0.5.0",
    instructions=(
        "You are working the counter of a small coffee shop.\n\n"
        "Read `cafe://menu` once at the start of a conversation; use "
        "`cafe://menu/dairy-free` when the customer avoids dairy, and "
        "`cafe://drinks/<slug>` for one drink in full.\n\n"
        "Sizes are S, M and L, but the menu marks unavailable sizes with a dash."
    ),
    cache_hints={
        "tools/list": CacheHint(ttl_ms=300_000, scope="public"),
        "resources/list": CacheHint(ttl_ms=600_000, scope="public"),
        "resources/templates/list": CacheHint(ttl_ms=600_000, scope="public"),
        "resources/read": CacheHint(ttl_ms=600_000, scope="public"),
        # `prompts/list` is cacheable. `prompts/get` is NOT — it renders against
        # arguments, so there is nothing stable to cache. Check for yourself:
        #   python -c "from mcp_types.methods import CACHEABLE_METHODS as C; print(sorted(C))"
        "prompts/list": CacheHint(ttl_ms=600_000, scope="public"),
    },
)


# --- Resources, carried forward from topic 04 ---
# Kept here because the completion handler below completes the {slug} in this
# template, and you cannot demonstrate that against a server that has no template.
@mcp.resource("cafe://menu", name="menu", title="The café menu", mime_type="text/markdown")
def menu_document() -> str:
    """The full menu as a markdown table, including each drink's slug.

    Read this once at the start of a conversation.
    """
    return render.menu_markdown()


@mcp.resource(
    "cafe://menu/dairy-free",
    name="dairy_free_menu",
    title="Dairy-free drinks",
    mime_type="text/markdown",
)
def dairy_free_document() -> str:
    """Only the dairy-free drinks. Attach this instead of the full menu when the
    customer avoids dairy."""
    return render.dairy_free_markdown()


@mcp.resource(
    "cafe://drinks/{slug}",
    name="drink_detail",
    title="One drink, in full",
    mime_type="application/json",
)
def drink_document(slug: str) -> str:
    """The full record for a single drink as JSON, including `available_sizes`.

    The `{slug}` is a drink slug as it appears in the Slug column of `cafe://menu`.
    """
    try:
        return render.drink_json(slug)
    except KeyError:
        raise ResourceNotFoundError(
            f"There is no drink with slug {slug!r}. Read `cafe://menu` for valid slugs."
        ) from None


# --- Prompts ---
# `@mcp.prompt()` registers a message template. Three things to notice as you read:
#
#   1. The RETURN VALUE is a list of messages, not a string. You are handing the
#      client a conversation opener, and it can have several turns.
#   2. Arguments arrive as STRINGS on the wire and are coerced by your type hints.
#      `dairy_free="true"` becomes Python `True`; `dairy_free="false"` becomes
#      `False`. That is pydantic, and it is why `bool` is a safe hint here.
#   3. `Annotated[..., Field(description=...)]` populates the argument description
#      in `prompts/list`, exactly as it does for tools. Without it a host shows the
#      user a bare argument name and no hint about what to type.
@mcp.prompt(name="order_for_me", title="Order something for me")
def order_for_me(
    mood: Annotated[
        str,
        Field(
            description=(
                "How the customer feels right now, which is what the recommendation "
                "should be based on. One of: " + ", ".join(MOODS) + "."
            )
        ),
    ],
    dairy_free: Annotated[
        bool,
        Field(description="Set true to restrict the recommendation to dairy-free drinks."),
    ] = False,
) -> list[Message]:
    """Recommend a drink based on how the customer is feeling.

    Invoke this when a customer says something like "surprise me" or "what should I
    get?" rather than naming a drink. It attaches the appropriate menu and asks for
    a single recommendation with a reason.
    """
    print(
        f"  [server] prompt order_for_me(mood={mood!r}, dairy_free={dairy_free})",
        file=sys.stderr,
    )

    if mood not in MOODS:
        # --- HOW TO FAIL FROM A PROMPT ---
        # This is NOT ToolError and NOT ResourceNotFoundError. Prompts have no
        # dedicated exception type in this SDK, and — this is the trap — an
        # ordinary exception from a prompt comes back as an opaque
        # `-32603 "Internal server error"`, with even a pydantic validation
        # message swallowed. See notes/05, "How a prompt fails".
        #
        # `MCPError` is the escape hatch: `get_prompt` re-raises it untouched, so
        # you choose the code, the message and the data.
        raise MCPError(
            code=INVALID_PARAMS,
            message=(
                f"{mood!r} is not a mood this prompt understands. Choose one of: "
                f"{', '.join(MOODS)}."
            ),
            data={"argument": "mood", "allowed": sorted(MOODS)},
        )

    menu_uri = "cafe://menu/dairy-free" if dairy_free else "cafe://menu"
    menu_text = render.dairy_free_markdown() if dairy_free else render.menu_markdown()
    constraint = (
        " The customer avoids dairy, so only the drinks in this list are acceptable."
        if dairy_free
        else ""
    )

    # A message's content can be an EMBEDDED RESOURCE rather than plain text. That
    # is better than pasting the markdown into a string: the client learns which URI
    # the text came from, so it can cache it, deduplicate it against a copy it
    # already holds, or show a human where the data came from.
    return [
        {
            "role": "user",
            "content": {
                "type": "resource",
                "resource": {"uri": menu_uri, "mimeType": "text/markdown", "text": menu_text},
            },
        },
        UserMessage(
            f"The customer is {mood} — {MOODS[mood]}.{constraint}\n\n"
            f"Recommend exactly one drink from the menu above, and a size. Give one "
            f"sentence of reasoning that refers to how they are feeling. Do not list "
            f"alternatives unless they ask."
        ),
    ]


@mcp.prompt(name="explain_drink", title="Explain a drink")
def explain_drink(
    slug: Annotated[
        str,
        Field(description="The drink's slug, as in the Slug column of `cafe://menu`."),
    ],
) -> list[Message]:
    """Explain one drink in plain language to someone who does not know coffee.

    Invoke this when a customer asks "what is a cortado?" or similar.
    """
    print(f"  [server] prompt explain_drink(slug={slug!r})", file=sys.stderr)

    drink = menu.find(slug)
    if drink is None:
        raise MCPError(
            code=INVALID_PARAMS,
            message=f"There is no drink with slug {slug!r}. Read `cafe://menu` for valid slugs.",
            data={"argument": "slug"},
        )

    return [
        {
            "role": "user",
            "content": {
                "type": "resource",
                "resource": {
                    "uri": f"cafe://drinks/{slug}",
                    "mimeType": "application/json",
                    "text": render.drink_json(slug),
                },
            },
        },
        UserMessage(
            f"Explain a {drink.name} to someone who has never ordered coffee beyond "
            f"instant. Two or three sentences. Say what it tastes like and how it "
            f"differs from a plain latte. Do not use the words 'microfoam', "
            f"'extraction' or 'crema' without explaining them."
        ),
    ]


@mcp.prompt(name="compare_drinks", title="Compare two drinks")
def compare_drinks(
    first: Annotated[str, Field(description="Slug of the first drink to compare.")],
    second: Annotated[
        str,
        Field(description="Slug of the second drink. Must be different from the first."),
    ],
) -> list[Message]:
    """Compare two drinks side by side for a customer who is undecided.

    Invoke this when a customer is choosing between two named drinks.

    This prompt exists mainly to demonstrate context-aware completion: when the
    client completes `second`, the value already chosen for `first` is excluded.
    """
    print(f"  [server] prompt compare_drinks({first!r}, {second!r})", file=sys.stderr)

    for name, slug in (("first", first), ("second", second)):
        if menu.find(slug) is None:
            raise MCPError(
                code=INVALID_PARAMS,
                message=f"There is no drink with slug {slug!r}.",
                data={"argument": name},
            )
    if first == second:
        raise MCPError(
            code=INVALID_PARAMS,
            message="`first` and `second` must be different drinks.",
            data={"argument": "second"},
        )

    left, right = menu.find(first), menu.find(second)
    return [
        UserMessage(
            f"A customer is choosing between a {left.name} and a {right.name}.\n\n"
            f"{left.name}: {left.description} Caffeine {left.caffeine_mg}mg. "
            f"Sizes {', '.join(menu.sizes_for(first))}.\n"
            f"{right.name}: {right.description} Caffeine {right.caffeine_mg}mg. "
            f"Sizes {', '.join(menu.sizes_for(second))}.\n\n"
            f"Give the single clearest difference between them in one sentence, then "
            f"one sentence on who should pick which. Do not recommend a third drink."
        )
    ]


# --- completion/complete ---
# ONE handler serves every completable argument on the server. It is registered
# with `@mcp.completion()` and receives three things:
#
#   ref       -- WHAT is being completed. Either a PromptReference (type
#                "ref/prompt", carrying `name`) or a ResourceTemplateReference
#                (type "ref/resource", carrying the TEMPLATE `uri`, not a resolved
#                one).
#   argument  -- WHICH argument, and what the user has typed so far
#                (`argument.name`, `argument.value`).
#   context   -- previously resolved arguments, or None. This is what makes
#                completion smarter than a static list.
#
# Returning None means "I have no suggestions for this", which the SDK turns into
# an empty completion. That is the correct answer for arguments you do not know
# about — do not guess.
@mcp.completion()
async def complete(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    """Autocomplete prompt arguments and resource-template placeholders."""
    typed = argument.value or ""
    print(
        f"  [server] complete: ref={type(ref).__name__} arg={argument.name}={typed!r} "
        f"context={getattr(context, 'arguments', None)}",
        file=sys.stderr,
    )

    all_slugs = [drink.slug for drink in menu.all_drinks()]

    # --- Resource template placeholders ---
    if isinstance(ref, ResourceTemplateReference):
        # `ref.uri` is the TEMPLATE, `cafe://drinks/{slug}`, not a resolved URI.
        # This is the answer to the gap topic 04 left: the template describes the
        # shape of the address, and completion describes the address space.
        if ref.uri == "cafe://drinks/{slug}" and argument.name == "slug":
            return _prefix(all_slugs, typed)
        return None

    # --- Prompt arguments ---
    if isinstance(ref, PromptReference):
        if ref.name == "order_for_me" and argument.name == "mood":
            return _prefix(sorted(MOODS), typed)

        if ref.name == "explain_drink" and argument.name == "slug":
            return _prefix(all_slugs, typed)

        if ref.name == "compare_drinks":
            if argument.name == "first":
                return _prefix(all_slugs, typed)
            if argument.name == "second":
                # --- CONTEXT-AWARE COMPLETION ---
                # `context.arguments` holds what the user has already filled in on
                # this same prompt. Comparing a latte with a latte is nonsense, so
                # exclude whatever `first` already is.
                #
                # This is the difference between completion as a static enum and
                # completion as a real function of state. A client filling a form
                # top to bottom gets suggestions that are already consistent with
                # its earlier answers, which removes an entire class of error before
                # it happens.
                already = (context.arguments or {}).get("first") if context else None
                candidates = [slug for slug in all_slugs if slug != already]
                return _prefix(candidates, typed)

    return None


def _prefix(candidates: list[str], typed: str) -> Completion:
    """Filter candidates by what the user has typed, and report honestly.

    `total` and `has_more` are how you tell the client "there are more than I sent".
    Being accurate here matters: a client that thinks it has the full list will stop
    asking. This server always sends everything, so has_more is always False — but
    the fields are filled in rather than left None, because a client showing "7 of
    12" to a human is more useful than one showing nothing.
    """
    matches = [candidate for candidate in candidates if candidate.startswith(typed)]
    return Completion(values=matches, total=len(matches), has_more=False)


# --- Health ---
@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(request: Request) -> JSONResponse:
    """Liveness check. `ping` was removed at 2026-07-28."""
    return JSONResponse({"status": "ok", "server": "cafe-mcp", "topic": "05"})


# --- Test / dry-run ---
def main() -> None:
    print("-" * 68)
    print("TOPIC 05 — prompts and completion/complete")
    print("-" * 68)
    print(f"  endpoint  : http://{HOST}:{PORT}/mcp")
    print("  prompts   : order_for_me, explain_drink, compare_drinks")
    print("  resources : cafe://menu, cafe://menu/dairy-free, cafe://drinks/{slug}")
    print("  tools     : none — this topic is about the other two primitives")
    print("-" * 68)
    print("  Try:")
    print("    bash curl/05_prompts_list.sh          note the argument descriptions")
    print("    bash curl/05_get_order_for_me.sh sleepy")
    print("    bash curl/05_get_order_for_me.sh sleepy true")
    print("    bash curl/05_get_order_for_me.sh grumpy    <- a clean -32602")
    print("    bash curl/05_get_explain_drink.sh cortado")
    print("    bash curl/05_complete_mood.sh s")
    print("    bash curl/05_complete_template.sh c        <- completing a URI")
    print("    bash curl/05_complete_with_context.sh      <- the interesting one")
    print("-" * 68)
    print("  With this topic the protocol surface is COMPLETE: all ten client")
    print("  methods of 2026-07-28 are now exercised somewhere in topics 01-05.")
    print("-" * 68, flush=True)

    mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)


if __name__ == "__main__":
    main()

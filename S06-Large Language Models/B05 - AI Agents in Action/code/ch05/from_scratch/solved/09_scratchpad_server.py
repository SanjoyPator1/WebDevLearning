# Problem 09 -- the Problem 08 scratchpad, moved onto a real MCP server.
# The notebook is one list of thoughts held by the server. A revision keeps
# the old thought and links the new one to it, a branch names an alternative,
# and a reference to a thought that does not exist is rejected before
# anything is stored.

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

mcp = MCPServer("Reasoning Scratchpad")

# The whole notebook: every thought, in the order record_thought was called.
_thoughts: list[dict] = []


class ThoughtReceipt(BaseModel):
    thought_number: int
    total_thoughts: int
    thoughts_so_far: int
    branches_seen: list[str]
    next_thought_needed: bool


class StoredThought(BaseModel):
    thought_number: int
    thought: str
    is_revision: bool
    revises_thought: int | None
    branch_from_thought: int | None
    branch_id: str | None


class ThoughtLog(BaseModel):
    thoughts: list[StoredThought]


@mcp.tool()
def record_thought(
    thought: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool,
    is_revision: bool = False,
    revises_thought: int | None = None,
    branch_from_thought: int | None = None,
    branch_id: str | None = None,
) -> ThoughtReceipt:
    """Record one step of reasoning on the scratchpad.

    Write down what you know and what you plan to do next, so your
    reasoning is kept even though you have no memory between calls. Set
    is_revision=True and revises_thought=<number> when new information
    contradicts something you recorded earlier -- the old thought stays,
    your new one is linked to it. Set branch_from_thought and branch_id
    when you want to explore an alternative without repeating the shared
    history that led up to it. Keep total_thoughts updated as your
    estimate changes, and set next_thought_needed=False only once you are
    genuinely done.
    """
    existing_numbers = {entry["thought_number"] for entry in _thoughts}

    if revises_thought is not None and revises_thought not in existing_numbers:
        raise ToolError(f"revises_thought={revises_thought} does not exist yet on the scratchpad")
    if branch_from_thought is not None and branch_from_thought not in existing_numbers:
        raise ToolError(f"branch_from_thought={branch_from_thought} does not exist yet on the scratchpad")

    _thoughts.append(
        {
            "thought_number": thought_number,
            "thought": thought,
            "is_revision": is_revision,
            "revises_thought": revises_thought,
            "branch_from_thought": branch_from_thought,
            "branch_id": branch_id,
        }
    )

    branches_seen = sorted({entry["branch_id"] for entry in _thoughts if entry["branch_id"]})
    return ThoughtReceipt(
        thought_number=thought_number,
        total_thoughts=total_thoughts,
        thoughts_so_far=len(_thoughts),
        branches_seen=branches_seen,
        next_thought_needed=next_thought_needed,
    )


@mcp.tool()
def get_thoughts() -> ThoughtLog:
    """Read back every thought on the scratchpad, in the order recorded."""
    return ThoughtLog(thoughts=_thoughts)


@mcp.tool()
def clear_thoughts() -> str:
    """Empty the scratchpad so a new run starts from a blank page. Meant
    for the code that runs the experiment; the model is never given it."""
    _thoughts.clear()
    return "scratchpad cleared"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8150, stateless_http=True)

# Problem 02 -- a server with all three primitives, each one wired to show
# how it fails. Tools hide a crash's real message, resources and prompts
# raise real JSON-RPC errors instead.

import sys

from mcp import MCPError
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp_types import INVALID_PARAMS

mcp = MCPServer("Recipe Book")

RECIPES = {
    "omelette": {
        "cuisine": "french",
        "minutes": 10,
        "ingredients": ["eggs", "butter", "salt"],
        "steps": ["beat the eggs", "melt butter in a pan", "pour and fold"],
    },
    "pasta aglio e olio": {
        "cuisine": "italian",
        "minutes": 15,
        "ingredients": ["pasta", "garlic", "olive oil", "chili flakes"],
        "steps": ["boil pasta", "fry garlic and chili in oil", "toss together"],
    },
    "masala chai": {
        "cuisine": "indian",
        "minutes": 8,
        "ingredients": ["tea leaves", "milk", "ginger", "cardamom", "sugar"],
        "steps": ["boil water with spices", "add tea leaves", "add milk and simmer"],
    },
    "ratatouille": {
        "cuisine": "french",
        "minutes": 45,
        "ingredients": ["eggplant", "zucchini", "tomato", "bell pepper", "garlic"],
        "steps": ["slice all vegetables", "layer in a dish", "bake until soft"],
    },
}


@mcp.tool()
def search_recipes(cuisine: str) -> list[str]:
    """Find recipe names for a given cuisine, e.g. 'italian' or 'french'."""
    if not cuisine:
        raise ToolError("cuisine cannot be empty")
    matches = [name for name, r in RECIPES.items() if r["cuisine"] == cuisine]
    print(f"search_recipes({cuisine!r}) -> {matches}", file=sys.stderr)
    return matches


@mcp.tool()
def broken_tool() -> str:
    """A tool that always crashes, to see what a client gets from an unplanned error."""
    raise ValueError("secret internal detail")


@mcp.resource("recipes://index")
def index() -> str:
    """List every recipe name this server knows."""
    return "\n".join(RECIPES.keys())


@mcp.resource("recipes://{name}")
def recipe(name: str) -> str:
    """Get the full recipe (ingredients and steps) for a given name."""
    if name not in RECIPES:
        raise ResourceNotFoundError(f"no recipe named {name!r}")
    r = RECIPES[name]
    lines = [
        f"{name} ({r['cuisine']}, {r['minutes']} min)",
        "ingredients: " + ", ".join(r["ingredients"]),
        "steps:",
    ]
    lines += [f"  {i + 1}. {step}" for i, step in enumerate(r["steps"])]
    return "\n".join(lines)


@mcp.prompt()
def cook_with(ingredient: str, max_minutes: int) -> str:
    """Ask the model to suggest a recipe using an ingredient, within a time limit."""
    if max_minutes < 5:
        raise MCPError(code=INVALID_PARAMS, message="max_minutes must be at least 5")
    return (
        f"Suggest a recipe that uses {ingredient} and takes at most "
        f"{max_minutes} minutes to cook."
    )


if __name__ == "__main__":
    mcp.run()

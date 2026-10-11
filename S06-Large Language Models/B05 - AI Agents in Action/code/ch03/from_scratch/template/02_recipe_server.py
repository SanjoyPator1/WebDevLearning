# Problem 02 -- a server with all three primitives, each one wired to show
# how it fails.

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
    # your turn: raise ToolError if cuisine is empty, else return matching names
    raise NotImplementedError


@mcp.tool()
def broken_tool() -> str:
    """A tool that always crashes, to see what a client gets from an unplanned error."""
    # your turn: raise a plain ValueError
    raise NotImplementedError


@mcp.resource("recipes://index")
def index() -> str:
    """List every recipe name this server knows."""
    # your turn: join RECIPES.keys() with newlines
    raise NotImplementedError


@mcp.resource("recipes://{name}")
def recipe(name: str) -> str:
    """Get the full recipe (ingredients and steps) for a given name."""
    # your turn: raise ResourceNotFoundError if name is unknown, else format the recipe
    raise NotImplementedError


@mcp.prompt()
def cook_with(ingredient: str, max_minutes: int) -> str:
    """Ask the model to suggest a recipe using an ingredient, within a time limit."""
    # your turn: raise MCPError(code=INVALID_PARAMS, ...) if max_minutes < 5
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run()

# Problem 05 -- the chapter 2 trip planner's tools, moved onto a real MCP
# server, plus a prompt for the persona and a resource for the house rules.

from mcp.server import MCPServer

mcp = MCPServer("Trip Planner")

DESTINATION_BY_MOOD = {
    "happy": ["Las Vegas", "California"],
    "sad": ["Country Side", "Japan"],
    "relaxing": ["France", "Italy"],
    "adventurous": ["India", "Vietnam"],
    "others": ["India", "France"],
}

WEATHER_CONDITION_BY_DESTINATION = {
    "Las Vegas": {"temperature": 32, "condition": "hot"},
    "California": {"temperature": 22, "condition": "pleasant"},
    "Country Side": {"temperature": 20, "condition": "cool"},
    "Japan": {"temperature": 17, "condition": "cool"},
    "France": {"temperature": 15, "condition": "cool"},
    "Italy": {"temperature": 18, "condition": "mild"},
    "India": {"temperature": 30, "condition": "warm"},
    "Vietnam": {"temperature": 28, "condition": "humid"},
    "others": {"temperature": 0, "condition": "unknown"},
}

ACTIVITIES_LIST_BY_DESTINATION = {
    "Las Vegas": ["Casino", "Nightlife", "Live Shows"],
    "California": ["Beach", "Hiking", "Surfing"],
    "Country Side": ["Nature Walks", "Hiking", "Picnics"],
    "Japan": ["Temples", "Cultural Tours", "Food Tours"],
    "France": ["Museums", "Food Tours", "Sightseeing"],
    "Italy": ["Historical Sites", "Food Tours", "Museums"],
    "India": ["Cultural Tours", "Food Tours", "Hiking"],
    "Vietnam": ["Beaches", "Food Tours", "Hiking"],
    "others": ["Explore Local Area", "Relax", "Sightseeing"],
}


@mcp.tool()
def get_destination_by_mood(mood: str) -> list[str]:
    """Suggest destinations for a given mood, e.g. 'happy', 'sad', 'adventurous'."""
    # your turn
    raise NotImplementedError


@mcp.tool()
def get_weather_condition_by_destination(destination: str) -> dict:
    """Get the temperature and condition for one destination."""
    # your turn
    raise NotImplementedError


@mcp.tool()
def get_activities_by_destination(destination: str) -> list[str]:
    """Get the list of activities for one destination."""
    # your turn
    raise NotImplementedError


@mcp.prompt()
def trip_planner_persona() -> str:
    """The system persona for the trip planning assistant."""
    # your turn: same persona text as chapter 2, plus the "must call tools
    # for at least two destinations" instruction
    raise NotImplementedError


@mcp.resource("trip://travel-rules")
def travel_rules() -> str:
    """House rules that constrain every trip plan this server suggests."""
    # your turn: a couple of short rules, e.g. budget and no overnight travel
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8005, stateless_http=True)

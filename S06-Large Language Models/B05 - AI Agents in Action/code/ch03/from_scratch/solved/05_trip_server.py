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
    return DESTINATION_BY_MOOD.get(mood, DESTINATION_BY_MOOD["others"])


@mcp.tool()
def get_weather_condition_by_destination(destination: str) -> dict:
    """Get the temperature and condition for one destination."""
    return WEATHER_CONDITION_BY_DESTINATION.get(destination, WEATHER_CONDITION_BY_DESTINATION["others"])


@mcp.tool()
def get_activities_by_destination(destination: str) -> list[str]:
    """Get the list of activities for one destination."""
    return ACTIVITIES_LIST_BY_DESTINATION.get(destination, ACTIVITIES_LIST_BY_DESTINATION["others"])


@mcp.prompt()
def trip_planner_persona() -> str:
    """The system persona for the trip planning assistant."""
    return """
You are a trip planner assistant.

**TASK INSTRUCTIONS**
- You will be given a mood of the user.
- First call get_destination_by_mood -- it returns a list of destinations.
- You must call get_weather_condition_by_destination and
  get_activities_by_destination for at least two of those destinations
  before answering.
- Then form the final plan using the values you got back from the tools.
"""


@mcp.resource("trip://travel-rules")
def travel_rules() -> str:
    """House rules that constrain every trip plan this server suggests."""
    return "budget under 5000 rupees per trip\nno overnight travel"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8005, stateless_http=True)

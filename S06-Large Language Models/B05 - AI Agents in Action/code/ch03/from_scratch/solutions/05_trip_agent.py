# Problem 05 -- the chapter 2 agent loop, pointed at tools that now live on
# an MCP server instead of in this file.

import asyncio
import json
import os

from dotenv import load_dotenv
from mcp.client import Client
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

SERVER_URL = "http://127.0.0.1:8005/mcp"


class McpToolbox:
    """Turns an MCP server's tools into OpenAI-shaped schemas, and routes a
    model's tool calls back through the MCP client that owns them."""

    def __init__(self, mcp_client: Client):
        self.mcp_client = mcp_client
        self.schemas: list[dict] = []

    async def load(self) -> None:
        # your turn: list_tools(), build self.schemas (OpenAI function shape)
        
        # get the tools from mcp
        tools = await self.mcp_client.list_tools()

        # create the schema
        self.schemas = [
            {
                "type" : "function",
                "function" : {
                    "name" : tool.name,
                    "description" : tool.description or "",
                    "parameters" : tool.input_schema
                }
            }
            for tool in tools.tools
        ]

    async def call(self, name: str, arguments: dict) -> str:
        # your turn: call_tool, then turn the result into a string --
        # "ERROR: " + text if is_error, else json.dumps(structured_content),
        # else join the text blocks in content
        
        # use mcp tool and call the tool providing the name and the arguments
        result = await self.mcp_client.call_tool(name, arguments)

        if result.is_error:
            # return it back to the caller so they can show it to the llm
            return "ERROR: " + result.content[0].text

        # guard claude return early if the tool returned a structured content
        if result.structured_content is not None:
            return json.dumps(result.structured_content)

        return "\n".join(block.text for block in result.content)

async def run_tool_loop(messages, toolbox: McpToolbox, *, max_steps=6):
    # your turn: same loop shape as chapter 2, but dispatch tool calls
    # through toolbox.call(name, arguments) instead of a local handler dict
    
    for _ in range(max_steps):
        response = await client.chat.completions.create(
            model=MODEL_NAME, messages=messages, tools=toolbox.schemas
        )
        message = response.choices[0].message

        # guard clause for end result i.e. no more tool call by model
        if not message.tool_calls:
            messages.append({
                "role" : "assistant",
                "content" : message.content or ""
            })

            return messages, message.content or ""

        # add the intermediate assistant response with role assistant and tool calls data
        messages.append({
            "role" : "assistant",
            "content" : message.content,
            "tool_calls" : [tc.model_dump() for tc in message.tool_calls]
        })

        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            print(f"    tool_call : {tool_call.function.name}({arguments})")

            # calling the tool that the llm requested using
            # the message -> tool_calls -> tool_call -> function.name
            result_text = await toolbox.call(tool_call.function.name, arguments)
            print(f"    tool result: {result_text}")

            # adding the tool call result to the messages
            messages.append({
                "role" : "tool",
                "tool_call_id" : tool_call.id,
                "content" : result_text
            })

    # edge case when no tool call was done and no final result
    return messages, None
        
async def main() -> None:
    print(f"[agent] connecting to {SERVER_URL}")

    async with Client(SERVER_URL) as mcp_client:
        # your turn: fetch the persona prompt and the travel-rules resource,
        # combine them into one system message -- this is the app deciding,
        # not the model
        prompt_result = await mcp_client.get_prompt("trip_planner_persona")
        persona = prompt_result.messages[0].content.text

        rules_result = await mcp_client.read_resource("trip://travel-rules")
        rules = rules_result.contents[0].text

        system_prompt = f"{persona}\n\n**HOUSE RULES**\n{rules}"
        print("[agent] system prompt built from: prompt 'trip_planner_persona' + resource 'trip://travel-rules'")
        print("system prompt : \n",system_prompt)

        # your turn: build an McpToolbox, load it, print the tool names
        toolbox = McpToolbox(mcp_client)
        await toolbox.load()
        print(f"[agent] tools from server: {[s['function']['name'] for s in toolbox.schemas]}")

        # your turn: build messages (system + a user mood message), run the
        # loop, print the final answer

        messages = [
            {
                "role" : "system",
                "content" : system_prompt
            },
            {
                "role" : "user",
                "content" : "I am feeling adventurous this weekend"
            }
        ]

        messages, final_answer = await run_tool_loop(messages, toolbox)

        print(f"Messages value at the end : ")
        print(json.dumps(messages, indent=4))

        print("\nFinal answer : ")
        print(final_answer or "(step budget ran out before a final answer)")


if __name__ == "__main__":
    asyncio.run(main())

# TERMINAL LOGS
# python 05_trip_agent.py
# [agent] connecting to http://127.0.0.1:8005/mcp
# [agent] system prompt built from: prompt 'trip_planner_persona' + resource 'trip://travel-rules'
# system prompt : 
 
# You are a trip planner assistant.

# **TASK INSTRUCTIONS**
# - You will be given a mood of the user.
# - First call get_destination_by_mood -- it returns a list of destinations.
# - You must call get_weather_condition_by_destination and
#   get_activities_by_destination for at least two of those destinations
#   before answering.
# - Then form the final plan using the values you got back from the tools.


# **HOUSE RULES**
# budget under 5000 rupees per trip
# no overnight travel
# [agent] tools from server: ['get_destination_by_mood', 'get_weather_condition_by_destination', 'get_activities_by_destination']
#     tool_call : get_destination_by_mood({'mood': 'adventurous'})
#     tool result: {"result": ["India", "Vietnam"]}
#     tool_call : get_weather_condition_by_destination({'destination': 'India'})
#     tool result: {
#   "temperature": 30,
#   "condition": "warm"
# }
#     tool_call : get_activities_by_destination({'destination': 'India'})
#     tool result: {"result": ["Cultural Tours", "Food Tours", "Hiking"]}
#     tool_call : get_weather_condition_by_destination({'destination': 'Vietnam'})
#     tool result: {
#   "temperature": 28,
#   "condition": "humid"
# }
#     tool_call : get_activities_by_destination({'destination': 'Vietnam'})
#     tool result: {"result": ["Beaches", "Food Tours", "Hiking"]}


# Messages value at the end : 
# [
#     {
#         "role": "system",
#         "content": "\nYou are a trip planner assistant.\n\n**TASK INSTRUCTIONS**\n- You will be given a mood of the user.\n- First call get_destination_by_mood -- it returns a list of destinations.\n- You must call get_weather_condition_by_destination and\n  get_activities_by_destination for at least two of those destinations\n  before answering.\n- Then form the final plan using the values you got back from the tools.\n\n\n**HOUSE RULES**\nbudget under 5000 rupees per trip\nno overnight travel"
#     },
#     {
#         "role": "user",
#         "content": "I am feeling adventurous this weekend"
#     },
#     {
#         "role": "assistant",
#         "content": null,
#         "tool_calls": [
#             {
#                 "id": "call_400925",
#                 "function": {
#                     "arguments": "{\"mood\":\"adventurous\"}",
#                     "name": "get_destination_by_mood"
#                 },
#                 "type": "function",
#                 "extra_content": {
#                     "google": {
#                         "thought_signature": "EmAKXgFpFH0TOksur0LQwXcSNx5QbfqBsfw6T0xRC8FHCTJ92941YuhYIx4jwMUc4PEIAgMFmuBJM+f1PHw6ds/CSv9mTE1vKjJQO6sym1cDc17LdxWoqBjlmKCP875V5p0="
#                     }
#                 }
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_400925",
#         "content": "{\"result\": [\"India\", \"Vietnam\"]}"
#     },
#     {
#         "role": "assistant",
#         "content": null,
#         "tool_calls": [
#             {
#                 "id": "call_270174",
#                 "function": {
#                     "arguments": "{\"destination\":\"India\"}",
#                     "name": "get_weather_condition_by_destination"
#                 },
#                 "type": "function",
#                 "extra_content": {
#                     "google": {
#                         "thought_signature": "EmAKXgFpFH0T3zHg22n6Ut4rgJR746R5BkwOyMJj4Rojszv5gJXuvm9BCVGWn30yEhc1mrJW8Zt3r2vmdUKgJnRJPM9qPV5cmtGy2wW3K9/d6nexuTkU4mH8jsKoG1YKBhc="
#                     }
#                 }
#             },
#             {
#                 "id": "call_270175",
#                 "function": {
#                     "arguments": "{\"destination\":\"India\"}",
#                     "name": "get_activities_by_destination"
#                 },
#                 "type": "function"
#             },
#             {
#                 "id": "call_270176",
#                 "function": {
#                     "arguments": "{\"destination\":\"Vietnam\"}",
#                     "name": "get_weather_condition_by_destination"
#                 },
#                 "type": "function"
#             },
#             {
#                 "id": "call_270177",
#                 "function": {
#                     "arguments": "{\"destination\":\"Vietnam\"}",
#                     "name": "get_activities_by_destination"
#                 },
#                 "type": "function"
#             }
#         ]
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_270174",
#         "content": "{\n  \"temperature\": 30,\n  \"condition\": \"warm\"\n}"
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_270175",
#         "content": "{\"result\": [\"Cultural Tours\", \"Food Tours\", \"Hiking\"]}"
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_270176",
#         "content": "{\n  \"temperature\": 28,\n  \"condition\": \"humid\"\n}"
#     },
#     {
#         "role": "tool",
#         "tool_call_id": "call_270177",
#         "content": "{\"result\": [\"Beaches\", \"Food Tours\", \"Hiking\"]}"
#     },
#     {
#         "role": "assistant",
#         "content": "Since you are feeling adventurous this weekend, here are two options based on your mood, keeping our house rules in mind (budget under \u20b95000 and no overnight travel):\n\n### Option 1: India\n* **Weather:** Warm, around 30\u00b0C\n* **Activities Available:** Cultural Tours, Food Tours, and Hiking\n* **Adventure Plan:** You can head out for a local hiking trail nearby and follow it up with an exciting food tour in the evening. This easily fits within a single day, keeping travel local and your budget well under \u20b95000.\n\n### Option 2: Vietnam\n* **Weather:** Humid, around 28\u00b0C\n* **Activities Available:** Beaches, Food Tours, and Hiking\n* **Adventure Plan:** If you want a coastal and rugged feel, you can plan a day trip involving a scenic hike followed by a relaxing or active beach excursion. \n\n*(Note: Since overnight travel is restricted, please choose a specific regional destination or local spot within your vicinity that matches these options!)*"
#     }
# ]

# Final answer : 
# Since you are feeling adventurous this weekend, here are two options based on your mood, keeping ourhouse rules in mind (budget under ₹5000 and no overnight travel):

# ### Option 1: India
# * **Weather:** Warm, around 30°C
# * **Activities Available:** Cultural Tours, Food Tours, and Hiking
# * **Adventure Plan:** You can head out for a local hiking trail nearby and follow it up with an exciting food tour in the evening. This easily fits within a single day, keeping travel local and your budget well under ₹5000.

# ### Option 2: Vietnam
# * **Weather:** Humid, around 28°C
# * **Activities Available:** Beaches, Food Tours, and Hiking
# * **Adventure Plan:** If you want a coastal and rugged feel, you can plan a day trip involving a scenic hike followed by a relaxing or active beach excursion. 

# *(Note: Since overnight travel is restricted, please choose a specific regional destination or localspot within your vicinity that matches these options!)*


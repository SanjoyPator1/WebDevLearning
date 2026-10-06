# hand written exercise - no ai no autocomplete
# use doc or search google stackoverflow like old days

import asyncio
import os
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

# PROVIDER = "gemini"
PROVIDER = "ollama"

if PROVIDER == "gemini":
    # create client for gemini
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    MODEL_NAME = os.environ["GEMINI_MODEL"]

elif PROVIDER =="ollama":
    client = AsyncOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama"
    )
    MODEL_NAME = "qwen3:4b"

else:
    raise ValueError(f"unknown provider: {PROVIDER}")

# Constant lookup table
# Destination by mood lookup
DESTINATION_BY_MOOD = {
    "happy": ["Las Vegas", "California"],
    "sad": ["Country Side", "Japan"],
    "relaxing": ["France", "Italy"],
    "adventurous": ["India", "Vietnam"],
    "others": ["India", "France"],
}


# Weather condition lookup table based on destination
WEATHER_CONDITION_BY_DESTINATION = {
    "Las Vegas": {
        "temperature": 32,
        "condition": "hot",
    },
    "California": {
        "temperature": 22,
        "condition": "pleasant",
    },
    "Country Side": {
        "temperature": 20,
        "condition": "cool",
    },
    "Japan": {
        "temperature": 17,
        "condition": "cool",
    },
    "France": {
        "temperature": 15,
        "condition": "cool",
    },
    "Italy": {
        "temperature": 18,
        "condition": "mild",
    },
    "India": {
        "temperature": 30,
        "condition": "warm",
    },
    "Vietnam": {
        "temperature": 28,
        "condition": "humid",
    },
    "others": {
        "temperature": 0,
        "condition": "unknown",
    },
}


# Activities lookup table based on destination
ACTIVITIES_LIST_BY_DESTINATION = {
    "Las Vegas": [
        "Casino",
        "Nightlife",
        "Live Shows",
    ],
    "California": [
        "Beach",
        "Hiking",
        "Surfing",
    ],
    "Country Side": [
        "Nature Walks",
        "Hiking",
        "Picnics",
    ],
    "Japan": [
        "Temples",
        "Cultural Tours",
        "Food Tours",
    ],
    "France": [
        "Museums",
        "Food Tours",
        "Sightseeing",
    ],
    "Italy": [
        "Historical Sites",
        "Food Tours",
        "Museums",
    ],
    "India": [
        "Cultural Tours",
        "Food Tours",
        "Hiking",
    ],
    "Vietnam": [
        "Beaches",
        "Food Tours",
        "Hiking",
    ],
    "others": [
        "Explore Local Area",
        "Relax",
        "Sightseeing",
    ],
}

# tool schema
get_destination_by_mood_tool_schema = {
    "type" : "function",
    "function" : {
        "name" : "get_destination_by_mood",
        "description" : (
            "provides you with a list of destination for a trip based on your input mood"        
        ),
        "parameters" : {
            "type" : "object",
            "properties" : {
                "mood" : {
                    "type" : "string",
                    "description" : (
                        "current mood of the user based on which we will decide the destination"
                        "example - happy, sad, relaxing, adventurous etc"
                    )
                },
            },
            "required" : ["mood"]
        },
    }
}

get_weather_condition_by_destination_tool_schema = {
    "type": "function",
    "function" : {
        "name" : "get_weather_condition_by_destination",
        "description" : (
            "provides you with a weather condition i.e. temperature and"
            "condition(e.g. sunny, rainy etc) given the destination name"
        ),
        "parameters" : {
            "type" : "object",
            "properties" : {
                "destination" : {
                    "type" :  "string",
                    "description" : (
                        "input destination based on which we will return the temperature and condition"
                        "its a single destination used here"
                    ),
                },
            },
            "required" : ["destination"]
        },
    }
}

get_activities_by_destination_tool_schema = {
    "type" : "function",
    "function" : {
        "name" : "get_activities_by_destination",
        "description" : (
            "provides you with a list of activities based on the destination you give"
        ),
        "parameters" : {
            "type" : "object",
            "properties" : {
                "destination" : {
                    "type" : "string",
                    "description" : (
                        "this is the input destination based on which we will return"
                        "a list of activities"
                    )
                }
            },
            "required" : ["destination"]
        }
    }
}

tool_schema = [get_destination_by_mood_tool_schema, get_weather_condition_by_destination_tool_schema, get_activities_by_destination_tool_schema]

# tool functions
def get_destination_by_mood(mood: str) -> list[str]:

    destination_list = DESTINATION_BY_MOOD.get(mood, DESTINATION_BY_MOOD["others"])

    return destination_list

def get_weather_condition_by_destination(destination: str):

    weather_condition = WEATHER_CONDITION_BY_DESTINATION.get(destination, WEATHER_CONDITION_BY_DESTINATION["others"])

    return weather_condition

def get_activities_by_destination(destination: str):

    activities_list = ACTIVITIES_LIST_BY_DESTINATION.get(destination, ACTIVITIES_LIST_BY_DESTINATION["others"])

    return activities_list


# tool handlers
tool_handlers = {
    "get_destination_by_mood" : get_destination_by_mood,
    "get_weather_condition_by_destination" : get_weather_condition_by_destination,
    "get_activities_by_destination" : get_activities_by_destination
}

instructions = """
You are a trip planner assistant.

**TASK INSTRUCTIONS**
- You will be given a mood of the user
- Based on that mood you have to first call get_destination_by_mood and it will return a list of destination
- You must call these two tools for at least two of the returned destinations before answering
- Then based on those destination you can call get_weather_condition_by_destination and get_activities_by_destination - which takes one destination at a time - so call them multiple time for all the destination
- At the end based on the tool calls form the final plan with the values that you got at the end
"""

class DestinationWeatherActivities(BaseModel):
    destination: str
    temperature: int
    condition: str
    activities: list[str]

class DestinationsData(BaseModel):
    mood: str
    destinations: list[DestinationWeatherActivities]

async def run_tool_loop(messages, tools_schema, tool_handlers, *, max_steps=6):
    for step in range(max_steps):
        # call the llm with the current messages, tools
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools_schema
        )

        message = response.choices[0].message

        # if the model is not calling any tool - its the final answer
        if not message.tool_calls:
            messages.append({
                "role" : "assistant",
                "content" : message.content or ""
            })

            # return the messages and this current turn message content
            return messages, message.content or ""

        # if the above guard is broken then its a tool call
        messages.append({
            "role" : "assistant",
            "tool_calls" : [tc.model_dump() for tc in message.tool_calls]
        })

        # iterate the tool calls done by model and handle it
        for tool_call in message.tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            print(f"     [tool] call: {tool_call.function.name} ({arguments})")

            handler = tool_handlers[tool_call.function.name]
            result = handler(**arguments)

            if hasattr(result, "__await__"):
                result = await result

            print(f"        [tool] result -> {result}")

            # adding the tool result in the messages
            messages.append({
                "role" : "tool",
                "tool_call_id" : tool_call.id,
                "content" : json.dumps(result, default=str)
            })

    return messages, None   # budget exhausted, no final text


async def run_llm_output_forcing_completion(messages: list[any], response_format_model: any):
    if PROVIDER == "gemini":
        response = await client.chat.completions.parse(
            model=MODEL_NAME,
            messages = messages,
            response_format = response_format_model
        )
    elif PROVIDER == "ollama":
        response = await client.chat.completions.parse(
            model=MODEL_NAME,
            messages = messages,
            response_format = response_format_model
        )

    return response
    
    

async def main():
    #step 1 : building messages and running the tool loop
    topic = "Plan me a trip - my current mood is sad"

    messages = [
        {
            "role" : "system", "content": instructions
        },
        {
            "role" : "user", "content":  topic
        }
    ]

    messages, plan_text = await run_tool_loop(
        messages,
        tool_schema,
        tool_handlers
    )

    print("\nPlan_text : ",plan_text)

    # step 2 : one more, tool less call to extract the structured destination result from the same conversation
    messages.append({
        "role": "user",
        "content": (
            "Now convert the plan above into ONLY JSON object of this exact shape,"
            "no other text or any markdown fences"
        )
    })

    response = await run_llm_output_forcing_completion(messages=messages, response_format_model=DestinationsData)
    json_result = response.choices[0].message.parsed
    print(f"    json result back from the model is this : \n")
    print(json_result.model_dump_json(indent=2))

    print(f"mood: {json_result.mood}")
    for destination in json_result.destinations:
        print(f"  {destination.destination}: {destination.temperature} deg, {destination.condition}")
        print(f"    activities: {destination.activities}")


if __name__ == "__main__":
    asyncio.run(main())

# got this output from running this file
# gemini model output
#      [tool] call: get_destination_by_mood ({'mood': 'sad'})
#         [tool] result -> ['Country Side', 'Japan']
#      [tool] call: get_weather_condition_by_destination ({'destination': 'Country Side'})
#         [tool] result -> {'temperature': 20, 'condition': 'cool'}
#      [tool] call: get_activities_by_destination ({'destination': 'Country Side'})
#         [tool] result -> ['Nature Walks', 'Hiking', 'Picnics']
#      [tool] call: get_weather_condition_by_destination ({'destination': 'Japan'})
#         [tool] result -> {'temperature': 17, 'condition': 'cool'}
#      [tool] call: get_activities_by_destination ({'destination': 'Japan'})
#         [tool] result -> ['Temples', 'Cultural Tours', 'Food Tours']

# Plan_text :  Here is a trip plan to help lift your spirits based on your current mood:

# ### Destination 1: Country Side
# * **Weather:** Cool, around 20°C
# * **Activities:** 
#   * Nature Walks
#   * Hiking
#   * Picnics
# * **Why it's great for you:** The peaceful scenery, fresh air, and gentle outdoor activities like picnics and nature walks are perfect for unwinding, reflecting, and finding comfort.

# ---

# ### Destination 2: Japan
# * **Weather:** Cool, around 17°C
# * **Activities:** 
#   * Temples
#   * Cultural Tours
#   * Food Tours
# * **Why it's great for you:** Immersing yourself in serene temples, rich cultural history, and comforting culinary experiences can provide a grounding and restorative escape. 

# Safe travels and I hope this trip brings you peace and joy!
#     json result back from the model is this : 

# {
#   "mood": "sad",
#   "destinations": [
#     {
#       "destination": "Country Side",
#       "temperature": 20,
#       "condition": "cool",
#       "activities": [
#         "Nature Walks",
#         "Hiking",
#         "Picnics"
#       ]
#     },
#     {
#       "destination": "Japan",
#       "temperature": 17,
#       "condition": "cool",
#       "activities": [
#         "Temples",
#         "Cultural Tours",
#         "Food Tours"
#       ]
#     }
#   ]
# }
# mood: sad
#   Country Side: 20 deg, cool
#     activities: ['Nature Walks', 'Hiking', 'Picnics']
#   Japan: 17 deg, cool
#     activities: ['Temples', 'Cultural Tours', 'Food Tours']

# ollama qwen3:4b output
#      [tool] call: get_destination_by_mood ({'mood': 'sad'})
#         [tool] result -> ['Country Side', 'Japan']
#      [tool] call: get_weather_condition_by_destination ({'destination': 'Country Side'})
#         [tool] result -> {'temperature': 20, 'condition': 'cool'}
#      [tool] call: get_weather_condition_by_destination ({'destination': 'Japan'})
#         [tool] result -> {'temperature': 17, 'condition': 'cool'}
#      [tool] call: get_activities_by_destination ({'destination': 'Country Side'})
#         [tool] result -> ['Nature Walks', 'Hiking', 'Picnics']
#      [tool] call: get_activities_by_destination ({'destination': 'Japan'})
#         [tool] result -> ['Temples', 'Cultural Tours', 'Food Tours']

# Plan_text :  Based on your sad mood, here's a personalized trip plan:

# **Recommended Destination**: Country Side  
# **Weather**: Cool (20°C)  
# **Suggested Activities**: Nature Walks, Hiking, Picnics  

# This peaceful setting with natural surroundings and gentle activities is ideal for easing sadness through calming outdoor experiences. 

# *Alternative*: Japan (cool 17°C) with Temples, Cultural Tours, and Food Tours could also provide a thoughtful break, though Country Side aligns more closely with immediate mood relief.
#     json result back from the model is this : 

# {
#   "mood": "sad",
#   "destinations": [
#     {
#       "destination": "Country Side",
#       "temperature": 20,
#       "condition": "cool",
#       "activities": [
#         "Nature Walks",
#         "Hiking",
#         "Picnics"
#       ]
#     },
#     {
#       "destination": "Japan",
#       "temperature": 17,
#       "condition": "cool",
#       "activities": [
#         "Temples",
#         "Cultural Tours",
#         "Food Tours"
#       ]
#     }
#   ]
# }
# mood: sad
#   Country Side: 20 deg, cool
#     activities: ['Nature Walks', 'Hiking', 'Picnics']
#   Japan: 17 deg, cool
#     activities: ['Temples', 'Cultural Tours', 'Food Tours']

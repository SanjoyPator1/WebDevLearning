# Chapter 2 — Own Practice: Weekend Trip Planner Agent

## How This Folder Is Different

Every file in `from_scratch/` came with a scaffold: a docstring spec, numbered steps, a `# --- Your turn ---` stub, and a `solved/` reference to check against. This folder has none of that on purpose. Below is a problem statement only — intuition, requirements, and an example of the expected output shape. No function signatures, no step-by-step build order, no solved reference (yet). Design the file structure, the helper functions, and the control flow yourself. Write it in a new file in this folder, e.g. `trip_planner_agent.py`.

The goal isn't a new concept — it's using everything from chapter 2 together, unassisted, so you can tell for yourself whether it's internalized or you were still leaning on the scaffold.

## The Scenario

Build an agent that plans a short trip. Given a `mood` ("relaxing", "adventurous", or anything else the user types), it should:

1. Look up a short list of candidate destinations matching that mood.
2. For at least two of those destinations, look up the weather and a list of activities.
3. Produce a final itinerary covering those destinations, as a validated, typed object — not a raw string you parse yourself.

## Required Techniques (the chapter 2 checklist)

Your implementation must use all of the following. Treat this as a checklist, not an ordered list of steps:

- **Three tools**, each a plain Python function with its own hand-written JSON schema (no decorator), registered together in one `tools_schema` list and one handler dict:
  - A destination-lookup tool, taking the mood as input, returning a short list of candidate destination names. Hardcode a small lookup table keyed by mood, with a sensible fallback list for an unrecognized mood — it should never crash on an unexpected input.
  - A weather-lookup tool, taking a destination name, returning a temperature and a condition (e.g. "Sunny", "Rainy"). Hardcode a lookup table with a fallback for an unknown destination.
  - An activities-lookup tool, taking a destination name, returning a short list of activity strings. Same hardcode-plus-fallback pattern.
- **Real tool chaining, not just multiple tools.** The weather and activities tools both need a destination name that only the first tool's result can supply. Don't hint the destination names anywhere else in the prompt — the model has to actually read the first tool's result out of the conversation and pass a name it saw, not guess one. You verify this the same way file 8 did: by reading a trace of tool calls afterward and confirming the order, not by assuming it worked because you got output.
- **At least one instance of calling a tool more than once in a single run** — the model should call the weather and/or activities tool for two different destinations, not just one. Nothing about your tool-dispatch code should need to change to support this; if it does, that's a sign the loop isn't general enough yet.
- **Native structured output, not the "asking" pattern.** The final itinerary must come back through provider-level schema forcing — `response_format=` with `.parse()` on the Gemini/OpenAI-compatible client, not a hand-written JSON-format instruction plus `json.loads`/`model_validate` in a `try/except`. You've now built both the asking and forcing paths once already; this is forcing only.
- **A persona that drives all of this without over-specifying it.** The system prompt should tell the model what order to do things in at a high level (look up destinations first, then investigate at least two of them, then produce the itinerary) — it should not need to spell out tool names or exact call counts for the model to behave correctly.

## Gotchas Worth Remembering (you've met all of these already)

- Strict/native schema enforcement guarantees **shape, not quantity or content**. Nothing in a JSON Schema can force "at least 2 destinations" — that has to come from the persona's instructions, and the model can still under- or over-deliver. Don't be surprised if you need to tighten the prompt wording after a first attempt.
- If you're on Gemini and manually reconstructing an assistant message's `tool_calls` after a tool-calling turn, don't hand-pick fields — Gemini attaches extra data (a thought signature) to each tool call that must be echoed back unchanged, or the next call in the loop fails with a 400. You already found and fixed this exact bug in file 7.
- If you extend this to Ollama as well (optional, see below), remember `qwen3:8b` is a thinking model — a forced-schema call with thinking left on can return a schema-valid but empty or degenerate result. You already found this in file 9.
- A tool handler should never crash on an input it didn't expect. Every lookup table needs a fallback value, the same pattern as `get_resource_url`'s unknown-source fallback in file 8.

## Example

**Input:** mood = `"adventurous"`

**Expected shape of the final result** (a validated Pydantic instance, not a string you parsed):

```json
{
  "mood": "adventurous",
  "destinations": [
    {
      "destination": "Manali",
      "temperature_c": 12,
      "condition": "Snowy",
      "activities": ["paragliding", "river rafting"]
    },
    {
      "destination": "Rishikesh",
      "temperature_c": 22,
      "condition": "Clear",
      "activities": ["white-water rafting", "bungee jumping"]
    }
  ]
}
```

Your actual destination names, weather values, and activities can be whatever you hardcode — the shape (a top-level `mood` plus a list of per-destination records, each with weather and activities) is what matters, and it must be the result of real tool calls, not something you wrote directly into the final model.

## Stretch Goals (optional, not required to call this done)

- Add a fourth tool with no dependency on the others (e.g. a packing-list suggestion based on the weather result), to practice registering a tool that chains off a *different* tool's result than the other two do.
- Run the same flow against Ollama too, using its native `format=` field, and compare: does the chaining still happen correctly on a smaller local model? Does `think=False` change anything here, the way it did in file 9?
- Add a temperature/sampling setting to the final structured-output call and note whether it visibly changes which destinations or activities get chosen between runs.

## When You're Done

Run it, read through the trace output yourself, and check off the required-techniques list above against your own code before considering it finished. If you want a reference to compare against afterward, ask for one then — not before, since seeing it first defeats the point of this folder.

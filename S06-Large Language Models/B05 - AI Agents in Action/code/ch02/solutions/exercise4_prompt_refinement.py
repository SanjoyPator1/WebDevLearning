# ============================================================
# EXERCISE 4: Apply prompt-engineering best practices.
# REF: Chapter 2, §2.5 Exercise 4 / table 2.2
# PROVIDERS: gemini (default) or ollama — see switch below
# ============================================================

# Exercise 4: Apply prompt-engineering best practices.

# Objective: Refine the prompt to use delimiters, explicit role, and length limits.

# Tasks:

# Duplicate the previous file as exercise4_prompt_refinement.py.
# Rewrite instructions so they follow at least four techniques from table 2.2 (for example, a clear persona, delimiters, a specific length, and positive wording).
# Add a Markdown code fence (```) around the TASK block to act as a delimiter.
# Keep the temperature at 0, and run the script twice.
# Confirm each run returns exactly five tasks, each ≤ 7 words (tight length spec).

# =============================================================================
# Table 2.2 Essential Prompt Techniques
# =============================================================================
#
# | Technique                              | Description                                      | Example prompt snippet                                       | How it works with agents                                      |
# |----------------------------------------|--------------------------------------------------|--------------------------------------------------------------|---------------------------------------------------------------|
# | Assign a clear role or persona         | State a role that sets vocabulary, tone,         | "You are a senior DevOps engineer. Diagnose the Docker       | Switch persona strings to create researcher, critic, or      |
# |                                        | and depth.                                       | error below …"                                               | planner agents without code changes.                         |
# | Front-load Instructions and use        | Put the directive first; fence user data         | Task: Summarize in ≤100 words. Article: `...`                | Always apply this practice with agents.                      |
# | delimiters                             | with unique markers.                             |                                                              |                                                               |
# | Be specific and detailed               | Supply concrete length, audience, and objective. | "Write a 200-word LinkedIn post in a friendly tone with      | Prevents agents from producing outputs that violate word     |
# |                                        |                                                  | two actionable tips …"                                       | limits or brand tone.                                        |
# | Define the exact output format         | Provide a skeleton JSON / CSV / Markdown         | {"title": "", "key_points": ["", "", ""], "cta": ""}         | OpenAI Agents SDK supports typed outputs, so this won't be    |
# |                                        | structure.                                       |                                                              | required in our examples.                                     |
# | Use few-shot examples                  | Embed labelled examples as mini unit-tests.      | Input: "Free Bitcoin!!!" ⇒ Label: Spam                       | Agents can store examples in a vector DB and retrieve        |
# |                                        |                                                  | Input: "Team lunch?" ⇒ Label: Not Spam                       | similar ones at runtime for adaptive prompting.              |
# | Chain-of-thought for complex reasoning | Ask the model to think step by step, then        | "Let's work this out step by step … Return only the final    | Produces an auditable reasoning trace that a critic or        |
# |                                        | answer.                                          | value."                                                      | verifier agent can inspect before execution.                  |
# | Emphasize positive instructions        | Say what to do, not just what to avoid.          | "Explain using high-school language." (versus                | Positive phrasing lowers rule-violation rates, boosting      |
# |                                        |                                                  | "Don't use jargon.")                                         | autonomous reliability.                                      |
# | Eliminate ambiguity                    | Replace fuzzy words with numeric bounds.         | "Provide 3–4 key points under 50 words total."               | Agent guardrails can auto-check length and count and trigger  |
# |                                        |                                                  |                                                              | retries if out of spec.                                      |
# | Pick the right model and settings      | Match model tier and generation knobs to         | model=gpt-4o, temperature=0.7, max_tokens=300                | Balances cost, latency, and reasoning depth so agents meet    |
# |                                        | the task.                                        |                                                              | specifications.                                               |
# | Iterate and refine                     | Treat each response as feedback; tighten and     | After each run, log prompt + output; adjust length spec or   | Logs feed a format-fixer sub-agent or fine-tune, creating a  |
# |                                        | repeat.                                          | add an example; rerun until >95% on spec.                    | self-improving agent pipeline.                                |
#
# =============================================================================

import os

from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled, ModelSettings
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from typing_extensions import TypedDict

load_dotenv()
set_tracing_disabled(True)

PROVIDER = "gemini"  # "gemini" or "ollama"

if PROVIDER == "gemini":
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    MODEL_NAME = os.environ["GEMINI_MODEL"]
elif PROVIDER == "ollama":
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL_NAME = "qwen3:8b"
else:
    raise ValueError(f"unknown PROVIDER: {PROVIDER!r}")

# --- Your turn ---
# Rewrite the persona to use at least 4 distinct prompt-engineering
# techniques (pick from: clear persona/role, delimiters, a specific length
# limit, few-shot examples, chain-of-thought, positive phrasing, eliminating
# ambiguity). Wrap the task/topic block in a Markdown code fence as one of
# your delimiters. Keep temperature at 0. Run it twice and confirm each run
# gives exactly 5 tasks, each 7 words or fewer.

# Agent Instructions
instructions = """
You are an expert research librarian and academic project planner.

```task
TASK DIRECTIVES:
1. You will receive a research topic enclosed in ```topic fences.
2. Produce a high-level research plan containing exactly 5 sequential tasks.
3. Keep each task description 7 words or fewer.
4. Begin every task description with an active imperative verb (such as "Survey", "Analyze", "Compare", "Interview", or "Draft").
5. Number the tasks sequentially from id 1 to 5.
```
"""

class Task(TypedDict):
    id: int
    description: str

class ResearchPlanModel(BaseModel):
    task: list[Task]
    """A list of tasks to perform for research"""

    model_config = ConfigDict(extra='forbid')

agent = Agent(
    name="Research Planner",
    instructions=instructions,
    model=OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client),
    model_settings= ModelSettings(
        temperature=0.0,
    ),
    output_type=ResearchPlanModel
)

raw_topic = "learn about ai agents"

input_data = f"""
```topic
{raw_topic}
```
"""

result = Runner.run_sync(
    agent,
    input=input_data
)

print(result.final_output)

# Automated verification check:
plan = result.final_output
tasks = plan.task
print(f"\nTotal tasks returned: {len(tasks)} (Expected: 5)")
assert len(tasks) == 5, f"Expected 5 tasks, got {len(tasks)}"
for t in tasks:
    word_count = len(t["description"].split())
    print(f"Task {t['id']} ({word_count} words): {t['description']}")
    assert word_count <= 7, f"Task '{t['description']}' exceeded 7 words ({word_count} words)"
print("\nVerification Passed: Exactly 5 tasks, all <= 7 words!")

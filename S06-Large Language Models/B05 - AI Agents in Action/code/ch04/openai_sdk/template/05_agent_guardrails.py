# ============================================================
# LISTING: 05_agent_guardrails.py  (reference implementation)
# BUILDING: A Drafting Agent protected by THREE layers of guardrail, from
#           cheapest to most expensive:
#             1. plain-code input guardrail  (blocks out-of-scope requests)
#             2. plain-code output guardrail (rejects replies that are too short)
#             3. agent-as-guardrail          (a real extra LLM call that
#                                             judges tone)
#           plus a bounded retry loop that feeds each rejection reason
#           back into the next attempt.
# REF: Chapter 4 notes, sections 9 (guardrails: semantic circuit breakers)
#      and 10 (guardrails at the handoff boundary)
# PROVIDERS: gemini (default) or ollama -- see switch below
# ============================================================
#
# A guardrail is a circuit breaker that stops a risky action BEFORE it
# happens -- not a filter that cleans up a mess after the fact. Tiers 1
# and 2 below cost nothing extra (plain Python); tier 3 is a genuine
# second model call every time it runs, which is worth noticing in the
# printed output.

import asyncio
import os

from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    OpenAIChatCompletionsModel,
    OutputGuardrailTripwireTriggered,
    Runner,
    input_guardrail,
    output_guardrail,
    set_tracing_disabled,
)
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()
set_tracing_disabled(True)  # no real OpenAI key -> no trace export attempts

PROVIDER = "gemini"  # "gemini" or "ollama"

if PROVIDER == "gemini":
    client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )
    MODEL_NAME = os.environ["GEMINI_MODEL"]
elif PROVIDER == "ollama":
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL_NAME = "qwen3:8b"  # swap for whatever tag `ollama list` shows you
else:
    raise ValueError(f"unknown PROVIDER: {PROVIDER!r}")

model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)

MAX_RETRIES = 2
MINIMUM_REPLY_LENGTH = 40
FORBIDDEN_TOPICS = ["legal advice", "lawsuit", "sue the company"]


class DraftedReply(BaseModel):
    reply_text: str

# --- Your turn ---
# 1. Write block_out_of_scope_requests(ctx, agent, input_text), decorated
#    with @input_guardrail. Check (case-insensitively) whether input_text
#    contains any string from FORBIDDEN_TOPICS. Print what you found.
#    Return GuardrailFunctionOutput(output_info=..., tripwire_triggered=...)
#    -- tripwire_triggered=True means "block this".
#
# 2. Write require_minimum_length(ctx, agent, output: DraftedReply),
#    decorated with @output_guardrail. Check whether
#    len(output.reply_text) < MINIMUM_REPLY_LENGTH. Print the length you
#    found, then return a GuardrailFunctionOutput the same way.
#
# 3. Build drafting_agent = Agent(...) with model=model,
#    output_type=DraftedReply, input_guardrails=[<your tier-1 input
#    guardrail>], output_guardrails=[<your tier-1 output guardrail>].
#
# 4. Build a ToneCheck(BaseModel) with is_professional_tone: bool and
#    reason: str, and a tone_guardrail_agent = Agent(...) whose job is to
#    judge tone and return that structured output.
#
# 5. Write async check_tone_before_sending(reply_text) -> ToneCheck that
#    runs tone_guardrail_agent on reply_text and returns its final_output.
#    Print a note that this is a real extra LLM call (tier 3).
#
# 6. Write async draft_and_send(ticket_text) -> str with a for-loop up to
#    MAX_RETRIES attempts:
#      - Runner.run(drafting_agent, current_input) inside a try/except
#        catching InputGuardrailTripwireTriggered (return a "blocked"
#        message immediately) and OutputGuardrailTripwireTriggered (fold
#        the rejection reason into current_input and `continue`).
#      - If drafting succeeds, call check_tone_before_sending() on the
#        reply. If the tone check fails, fold the reason into
#        current_input and `continue`.
#      - If everything passes, return the reply.
#    If the loop exhausts MAX_RETRIES, return an escalation message.
#
# 7. Write an async main() that calls draft_and_send() on both sample
#    tickets below and prints the final result for each.

tickets = [
    "My card was charged twice for order ORD-4471, please help.",
    "I want legal advice on whether I can sue the company.",
]

if __name__ == "__main__":
    asyncio.run(main())

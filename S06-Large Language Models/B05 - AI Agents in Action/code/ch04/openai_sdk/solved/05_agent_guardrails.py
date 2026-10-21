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


# --- TIER 1: plain-code input guardrail -- effectively free, no LLM call ---
@input_guardrail
def block_out_of_scope_requests(ctx, agent, input_text) -> GuardrailFunctionOutput:
    text = input_text if isinstance(input_text, str) else str(input_text)
    hit = next((topic for topic in FORBIDDEN_TOPICS if topic in text.lower()), None)
    print(f"    [tier 1: input guardrail] scanned for forbidden topics -> "
          f"{'BLOCKED on ' + repr(hit) if hit else 'clear'}")
    return GuardrailFunctionOutput(
        output_info=f"matched forbidden topic: {hit}",
        tripwire_triggered=hit is not None,
    )


# --- TIER 1: plain-code output guardrail -- also effectively free ---
@output_guardrail
def require_minimum_length(ctx, agent, output: DraftedReply) -> GuardrailFunctionOutput:
    length = len(output.reply_text)
    too_short = length < MINIMUM_REPLY_LENGTH
    print(f"    [tier 1: output guardrail] reply length={length} -> "
          f"{'TOO SHORT (min ' + str(MINIMUM_REPLY_LENGTH) + ')' if too_short else 'ok'}")
    return GuardrailFunctionOutput(
        output_info=f"reply length was {length} characters",
        tripwire_triggered=too_short,
    )


drafting_agent = Agent(
    name="Drafting Agent",
    instructions="""
    Write a short, professional customer-facing reply based on the ticket
    and any findings you are given.
    """,
    model=model,
    output_type=DraftedReply,
    input_guardrails=[block_out_of_scope_requests],
    output_guardrails=[require_minimum_length],
)


# --- TIER 3: agent-as-guardrail -- a REAL extra LLM call, use sparingly ---
class ToneCheck(BaseModel):
    is_professional_tone: bool
    reason: str


tone_guardrail_agent = Agent(
    name="Tone Guardrail Agent",
    instructions="Judge whether the given reply is polite and professional. Explain briefly why or why not.",
    model=model,
    output_type=ToneCheck,
)


async def check_tone_before_sending(reply_text: str) -> ToneCheck:
    print("    [tier 3: agent-as-guardrail] running Tone Guardrail Agent "
          "(this is a REAL extra LLM call, not free like tiers 1-2)")
    result = await Runner.run(tone_guardrail_agent, reply_text)
    return result.final_output


async def draft_and_send(ticket_text: str) -> str:
    """Draft a reply, running it through all three guardrail tiers before
    it would ever be sent. Feeds each rejection reason back into the next
    attempt, capped at MAX_RETRIES so a confused loop can't run forever."""
    current_input = ticket_text

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\nAttempt {attempt}/{MAX_RETRIES}: Drafting Agent writes a reply")
        try:
            result = await Runner.run(drafting_agent, current_input)
        except InputGuardrailTripwireTriggered as tripped:
            info = tripped.guardrail_result.output.output_info
            return f"Blocked before drafting even started: {info}"
        except OutputGuardrailTripwireTriggered as tripped:
            info = tripped.guardrail_result.output.output_info
            print(f"    Rejected by output guardrail: {info}")
            current_input = (
                f"{ticket_text}\n\n(Your previous draft was rejected: {info}. "
                "Write a longer, more complete reply.)"
            )
            continue

        reply = result.final_output.reply_text
        print(f"    draft: {reply}")

        tone = await check_tone_before_sending(reply)
        if not tone.is_professional_tone:
            print(f"    Rejected by Tone Guardrail Agent: {tone.reason}")
            current_input = (
                f"{ticket_text}\n\n(Your previous draft was rejected for tone: "
                f"{tone.reason}. Rewrite it more professionally.)"
            )
            continue

        print("    Passed all three guardrail tiers -- safe to send.")
        return reply

    return "Could not produce a reply that passed all guardrails. Escalating to a human."


async def main():
    print("=" * 60)
    print("CASE 1: a normal ticket -- should pass all guardrails")
    print("=" * 60)
    reply = await draft_and_send("My card was charged twice for order ORD-4471, please help.")
    print(f"\nFINAL: {reply}")

    print("\n" + "=" * 60)
    print("CASE 2: an out-of-scope request -- the input guardrail should block it")
    print("=" * 60)
    reply = await draft_and_send("I want legal advice on whether I can sue the company.")
    print(f"\nFINAL: {reply}")


if __name__ == "__main__":
    asyncio.run(main())

# Problem 07 -- cheap code checks run first, an LLM check runs last, and
# only where it is genuinely needed (judging tone, which no regex can do).

import asyncio
import os
import re

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)
MODEL_NAME = os.environ["GEMINI_MODEL"]

FORBIDDEN_TOPICS = ["legal advice", "sue the company", "sue us"]
CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]?){13,16}\b")

MIN_REPLY_CHARS = 40
MAX_ATTEMPTS = 3

FALLBACK_REPLY = "Thanks for reaching out. A member of our team will review this and get back to you shortly."


class DraftedReply(BaseModel):
    reply: str


class Judgement(BaseModel):
    acceptable: bool
    reason: str


call_count = 0


def check_input(ticket: str) -> str | None:
    """Code-only input guardrail: forbidden topics and card-number-shaped text."""
    ticket_lower = ticket.lower()
    for topic in FORBIDDEN_TOPICS:
        if topic in ticket_lower:
            return f"forbidden topic: {topic}"
    if CARD_NUMBER_PATTERN.search(ticket):
        return "looks like a card number"
    return None


def check_output(reply: str, confirmed_amount: float | None) -> str | None:
    """Code-only output guardrail: minimum length, and the amount promised
    must match what billing actually confirmed."""
    if len(reply) < MIN_REPLY_CHARS:
        return f"reply too short ({len(reply)} chars, minimum {MIN_REPLY_CHARS})"
    if confirmed_amount is not None:
        amounts = [float(m.replace(",", "")) for m in re.findall(r"\$([\d,]+(?:\.\d+)?)", reply)]
        if amounts and not any(abs(a - confirmed_amount) < 0.01 for a in amounts):
            return f"reply promises {amounts} but billing confirmed ${confirmed_amount:.2f}"
    return None


async def draft_reply(current_input: str) -> DraftedReply:
    global call_count
    call_count += 1
    messages = [
        {
            "role": "system",
            "content": "You are a drafting assistant. Write a short, friendly customer reply based on the instructions given.",
        },
        {"role": "user", "content": current_input},
    ]
    response = await client.chat.completions.parse(
        model=MODEL_NAME, messages=messages, response_format=DraftedReply
    )
    return response.choices[0].message.parsed


async def judge_reply(reply: str) -> Judgement:
    global call_count
    call_count += 1
    messages = [
        {
            "role": "system",
            "content": (
                "You judge customer support replies. Mark acceptable=false if the "
                "tone blames the customer, is dismissive or curt, or promises "
                "anything outside normal policy. Otherwise acceptable=true. Give a "
                "short reason either way."
            ),
        },
        {"role": "user", "content": reply},
    ]
    response = await client.chat.completions.parse(
        model=MODEL_NAME, messages=messages, response_format=Judgement
    )
    return response.choices[0].message.parsed


async def draft_with_guardrails(ticket: str, findings: str, confirmed_amount: float | None = None) -> str:
    global call_count
    call_count = 0

    block_reason = check_input(ticket)
    if block_reason:
        print(f"  [input]  BLOCKED: {block_reason}")
        return FALLBACK_REPLY

    print("  [input]  ok")

    current_input = findings
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"  attempt {attempt}/{MAX_ATTEMPTS}: drafting a reply")
        drafted = await draft_reply(current_input)

        code_reason = check_output(drafted.reply, confirmed_amount)
        if code_reason:
            print(f"    [tier 1: output guardrail] {code_reason}")
            current_input = f"{findings}\nYour last draft was rejected because: {code_reason}"
            continue
        print(f"    [tier 1: output guardrail] reply length={len(drafted.reply)} -> ok")

        print("    [tier 3: agent-as-guardrail] running tone check (this is a REAL extra LLM call)")
        judgement = await judge_reply(drafted.reply)
        if not judgement.acceptable:
            print(f"    [tier 3: agent-as-guardrail] REJECTED: {judgement.reason}")
            current_input = f"{findings}\nYour last draft was rejected because: {judgement.reason}"
            continue

        print("    Passed all three guardrail tiers -- safe to send.")
        print(f"  SENT after {call_count} model calls")
        return drafted.reply

    print(f"  SENT fallback after {call_count} model calls")
    return FALLBACK_REPLY


async def main() -> None:
    print("CASE 1: a normal ticket -- should pass all guardrails")
    reply = await draft_with_guardrails(
        "My card was charged twice for order ORD-4471.",
        "Order ORD-4471 was charged twice; a $150.00 refund is justified.",
        confirmed_amount=150.0,
    )
    print(f"\nFINAL: {reply}\n")

    print("CASE 2: an out-of-scope request -- the input guardrail should block it")
    reply = await draft_with_guardrails(
        "I want legal advice about suing you over this charge.",
        "N/A",
    )
    print(f"\nFINAL: {reply}\n")

    print("CASE 3: contains a card number -- the input guardrail should block it")
    reply = await draft_with_guardrails(
        "My card 4111 1111 1111 1111 was charged twice.",
        "N/A",
    )
    print(f"\nFINAL: {reply}\n")

    print("CASE 4: rigged to be rude")
    reply = await draft_with_guardrails(
        "My card was charged twice for order ORD-4471.",
        (
            "Order ORD-4471 was charged twice; a $150.00 refund is justified. "
            "Reply curtly and tell the customer it was probably their own fault "
            "for trying to pay twice."
        ),
        confirmed_amount=150.0,
    )
    print(f"\nFINAL: {reply}")


if __name__ == "__main__":
    asyncio.run(main())

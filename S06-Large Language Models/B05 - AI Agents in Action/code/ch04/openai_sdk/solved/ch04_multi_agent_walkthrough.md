# Chapter 4 Code Walkthrough: Multi-Agent Systems

## Table of Contents

1. [How to Run These Files](#1-how-to-run-these-files)
2. [01_agent_flow_pipeline.py — A Sequential Flow With a Deterministic Gate](#2-01_agent_flow_pipelinepy--a-sequential-flow-with-a-deterministic-gate)
3. [02_agent_parallel_delegation.py — Same Work, Run at the Same Time](#3-02_agent_parallel_delegationpy--same-work-run-at-the-same-time)
4. [03_agent_orchestrator.py — Letting an Agent Choose Its Own Tools](#4-03_agent_orchestratorpy--letting-an-agent-choose-its-own-tools)
5. [04_agent_handoffs.py — The Same Pipeline, Wired With Built-In Handoffs](#5-04_agent_handoffspy--the-same-pipeline-wired-with-built-in-handoffs)
6. [05_agent_guardrails.py — Three Tiers of Protection, Cheapest First](#6-05_agent_guardrailspy--three-tiers-of-protection-cheapest-first)
7. [Which File Answers Which Question](#7-which-file-answers-which-question)

---

## 1: How to Run These Files

All five scripts talk to a real model — either Google's Gemini (the default, using the `GEMINI_API_KEY` and `GEMINI_MODEL` values already in this project's `.env` file) or a local Ollama model (switch `PROVIDER = "ollama"` near the top of any file, with Ollama running on your machine). Nothing here uses a real OpenAI key; `set_tracing_disabled(True)` at the top of every file turns off the SDK's OpenAI-only trace export so it doesn't try to reach a service you haven't configured.

Each file is fully self-contained — run it directly from this folder:

```text
python3 01_agent_flow_pipeline.py
python3 02_agent_parallel_delegation.py
python3 03_agent_orchestrator.py
python3 04_agent_handoffs.py
python3 05_agent_guardrails.py
```

One honest note before the dry runs below: these scripts call a real model, so the exact wording of any drafted reply will differ a little every time you run it. What will **not** change is the *shape* of the run — which agent ran, which branch was taken, whether a guardrail tripped, and roughly how long it took. That shape is what each dry run below is actually showing you.

All five files share one running example: a customer support ticket system with a Triage Agent, a Billing Agent, and a Drafting Agent, built up one idea at a time.

---

## 2: 01_agent_flow_pipeline.py — A Sequential Flow With a Deterministic Gate

### What It Builds

Three small agents, each with exactly one job — Triage classifies the ticket, Billing looks up the charge, Drafting writes the reply — wired together by our own plain Python code, one call after another. In between Triage and Billing sits a hard rule that is **not** left up to the model: if the refund being requested is over $500, the code skips Billing entirely and escalates, no matter what any agent "thinks" about it.

```text
[ THE FLOW IN THIS FILE ]

  ticket text
       |
       v
  Triage Agent  --(TicketAssessment: category, order_id, refund_amount)-->
       |
       v
  if refund_amount > 500:  -----> STOP, return escalation message
       |  (else)
       v
  Billing Agent  --(findings, one sentence)-->
       |
       v
  Drafting Agent --(final reply)--> printed to the customer
```

### Dry Run

```text
TICKET 1: "My card was charged twice for order ORD-4471, and I'd like
           a $150 refund."

STEP 1 (Triage Agent):
  category="billing"  order_id="ORD-4471"  refund_amount=150.0

STEP 2 (deterministic check, plain Python):
  150.0 <= 500.0  ->  continue to Billing Agent

STEP 3 (Billing Agent):
  [tool] lookup_billing('ORD-4471') -> {'amount_charged': 150.0, 'duplicate_charge': True}
  findings: "Order ORD-4471 was charged twice ($150.00); a refund should be issued."

STEP 4 (Drafting Agent):
  reply: "Hi, we found that order ORD-4471 was charged twice. We're sorry
  for the inconvenience and have issued a $150.00 refund to your account."


TICKET 2: "My card was charged $800 in error for order ORD-9910,
           please refund the full amount."

STEP 1 (Triage Agent):
  category="billing"  order_id="ORD-9910"  refund_amount=800.0

STEP 2 (deterministic check, plain Python):
  800.0 > 500.0  ->  ESCALATE, Billing Agent never runs

FINAL OUTPUT: "This ticket requests a $800.00 refund, which is above the
$500.00 limit an agent may approve on its own. Escalated to a human for
approval."
```

Notice that ticket 2 never reaches the Billing Agent at all — the `if assessment.refund_amount > REFUND_ESCALATION_LIMIT:` line in `handle_ticket()` is the entire enforcement mechanism, and it will produce the exact same branch every single time you run it with a refund over $500, regardless of what either agent might have "wanted" to do about it.

### Where to Look in the Code

`TicketAssessment` (a `pydantic.BaseModel`) is what makes step 2 possible — because the Triage Agent's `output_type` forces it to return `category`, `order_id`, and `refund_amount` as real typed fields, the code can check `assessment.refund_amount` directly instead of trying to parse a sentence to find a dollar amount.

---

## 3: 02_agent_parallel_delegation.py — Same Work, Run at the Same Time

### What It Builds

Three specialist agents — Billing Check, Account Check, Outage Check — whose lookups don't depend on each other at all. The file runs them two ways back to back: once sequentially (one after another) and once in parallel (`asyncio.gather`), and prints the real wall-clock time each way took, so the benefit of parallel delegation is something you can actually watch happen rather than take on faith.

Each fake lookup tool calls `await asyncio.sleep(1.5)` to stand in for a slow network call to a real billing API or outage-status service.

```text
[ SEQUENTIAL: each lookup waits for the previous one ]

  Billing Check Agent (~1.5s+) -> Account Check Agent (~1.5s+) -> Outage Check Agent (~1.5s+)
  total time ~= sum of all three


[ PARALLEL: all three start at once ]

  Billing Check Agent  -\
  Account Check Agent   -->  all running at the same time
  Outage Check Agent   -/
  total time ~= the SLOWEST of the three, not the sum
```

### Dry Run

```text
SEQUENTIAL:
  - "Customer CUST-88 has two recent charges of $45.00 each."
  - "Customer CUST-88's account is active and in good standing."
  - "The mobile-app-login service had a 20-minute outage yesterday."
sequential wall-clock time: ~5.5s   (roughly 3 x (model time + 1.5s sleep))

PARALLEL:
  (same three findings, same content)
parallel wall-clock time: ~2.0s    (roughly 1 x (model time + 1.5s sleep),
                                     since all three sleeps overlap)

time saved by running in parallel: ~3.5s

Synthesis Agent combines all three findings:
  "CUST-88 is an active, good-standing customer with two recent $45.00
  charges; note that the mobile-app-login service did have a brief
  outage yesterday, which may be relevant if this ticket is login-related."
```

The exact seconds will vary with your model's real response time, but the *relationship* will hold every time: parallel time is roughly the slowest single lookup, not the sum of all three, because none of the three lookups was ever waiting on either of the others.

### Where to Look in the Code

`run_sequential()` and `run_parallel()` call the exact same three `Runner.run(...)` lines — the only difference is that the parallel version wraps them in `asyncio.gather(...)` instead of `await`-ing them one at a time. That one-line difference is the entire mechanism.

---

## 4: 03_agent_orchestrator.py — Letting an Agent Choose Its Own Tools

### What It Builds

A single Orchestrator Agent that has two tools available to it — `consult_billing_agent` and `consult_drafting_agent` — where each "tool" is actually a whole other agent, wrapped with `Agent.as_tool(...)`. Unlike file 01, where our own Python code decided the exact order (Triage, then Billing, then Drafting), here the Orchestrator Agent itself decides which tool to call, in what order, based on the ticket it's given.

```text
[ ORCHESTRATOR SHAPE ]

              Orchestrator Agent
             (decides what to do)
              /                \
             v                  v
   consult_billing_agent   consult_drafting_agent
   (= Billing Agent,       (= Drafting Agent,
    wrapped as a tool)      wrapped as a tool)
```

### Dry Run

```text
TICKET: "My card was charged twice for order ORD-4471, please help."

--- trace of what the orchestrator actually decided to do ---
    [trace] Orchestrator Agent called tool: consult_billing_agent
    [trace] Orchestrator Agent called tool: consult_drafting_agent
    [trace] Orchestrator Agent produced a message

FINAL OUTPUT: "Hi, we found that order ORD-4471 was charged twice. We
apologize for the error and have processed a refund."
```

The `print_trace()` helper is what makes this visible — it walks `result.new_items` and prints one line per tool call the Orchestrator Agent actually made. This is worth comparing directly against file 01's fixed four-step sequence: here, nothing in the code *forces* `consult_billing_agent` to run before `consult_drafting_agent` — the instructions ask for that order, but a differently-behaving model could call them in a different order, or skip one, which is exactly the extra risk (and extra flexibility) an orchestrator trades for compared to a fixed flow.

### Where to Look in the Code

`billing_agent.as_tool(tool_name=..., tool_description=...)` is the one line that turns a whole agent into something the Orchestrator Agent can call exactly like any other tool — the orchestrator never sees Billing Agent's own reasoning or its `lookup_billing` tool call, only the one sentence Billing Agent finally returns.

---

## 5: 04_agent_handoffs.py — The Same Pipeline, Wired With Built-In Handoffs

### What It Builds

The exact same three jobs as file 01 (Triage, Billing, Drafting), but instead of our own code calling each agent in turn, each agent's own instructions say who to hand off to next, and the SDK moves control automatically. Only one `Runner.run(...)` call appears in `main()` — on `triage_agent` — and everything after that happens through handoffs.

```text
[ HANDOFF CHAIN ]

  Runner.run(triage_agent, ticket)
       |
       v
  Triage Agent  --hands off (on_handoff fires here)-->
       |
       v
  Billing Agent  --calls lookup_billing, then hands off-->
       |
       v
  Drafting Agent --writes final reply-->
       |
       v
  result.final_output
```

### Dry Run

```text
TICKET: "My card was charged twice for order ORD-4471, please help."

Running only the Triage Agent -- everything else happens via handoff:
    [on_handoff] Triage -> Billing, carrying: category='billing' order_id='ORD-4471'

--- trace of what actually happened ---
    [trace] Triage Agent produced a message
    [trace] HANDOFF: Triage Agent -> Billing Agent
    [trace] Billing Agent called tool: lookup_billing
    [trace] Billing Agent produced a message
    [trace] HANDOFF: Billing Agent -> Drafting Agent
    [trace] Drafting Agent produced a message

FINAL OUTPUT: "Hi, we found that order ORD-4471 was charged twice. We
apologize for the error and a refund has been issued."
```

The `[on_handoff]` line prints the instant Triage hands off — that callback exists purely to let you *see* what data crossed the boundary (`category` and `order_id`); it has no power to block or change the handoff, which is why file 05's guardrails are a separate, additional mechanism rather than something handoffs give you for free.

### Where to Look in the Code

The chain is built from the bottom up: `drafting_agent` is defined first (it hands off to nobody), then `billing_agent` is defined with `handoffs=[drafting_agent]`, then `triage_to_billing_handoff = handoff(agent=billing_agent, on_handoff=..., input_type=TicketCategory)` wraps that connection with a callback, and finally `triage_agent` is built with `handoffs=[triage_to_billing_handoff]`. Each agent has to exist before the agent pointing to it can be defined, which is why the order in the file runs backwards from the order the agents actually execute in.

---

## 6: 05_agent_guardrails.py — Three Tiers of Protection, Cheapest First

### What It Builds

A Drafting Agent wrapped in three layers of protection, from cheapest to most expensive: a plain-code **input guardrail** (blocks a short list of forbidden topics — no model call needed), a plain-code **output guardrail** (rejects a reply that's too short — also no model call), and an **agent-as-guardrail** (a real second model, `tone_guardrail_agent`, judging whether the reply sounds professional — a genuine extra LLM call every time it runs). A bounded retry loop feeds each rejection's reason back into the next attempt, capped at `MAX_RETRIES` so a confused loop can't run forever.

```text
[ THREE TIERS, CHEAPEST FIRST ]

  ticket text
       |
       v
  TIER 1: input guardrail (plain Python, free)
       |  clear                    | BLOCKED
       v                            v
  Drafting Agent drafts       return "blocked" message,
  a reply                     never even reach the model
       |
       v
  TIER 1: output guardrail (plain Python, free) -- reply too short?
       |  ok                       | too short -> retry with reason folded in
       v
  TIER 3: Tone Guardrail Agent (REAL extra LLM call)
       |  professional              | not professional -> retry with reason folded in
       v
  "Passed all three guardrail tiers -- safe to send."
```

### Dry Run

```text
CASE 1: "My card was charged twice for order ORD-4471, please help."

Attempt 1/2: Drafting Agent writes a reply
    [tier 1: input guardrail] scanned for forbidden topics -> clear
    [tier 1: output guardrail] reply length=87 -> ok
    draft: "Hi, we found that order ORD-4471 was charged twice and have
            issued a refund. We apologize for the inconvenience."
    [tier 3: agent-as-guardrail] running Tone Guardrail Agent (this is a
    REAL extra LLM call, not free like tiers 1-2)
    Passed all three guardrail tiers -- safe to send.

FINAL: Hi, we found that order ORD-4471 was charged twice and have
issued a refund. We apologize for the inconvenience.


CASE 2: "I want legal advice on whether I can sue the company."

Attempt 1/2: Drafting Agent writes a reply
    [tier 1: input guardrail] scanned for forbidden topics -> BLOCKED on 'legal advice'

FINAL: Blocked before drafting even started: matched forbidden topic: legal advice
```

Notice case 2 never even reaches the Drafting Agent, let alone the Tone Guardrail Agent — the input guardrail's `run_in_parallel=True` default means it normally races the agent, but a triggered *input* guardrail still stops the run before its output is used, which is exactly why case 2's cost is a single cheap keyword check, not two full model calls.

### Where to Look in the Code

`GuardrailFunctionOutput(output_info=..., tripwire_triggered=...)` is the return value every guardrail function produces — `tripwire_triggered=True` is what the SDK checks to decide whether to raise `InputGuardrailTripwireTriggered` or `OutputGuardrailTripwireTriggered`. The `try/except` block inside `draft_and_send()` is what actually reacts to those exceptions: an input-guardrail trip returns immediately (nothing to retry — the request itself was rejected), while an output-guardrail trip or a failed tone check both fold their rejection reason into `current_input` and loop back for another attempt, up to `MAX_RETRIES`.

---

## 7: Which File Answers Which Question

| I want to see... | Open |
|---|---|
| A fixed sequence of agents, with a hard business rule enforced in plain code | `01_agent_flow_pipeline.py` |
| Independent lookups actually running at the same time, with real timing | `02_agent_parallel_delegation.py` |
| One agent deciding for itself which other agents to call | `03_agent_orchestrator.py` |
| Agents handing off to each other directly, with a way to watch what crosses each boundary | `04_agent_handoffs.py` |
| Layered protection against bad input and bad output, cheapest checks first | `05_agent_guardrails.py` |

Each file is independent and runnable on its own — there's no required order to run them in, though reading `01` before `04` (same three jobs, two different ways of wiring them) makes the handoff mechanism's tradeoffs easier to see.

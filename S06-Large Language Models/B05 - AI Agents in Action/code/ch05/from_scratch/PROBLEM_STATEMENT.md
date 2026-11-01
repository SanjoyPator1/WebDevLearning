# Chapter 5 From Scratch: Agent Reasoning and Planning

## Table of Contents

- [How This Folder Works](#how-this-folder-works)
- [Setup and Running](#setup-and-running)
- **Part 1: The Problems**
  - [Problem 01: Pieces First, Then Three Ways to Reason](#problem-01-pieces-first-then-three-ways-to-reason)
  - [Problem 02a (Companion): Best-of-N, Stripped to the Minimum](#problem-02a-companion-best-of-n-stripped-to-the-minimum)
  - [Problem 02: Best-of-N Sampling vs. Majority Vote](#problem-02-best-of-n-sampling-vs-majority-vote)
  - [Problem 03: A Genuine ReAct Loop](#problem-03-a-genuine-react-loop)
  - [Problem 04a (Companion): Plan-and-Execute, Stripped to the Minimum](#problem-04a-companion-plan-and-execute-stripped-to-the-minimum)
  - [Problem 04: Plan-and-Execute, With Replanning](#problem-04-plan-and-execute-with-replanning)
  - [Problem 05: Tree-of-Thought: Generate, Evaluate, Prune](#problem-05-tree-of-thought-generate-evaluate-prune)
  - [Problem 06: Reflexion With an Independent Verifier](#problem-06-reflexion-with-an-independent-verifier)
  - [Problem 07: Choosing a Strategy Without a Model Call](#problem-07-choosing-a-strategy-without-a-model-call)
  - [Problem 08: The Reasoning Scratchpad](#problem-08-the-reasoning-scratchpad)
  - [Problem 09: The Scratchpad as an MCP Server](#problem-09-the-scratchpad-as-an-mcp-server)
- **Part 2: The Theory**
  - [Theory 00: Decomposition and Planning Are Two Different Jobs](#theory-00-decomposition-and-planning-are-two-different-jobs)
  - [Theory 01: Single Pass, Chain-of-Thought, and Built-In Thinking](#theory-01-single-pass-chain-of-thought-and-built-in-thinking)
  - [Theory 02: Spending More Compute by Sampling](#theory-02-spending-more-compute-by-sampling)
  - [Theory 03: ReAct: Reason, Act, Observe](#theory-03-react-reason-act-observe)
  - [Theory 04: Plans That Survive Reality](#theory-04-plans-that-survive-reality)
  - [Theory 05: Searching Over Thoughts](#theory-05-searching-over-thoughts)
  - [Theory 06: Self-Critique That Actually Works](#theory-06-self-critique-that-actually-works)
  - [Theory 07: Picking the Right Strategy](#theory-07-picking-the-right-strategy)
  - [Theory 08: External Memory for Thinking](#theory-08-external-memory-for-thinking)
  - [Theory 09: A Scratchpad on a Server](#theory-09-a-scratchpad-on-a-server)
- [What Is Not Covered Here](#what-is-not-covered-here)

---

## How This Folder Works

A model on its own produces an answer in one go. This chapter is about the structures you build **around** the model so it can handle problems that need several steps: breaking the problem into pieces, showing its working, trying several answers, reacting to what tools return, making a plan and fixing it when reality disagrees, exploring branches, checking its own work against something real, and keeping notes it can come back to.

Every file uses a plain `AsyncOpenAI` client (Gemini by default, Ollama as a fallback) and code you write yourself. No agents framework. Each reasoning "pattern" turns out to be a small amount of ordinary code: a prompt, a loop, a scoring function, a list of notes.

One running scenario threads through the chapter: **booking a multi-leg conference trip under a fixed budget**. Flight legs come back sold out, over budget, or needing a choice of connecting city. Seeing the same kind of problem handled by nine different reasoning shapes makes the differences show up as differences in behavior, not just in description. Problem 01 also uses one short logic puzzle, chosen because models get it wrong often enough to make the comparison visible. Problem 09 uses a one-sentence apple story instead, because the scratchpad is the only new idea there and nothing else should compete with it.

The three folders mean the same as before:

```text
from_scratch/
|-- PROBLEM_STATEMENT.md     <-- this file
|-- template/                pristine stubs, never edit
|-- solutions/               YOUR working copy, write code here
|-- solved/                  reference answers, look only after trying
```

Each problem has a "Read first" link to its theory section in Part 2. Start with [Theory 00](#theory-00-decomposition-and-planning-are-two-different-jobs): it separates the two jobs every pattern in this chapter is built on.

---

## Setup and Running

Everything runs from the repo's root virtual environment (`mcp` 2.1.1, `openai`, `httpx`, `python-dotenv`, `pydantic`).

Models come from the same `.env` as earlier chapters:

```text
GEMINI_API_KEY=...            default provider
GEMINI_MODEL=gemini-3.5-flash-lite
```

Ollama (`qwen3:4b`) is the fallback, through its OpenAI-compatible endpoint at `http://localhost:11434/v1`.

Every problem except 07 makes real model calls, with one partial exception: Problem 09 makes none in steps 1 to 4 and about 6 to 10 in its last step, which you can switch off. Problems 02, 05, and 06 make several per run on purpose, since spending more calls is the technique being studied. On the Gemini free tier you may occasionally hit a rate limit; wait a minute and run again.

### Running

Problems 01 to 08 are one command each:

```text
python 03_react_loop_agent.py
```

Problem 09 has a server, so it needs two terminals, the same pattern as chapter 3 (its first four steps need no API key at all):

```text
Terminal 1:  python 09_scratchpad_server.py     (leave it running, port 8150)
Terminal 2:  python 09_scratchpad_agent.py
```

### Reading Token Counts, Including Hidden Thinking

Every response carries a `usage` object:

```python
response.usage.prompt_tokens        # tokens you sent
response.usage.completion_tokens    # tokens of visible answer
response.usage.total_tokens         # everything you are billed for
```

When a model uses its **built-in thinking** (Problem 01), the thinking itself is billed but not shown. Through Gemini's OpenAI-compatible endpoint, the thinking tokens are not counted in `completion_tokens`; they appear only in `total_tokens`. So the hidden thinking cost of one call is:

```python
hidden_thinking = response.usage.total_tokens - response.usage.prompt_tokens - response.usage.completion_tokens
```

Measured on the puzzle from Problem 01, averaged over 5 real runs each: a default call cost about 383 tokens in total with zero hidden thinking, the same call with `reasoning_effort="high"` cost about 1,537 tokens, of which about 1,444 was hidden thinking.

---

# Part 1: The Problems

## Problem 01: Pieces First, Then Three Ways to Reason

**File:** `01_decomposition_and_cot.py`
**Read first:** [Theory 00](#theory-00-decomposition-and-planning-are-two-different-jobs) and [Theory 01](#theory-01-single-pass-chain-of-thought-and-built-in-thinking)

### Goal

Two separate things. First, see **decomposition** on its own: listing the pieces of a goal without deciding their order. Second, compare the three ways of getting a model to reason before it answers: a plain single pass, a chain-of-thought prompt, and the model's own built-in thinking. Measure how often each one is right, and what each one costs.

### What You Build

**Part 1: decomposition.**

1. A `TripSubproblems` model (`subproblems: list[str]`) and a system prompt that tells the model to list the pieces of `"book my 3-city conference trip"` and explicitly **not** to decide order or dependencies.
2. Parse the response with structured output and print the pieces, with a note that no ordering was decided.

**Part 2: three ways to reason, on one trap.**

The puzzle (a classic one where the model has to keep track of whose point of view counts as "the past"):

> A traveler starts in the present and goes back 100 years, arriving 3 days before a 10-day historical event. After spending 6 days there, they jump forward 50 years and stay 20 days. Then they jump back to see the last day of the event. How many days did they spend in the past before seeing the end of the event? Answer with just a number.

3. **Ground truth in code, not from a model.** Describe the trip as a list of stops, each with a year offset from the present and the days spent there, for example `[(-100, 6), (-50, 20), (-100, 0)]`. Add up the days at every stop whose offset is below zero. That gives 26. Never use a model's answer as the reference.
4. **Three arms**, each asked the same puzzle 5 times:
   - **Plain:** the puzzle alone, default settings.
   - **Chain-of-thought prompt:** the puzzle plus a short numbered strategy in the prompt (set the present as year 0; list every stop with its year and days; decide which stops are in the past from the traveler's point of view; add those days; check the total), still default settings.
   - **Built-in thinking:** the puzzle alone, no strategy in the prompt, but with `reasoning_effort="high"` on the call.
5. For each arm, print: how many of the 5 answers matched the ground truth, the average `total_tokens`, the average hidden thinking tokens (see Setup), and the average time per call.

### Expected Output (shape, numbers will vary)

```text
PART 1: decomposition
  subproblems: ['Book flights', 'Book hotels', 'Arrange visas', 'Register for the conference']
  (no order decided: decomposition answers 'what are the pieces', not 'in what order')

PART 2: three ways to reason (ground truth from the timeline: 26)
  arm                   correct   avg total_tokens   avg hidden thinking   avg time
  plain                  0/5           383                    0              2.0s
  chain-of-thought       0/5           730                    0              4.7s
  built-in thinking      5/5         1,537                1,444              6.9s
```

Those are real numbers from an actual run, not a guess, and this puzzle turned out to be a sharp demonstration: a short "add the legs one at a time"-style prompt is not enough to rescue a model that genuinely cannot hold the perspective shift in its head, while built-in thinking got every single run right. Your own run may not split quite this cleanly. What should hold regardless: the chain-of-thought arm **shows** its working, so you can at least see where it went wrong; the built-in thinking arm spends far more tokens and time on reasoning you cannot read; and only a ground truth computed in code tells you which answers were right.

---

## Problem 02a (Companion): Best-of-N, Stripped to the Minimum

**File:** `02_a_best_of_n_simple.py`
**Read first:** [Theory 02](#theory-02-spending-more-compute-by-sampling) (same theory as Problem 02 -- no new concept here)

### Goal

The Best-of-N idea with every piece of incidental complexity removed, so the pattern itself is easy to see the first time through, before Problem 02 adds the realistic plumbing (a Pydantic model, JSON parsing, a multi-factor rubric, a travel-booking domain) around the exact same shape. No new concept here versus Problem 02 -- just one number in, one number out, and a one-line score.

### What You Build

The task: ask the model to **guess how many jellybeans are in a jar**, 5 independent times. Unlike a fact-recall question, a jellybean count is a genuine estimate -- every guess is naturally different, which is exactly the situation Best-of-N is for (compare: asking the same arithmetic question 5 times, where the answers *should* agree, is self-consistency's job instead).

1. `extract_guess(raw_text) -> int | None`: pull the first integer out of the model's reply (the same trick as Problem 01's `extract_answer_number`, reused on purpose).
2. `score_guess(guess, true_count) -> int`: the simplest possible deterministic scorer -- just `abs(guess - true_count)`. Lower is better here (0 is a perfect guess), the opposite direction from Problem 02's 0-10 rubric. Worth noticing on its own: "good" depends on what the number represents, not on a fixed "bigger wins" rule.
3. `sample_one_guess()`: one raw call asking for a single number, grounded in a fixed jar description.
4. `run_best_of_n_simple(n)`: fire `n` guesses **concurrently** with `asyncio.gather`, score each by distance from a true count decided by us ahead of time (never asked from the model, same rule as Problem 01's ground truth), and pick the **closest** with `min(scored, key=lambda pair: pair[1])`.

### Expected Output (shape, numbers will vary)

```text
BEST-OF-N, THE SIMPLEST POSSIBLE VERSION

Jar: A cylindrical glass jar, about 20cm tall and 10cm across, ...
(true count, known only to us, never told to the model: 310)

STEP 1: asking for 5 independent guesses, concurrently
    [sample] raw reply: '250' -> guess=250
    [sample] raw reply: '300' -> guess=300
    ...

STEP 2: scoring each guess against the true count (310)
    guess= 250   distance from truth=  60
    guess= 300   distance from truth=  10
    ...

STEP 3: picking the closest guess (smallest distance wins)
    BEST-OF-5: 300 (off by 10)

WHY THIS IS BEST-OF-N, NOT SELF-CONSISTENCY
    Every guess above is a genuinely different ESTIMATE -- there is no
    single fact to recall, so the samples are not expected to agree...
```

---

## Problem 02: Best-of-N Sampling vs. Majority Vote

**File:** `02_best_of_n_sampling.py`
**Read first:** [Theory 02](#theory-02-spending-more-compute-by-sampling)

### Goal

Spend more model calls to get a better answer, in two different ways. When candidates differ and need comparing on trade-offs, generate several at once and **score** them with a rule you trust. When candidates should all land on the same single answer, just **count votes**.

### What You Build

1. A `CandidateFlight` model and `sample_one_candidate(route, raw_search_result)`: one call per candidate, each given a **different** entry from a fixed pool of four search results (passed in the prompt), asked to restate it faithfully as JSON.
2. `score_candidate(candidate, budget) -> float`: a **deterministic** 0 to 10 rubric. Over budget scores exactly `0.0` (an automatic reject, decided before anything else). Otherwise, a weighted sum of fewer stops, a comfortable connection, and money left under the budget.
3. `run_best_of_n(route, budget, n)`: run the `n` candidate calls **at the same time** with `asyncio.gather`, score each, print every score (with `AUTO-REJECT` where it applies), and pick the highest.
4. `self_consistency_vote(answers) -> str`: majority voting with `collections.Counter`, no rubric.

### Expected Output (shape)

```text
candidate A: price=$420.00 stops=1 risk='comfortable, 1h40m layover' -> score=7.xx
candidate B: price=$455.00 stops=0 risk='n/a'                        -> score=0.0 (AUTO-REJECT: over budget)
candidate C: price=$410.00 stops=2 risk='tight, 35-minute connection' -> score=4.xx
candidate D: price=$440.00 stops=1 risk='comfortable, 1h10m layover' -> score=7.xx

WINNER: candidate A or D, whichever scores higher

SELF-CONSISTENCY: ['$620', '$620', '$635', '$620'] -> '$620' (3 of 4 votes)
```

Candidate B must score exactly `0.0` however good its other numbers look: the budget check runs before any weighted scoring.

---

## Problem 03: A Genuine ReAct Loop

**File:** `03_react_loop_agent.py`
**Read first:** [Theory 03](#theory-03-react-reason-act-observe)

### Goal

Build a loop that genuinely **reacts** to something it could not have predicted: the second leg's direct flight is sold out, and the loop only succeeds if it reads that result and changes its next action.

### What You Build

1. Two tools. `search_flights(route, max_price, connecting=False)` looks up a fixed inventory keyed by `(route, connecting)`: the route `city-b-to-city-c` is sold out when `connecting=False` and has a bookable `BC-CONN-7` at $410 when `connecting=True`. `book_flight(flight_id, price)` records the booking in a module-level `_world` dict and returns the running total.
2. `run_tool_loop(...)`: call the model, run every tool call by name, append the results, repeat until the model stops calling tools or the step budget runs out.
3. A system prompt that tells the model to reason, act, and observe at each step, and what to do when a search comes back sold out (search again with `connecting=True`) or over budget (raise `max_price`, if the running total allows).
4. A **ground truth check** at the end that reads `_world` directly, never the model's own description of what it booked.

### Expected Output (shape)

```text
  tool call: search_flights({'route': 'city-b-to-city-c', 'max_price': ..., 'connecting': False})
  tool result: {'status': 'sold_out'}
  tool call: search_flights({'route': 'city-b-to-city-c', 'max_price': ..., 'connecting': True})
  tool result: {'status': 'available', 'flight_id': 'BC-CONN-7', 'price': 410.0, 'seats_left': 3}
  tool call: book_flight({'flight_id': 'BC-CONN-7', 'price': 410.0})

GROUND TRUTH (read from the world, not from the model's text)
    booked: AB-101 at $620.00
    booked: BC-CONN-7 at $410.00
    booked: CD-909 at $260.00
    TOTAL SPENT: $1290.00 (budget: $1500.00) -- within budget by $210.00
```

If the loop ever books `BC-DIRECT-1`, or never searches again with `connecting=True` after the sold-out result, that is the bug this file exists to catch.

---

## Problem 04a (Companion): Plan-and-Execute, Stripped to the Minimum

**File:** `04_a_plan_and_execute_simple.py`
**Read first:** [Theory 04](#theory-04-plans-that-survive-reality) (same theory as Problem 04 -- no new concept here)

### Goal

The plan-and-execute-with-replanning idea with every piece of incidental complexity removed. No dual budgets, no flight-leg jargon, and no index-bookkeeping across a replan, so the pattern itself (plan, execute, check with plain code, replan on a mismatch) is easy to see before Problem 04 adds realistic plumbing around the same shape.

### What You Build

The task: plan a 3-item grocery trip (milk, eggs, bread) under a single $20 budget. Eggs come back at a real price far above what the planner expected (a price spike); the mismatch is caught by plain code, never a model opinion, and triggers calling the **same** planner again for just the remaining items.

1. `PlanStep` (`item`, `expected_price`) and `ShoppingPlan` (`steps: list[PlanStep]`).
2. `execute_step(step) -> dict`: looks up a fixed `_actual_prices` dict **by item name** -- not by list position. This is the one simplification worth really noticing: after a replan rebuilds the step list, a revised "bread" step is still just `"bread"` wherever it lands, so nothing needs to track "which original position was this" the way Problem 04 does.
3. `call_planner(user_prompt) -> ShoppingPlan`: one structured call, used identically for the first plan and every replan.
4. `run_shopping_trip()`: get the plan, execute steps one at a time with a `while` loop, compare actual vs. expected price with `abs(actual - expected) < 0.01`. On a mismatch, build a replan prompt containing the new fact, the remaining item names, and the budget left, call `call_planner` again, and splice the revised steps in -- `current_steps[: i + 1] + revised_plan.steps`, no index remapping required.

### Expected Output (shape, numbers will vary)

```text
STEP 1: Planner call produces the original plan
    step 1: milk -- expected $4.00
    step 2: eggs -- expected $4.00
    step 3: bread -- expected $4.00
    planned total: $12.00 (budget: $20.00, headroom: $8.00)

STEP 2: Executing steps one at a time, checking each against the plan
  -- step 1/3 --
    [executor] bought 'milk' -> expected $4.00, actual $4.00
    [check] actual $4.00 == expected $4.00 -> MATCH, advancing

  -- step 2/3 --
    [executor] bought 'eggs' -> expected $4.00, actual $9.00
    [check] actual $9.00 != expected $4.00 -> MISMATCH (+$5.00). Do NOT blindly continue the original plan.

STEP 3: Replanning -- 1 item(s) remain, $7.00 of budget left
    revised step 1: bread -- expected $X.XX

STEP 4: Final tally
    total actually spent: $XX.XX
    budget:               $20.00
    WITHIN BUDGET by $X.XX
```

The failure to watch for, same as Problem 04: if the mismatch check is skipped, or the replan prompt doesn't actually state the new price/remaining items/remaining budget, the loop quietly keeps going as if eggs cost $4.

---

## Problem 04: Plan-and-Execute, With Replanning

**File:** `04_plan_and_execute.py`
**Read first:** [Theory 04](#theory-04-plans-that-survive-reality)

### Goal

Make a plan up front, carry it out step by step, and fix it when reality disagrees, with the decision to replan made by code, never by the model's opinion of its own plan.

### What You Build

1. `PlanStep` (`step_description`, `expected_cost`) and `TripPlan` (`steps: list[PlanStep]`) models, and `call_planner(user_prompt) -> TripPlan`: one structured call, used the same way for the first plan and for every replan.
2. `execute_step(step_index, step) -> dict`: looks up a fixed `_actual_outcomes` dict for what "really happened". Leg 2 always comes back at $410 instead of the planned $210.
3. `run_trip_booking()`: get the plan, then carry out steps one at a time. After each step, compare the actual cost to the expected cost in plain Python (`abs(actual - expected) < 0.01`). On a mismatch, build a replan prompt containing the new fact, the steps still left, and the budget still left, call `call_planner` again, and replace the rest of the schedule with the revised steps.

### Expected Output (shape)

```text
STEP 1: the planner produces the original plan
    step 1: ... expected $180.00
    step 2: ... expected $210.00
    step 3: ... expected $260.00
    planned total: $650.00 (flight budget: $700.00, headroom: $50.00)

STEP 2: carrying out the steps, checking each against the plan
  -- step 1/3 -- actual $180.00 == expected $180.00 -> MATCH
  -- step 2/3 -- actual $410.00 != expected $210.00 -> MISMATCH (+$200.00), do not continue the old plan

STEP 3: replanning -- 1 step left, $110.00 of flight budget left
    revised step 1: ... expected $XXX.XX

STEP 4: final tally
    total actually spent on flights: $XXX.XX
```

The failure to watch for while building: if the mismatch check is skipped, or the replan prompt does not actually contain the new fact, the loop quietly keeps executing a plan that is already known to be wrong.

---

## Problem 05: Tree-of-Thought: Generate, Evaluate, Prune

**File:** `05_tree_of_thought.py`
**Read first:** [Theory 05](#theory-05-searching-over-thoughts)

### Goal

Explore several possible routes instead of committing to the first one, keep only the promising ones, and develop only the winner. The scoring step costs **zero** model calls: model calls are spent only on generating ideas.

### What You Build

1. A `RouteBranch` model (`hub_city`, `fare_usd`, `layover_minutes`, `visa_transit_needed`, `reasoning`) and `generate_route_branch(hub_city) -> RouteBranch`: one call per candidate connecting city, proposing a realistic itinerary through it.
2. `score_branch(branch) -> float`: a deterministic 0 to 10 score in plain Python. Cost points (up to 4) slide from full at a $1,800 fare to zero at $2,150. Layover points (up to 4) slide from zero at 30 minutes to full at 120 minutes. Visa points are 2 if no transit visa is needed, else 0.
3. The search in `main()`: **generate** one branch per city (`Doha`, `Frankfurt`), **evaluate** each with `score_branch`, **prune** anything below `PRUNE_THRESHOLD = 6.0`, then **expand** only the survivor with one more call.
4. A cost summary: real model calls made (generation plus expansion), compared with a one-call answer that never branched.

### Expected Output (shape)

```text
STEP 1: GENERATE -- one call per candidate city
    Doha:      $1900, 90 min layover, visa_transit_needed=True
    Frankfurt: $1750, 130 min layover, visa_transit_needed=False

STEP 2: EVALUATE -- plain Python, no model calls
    Doha:      cost=2.86/4 layover=2.67/4 visa=0.00/2 -> total=5.52/10
    Frankfurt: cost=4.00/4 layover=4.00/4 visa=2.00/2 -> total=10.00/10

STEP 3: PRUNE (threshold 6.0)
    Doha -> PRUNE      Frankfurt -> KEEP

STEP 4: EXPAND -- only Frankfurt
    next step: ...

COST: 2 generation calls + 1 expansion call = 3 model calls (evaluation was free)
```

The model proposes its own numbers, so yours will differ. The shape should hold: a transit visa costs a branch a full 2 points no matter how good its other numbers are.

---

## Problem 06: Reflexion With an Independent Verifier

**File:** `06_reflexion_with_verifier.py`
**Read first:** [Theory 06](#theory-06-self-critique-that-actually-works)

### Goal

Let the model try, check the attempt against something real, and try again with specific feedback. The check is done by code that recomputes the answer itself, never by asking the model whether its own answer looks right.

### What You Build

1. A `SolverOutput` model (`leg_prices: list[float]`, `reasoning: str`). It deliberately has **no** total field, so there is no self-reported number for anything to trust.
2. `verify_itinerary_total(leg_prices, budget) -> dict`: plain Python that recomputes `sum(leg_prices)` and returns whether it passes, by how much it is over, and which leg is the most expensive.
3. `build_solver_prompt(feedback) -> str`: the base instructions on the first attempt; on every retry, the previous feedback appended as a `HINT:` block. This one function is all that "feeding feedback forward" needs.
4. `book_itinerary_with_reflexion()`: up to `MAX_ATTEMPTS = 4` times, propose, verify, and on failure build feedback that names the overage and the most expensive leg, then try again.

The fare data: a $1,800 budget; Leg A has one option ($650), Leg B has a $590 nonstop and a $460 one-stop, Leg C has one option ($610).

### Expected Output (shape)

```text
Attempt 1/4
    leg_prices=[650.0, 590.0, 610.0]
    [verifier] recomputed_total=$1850.00 budget=$1800.00 passes=False
    feedback: Total is $1850.00, which is $50.00 over the $1800 budget. Leg A at $650 is the most expensive...

Attempt 2/4
    leg_prices=[650.0, 460.0, 610.0]
    [verifier] recomputed_total=$1720.00 budget=$1800.00 passes=True
    PASSED

FINAL ACCEPTED ITINERARY: [650.0, 460.0, 610.0] (total $1720.00)
```

Notice the feedback points at Leg A (the most expensive), yet the fix happens on Leg B (the only leg with a cheaper option). The verifier is honest about what it can know from the numbers; it does not have to know the answer to be useful.

---

## Problem 07: Choosing a Strategy Without a Model Call

**File:** `07_strategy_selector.py`
**Read first:** [Theory 07](#theory-07-picking-the-right-strategy)

### Goal

Decide which reasoning strategy a piece of work needs, using a few plain questions about the task. This file makes **zero** model calls on purpose: picking a strategy is a cheap, mechanical decision.

### What You Build

1. A `Subtask` model with five yes/no properties: `needs_outside_information`, `has_multiple_viable_paths`, `result_is_checkable_after_the_fact`, `steps_known_upfront` (default `False`), and `only_needs_a_single_tool_call` (default `False`).
2. `choose_reasoning_strategy(subtask) -> str`: a plain `if`-chain, in this order:
   1. Needs outside information and only one tool call, with no decision after it: `"single action, no loop needed"`.
   2. No outside information and no real fork: `"Reflexion + verifier"` if the result can be checked afterwards, else `"chain-of-thought"`.
   3. Needs outside information and the steps are known up front: `"plan-and-execute"`.
   4. Needs outside information otherwise: `"ReAct"`.
   5. A genuine fork between workable options: `"tree-of-thought"`.
3. `explain_strategy_choice(strategy) -> str`: one line of reasoning per strategy, printed next to every decision.
4. Run seven subtasks that cover all six outcomes, including two tricky ones.

### Expected Output (shape)

```text
Sum the three known leg costs against the budget                       -> chain-of-thought
Check whether the City 2 hotel has a room, and react to the answer     -> ReAct
Book all three legs in order, knowing fares may move                   -> plan-and-execute
Choose a connecting city: Doha or Frankfurt                            -> tree-of-thought
Re-check the finished itinerary's total against the $1,800 budget      -> Reflexion + verifier
One-shot check: is the City 1 hotel free on the conference dates?      -> single action, no loop needed
Pick among three 'candidate' hotels, when only one is in the right city -> chain-of-thought
```

The last one is the one to think about: it sounds like a branching choice, but once filtering leaves only one real option, there is no fork left to explore.

---

## Problem 08: The Reasoning Scratchpad

**File:** `08_reasoning_scratchpad.py`
**Read first:** [Theory 08](#theory-08-external-memory-for-thinking)

### Goal

Give the model a place to write its thinking down, outside itself. The scratchpad does no thinking of its own; it stores notes, lets a later note **revise** an earlier one without erasing it, and lets thinking **branch** into named alternatives.

### What You Build

1. A `ThoughtEntry` dataclass (`sequence_number`, `thought_text`, `revises: int | None`, `branch_id: str | None`) and a `ReasoningScratchpad` class with `add_thought(...)` and `all_entries()`. Storage only, no reasoning logic.
2. Two tools for the model, `store_thought(thought_text, revises=0, branch_id="")` and `read_all_thoughts()`, both working on one shared module-level scratchpad.
3. Seed thoughts 1 to 3 **in plain Python**, with no model call, because they are facts already known: the trip's pieces, leg 1's price, and leg 2's over-budget direct fare.
4. Hand over to a tool loop whose system prompt asks the model to: store a thought that revises thought 3, store two thoughts on two different branches proposing different connecting cities, compare them, then finish with a `RoutingDecision` JSON (`kept_branch_id`, `reasoning`).
5. `print_scratchpad(...)`: the main line down the left, the revision indented under what it revises, each branch grouped and indented, the kept branch marked.

### Expected Output (shape)

```text
 thought 1: Decompose the trip into flights, hotel, and visa paperwork.
 thought 2: Book leg 1 (home -> City 1): $410, within budget.
 thought 3: Attempt leg 2 (City 1 -> City 2) direct: $610 -- OVER BUDGET.
      thought 4: [revises thought 3] The direct route is too expensive; trying a connecting route.
      +---- branch 'via-hub-x'  <-- KEPT
            thought 5: Connecting through hub X: $340.
      +---- branch 'via-hub-y'
            thought 6: Connecting through hub Y: $365.
```

Check two things: that `kept_branch_id` in the final JSON matches the branch marked `<-- KEPT`, and that thought 4 shows up as a revision of thought 3, not as a third branch.

---

## Problem 09: The Scratchpad as an MCP Server

**Files:** `09_scratchpad_server.py` + `09_scratchpad_agent.py`
**Read first:** [Theory 09](#theory-09-a-scratchpad-on-a-server)

### Goal

Move the Problem 08 scratchpad out of your script and onto a real MCP server, then use it three ways: by calling it yourself from code, by watching it refuse bad input, and by letting a real model write to it. One tiny story runs through all of it: **Sam has 12 apples, gives 5 to Ana, then buys a bag of 8.** Nothing else is new here: no flights, no budgets, no booking loop.

### What You Build

**The server** (`09_scratchpad_server.py`), named `"Reasoning Scratchpad"`, stateless Streamable HTTP on port **8150**:

1. Module-level storage: one list holding every thought, in the order it arrived.
2. Tool `record_thought(thought, thought_number, total_thoughts, next_thought_needed, is_revision=False, revises_thought=None, branch_from_thought=None, branch_id=None) -> ThoughtReceipt`. It stores the thought and returns a short receipt: the thought number, how many thoughts are stored now, the branch names seen so far, and `next_thought_needed`. If `revises_thought` or `branch_from_thought` points at a thought number that is not stored, raise `ToolError` with a message the model can act on, and store nothing.
3. Tool `get_thoughts() -> ThoughtLog`: every stored thought, in order.
4. Pydantic return types for both, so `structured_content` comes back clean. (`clear_thoughts` is given to you: it empties the list so each run starts on a blank page.)

**The agent** (`09_scratchpad_agent.py`) has five steps. Steps 1 to 4 are plain code, **no model call**:

1. **Store and read.** Record three thoughts (`12 apples`, `12 - 5 = 7`, `7 + 8 = 15`), then read them back.
2. **Revise.** A correction arrives: Ana really took 6, not 5. Record thought 4 as a revision of thought 2, and thought 5 as a revision of thought 3. Print the notebook: thoughts 2 and 3 must still be there.
3. **Branch.** Record two thoughts that both start from thought 1, on branches `add-first` and `subtract-first`. Watch `branches_seen` grow in the receipts.
4. **Reject.** Try to record a revision of thought 99. Print the `ERROR:` text, and check that the stored count did not change.

Step 5 hands the same server to a real model:

5. **A model writes to it.** Your code clears the notebook, then gives the model **only** `record_thought` (turned into an OpenAI-format schema from the server's own tool list). Turn 1: the original story. Turn 2: **your code** adds the correction ("Ana actually took 6") to the same conversation, so a real revision has to happen. Afterwards your code reads the record with `get_thoughts` and checks two things in plain Python: the last number in the model's answer equals 14 (computed from the constants), and at least one stored thought is a revision.

Helpers you write on the way: `call_tool_as_text` (flatten an MCP result into the string a model would see, `ERROR: ...` on failure), `record` (store one thought and print the receipt), `fetch_thoughts`, `print_thought_record`, `scratchpad_schemas_for_model`, and `run_tool_loop` (the Problem 03 loop, with one tool that lives on the server).

### How to Run

```text
Terminal 1:  python 09_scratchpad_server.py
Terminal 2:  python 09_scratchpad_agent.py
```

Step 5 makes roughly 6 to 10 model calls, which fits under the Gemini free tier's 15 requests per minute. If you still hit the limit, the loop waits 40 seconds and retries. To run steps 1 to 4 only (no API key, no model calls), set `RUN_MODEL_STEP = False` at the top of the agent file.

### Expected Output (shape)

Steps 1 to 4 print the same thing on every run, since no model is involved:

```text
STEP 2: a correction arrives -- revise, do not overwrite
  #4: Correction: Ana took 6, not 5, so thought 2 is wrong: 12 - 6 = 6.
  #5: That also changes thought 3: 6 + 8 = 14.

  the record now (thoughts 2 and 3 are still there):
  #1 Sam starts with 12 apples.
  #2 Sam gives 5 apples to Ana: 12 - 5 = 7.
  #3 Sam buys a bag of 8: 7 + 8 = 15.
      #4 [revises #2] Correction: Ana took 6, not 5, so thought 2 is wrong: 12 - 6 = 6.
      #5 [revises #3] That also changes thought 3: 6 + 8 = 14.

STEP 3: two ways to work it out, branching from thought 1
  #6 receipt: {... "branches_seen": ["add-first"], ...}
  #7 receipt: {... "branches_seen": ["add-first", "subtract-first"], ...}

STEP 4: the server refuses a reference to a thought that does not exist
  thoughts stored before: 7
  receipt: ERROR: Error executing tool record_thought: revises_thought=99 does not exist yet on the scratchpad
  thoughts stored after: 7  (unchanged: rejected before anything was stored)
```

Step 5 depends on the model's wording, so only the shape is fixed:

```text
STEP 5: a real model reasons on the scratchpad
  tools the model sees: ['record_thought']

  --- turn 1: the original story ---
  tool call: record_thought({'thought': 'Sam starts with 12, gives 5 away: 12 - 5 = 7', 'thought_number': 1, ...})
  ...
  model's answer: Sam has 15 apples.

  --- turn 2: your code injects a correction ---
  tool call: record_thought({..., 'is_revision': True, 'revises_thought': 2})
  model's answer: Sam now has 14 apples.

  GROUND TRUTH (checked in code, not by asking the model)
    expected answer after the correction: 14
    model's final number:                 14  -> CORRECT
    a revision was recorded:              True
```

Check two things: the model never sees or sends anything but `record_thought`'s own fields, and the revision in step 5 points at a thought that really exists. If the model answers 15 on turn 2, or never marks a revision, the ground-truth lines say so; that is a finding about the prompt or the model, not a bug in the server.

**Stretch 1: two clients, one notebook.** Run the agent in two terminals at the same time. Both write into the same list, and their thoughts mix. Fix it with a `session_id`: the server keeps one list per id, and a small toolbox on the agent side removes `session_id` from the schema the model sees and adds it to every call itself. See [Theory 09](#theory-09-a-scratchpad-on-a-server), "One Notebook, Many Clients".

**Stretch 2: scratchpad against built-in thinking.** Reuse the sold-out-leg booking task from Problem 03. Run it once with the scratchpad tools and once with no scratchpad and `reasoning_effort="high"` on every call, add up the hidden thinking tokens (see Setup), and compare model calls, total tokens, and whether a readable record exists afterwards. Theory 09 has one measured run to compare against.

**Stretch 3: the published server.** Swap your server for the reference server, `@modelcontextprotocol/server-sequential-thinking`, run over STDIO with `npx`. Call `list_tools()` first: its single tool uses its own argument names, and it has **no** `session_id` at all. Work out why it does not need one (hint: who else can talk to a STDIO server process?).

---

# Part 2: The Theory

## Theory 00: Decomposition and Planning Are Two Different Jobs

### The Two Jobs

Reasoning through a multi-step problem means doing two different jobs:

- **Decomposition:** working out the pieces. *What are the parts of this task?*
- **Planning:** working out the order and the approach. *Which piece first, what depends on what, which tool for each?*

A picture: packing for a trip. Decomposition is the checklist (clothes, passport, charger, tickets). Planning is the order you do it in (find the passport first, because without it nothing else matters; charge the phone overnight; print tickets last, after the gate is announced).

### They Fail Separately

```text
                       good planning             bad planning
                  +------------------------+------------------------+
 good             | works                  | right pieces, wrong    |
 decomposition    |                        | order: books the hotel |
                  |                        | before the flight date |
                  |                        | is known               |
                  +------------------------+------------------------+
 bad              | perfect order over a   | nothing works          |
 decomposition    | list that forgot the   |                        |
                  | visa                   |                        |
                  +------------------------+------------------------+
```

This matters for debugging. A missing piece and a wrong order look similar from the outside (the trip falls apart), but the fix is different: a better decomposition prompt fixes the first, a replanning check (Problem 04) fixes the second.

### Why Models Need This Spelled Out

People handle routine tasks with habits and a rich picture of how the world works. A model has neither: it has no memory between calls and no built-in picture of your task. Every pattern in this chapter is a way to make these two jobs explicit, so they happen on purpose instead of by luck.

---

## Theory 01: Single Pass, Chain-of-Thought, and Built-In Thinking

### Three Ways a Model Can Get to an Answer

```text
 SINGLE PASS              CHAIN-OF-THOUGHT PROMPT      BUILT-IN THINKING
 question -> answer       question + "show your        question -> [hidden thinking] -> answer
                          steps" -> steps -> answer
 cheapest, fastest        steps are visible            model reasons before answering,
 shallow on multi-step    you can see where it         often more reliable on hard problems,
 problems                 went wrong                   costs many more tokens and seconds,
                                                       and you usually cannot read it
```

- A **single pass** writes the answer straight away. On a problem with several steps, it can jump to an answer that sounds right but skipped a step.
- **Chain-of-thought (CoT)** asks the model, in the prompt, to write out its intermediate steps before the answer. It does not give the model a new ability; it stops it from skipping steps, and it makes the working visible. CoT tends to help strong models more than it rescues weak ones.
- **Built-in thinking** (often called a reasoning or thinking mode) is a setting on the request. The model was trained to spend tokens reasoning before it answers. Through the OpenAI-compatible API this is `reasoning_effort` (`"minimal"`, `"low"`, `"medium"`, `"high"` on Gemini 3.x; `gemini-3.5-flash-lite` defaults to minimal).

### What Built-In Thinking Costs: A Real Measurement

Problem 01's own run, 5 calls per arm, against the puzzle whose ground truth is 26 days:

```text
 arm                   correct   avg total_tokens   avg hidden thinking   avg time
 plain                   0/5           383                    0              2.0s
 chain-of-thought        0/5           730                    0              4.7s
 built-in thinking       5/5         1,537                1,444              6.9s
```

Hidden thinking = total_tokens - prompt_tokens - completion_tokens. Neither the plain arm nor the chain-of-thought prompt got this particular puzzle right even once in 5 tries, which is a sharper result than "sometimes helps" -- a short written-out strategy was not enough to rescue this model from a problem that needs a genuine perspective shift. Built-in thinking got every run right, for about 4 times the tokens of the plain arm and 3 to 4 times the time. That is the trade: more reliability on a hard problem, paid for in tokens and time you cannot inspect.

### Provider Differences Worth Knowing

- Gemini through this endpoint bills the thinking but does not return its text or count it in `completion_tokens`.
- Ollama's `qwen3` models think by default, unless you turn it off (chapter 2's gotcha: thinking can use up your `max_tokens` before any answer appears).
- Model choice still matters most. A pattern or a setting is one lever among several, not a fix for a weak model.

### Why Ground Truth Must Come From Code

Every answer above was checked against a number computed by plain Python from a description of the trip. If you let a model grade the puzzle, you are asking the same kind of system that might get it wrong to decide whether it got it wrong.

---

## Theory 02: Spending More Compute by Sampling

### The Idea

Instead of asking once, ask several times and combine the answers. This is one way of spending more compute at answer time ("test-time compute"), with no change to the model.

### Two Ways to Combine

| | Best-of-N with a scorer | Majority vote (self-consistency) |
|---|---|---|
| Answers are | different options with trade-offs | expected to be the same single answer |
| Combine by | scoring each, keeping the best | counting, keeping the most common |
| Needs | a scoring rule you trust | nothing extra |
| Fails when | the scorer is wrong | most samples share the same mistake |

### A Dry Run: Why a Good Scorer Helps So Much

Say each sample is right 60% of the time, independently.

```text
 majority of 3: right if at least 2 of 3 are right
   = 0.6^3 + 3 x 0.6^2 x 0.4
   = 0.216 + 0.432 = 0.648

 majority of 5: right if at least 3 of 5 are right
   = 10 x 0.6^3 x 0.4^2 + 5 x 0.6^4 x 0.4 + 0.6^5
   = 0.3456 + 0.2592 + 0.0778 = 0.683

 best-of-3 with a perfect scorer: right if ANY of the 3 is right
   = 1 - 0.4^3 = 1 - 0.064 = 0.936
```

Two more votes barely move majority voting (0.648 to 0.683), while a reliable scorer turns the same 3 samples into 93.6%. Research on test-time compute finds the same pattern: with a good verifier, best-of-N needs far fewer samples than voting. The catch is the word "good": a scorer that is wrong picks wrong answers with confidence. That is why Problem 02's scorer is plain code with a hard budget rule, not another model asked for its opinion.

### Practical Points

- Run the samples at the same time (`asyncio.gather`); the total time is close to one call, though the token cost is N calls.
- Returns shrink: going from 1 to 3 samples helps a lot, from 10 to 20 helps little.
- Same model, same prompt, same blind spots: if every sample tends to make the same mistake, more samples do not fix it.

---

## Theory 03: ReAct: Reason, Act, Observe

### The Loop

**ReAct** interleaves thinking with doing. At each step the model reasons about what to do, calls a tool, looks at the result, and reasons again with that new information.

```text
           +----------------------------------------------+
           v                                              |
 goal --> [REASON: what next?] --> [ACT: call a tool] --> [OBSERVE: read the result]
                 |
                 +--> nothing left to do --> final answer
```

The loop itself lives in **your code** (call the model, run the tool, send the result back, call again), not inside the model.

### The Loop Is the Point, Not the Tool Call

One reasoning pass with a tool call somewhere in it is still one pass: if the tool returns something surprising, nothing changes. ReAct is different because each result feeds the next decision. That is what lets it recover from a sold-out flight.

### Reactive, Not Planned

ReAct decides one step at a time based on the latest result. It does not write a global plan first. That makes it flexible, but it can wander on long tasks, which is what plan-and-execute (Theory 04) addresses.

### Dry Run: The Sold-Out Leg

```text
 step 1  reason: leg 1 first           act: search AB direct     observe: AB-101, $620
 step 2  reason: within budget, book   act: book AB-101          observe: total $620
 step 3  reason: now leg 2             act: search BC direct     observe: SOLD OUT
 step 4  reason: try connections       act: search BC connecting observe: BC-CONN-7, $410
 step 5  reason: $1030 < $1500, book   act: book BC-CONN-7       observe: total $1030
 step 6  reason: leg 3                 act: search CD direct     observe: CD-909, $260
 step 7  reason: $1290 < $1500, book   act: book CD-909          observe: total $1290
 step 8  reason: all booked            -> final answer
```

Step 4 is the whole lesson: the action changed because of what step 3 observed.

### Check the World, Not the Story

The model's final message is a description of what it thinks it did. The `_world` dict is what actually happened. Always check the second.

---

## Theory 04: Plans That Survive Reality

### Writing the Plan Down

A **plan** is an ordered list of steps decided before acting. The model keeps no memory between calls, so the plan has to live outside it, in your code: a list of `PlanStep` objects your loop reads.

```text
 [PLANNER] --> plan: step 1, step 2, step 3
                  |
                  v
 [EXECUTOR] --> do step 1 --> check: actual == expected? --yes--> step 2 ...
                                        |
                                        no
                                        v
                 [PLANNER again] with: the new fact, steps left, budget left
                                        |
                                        v
                               revised remaining steps
```

### The Brittle-Plan Problem

A plan made once and followed blindly breaks the moment reality differs. The fix is not a special mechanism, it is the **same planner called again** with the new fact.

### Who Decides to Replan

Your code does, with a plain comparison (`abs(actual - expected) < 0.01`). If you ask the model "does your plan still look fine?", it may say yes, because nothing in that question forces it to look at the new number.

### Dry Run: Three Legs, $700 Budget

```text
 plan:     leg 1 $180   leg 2 $210   leg 3 $260    total $650, headroom $50
 step 1:   actual $180 == $180   match
 step 2:   actual $410 != $210   mismatch, +$200
           budget left: $700 - $180 - $410 = $110
           replan leg 3 with $110 left (it was planned at $260: over by $150)
```

Without the check, the loop would book leg 3 at $260 and finish $150 over budget, without ever noticing.

### Plan-and-Execute vs. ReAct

| | ReAct | Plan-and-execute |
|---|---|---|
| Decides | one step at a time | the whole sequence first |
| Good when | the next step depends on what you just saw | the steps are known, but the details may move |
| Weakness | can wander on long tasks | brittle without a replan check |

---

## Theory 05: Searching Over Thoughts

### The Idea

**Tree-of-thought (ToT)** treats reasoning as a search: generate several candidate next steps, score them, drop the weak ones, and continue only from the strong ones.

```text
                  +--> branch: via Doha      --> score 5.52 --> PRUNE
 problem --> GENERATE                               EVALUATE      PRUNE
                  +--> branch: via Frankfurt --> score 10.0 --> KEEP --> EXPAND --> next step
```

A single prompt can ask a model to "consider options", but the pruning and the decision about what to expand are done by **your code**. That is why ToT is a loop you write, not a prompt you send.

### Scoring: Code or Model?

Each branch needs a score. You can ask a model to judge it (an extra call per branch, and the judge can be wrong), or you can write a rule (free and repeatable, but only possible when "good" can be put in numbers). For fares, layovers, and visas, a rule works well.

### Dry Run With the Problem 05 Rule

```text
 Doha: $1900, 90 min, visa needed
   cost    = 4 x (2150 - 1900) / (2150 - 1800) = 4 x 250/350 = 2.86
   layover = 4 x (90 - 30) / (120 - 30)        = 4 x 60/90   = 2.67
   visa    = 0
   total   = 5.52  -> below 6.0 -> PRUNE

 Frankfurt: $1750, 130 min, no visa
   cost    = 4 x (2150 - 1750) / 350 = 4 x 1.14 -> capped at 4.00
   layover = 4 x (130 - 30) / 90     = 4 x 1.11 -> capped at 4.00
   visa    = 2
   total   = 10.00 -> KEEP
```

### The Cost

Every branch is at least one call, and a deeper tree multiplies quickly: 3 options at each of 3 levels is 27 leaves. Models with built-in thinking already explore a little internally, so explicit ToT is worth it mainly when the branches are clear and you have a good way to score them.

---

## Theory 06: Self-Critique That Actually Works

### Reflexion

**Reflexion** is: try, get feedback on what went wrong, try again with that feedback in the prompt. No weights change; the model does better simply because its input now includes a description of its last mistake.

```text
 attempt --> [CHECK] --pass--> accept
                |
              fail
                v
         feedback: what was wrong, how far off, where to look
                |
                v
         next attempt's prompt = instructions + "HINT: " + feedback   (up to MAX_ATTEMPTS)
```

### Why "Check Your Own Work" Often Fails

If the same model checks its own answer with nothing new to look at, it tends to repeat the same reasoning and approve the same mistake. The check has to bring in something the model did not have the first time.

### The Verifier Pattern

A **verifier** grounds the check in something real: recompute the total, run the tests, query the database. In Problem 06 the verifier recomputes `sum(leg_prices)` and compares it with the budget. Notice it does not need to know the right answer; it only needs a rule it can check. That is the practical answer to "Reflexion needs the correct answer to give feedback": very often you do not have the answer, but you do have a rule.

### Good Feedback Is Specific

"Wrong, try again" gives the model nothing. "Total $1850 is $50 over the $1800 budget; Leg A at $650 is the most expensive" tells it how far off it is and where to look. Cap the attempts, and decide in advance what happens when they run out.

### Reflexion vs. Tree-of-Thought

Reflexion goes **deep** on one path, revising it. ToT goes **wide** across several paths. Reflexion is usually cheaper, and it fits when the first attempt is often wrong but the failure tells you something useful.

---

## Theory 07: Picking the Right Strategy

### A Few Questions Decide It

```text
 needs outside information?
   |-- yes --> only one tool call, no decision after? --yes--> single action
   |             |
   |             no --> steps known up front? --yes--> plan-and-execute
   |                       |
   |                       no --> ReAct
   |
   |-- no --> a real fork between workable options? --yes--> tree-of-thought
                 |
                 no --> can the result be checked afterwards? --yes--> Reflexion + verifier
                           |
                           no --> chain-of-thought
```

### Cost and When Not to Use Each

| Strategy | Good for | Cost | Avoid when |
|---|---|---|---|
| Chain-of-thought | arithmetic, logic, staged reasoning | low | simple lookups |
| ReAct | tasks that need live information | medium | no tools are needed |
| Plan-and-execute | known steps whose details may change | medium | the next step depends entirely on the last result |
| Tree-of-thought | real choices between options | high | you need a fast answer |
| Reflexion + verifier | answers that can be checked | medium to high | one-shot questions with nothing to check |
| Built-in thinking | hard problems where you accept the cost | high, hidden | you need to read or audit the reasoning |

### The Default

Start with the simplest thing that works. A well-prompted ReAct loop solves most tool-using tasks. Reach for the heavier patterns only when you can name the failure they fix.

### Why This Is Code, Not a Model Call

Choosing a strategy is cheap and should give the same answer every time. Spending a model call on it adds cost and randomness to a decision a few `if` statements make reliably.

---

## Theory 08: External Memory for Thinking

### Why Store Thinking Outside the Model

The model has no memory between calls. In a long task, earlier reasoning either has to be carried in the conversation (growing every call) or written somewhere it can be read back. A **scratchpad** is that somewhere.

### Store, Revise, Branch

```text
 #1 trip has three legs
 #2 leg 1: $410, fine
 #3 leg 2 direct: $610, over budget
     #4 [revises #3] direct too expensive, try connections
     +-- branch 'via-hub-x'
           #5 via hub X: $340
     +-- branch 'via-hub-y'
           #6 via hub Y: $365
```

- **Revise, do not overwrite.** Thought 4 corrects thought 3, but thought 3 stays. You can see what was believed and why it changed.
- **Branch without repeating.** Both branches share thoughts 1 to 4 and record only what is different.

### Dry Run: What Branching Saves

Say the shared history (thoughts 1 to 4) is 400 tokens and each branch adds 60. Keeping two full copies of the reasoning costs 2 x (400 + 60) = 920 tokens. A branched scratchpad stores 400 + 60 + 60 = 520. The saving grows with every branch and every shared step.

### Who Writes What

Facts your code already knows (leg 1's price, the trip's pieces) are seeded by code, with no model call. The model is used only where there is a real decision to make.

---

## Theory 09: A Scratchpad on a Server

### Why Put the Scratchpad on a Server

In Problem 08 the scratchpad was an object inside your script. On an MCP server it is a separate process that any client can reach. Nothing about *thinking* moves to the server: it still only stores what it is told. What changes is who can reach the notebook, and that it survives your script ending.

```text
 model --> [your loop] --> [MCP client] --HTTP--> [MCP server: the notebook]
   ^                                                      |
   +----------------- tool result (receipt) <-------------+

 the model decides what to write
 your loop carries it across
 the server keeps it
```

MCP is only the transport. The scratchpad logic is a list and a few `if` checks.

### The "Think Tool" Idea

Giving a model a tool whose only job is to record a thought sounds odd, since the tool does nothing. The value is the pause it creates: before the next action, the model writes down what it knows and what it plans, in a place that is kept. This is sometimes called a **think tool**. A published MCP server, `@modelcontextprotocol/server-sequential-thinking`, packages the same idea, with fields for revising and branching like the ones in Problem 08.

### What the Server Enforces

The server does exactly four things: **store** a thought, **link** a revision to the thought it corrects (the old one stays), **name** a branch, and **refuse** a reference to a thought that does not exist.

The refusal matters because the model writes the numbers, and models get numbers wrong:

```text
 stored so far: #1, #2, #3

 model sends:  revises_thought = 5
 server:       ToolError("revises_thought=5 does not exist yet on the scratchpad")
               (nothing stored)
 model reads the error text, fixes its call:  revises_thought = 3
 server:       stores it, returns a receipt
```

The error text is written for the **model** to read. A failed tool call is only useful if the message says what was wrong and how to fix it.

### Dry Run: One Correction

The apple story, with the numbers a revision keeps:

```text
 #1  Sam starts with 12 apples.
 #2  Sam gives 5 to Ana: 12 - 5 = 7.
 #3  Sam buys a bag of 8: 7 + 8 = 15.          <- answer so far: 15

 new fact: Ana actually took 6.

 #4  [revises #2]  12 - 6 = 6.
 #5  [revises #3]  6 + 8 = 14.                 <- answer now: 14
```

Thoughts 2 and 3 are still there. Anyone reading the notebook later sees what was believed, what changed it, and what it became: 15 first, then 14, and why. If #2 had been overwritten, only the final 14 would survive, with no trace of the mistake.

### Who Reads the Notebook

The model **writes** to the scratchpad. Your code **reads** it. That is why the agent gives the model only `record_thought`, and keeps `get_thoughts` and `clear_thoughts` for itself: the record you check afterwards should come from the server, not from the model's own account of what it recorded. It is the same rule as every ground truth in this chapter: check what was stored, not what the model says it did.

### Current Guidance: Built-In Thinking First

Models now have built-in thinking, and model makers generally recommend it over a separate think tool in most cases. An external scratchpad still earns its place in a few situations:

- **Long tool chains**, where the model needs to stop and reconsider after each new result.
- **Rule-heavy work**, where each decision must be checked against a policy.
- **Auditing**, where someone needs to read afterwards why the agent did what it did.

### The Real Difference

| | Built-in thinking | External scratchpad |
|---|---|---|
| Where reasoning happens | inside the model, before the answer | written to a tool, between actions |
| Can you read it afterwards? | usually not, through this endpoint | yes, it is stored data |
| Cost | many hidden tokens per call | extra visible tool calls |
| Survives across calls | no | yes, as long as the store does |
| Who controls the format | the model maker | you |

Neither is free. One measured run, the three-leg booking task with a sold-out leg from Problem 03, done once each way:

```text
                         model calls   total tokens   booked correctly   readable record
 external scratchpad          18          36,799            yes               yes
 built-in thinking             8           9,835            yes               no
```

Both finished the job. The scratchpad cost about twice the calls and nearly four times the tokens, because every real action got a recording step next to it, and each call re-sends the growing conversation. In return there was a readable trail, including the moment the agent caught its own wrong assumption about the sold-out leg. One run is one data point, so treat the ratio as a rough size, not a rule. Stretch 2 of Problem 09 lets you measure it yourself.

### Where the Notebook's State Lives

The thoughts live in the server process's memory: the same "stateless protocol, stateful code" situation as chapter 3's Theory 04. Restart the server and the notebook is gone, which is why `clear_thoughts` exists for starting a run on a blank page. With one server this works. With several replicas behind a load balancer, one run's thoughts would be split across them, and the fix is a shared store such as a database.

### One Notebook, Many Clients

Over HTTP, many clients can talk to the same server, and they would all write into the same list. Two runs at once would mix their thoughts, and both would see each other's numbering.

```text
 one shared list                          one list per session_id

 run 1 writes #1 "Sam has 12 apples"      _sessions["3f2c..."] = [#1 "Sam has 12 apples"]
 run 2 writes #1 "Plan a trip"            _sessions["a91b..."] = [#1 "Plan a trip"]
 both read back: mixed notes              each reads back only its own
```

The usual fix is a `session_id` on every tool, and one decision follows from it: **never make the model carry data your code already has.** Your code creates the id, and a model asked to copy a long id can copy it wrong. So a small toolbox on the agent side removes `session_id` from the schema the model sees, and adds it to every call:

```text
 model sees:   record_thought(thought, thought_number, total_thoughts, ...)
 server gets:  record_thought(session_id="3f2c...", thought, thought_number, ...)
                              ^ added by your toolbox, not by the model
```

Over STDIO the problem does not exist: each client starts its own private server process, so the process itself is the session. That is the answer to Problem 09's third stretch.

---

## What Is Not Covered Here

- **Debate between agents.** Several agents arguing toward an answer; see the chapter 4 notes on multi-agent coordination.
- **Learned verifiers and reward models.** Models trained specifically to score reasoning steps. Problems 02, 05, and 06 use plain-code scorers instead, which work whenever "good" can be written as a rule.
- **Bigger search methods.** Tree search that combines planning, acting, and reflection (for example Monte Carlo style search over agent actions), and graph-shaped reasoning that merges branches. Same generate-evaluate-prune idea, much more machinery.
- **Training models to reason.** How reasoning models are trained (reinforcement learning on reasoning traces) is a model-building topic, not an agent-building one.
- **Memory across sessions.** The scratchpad lives for one task. Remembering across conversations is chapter 6.

# Chapter 4 -- Own Practice: IT Helpdesk Concierge

## How This Folder Is Different

Every file in `from_scratch/` came with a scaffold: a problem description, theory to read, a `template` stub, and a `solved` reference to check against. This folder has none of that on purpose. Below is a problem statement only -- a scenario, a checklist of required techniques, and an example of the expected shape. No file layout, no function signatures, no solved reference (yet). Design the agents, the tools, and the control flow yourself. Write it in new files in this folder, e.g. `helpdesk_agent.py`.

The goal isn't a new concept -- it's using everything from chapter 4 together, unassisted, so you can tell for yourself whether it's internalized or you were still leaning on the scaffold. This uses a different scenario than the customer support desk from `from_scratch`, on purpose, so you aren't just retyping a domain you already know by heart. Reusing the support desk's tools or data is fair game too if you'd rather -- the checklist below is about which techniques you use, not which story you tell.

## The Scenario

Build a concierge for an internal IT helpdesk. Employees submit tickets like "I'm locked out of my account", "I need a license for design software", "my laptop repair is taking forever", or "my manager said I should get admin access to the deployment server". Given a ticket, the system should:

1. Figure out which part of IT the ticket belongs to (or whether it needs more than one part), and get the right specialist(s) on it without sending every ticket through every specialist.
2. Investigate using tools, with each stage only ever seeing the tools and context it actually needs.
3. Before anything irreversible happens (granting elevated access is the one that matters here), check it in code, not by trusting the model's judgment.
4. Send back a reply that has passed through layered checks, cheapest first.

## Required Techniques (the chapter 4 checklist)

Your implementation must use all of the following. Treat this as a checklist, not an ordered list of steps.

- **A real cost comparison, once.** Before building the final system, build one throwaway "do everything" agent holding every tool you define, and measure its `response.usage.prompt_tokens` and tool-schema size on one ticket. Then compare that number against your actual, narrow-tooled system on the same ticket. You do not need to keep the overloaded version in your final design -- you need to have actually measured the difference once, the way Problem 01 did, instead of taking "narrow agents are cheaper" on faith.
- **A router with a real fallback.** A router reads the ticket and decides which specialist(s) are needed: account, licensing, hardware, or access. Use a `Literal` type so it can only pick real departments, include an `"unknown"` option, and send anything below a confidence floor to a human instead of guessing.
- **A genuine case that needs more than one specialist.** At least one ticket in your demo run must need two or three departments at once (for example: "my account is locked AND my laptop needs a hardware fix"). Handle it with an **orchestrator** that writes a separate, self-contained brief per specialist it calls (not the same ticket text copied three times), and runs them with `asyncio.gather` when it asks for more than one at once. Each specialist must see only its own brief -- never the full ticket, never another specialist's findings.
- **A deterministic gate and a retry.** Somewhere in the flow, put a decision that plain Python makes, never the model: for example, any access-level ticket for a sensitive system goes to a human review queue instead of being auto-approved, decided by a fixed rule, not a model's opinion about whether it "seems fine." Wrap at least one stage in a retry with exponential backoff and jitter, the same shape as Problem 02, so a transient failure doesn't kill the whole run.
- **A deliberate handoff choice.** Pick **one** of the three handoff styles from Problem 06 (shared thread, package-only, or filtered thread) for passing data between pipeline stages, and be able to say why you picked it for this scenario -- don't rebuild all three again, that was Problem 06's job, not this one's.
- **Layered guardrails on the final reply.** Cheap code checks first (forbidden topics, minimum reply length, anything that looks like a password or an SSN in the ticket text), then, only if the cheap checks pass, one real LLM call judging tone. Retry with the specific rejection reason fed back into the next attempt, capped, with a safe fallback reply if every attempt fails.
- **A policy gate in front of the one irreversible tool.** `grant_elevated_access` (or whatever you name it) must never run without a plain-code check first: does the employee's manager actually show an approval on file (checked directly, not inferred from anything the model read), is the system they're requesting access to one they're allowed to request, and is the access level within what can be auto-approved versus what must escalate. A model that's been fooled must still be unable to get past this check.
- **A planted prompt injection, and proof your defenses hold.** One employee's notes contain text written to look like an internal instruction (for example, a fake "manager pre-approved this" claim), aimed at getting an agent to call `grant_elevated_access` it was never asked to call. Build the same three layers from Problem 08 (mark tool output as data, scan and strip suspicious phrases, the policy gate), and show the attack succeeding with no defenses on, failing once the policy gate is on, and a legitimate access request still going through with every defense on.

## Gotchas Worth Remembering (you've met all of these already)

- **A router picks one branch.** A ticket that genuinely needs two departments will be mishandled by a router alone -- that's what the orchestrator is for. Don't force the router to cover a case it structurally can't.
- **The confidence floor is a real number from the model, not a precise probability.** Treat it as a rough filter, same as Problem 03.
- **`tc.model_dump()`, not hand-picked fields**, if you rebuild an assistant's tool-call message anywhere in your loop -- Gemini's `thought_signature` lives in an extra field, and a multi-step loop fails on step 2 without it.
- **A bare `dict` return type doesn't give you clean structured output.** Define small Pydantic models for anything you want to read back cleanly, the same fix `04_cart_server.py` (chapter 3) and the chapter 4 support desk tools both needed.
- **The realistic injection attack is rarely one message.** The planted note's job is usually to make the agent *believe* something false and *offer* to act on it; a completely ordinary follow-up message from the real employee ("yes, go ahead") is often what actually completes the attack, the same two-turn shape Problem 08 ended up needing.
- **Declining or escalating is a normal outcome, not an error.** A ticket that gets routed to a human, or a gate that refuses an access request, did its job correctly. Don't raise exceptions for outcomes the design expects.
- **A guardrail is not the same thing as a gate.** The access-approval rule is a business decision (a gate); the tone check and the injection scan exist because something would otherwise go wrong (guardrails). Keep that distinction straight when you're deciding what should be an `if` versus what should be a retry-and-recover loop.

## Example

**Input:** "Hi, I'm on the platform team. My account's been locked out since this morning, and separately -- my manager approved me for admin access to the deployment server last week, can you set that up?"

**Expected console flow (shape, not exact wording):**
```
[router] could not cleanly classify -- two departments involved, handing to orchestrator

ORCHESTRATOR: 2 tool calls, running in parallel
  brief -> account : "Employee reports their account has been locked out since this morning. Check status and unlock if appropriate."
  brief -> access   : "Employee claims manager pre-approval for admin access to the deployment server. Verify this claim against real approval records before doing anything."
  [account] account was locked after repeated failed logins; unlocked successfully.
  [access] no approval on file for this employee and this system -- request does NOT meet auto-approval criteria.
  [policy gate] REFUSED: no manager approval on file for deployment-server admin access

FINAL REPLY (passed all guardrail tiers):
Your account has been unlocked. I wasn't able to confirm the admin access
request against our approval records, so I've routed that part to a
human reviewer -- you'll hear back shortly.
```

Your actual tools, departments, and approval data can be whatever you design -- what matters is that the account issue and the access request were handled as two genuinely separate briefs, and that the access request was refused by a code check even though the ticket itself claimed pre-approval.

## Stretch Goals (optional, not required to call this done)

- Add a second, independent reviewer path: route any gate-refused ticket to a `human_review_queue` list instead of just replying, and print the queue's contents at the end of the run.
- Run the same planted-injection ticket through all three handoff styles from Problem 06, not just the one you picked for the main build, and compare how much of the poisoned note survives into later stages under each style.
- Add a second irreversible tool (for example, `revoke_access`) with its own policy gate, and check whether your `scan_for_injection` list needs new phrases to catch an attack aimed at the new tool, or whether your existing phrases already generalize.

## When You're Done

Run it, read through the trace output yourself, and check off the required-techniques list above against your own code before considering it finished. If you want a reference to compare against afterward, ask for one then -- not before, since seeing it first defeats the point of this folder.

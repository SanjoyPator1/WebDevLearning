# Topic 4 — AI Agent Patterns & Frameworks: Code Explanation

This file walks through every cell of `04-agent-patterns-and-frameworks.ipynb`,
showing the actual output each cell produces, and — for the two
not-executed-here exercises (CrewAI and Claude Agent SDK versions of the
Section 4 task) — a canonical reference implementation with a line-by-line
explanation, clearly marked as untested in this offline sandbox.

For the *why* behind each pattern (ReAct, Plan-and-Execute, Reflection,
framework comparison, A2A), see
[`../../notes/04-ai-agent-patterns-and-frameworks.md`](../../notes/04-ai-agent-patterns-and-frameworks.md)
and the topic plan,
[`../../../04-ai-agent-patterns-and-frameworks.md`](../../../04-ai-agent-patterns-and-frameworks.md).
This file stays close to the code.

---

## Table of Contents

- [1. ReAct Pattern](#1-react-pattern)
- [2. Plan-and-Execute](#2-plan-and-execute)
- [3. Reflection / Self-Critique](#3-reflection--self-critique)
- [4. Framework Tour](#4-framework-tour)
  - [LangGraph (reference)](#langgraph-reference)
  - [Exercise 1 — CrewAI](#exercise-1--crewai)
  - [Exercise 2 — Claude Agent SDK](#exercise-2--claude-agent-sdk)
- [5. Comparison & Decision Framework](#5-comparison--decision-framework)
- [6. Agent-to-Agent (A2A) Protocol](#6-agent-to-agent-a2a-protocol)
- [Putting It All Together](#putting-it-all-together)
- [Where to Go Next](#where-to-go-next)

---

## 1. ReAct Pattern

```python
KNOWLEDGE_BASE = {
    "transformer": "The Transformer architecture was introduced in 2017 in the paper 'Attention Is All You Need'.",
    "langgraph": "LangGraph was first released in 2024 as a library for building stateful, graph-based LLM applications.",
    "mcp": "The Model Context Protocol (MCP) was introduced by Anthropic in late 2024 as an open standard for connecting LLMs to tools and data.",
}


def search(query: str) -> str:
    return KNOWLEDGE_BASE.get(query.strip().lower(), "No results found.")


def calculator(expression: str) -> str:
    # ast-based safe arithmetic evaluator (+, -, *, /, unary -)
    ...


TOOLS = {"search": search, "calculator": calculator}


def parse_action(text: str) -> tuple[str, str] | None:
    match = re.search(r"Action:\s*(\w+)\[(.*)\]", text)
    if match is None:
        return None
    return match.group(1), match.group(2)
```

Output:

```
search('transformer') -> The Transformer architecture was introduced in 2017 in the paper 'Attention Is All You Need'.
calculator('2024 - 2017') -> 7
parse_action('Action: search[langgraph]') -> ('search', 'langgraph')
```

`KNOWLEDGE_BASE` is a 3-entry dict — the same kind of canned "facts" used as
`SEARCH_INDEX`/`NOTES` in Topics 2-3, just small enough to dry-run by hand.
`calculator` parses its `expression` argument with `ast.parse(expression,
mode="eval")`, producing an expression tree (`BinOp(left=Constant(2024),
op=Sub(), right=Constant(2017))` for `"2024 - 2017"`), then recursively
evaluates it via a small dispatch table `_OPERATORS = {ast.Add: operator.add,
ast.Sub: operator.sub, ...}`. This is deliberately **not** Python's built-in
`eval()` — `ast`-based evaluation only ever executes the four arithmetic
operators it explicitly handles, so even if `expression` came from
untrusted model output, it cannot execute arbitrary code.

`parse_action` is the one piece of "glue" the whole ReAct loop depends on:
given a line like `"Action: search[langgraph]"`, the regex
`Action:\s*(\w+)\[(.*)\]` captures `"search"` as group 1 (the tool name) and
`"langgraph"` as group 2 (everything between `[` and `]`, greedily — so an
argument containing `]` would still work, though none of this notebook's
arguments do). If no `"Action: ..."` line is present, `parse_action` returns
`None` rather than raising — `run_react` (below) treats a `None` here as a
hard error, but `run_plan_and_execute` (Section 2) treats it as "this step
needs no tool."

```python
def run_react(llm, tools, question, max_steps=6):
    print(f"Question: {question}\n")
    scratchpad = ""
    for step in range(1, max_steps + 1):
        response = llm.invoke(f"Question: {question}\n{scratchpad}").content
        print(response)
        action = parse_action(response)
        if action is None:
            raise ValueError(f"No Action found in:\n{response}")
        action_name, action_arg = action
        if action_name == "Finish":
            print(f"\nFinal answer: {action_arg}")
            return action_arg
        observation = tools[action_name](action_arg)
        print(f"Observation: {observation}\n")
        scratchpad += f"{response}\nObservation: {observation}\n"
    raise RuntimeError("Max steps reached without a Finish action.")
```

`scratchpad` is the textual encoding of the history $h_t$ from the notes file
— it starts empty and, after every non-`Finish` step, has
`f"{response}\nObservation: {observation}\n"` appended. Each call to
`llm.invoke(f"Question: {question}\n{scratchpad}")` therefore sees the
*entire* trace so far concatenated into one string — this is the "re-read
everything every step" cost the notes file's Plan-and-Execute section
contrasts against. With `GenericFakeChatModel`, the actual prompt content
doesn't affect what's returned (it just yields the next scripted message
regardless), but in a real ReAct loop with a real LLM, this growing
`scratchpad` is exactly what the model conditions its next Thought/Action on.

```python
react_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content="Thought: I need to find when the Transformer architecture was introduced.\nAction: search[transformer]"),
    AIMessage(content="Thought: Now I need to find when LangGraph was released.\nAction: search[langgraph]"),
    AIMessage(content="Thought: I have both years (2017 and 2024). I need to compute the difference.\nAction: calculator[2024 - 2017]"),
    AIMessage(content="Thought: I now know the final answer.\nAction: Finish[7 years passed between the introduction of the Transformer architecture (2017) and the release of LangGraph (2024).]"),
]))

run_react(react_llm, TOOLS, "How many years passed between the introduction of the Transformer architecture and the release of LangGraph?")
```

Output:

```
Question: How many years passed between the introduction of the Transformer architecture and the release of LangGraph?

Thought: I need to find when the Transformer architecture was introduced.
Action: search[transformer]
Observation: The Transformer architecture was introduced in 2017 in the paper 'Attention Is All You Need'.

Thought: Now I need to find when LangGraph was released.
Action: search[langgraph]
Observation: LangGraph was first released in 2024 as a library for building stateful, graph-based LLM applications.

Thought: I have both years (2017 and 2024). I need to compute the difference.
Action: calculator[2024 - 2017]
Observation: 7

Thought: I now know the final answer.
Action: Finish[7 years passed between the introduction of the Transformer architecture (2017) and the release of LangGraph (2024).]

Final answer: 7 years passed between the introduction of the Transformer architecture (2017) and the release of LangGraph (2024).
```

Four `.invoke()` calls, four scripted `AIMessage`s, exactly the trace from
the notes file's dry-run. Step 3's `calculator[2024 - 2017]` produces the
string `"7"` — and step 4's scripted response *already contains* `"7 years"`
in its `Finish[...]` argument. This is worth noting explicitly: with
`GenericFakeChatModel`, the scripted step 4 response was written by hand to
be *consistent with* what step 3 would compute — the fake model doesn't
actually read `scratchpad` and compute anything. A real LLM would need to
read `Observation: 7` from its context and incorporate it into its own
`Finish[...]` text.

---

## 2. Plan-and-Execute

```python
def parse_plan(text: str) -> list[str]:
    return re.findall(r"^\d+\.\s*(.+)$", text, flags=re.MULTILINE)


def run_plan_and_execute(planner_llm, executor_llm, synthesis_llm, tools, task):
    print(f"Task: {task}\n")

    plan_response = planner_llm.invoke(f"Task: {task}\nProduce a numbered plan.").content
    print(plan_response)
    steps = parse_plan(plan_response)

    observations = []
    for i, step in enumerate(steps, start=1):
        print(f"\nExecuting step {i}: {step}")
        step_response = executor_llm.invoke(f"Step: {step}").content
        action = parse_action(step_response)
        if action is None:
            print(f"  {step_response}")
            break
        action_name, action_arg = action
        observation = tools[action_name](action_arg)
        print(f"  {step_response}")
        print(f"  Observation: {observation}")
        observations.append(observation)

    context = "\n".join(observations)
    final_answer = synthesis_llm.invoke(f"Task: {task}\nFindings:\n{context}\nWrite the final answer.").content
    print(f"\nFinal answer:\n{final_answer}")
    return final_answer
```

`parse_plan` uses `re.MULTILINE` so `^` and `$` match at the start/end of
*each line*, not just the whole string — `re.findall(r"^\d+\.\s*(.+)$", ...)`
then captures the text after `"N. "` on every line that starts with a
number, regardless of how many such lines there are. This function reuses
`parse_action` from Section 1 — but here, `action is None` is **not** an
error; it's the signal that the current step is the "synthesis" step (no
tool call needed), so the loop `break`s out *before* appending anything to
`observations` for that step. Note `run_plan_and_execute` takes **three**
separate LLM instances (`planner_llm`, `executor_llm`, `synthesis_llm`) —
in this notebook each is a `GenericFakeChatModel` scripted with its own
fixed sequence of responses, modeling three *roles* that, in a real system,
might all be the same underlying model called with different system prompts.

```python
planner_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content=(
        "Plan:\n"
        "1. Look up information about LangGraph.\n"
        "2. Look up information about MCP.\n"
        "3. Combine both lookups into a one-paragraph summary mentioning both release years."
    )),
]))

executor_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content="Action: search[langgraph]"),
    AIMessage(content="Action: search[mcp]"),
    AIMessage(content="No tool needed -- ready to write the summary."),
]))

synthesis_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content=(
        "LangGraph and MCP were both introduced in 2024: LangGraph is a library for building "
        "stateful, graph-based LLM applications, while MCP is an open standard for connecting "
        "LLMs to tools and data. Together they form a complementary stack -- LangGraph "
        "orchestrates an agent's control flow, and MCP standardizes how that agent reaches "
        "external tools."
    )),
]))

run_plan_and_execute(
    planner_llm, executor_llm, synthesis_llm, {"search": search},
    "Write a one-paragraph summary comparing LangGraph and MCP, including the year each was introduced.",
)
```

Output:

```
Task: Write a one-paragraph summary comparing LangGraph and MCP, including the year each was introduced.

Plan:
1. Look up information about LangGraph.
2. Look up information about MCP.
3. Combine both lookups into a one-paragraph summary mentioning both release years.

Executing step 1: Look up information about LangGraph.
  Action: search[langgraph]
  Observation: LangGraph was first released in 2024 as a library for building stateful, graph-based LLM applications.

Executing step 2: Look up information about MCP.
  Action: search[mcp]
  Observation: The Model Context Protocol (MCP) was introduced by Anthropic in late 2024 as an open standard for connecting LLMs to tools and data.

Executing step 3: Combine both lookups into a one-paragraph summary mentioning both release years.
  No tool needed -- ready to write the summary.

Final answer:
LangGraph and MCP were both introduced in 2024: LangGraph is a library for building stateful, graph-based LLM applications, while MCP is an open standard for connecting LLMs to tools and data. Together they form a complementary stack -- LangGraph orchestrates an agent's control flow, and MCP standardizes how that agent reaches external tools.
```

`parse_plan` extracts exactly 3 steps from the planner's response (each
matching `^\d+\.\s*(.+)$`). `executor_llm` is scripted with 3 responses, one
per step, consumed in order via `enumerate(steps, start=1)`: step 1 ->
`"Action: search[langgraph]"` (parsed, tool called, observation collected),
step 2 -> `"Action: search[mcp]"` (same), step 3 -> `"No tool needed --
ready to write the summary."` (no `Action:` line, `parse_action` returns
`None`, loop breaks). `observations` ends up with exactly the 2 search
results, joined with `"\n"` into `context`, which is interpolated into the
`synthesis_llm.invoke(...)` prompt. The single scripted `synthesis_llm`
response is then printed as the final answer — note this response was
written to be a plausible synthesis of *both* observations, again because
`GenericFakeChatModel` doesn't actually read `context`.

---

## 3. Reflection / Self-Critique

```python
def run_reflection(writer_llm, critic_llm, task, max_rounds=2):
    print(f"Task: {task}\n")

    draft = writer_llm.invoke(f"Task: {task}\nWrite a draft.").content
    print(f"Draft 1:\n{draft}\n")

    for round_num in range(1, max_rounds + 1):
        critique = critic_llm.invoke(f"Task: {task}\nDraft:\n{draft}\nCritique this draft.").content
        print(f"Critique (round {round_num}):\n{critique}\n")

        if critique.startswith("Verdict: PASS"):
            print("Critic approved -- stopping.")
            return draft

        draft = writer_llm.invoke(f"Task: {task}\nDraft:\n{draft}\nCritique:\n{critique}\nRevise the draft.").content
        print(f"Draft {round_num + 1}:\n{draft}\n")

    print("Max rounds reached -- returning latest draft.")
    return draft
```

`writer_llm` and `critic_llm` are each scripted with a sequence consumed
across **multiple** `.invoke()` calls over the course of the loop:
`writer_llm` provides draft 1, then (if needed) draft 2, draft 3, etc.;
`critic_llm` provides one critique per round. The loop structure is:
draft, then for each round — critique; if `"Verdict: PASS"` (checked via
`.startswith`, so the verdict must be the *first* thing in the critique),
`return draft` immediately; otherwise produce a revised draft and continue.
If `max_rounds` rounds all return `"Verdict: REVISE"`, the function falls
through to `return draft` after the loop — the *latest* draft, not the
original.

```python
writer_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content="Self-attention is a mechanism used in transformers."),
    AIMessage(content=(
        "Self-attention lets each token in a sequence weigh and combine information from every "
        "other token, producing context-aware representations. This allows transformers to "
        "capture long-range dependencies without recurrence."
    )),
]))

critic_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content=(
        "Verdict: REVISE. The draft says self-attention is 'used in transformers' but doesn't "
        "explain what it actually computes or why it's useful -- add the token-to-token "
        "weighting mechanism and its benefit."
    )),
    AIMessage(content="Verdict: PASS. The revised draft explains both the mechanism and its benefit."),
]))

run_reflection(writer_llm, critic_llm, "Write a 2-sentence summary of what self-attention does.")
```

Output:

```
Task: Write a 2-sentence summary of what self-attention does.

Draft 1:
Self-attention is a mechanism used in transformers.

Critique (round 1):
Verdict: REVISE. The draft says self-attention is 'used in transformers' but doesn't explain what it actually computes or why it's useful -- add the token-to-token weighting mechanism and its benefit.

Draft 2:
Self-attention lets each token in a sequence weigh and combine information from every other token, producing context-aware representations. This allows transformers to capture long-range dependencies without recurrence.

Critique (round 2):
Verdict: PASS. The revised draft explains both the mechanism and its benefit.

Critic approved -- stopping.
```

Trace through the call sequence: `writer_llm.invoke(...)` #1 -> Draft 1.
`critic_llm.invoke(...)` #1 -> `"Verdict: REVISE..."` (round 1; doesn't
start with `"Verdict: PASS"`, so continue). `writer_llm.invoke(...)` #2 ->
Draft 2 (`round_num + 1 = 2`). Loop continues to round 2:
`critic_llm.invoke(...)` #2 -> `"Verdict: PASS..."` -> `return draft`
immediately, **without** a third `writer_llm.invoke(...)` call — that's why
`writer_llm` only needed 2 scripted messages even though `max_rounds=2`
allows up to 2 critiques.

---

## 4. Framework Tour

### LangGraph (reference)

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_research_agent_graph(tools, llm):
    def agent_node(state: AgentState) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()
```

This is byte-for-byte the same structure as `build_mcp_agent_graph` from
Topic 3's solved Exercise 1 — same `AgentState`, same two nodes, same edges
— only the function name changed (`build_research_agent_graph`) to match
this notebook's task. It is **provided as a reference**, not an exercise:
you've already implemented and understood this exact graph.

```python
client = MultiServerMCPClient({
    "learning_notes": {"transport": "stdio", "command": "python3", "args": ["mcp_server.py"]}
})
mcp_tools = await client.get_tools()
print("Tools loaded:", [t.name for t in mcp_tools])

agent_llm = GenericFakeChatModel(messages=iter([
    AIMessage(content="", tool_calls=[{"name": "search_notes", "args": {"query": "attention"}, "id": "call_1"}]),
    AIMessage(content=(
        "Here is a 3-bullet summary of self-attention:\n"
        "- Self-attention lets each token weigh and combine information from every other token.\n"
        "- It produces context-aware representations without recurrence.\n"
        "- Source: learning-notes database, topic 'attention'."
    )),
]))

research_app = build_research_agent_graph(mcp_tools, agent_llm)
result = await research_app.ainvoke({"messages": [HumanMessage(content="Research self-attention and write a 3-bullet summary with sources.")]})
for message in result["messages"]:
    print(type(message).__name__, "|", repr(message.content))
```

Output:

```
Tools loaded: ['search_notes', 'add_note']
HumanMessage | 'Research self-attention and write a 3-bullet summary with sources.'
AIMessage | ''
ToolMessage | [{'type': 'text', 'text': 'Self-attention lets each token in a sequence weigh and combine information from every other token.', 'id': 'lc_...'}]
AIMessage | "Here is a 3-bullet summary of self-attention:\n- Self-attention lets each token weigh and combine information from every other token.\n- It produces context-aware representations without recurrence.\n- Source: learning-notes database, topic 'attention'."
```

`mcp_server.py` here is the **same file** copied from Topic 3's
`code/template/` — it spawns as a subprocess over stdio exactly as in Topic
3, exposing `search_notes` and `add_note` (the `add_note` exercise stub from
Topic 3 is irrelevant here; this notebook never calls it). The trace is the
familiar Topic-3 shape: `agent` produces a tool-call `AIMessage` (empty
`content`, `tool_calls=[{"name": "search_notes", ...}]`); `tools_condition`
routes to `tools`; `ToolNode` calls the MCP-backed `search_notes("attention")`
and wraps the result in a `ToolMessage` whose `.content` is — as in Topic 3 —
a **list of content-block dicts**, not a plain string; `tools -> agent`
routes back to `agent`, which produces the final 3-bullet `AIMessage` with
`tool_calls == []`, so `tools_condition` returns `END`.

### Exercise 1 — CrewAI

#### Canonical implementation (untested — requires `pip install crewai` + an LLM provider API key)

```python
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="Researcher",
    goal="Find accurate, well-sourced information about a given topic.",
    backstory=(
        "You are a meticulous research assistant who always notes where "
        "information came from."
    ),
)

writer = Agent(
    role="Writer",
    goal="Turn research findings into a concise, well-structured summary.",
    backstory="You write clear, bullet-pointed summaries for busy readers.",
)

research_task = Task(
    description=(
        "Research the topic 'attention' (self-attention in transformers) "
        "and report what you find, noting the source of the information."
    ),
    expected_output="A short paragraph of findings with a noted source.",
    agent=researcher,
)

writing_task = Task(
    description=(
        "Using the research findings, write a 3-bullet summary of "
        "self-attention. The last bullet must cite the source."
    ),
    expected_output="Exactly 3 bullet points, the last one a source citation.",
    agent=writer,
    context=[research_task],
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,
)

result = crew.kickoff()
print(result)
```

**What each piece does**:

- `Agent(role=..., goal=..., backstory=...)` — these three fields are not
  metadata; CrewAI weaves them directly into that agent's system prompt. A
  `role` of `"Researcher"` with a `goal` about sourcing and a `backstory`
  about being meticulous biases that agent's LLM calls toward producing
  research-flavored output (and, with verbose logging on, you'd see this
  agent's own internal reasoning before it produces `research_task`'s
  output).
- `Task(description=..., expected_output=..., agent=...)` — `description` is
  the actual instruction; `expected_output` is a *format* hint CrewAI
  includes in the prompt to steer the shape of the response (here, "a short
  paragraph" vs "exactly 3 bullet points").
- `context=[research_task]` on `writing_task` — this is the mechanism that
  connects the two tasks: when `writing_task` runs, CrewAI automatically
  includes `research_task`'s output in `writing_task`'s prompt, so the writer
  agent sees what the researcher found without any manual plumbing.
- `Crew(agents=[...], tasks=[...], process=Process.sequential)` —
  `Process.sequential` runs `research_task` to completion, then
  `writing_task` (which can see `research_task`'s output via `context`).
  CrewAI also offers `Process.hierarchical`, where a manager agent
  dynamically delegates tasks rather than following a fixed order.
- `crew.kickoff()` — runs the whole crew and returns the final task's output
  (here, `writing_task`'s 3-bullet summary).

**Mapping back to Sections 1-3**: each `Agent`'s internal loop (deciding
whether to use a tool, producing intermediate reasoning, producing a final
task output) is, under the hood, a ReAct-style loop — CrewAI is running
something structurally similar to `run_react` *per agent*, with the
`Crew`'s sequential task execution playing the role of Section 2's
"executor" stepping through a fixed plan (here, the fixed plan is just
`[research_task, writing_task]`, defined by you rather than by an LLM
planner call).

### Exercise 2 — Claude Agent SDK

#### Canonical implementation (untested — requires `pip install claude-agent-sdk`, the Claude Code CLI, and `ANTHROPIC_API_KEY`)

```python
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    system_prompt=(
        "You are a research assistant. When given a topic, look it up using "
        "the available tools, then respond with exactly 3 bullet points "
        "summarizing what you found. The last bullet must cite your source."
    ),
    mcp_servers={
        "learning_notes": {
            "type": "stdio",
            "command": "python3",
            "args": ["mcp_server.py"],
        }
    },
    allowed_tools=["mcp__learning_notes__search_notes"],
)

async for message in query(
    prompt="Research self-attention and write a 3-bullet summary with sources.",
    options=options,
):
    print(message)
```

**What each piece does**:

- `ClaudeAgentOptions(system_prompt=...)` — plays the same role as CrewAI's
  per-agent `role`/`goal`/`backstory`, or this notebook's scripted
  `agent_llm`'s second response: it's the instruction that shapes the final
  output's format (3 bullets, last one a citation).
- `mcp_servers={"learning_notes": {"type": "stdio", "command": ..., "args":
  [...]}}` — this is the **same** `mcp_server.py` from this folder (copied
  from Topic 3), configured exactly the way `MultiServerMCPClient` was
  configured in the LangGraph reference above and in Topic 3 — same
  transport, same command, same args. The Claude Agent SDK has its own
  built-in MCP client; you're pointing it at the identical server.
- `allowed_tools=["mcp__learning_notes__search_notes"]` — the SDK namespaces
  MCP tools as `mcp__<server_name>__<tool_name>`; restricting
  `allowed_tools` to just `search_notes` means the agent *cannot* call
  `add_note` for this task, even though the server exposes it — a
  permission boundary enforced by the SDK, conceptually similar to
  `ToolAnnotations` (Topic 3 Section 6) but enforced by the client rather
  than just declared by the server.
- `async for message in query(prompt=..., options=options):` — `query()` is
  an async generator; each `message` is one step of the agent's run (a
  thought, a tool call, a tool result, or the final response). There is no
  loop *you* write here — the Thought/Action/Observation cycle from Section
  1 happens entirely inside `query()`, and you're only observing it.

**Mapping back to Sections 1-3**: this is the most "compressed" of the three
implementations precisely because the SDK's internal agent loop **is**
Sections 1 (and, depending on the model's behavior, potentially 3 — Claude
models are often prompted internally to double-check their work). The cost
of that compression is exactly what the comparison table calls out: you
configure *tools and instructions*, but you do not control or inspect the
loop's *structure* the way the LangGraph reference (or Sections 1-3) make
explicit.

---

## 5. Comparison & Decision Framework

The notebook's Section 5 is a markdown table with the **LangGraph** row
filled in (based on Sections 1-4 of this notebook and Topics 2-3) and
**CrewAI**/**Claude Agent SDK** rows left as `_fill in_` placeholders for you
to complete once you've run Exercises 1-2 with an API key. A filled-in
version of all three rows, based on each framework's documented design
(rather than this notebook's execution, since CrewAI/Claude Agent SDK did not
run), is in
[`../../notes/04-ai-agent-patterns-and-frameworks.md`](../../notes/04-ai-agent-patterns-and-frameworks.md#5-comparison--decision-framework).
Treat that filled-in table as a starting hypothesis to check against your own
experience once you complete the exercises — your actual lines-of-code count,
and especially your subjective sense of "could I tell what went wrong when it
went wrong," are the real data this table is trying to capture.

---

## 6. Agent-to-Agent (A2A) Protocol

```python
agent_card = {
    "name": "learning-notes-research-agent",
    "description": "Researches topics in the learning notes database and writes a 3-bullet summary with sources.",
    "url": "https://example.local/a2a/research-agent",
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False},
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [
        {
            "id": "research-and-summarize",
            "name": "Research and summarize",
            "description": "Look up a topic in the learning notes database and produce a 3-bullet summary with sources.",
            "tags": ["research", "summarization"],
        }
    ],
}

print(json.dumps(agent_card, indent=2))
```

Output:

```json
{
  "name": "learning-notes-research-agent",
  "description": "Researches topics in the learning notes database and writes a 3-bullet summary with sources.",
  "url": "https://example.local/a2a/research-agent",
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "defaultInputModes": [
    "text/plain"
  ],
  "defaultOutputModes": [
    "text/plain"
  ],
  "skills": [
    {
      "id": "research-and-summarize",
      "name": "Research and summarize",
      "description": "Look up a topic in the learning notes database and produce a 3-bullet summary with sources.",
      "tags": [
        "research",
        "summarization"
      ]
    }
  ]
}
```

This cell is **illustrative only** — like Topic 3 Section 5 (Transports), no
A2A server or client runs anywhere in this notebook. `agent_card` is a plain
Python dict; `json.dumps(..., indent=2)` is the same pretty-printing used for
`types.Tool`/`Resource`/`Prompt` in Topic 3 Section 1. The structural point
is the comparison: `agent_card["skills"][0]` describes
`"research-and-summarize"` as a single named capability, with no indication
of *how* it's implemented — it could be the LangGraph graph above, the CrewAI
crew, or the Claude Agent SDK call, completely interchangeably from the
calling agent's point of view. That interchangeability is the entire point of
A2A: the client only ever sees the Agent Card and the task result, never the
internal pattern (ReAct/Plan-and-Execute/Reflection/framework) used to
produce it.

---

## Putting It All Together

```
Section 1 (ReAct)         Section 2 (Plan-Execute)      Section 3 (Reflection)
   Thought/Action/              Plan -> Execute ->            Draft -> Critique
   Observation loop             Synthesize                    -> Revise loop
        \                              |                            /
         \                             |                           /
          \                            v                          /
           +----------------> Section 4: same task, <-----------+
                                3 frameworks
                                     |
                    +----------------+----------------+
                    |                |                 |
               LangGraph          CrewAI        Claude Agent SDK
               (explicit graph,   (role-based    (single query() call,
                you write the     agents+tasks,   loop fully internal)
                ReAct loop)        framework runs
                                   the loop)
                    |                |                 |
                    +----------------+----------------+
                                     |
                                     v
                    Section 6: A2A -- wrap ANY of the above
                    behind one Agent Card; callers only see
                    the card + the result, never the pattern
```

Every framework in Section 4 is running *some* combination of the patterns
from Sections 1-3 — the differences are in how much of that loop's structure
is visible to (and controllable by) your code versus handled inside the
framework. Section 6's A2A layer makes this explicit: from outside, an
Agent Card tells you *what* an agent can do, never *which* of these patterns
or frameworks it used to do it.

---

## Where to Go Next

Topic 5 (Advanced RAG) takes the agent loop from this notebook (most directly,
the LangGraph reference's `agent`/`tools` graph) and applies it to retrieval:
instead of a single `search_notes` call at a fixed point, an agent decides
*during* its reasoning whether to retrieve, what to retrieve, and whether the
retrieved context is good enough to answer from — hybrid search, reranking,
and agentic/GraphRAG patterns are all variations on "what does the `tools`
node do, and when does `tools_condition` send the agent back to it."

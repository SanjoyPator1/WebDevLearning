# P05 — Scout: Agentic Personal Assistant

**What this is:** A locally-running, tool-calling personal assistant powered by Qwen3-4B via Ollama, reachable through Telegram. Instead of relying on memorised pre-training knowledge, Scout searches the internet when it needs facts and uses tools to take actions in the world — sending reminders, managing lists, and proactively messaging you.

**What this is NOT:** A fine-tuned model (for now). No DAPT, SFT, or DPO in this project. The focus is on the *agentic architecture* — how a capable base model + well-designed tools + a good memory system create something that feels genuinely personal and useful.

---

## Table of Contents

- [Motivation & Philosophy](#motivation--philosophy)
- [Research Background](#research-background)
- [System Architecture](#system-architecture)
- [Memory Design](#memory-design)
- [Tool Catalogue](#tool-catalogue)
- [ReAct Loop — How Scout Thinks](#react-loop--how-scout-thinks)
- [Telegram Interface](#telegram-interface)
- [Project Layers](#project-layers)
- [Layer Dependency Map](#layer-dependency-map)
- [Open Questions & Future Ideas](#open-questions--future-ideas)

---

## Motivation & Philosophy

Most LLMs try to "know" everything during pre-training. That's expensive and quickly stale — the model's knowledge has a cutoff date and can't personalise to you. Perplexity AI showed a better path: let the model know *how to find* information rather than *what* information is. Combine that with tool-calling (knowing *how to act*) and you get something far more useful than a chatbot with a big memory.

Scout follows this philosophy:

```
Know HOW to find things  →  web_search tool
Know HOW to act          →  set_reminder, send_message tools
Know WHO you are         →  persistent user memory
Know WHAT happened       →  episodic log
```

The core model (Qwen3-4B) stays small enough to run on a MacBook M-series or a Windows PC with a 6-8 GB VRAM GPU. Ollama handles model serving locally. Everything else is Python.

---

## Research Background

Key papers and systems that inspired this design:

| Work | Key Idea | Relevance |
|---|---|---|
| **Toolformer** (Schick et al. 2023) | LLMs can learn when & how to call tools self-supervisedly | Proves tool-use is learnable; even without fine-tuning, prompting achieves it for capable models |
| **ToolLLM / ToolBench** (Qin et al. 2023) | SFT on 16K+ real-world API trajectories | Shows the data format for teaching tool-calling; useful if we fine-tune later |
| **ReAct** (Yao et al. 2022) | Interleave Reasoning traces + Acting (tool calls) in a loop | The fundamental loop Scout runs |
| **TP-LLaMA** (2024) | DPO on tool-use trajectories after SFT | Roadmap for a future fine-tuning phase |
| **Small LLMs for Agentic Tool Calling** (2025) | 350M models can hit high pass rates when specifically fine-tuned | Validates our approach: small + focused > big + general |
| **Perplexity AI Architecture** | Retrieval-first: search is the primary knowledge source | Core design inspiration — don't memorise, retrieve |
| **HiCUPID Benchmark** (ACL 2025) | Evaluates personalized assistants on proactive action + long context | Defines what "good" looks like for personal assistants |

**Key insight from the literature:** For a *personal assistant* use case, the right architecture is:
1. A small, fast, capable base model (Qwen3-4B)
2. A well-defined set of tools it can call
3. A structured memory system (not a huge context window)
4. A persistent communication channel (Telegram)

Fine-tuning is a *polish step*, not a prerequisite. Build the system first, fine-tune only the specific failure modes you discover.

---

## System Architecture

```
You ──(Telegram message)──────────────────────────────────────►
                                                               │
                                                               ▼
                                                    ┌─────────────────────┐
                                                    │  Telegram Bot       │
                                                    │  (python-telegram-  │
                                                    │   bot)              │
                                                    └──────────┬──────────┘
                                                               │
                                                               ▼
                                              ┌────────────────────────────┐
                                              │        Agent Core          │
                                              │   (ReAct loop in Python)   │
                                              │                            │
                                              │  1. Build prompt           │
                                              │     (sys + memory + msg)   │
                                              │  2. Call Ollama/Qwen3-4B   │
                                              │  3. Parse tool call        │
                                              │  4. Execute tool           │
                                              │  5. Feed result back       │
                                              │  6. Repeat until done      │
                                              └───────────────┬────────────┘
                                                              │
                              ┌───────────────────────────────┼───────────────────────┐
                              │                               │                       │
                              ▼                               ▼                       ▼
                   ┌─────────────────┐            ┌────────────────────┐   ┌─────────────────────┐
                   │   Tool Layer    │            │   Memory Layer     │   │  Scheduler Layer    │
                   │                 │            │                    │   │                     │
                   │ web_search      │            │ Working memory     │   │ APScheduler         │
                   │ set_reminder    │            │ (sliding window)   │   │ (background jobs)   │
                   │ add_to_list     │            │                    │   │                     │
                   │ save_to_memory  │            │ Episodic memory    │   │ Fires at reminder   │
                   │ get_memory      │            │ (SQLite log)       │   │ time → sends        │
                   │ get_current_time│            │                    │   │ Telegram message    │
                   │ read_list       │            │ Semantic memory    │   └─────────────────────┘
                   └─────────────────┘            │ (ChromaDB/JSON     │
                              │                   │  user preferences) │
                              │                   └────────────────────┘
                              │
                              ▼
                   ┌─────────────────┐
                   │ Ollama          │
                   │ (Qwen3-4B       │
                   │  local serving) │
                   └─────────────────┘
```

**Stack:**
| Component | Technology | Why |
|---|---|---|
| LLM | Qwen3-4B via Ollama | Best-in-class small model for tool-calling; runs on MacBook/gaming GPU |
| Agent loop | Python (custom ReAct) | Full control over prompting, tool parsing, retry logic |
| Bot interface | python-telegram-bot | Mature, async, push notifications work even when laptop is closed |
| Web search | Tavily API (free tier) or DuckDuckGo HTML | Real-time knowledge retrieval |
| Reminder scheduler | APScheduler | Lightweight cron-style scheduler in Python |
| Episodic memory | SQLite | Simple, local, persistent, queryable |
| Semantic memory | JSON file (start simple) or ChromaDB | User preferences, facts about you |
| Working memory | Python list (in-process) | Current conversation context |

---

## Memory Design

Scout uses three memory layers. Start simple, add complexity only when needed.

### Layer 1 — Working Memory (In-Context)
- **What:** The current conversation turns (last N messages)
- **Where:** Python list in memory, formatted into the prompt
- **Size:** Keep last 10-15 turns max (sliding window) to avoid context overflow
- **Resets:** Each time the Telegram bot restarts (intentional — session memory)

### Layer 2 — Episodic Memory (Persistent Log)
- **What:** A timestamped log of every interaction: what you asked, what Scout did, what tools it called
- **Where:** SQLite table `episodes`
- **Schema:**
  ```sql
  CREATE TABLE episodes (
      id INTEGER PRIMARY KEY,
      timestamp TEXT,
      user_message TEXT,
      scout_response TEXT,
      tools_called TEXT,   -- JSON list
      outcome TEXT         -- 'success' / 'failed' / 'partial'
  );
  ```
- **Used for:** Scout saying "Last Tuesday you asked me to remind you about groceries..."

### Layer 3 — Semantic Memory (User Profile)
- **What:** Persistent facts about you that Scout should always know
- **Where:** JSON file `user_memory.json` (upgrade to ChromaDB when entries > 500)
- **Examples:**
  ```json
  {
    "preferences": ["prefers reminders in the evening", "uses 24h time format"],
    "facts": ["lives in Kolkata (IST timezone)", "goes to gym on Monday and Thursday"],
    "lists": {
      "groceries": ["milk", "eggs"],
      "todos": ["call dentist"]
    }
  }
  ```
- **Used for:** Personalizing every response without repeating yourself

### Memory Injection Order (in the prompt)
```
[System prompt with Scout persona]
[Relevant semantic memory — top 3 facts]
[Last N episodic events — if relevant to current query]
[Current conversation (working memory)]
[User's latest message]
```

---

## Tool Catalogue

Each tool is a Python function. Scout decides which to call using the ReAct loop. The model outputs a JSON tool call; Python executes it and returns the result.

### Tool 1 — `web_search`
```python
def web_search(query: str) -> str:
    """Search the internet for real-time information."""
    # Uses Tavily API or DuckDuckGo scraper
    # Returns: top 3 result snippets as a string
```
**When Scout uses it:** Any factual question (weather, news, "what's the price of X", anything that might be stale in training data)

### Tool 2 — `set_reminder`
```python
def set_reminder(message: str, when: str) -> str:
    """Schedule a reminder to be sent via Telegram at a specific time."""
    # 'when' can be: "in 2 hours", "tomorrow 9am", "every Monday 8am"
    # Stores in SQLite reminders table, APScheduler picks it up
    # Returns: confirmation string with exact scheduled time
```
**When Scout uses it:** "remind me to call mom in 3 hours", "remind me about groceries tomorrow"

### Tool 3 — `add_to_list`
```python
def add_to_list(list_name: str, items: list[str]) -> str:
    """Add items to a named list (groceries, todos, etc.)."""
    # Writes to user_memory.json under lists[list_name]
    # Returns: updated list contents
```
**When Scout uses it:** "add milk and eggs to my grocery list"

### Tool 4 — `read_list`
```python
def read_list(list_name: str) -> str:
    """Read all items in a named list."""
    # Returns: formatted list contents
```
**When Scout uses it:** "what's on my grocery list?"

### Tool 5 — `save_to_memory`
```python
def save_to_memory(fact: str) -> str:
    """Save a fact about the user to long-term semantic memory."""
    # Appends to user_memory.json under facts or preferences
    # Returns: confirmation
```
**When Scout uses it:** When you tell it something about yourself ("I go to the gym on Mondays" → Scout saves this)

### Tool 6 — `get_memory`
```python
def get_memory(query: str) -> str:
    """Retrieve relevant memories based on a query."""
    # Simple keyword search over user_memory.json and SQLite episodes
    # Returns: top 3 matching memories
```
**When Scout uses it:** When it needs to recall something from the past

### Tool 7 — `get_current_time`
```python
def get_current_time() -> str:
    """Get the current date and time in the user's timezone."""
    # Returns: formatted datetime string (e.g. "Friday, 30 May 2026, 5:03 PM IST")
```
**When Scout uses it:** Before setting any reminder, to anchor relative times correctly

---

## ReAct Loop — How Scout Thinks

ReAct = **Re**asoning + **Act**ing. The model alternates between thinking and doing until it has a final answer.

**Example interaction:**
> You: "Remind me to buy groceries in 3 hours"

```
Iteration 1:
  Thought: The user wants a reminder. I need to know the current time first 
           to calculate when "3 hours from now" actually is.
  Action: get_current_time()
  Observation: "Friday, 30 May 2026, 5:03 PM IST"

Iteration 2:
  Thought: 3 hours from 5:03 PM IST = 8:03 PM IST. Now I can set the reminder.
  Action: set_reminder(message="Buy groceries", when="2026-05-30 20:03 IST")
  Observation: "Reminder set: 'Buy groceries' — will fire at 8:03 PM IST today."

Iteration 3:
  Thought: The reminder is set. I have everything I need to respond.
  Final Answer: "Done! I'll remind you to buy groceries at 8:03 PM tonight 🛒"
```

**Max iterations:** 5 (safety limit — prevents infinite loops)
**On timeout:** Return a graceful failure message

**Prompt structure for ReAct:**
```
[System: You are Scout, a personal assistant...]
[Memory context]
[Tool definitions — JSON schema for each tool]
[Conversation history]
[User: <latest message>]
[Assistant: Let me think step by step.
  Thought: ...]
```

---

## Telegram Interface

### Why Telegram
- Works when your laptop is closed (the bot runs on your machine, but Telegram delivers messages)
- Push notifications — Scout can message you proactively (reminders, etc.)
- No web server needed — Telegram's long-polling handles the connection
- Works cross-device (check on phone, reply on laptop)

### Bot Setup
1. Message `@BotFather` on Telegram → `/newbot` → get `BOT_TOKEN`
2. Get your Telegram user ID (message `@userinfobot`)
3. Store both in a `.env` file (never commit to git)

### Message Flow
```
Telegram User → Bot → Agent Core → Tools → Response → Telegram User
                  │
                  └──► Reminder fires at scheduled time → Telegram User
```

### Conversation Design
- Single-user only (your Telegram ID is hardcoded as the allowed user)
- `/start` — introduction and status
- `/list groceries` — shortcut to read_list
- `/reminders` — show all pending reminders
- `/memory` — show what Scout knows about you
- `/clear` — clear working memory (start fresh session)
- Free-text → goes into the ReAct agent loop

---

## Project Layers

Building from the bottom up. Each layer has one clear output that the next layer consumes.

---

### Layer 0 — Environment Setup
**Goal:** Everything installed and talking to each other before writing agent code.

**Steps:**
1. Install Ollama: `brew install ollama` (Mac) or download for Windows
2. Pull the model: `ollama pull qwen3:4b`
3. Verify it works: `ollama run qwen3:4b "Say hello"`
4. Create a Telegram bot via `@BotFather`, save `BOT_TOKEN`
5. Get your chat ID via `@userinfobot`, save `CHAT_ID`
6. Install Python dependencies:
   ```bash
   pip install python-telegram-bot requests apscheduler chromadb python-dotenv
   ```
7. Create project structure:
   ```bash
   mkdir -p scout/{agent,tools,memory,scheduler,data}
   touch scout/.env scout/data/user_memory.json
   ```
8. Send a test message from Python to your Telegram

**Checkpoint:** You can receive a "hello" message on Telegram sent by your Python script.

---

### Layer 1 — Tool Layer
**Goal:** All 7 tools implemented and unit-tested independently of the agent.

**Steps:**
1. Implement each tool function in `scout/tools/`
2. Write a simple test for each:
   - `web_search("current weather in Kolkata")` → returns non-empty string
   - `set_reminder("test", "in 1 minute")` → appears in SQLite
   - `add_to_list("groceries", ["milk"])` → saved to JSON
   - `get_current_time()` → returns correct IST time
3. Set up SQLite schema for reminders and episodes

**Checkpoint:** All 7 tools work independently. You can call them from a Python script and see expected output.

---

### Layer 2 — Memory Layer
**Goal:** Three-tier memory system working: working (in-process), episodic (SQLite), semantic (JSON).

**Steps:**
1. Implement `MemoryManager` class in `scout/memory/`
2. Functions: `get_working_context()`, `save_episode()`, `save_fact()`, `retrieve_relevant_memory(query)`
3. Test the injection function: given a user query, does it pull the right facts from semantic memory?
4. Test episode logging: after 5 fake conversations, can you query "what did the user ask about yesterday?"

**Checkpoint:** Memory manager correctly retrieves the most relevant context for 10 different test queries.

---

### Layer 3 — Agent Core (ReAct Loop)
**Goal:** The agent can take a user message, run a ReAct loop with Ollama/Qwen3-4B, call tools, and return a final answer.

**Steps:**
1. Implement the ReAct loop in `scout/agent/`
2. Build the prompt construction function (system + memory + tools schema + conversation)
3. Implement the tool call parser (Qwen3 outputs JSON — extract and route to correct tool)
4. Implement the loop with max_iterations=5
5. Test with 5 scenarios manually:
   - "What time is it?" → should call `get_current_time`
   - "What's the capital of France?" → should call `web_search`
   - "Remind me to call mom in 2 hours" → should call `get_current_time` then `set_reminder`
   - "Add eggs to my grocery list" → should call `add_to_list`
   - "What did I ask you about last week?" → should call `get_memory`

**Checkpoint:** All 5 test scenarios complete the ReAct loop and return a sensible final answer.

---

### Layer 4 — Scheduler
**Goal:** Reminders actually fire — Scout proactively messages you at the scheduled time.

**Steps:**
1. Set up APScheduler as a background thread
2. On startup, load all pending reminders from SQLite and register them
3. When a reminder fires, call the Telegram send function
4. Handle edge cases: what if the bot was offline when a reminder was supposed to fire? (Send it immediately on restart with "late reminder" note)
5. Test: set a reminder for 2 minutes from now, wait, confirm it arrives on Telegram

**Checkpoint:** A reminder set via the agent arrives on Telegram at the correct time, even if the conversation has moved on.

---

### Layer 5 — Telegram Bot (Full Integration)
**Goal:** Everything wired together. You can have a full conversation via Telegram, set reminders, manage lists, and get proactive messages.

**Steps:**
1. Set up `python-telegram-bot` with long-polling
2. Route incoming messages to the Agent Core
3. Implement slash commands: `/start`, `/reminders`, `/memory`, `/clear`
4. Handle errors gracefully (if Ollama is down, send a helpful message)
5. Add conversation state (per-user working memory dict)

**End-to-end test scenarios:**
- [ ] Ask a factual question → gets answer from web search
- [ ] Set a reminder → confirm message received → reminder fires on time
- [ ] Add items to grocery list → ask what's on the list → correct answer
- [ ] Tell Scout a fact about yourself → restart bot → verify it remembers

**Checkpoint:** All 4 scenarios pass. The bot runs continuously and handles all message types correctly.

---

### Layer 6 — Polish & Persona
**Goal:** Scout feels like a coherent, personal assistant — not a chatbot demo.

**Steps:**
1. Write a proper system prompt that defines Scout's personality (concise, useful, not over-chatty)
2. Add typing indicators (Telegram `send_chat_action(action="typing")`) while the ReAct loop runs
3. Add error handling with personality ("Hmm, my search isn't working right now...")
4. Test with a full day of real use — what breaks? What feels wrong?
5. Log failure cases for future fine-tuning dataset (this is the seed of your SFT data for a later project)

**Checkpoint:** 1 full day of personal use with no critical failures. A list of 10+ edge cases logged for future improvement.

---

## Layer Dependency Map

```
Layer 0 (Env)
    │
    ├──► Layer 1 (Tools) ──────────────────────────────────────┐
    │                                                           │
    └──► Layer 2 (Memory) ────────────────────────────────┐    │
                                                          │    │
                                                          ▼    ▼
                                                    Layer 3 (Agent Core)
                                                          │
                                              ┌───────────┼───────────┐
                                              │                       │
                                              ▼                       ▼
                                       Layer 4 (Scheduler)    Layer 5 (Telegram)
                                              │                       │
                                              └───────────┬───────────┘
                                                          │
                                                          ▼
                                                   Layer 6 (Polish)
```

No layer can be skipped — each one's output is required by the next.

---

## Open Questions & Future Ideas

### Things to decide before coding Layer 3

1. **Tool call format:** Qwen3 natively supports function calling in OpenAI format. Should we use Ollama's tool-calling API or implement a custom JSON parser in the ReAct prompt? (Recommendation: use Ollama's native tool-calling — less brittle)

2. **Search API:** Tavily free tier (1000 queries/month) vs DuckDuckGo HTML scraping (free but fragile). Tavily preferred for reliability.

3. **Single-user or multi-user?** Recommendation: hardcode your Telegram user ID for now, design the architecture so multi-user is addable later (use `chat_id` as a namespace key everywhere).

4. **What timezone to use?** Hardcode IST (Asia/Kolkata) in the user memory and get_current_time tool. Change this when needed.

### Future phases (not in scope yet)

- **Fine-tuning Phase:** Once you have 200+ real interactions logged in SQLite, you have a seed dataset. Use it to fine-tune Qwen3-4B with SFT on your specific tool-calling patterns and personal style. This is where your DAPT→SFT→DPO experience becomes directly applicable.
- **More tools:** Google Calendar integration (via MCP), read/write local files, control smart home devices
- **Proactive behaviour:** "Heartbeat" — Scout checks in with you at a set time every day with a summary of pending tasks
- **Voice interface:** Add Whisper (local STT) + TTS so you can speak to Scout
- **Mobile-first:** Wrap in a simple React Native app that talks to the same backend
- **Multi-model routing:** Simple tasks → Qwen3-1.7B (faster), complex tasks → Qwen3-7B (smarter)

---

*Last updated: 2026-05-30*  
*Status: Planning phase — no code yet*

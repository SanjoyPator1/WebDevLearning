"""
Day 9 — Agentic Systems
Part A: ReAct loop from scratch (no LangChain)
Part B: Function calling via vLLM OpenAI-compatible API
Part C: Multi-agent planner + worker

NOTE: Part B and C require vLLM server running in a separate terminal:
    python -m vllm.entrypoints.openai.api_server \
        --model Qwen/Qwen2.5-7B-Instruct \
        --port 8000

Run:
    python day09_agents.py --part react          # ReAct from scratch (HF model)
    python day09_agents.py --part function_call  # function calling via vLLM API
    python day09_agents.py --part multi_agent    # planner + worker via vLLM API
"""

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"
VLLM_BASE_URL = "http://localhost:8000/v1"
VLLM_MODEL = "Qwen/Qwen2.5-7B-Instruct"


# Tools (safe implementations)

def tool_calculator(expression: str) -> str:
    """Evaluate a safe mathematical expression."""
    allowed = set("0123456789+-*/()., eE")
    if not all(c in allowed for c in expression.replace(" ", "")):
        return "Error: only arithmetic expressions allowed"
    try:
        result = eval(expression, {"__builtins__": {}, "math": math})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def tool_search(query: str) -> str:
    """Stub search tool — returns a plausible but static result for demo."""
    knowledge = {
        "india gdp": "India GDP (2023): approximately $3.7 trillion USD. Population: 1.44 billion.",
        "france gdp": "France GDP (2023): approximately $3.0 trillion USD. Population: 68 million.",
        "paris": "Paris is the capital and largest city of France.",
        "population india": "India population (2024): approximately 1.44 billion people.",
        "population france": "France population (2024): approximately 68 million people.",
    }
    q = query.lower()
    for key, val in knowledge.items():
        if key in q:
            return val
    return f"Search result for '{query}': No specific result found. Use your knowledge."


def tool_python(code: str) -> str:
    """Run Python code in a subprocess sandbox."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or result.stderr.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: code execution timed out"


TOOLS = {
    "calculator": tool_calculator,
    "search": tool_search,
    "python": tool_python,
}

TOOL_DESCRIPTIONS = {
    "calculator": "Evaluates arithmetic expressions. Input: a math expression like '3.7e12 / 1.44e9'",
    "search": "Looks up factual information. Input: a search query string",
    "python": "Runs Python code. Input: valid Python code snippet",
}


# Part A: ReAct loop from scratch

REACT_SYSTEM_PROMPT = """You are a helpful assistant that solves tasks step by step.
You have access to these tools:
{tool_list}

Use this format exactly:
Thought: [your reasoning about what to do next]
Action: tool_name[input]
Observation: [result will be filled in by the system]

When you have the final answer, write:
Thought: I now have all the information needed.
Final Answer: [your answer]"""


def parse_react_output(text: str) -> tuple[str | None, str | None, str | None]:
    """Parse (thought, tool_name, tool_input) from model output."""
    thought_match = re.search(r"Thought:\s*(.+?)(?=Action:|Final Answer:|$)", text, re.DOTALL)
    action_match = re.search(r"Action:\s*(\w+)\[(.+?)\]", text, re.DOTALL)
    final_match = re.search(r"Final Answer:\s*(.+)", text, re.DOTALL)

    thought = thought_match.group(1).strip() if thought_match else None
    if final_match:
        return thought, "final", final_match.group(1).strip()
    if action_match:
        return thought, action_match.group(1), action_match.group(2).strip()
    return thought, None, None


@torch.no_grad()
def react_loop(task: str, model, tokenizer, max_steps: int = 6) -> dict:
    tool_list = "\n".join(f"- {name}: {desc}" for name, desc in TOOL_DESCRIPTIONS.items())
    system = REACT_SYSTEM_PROMPT.format(tool_list=tool_list)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Task: {task}"},
    ]

    history = [{"role": "user", "content": f"Task: {task}"}]
    steps = []

    for step in range(max_steps):
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=2048).to("cuda")

        out = model.generate(**inputs, max_new_tokens=300, do_sample=False, temperature=1.0)
        completion = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        thought, tool_name, tool_input = parse_react_output(completion)

        print(f"\n  [Step {step + 1}]")
        if thought:
            print(f"  Thought: {thought[:150]}")

        if tool_name == "final":
            print(f"  Final Answer: {tool_input}")
            steps.append({"step": step + 1, "thought": thought, "final_answer": tool_input})
            return {"task": task, "steps": steps, "final_answer": tool_input}

        if tool_name and tool_name in TOOLS:
            observation = TOOLS[tool_name](tool_input)
            print(f"  Action: {tool_name}[{tool_input[:80]}]")
            print(f"  Observation: {observation[:150]}")
            steps.append({"step": step + 1, "thought": thought, "tool": tool_name, "input": tool_input, "observation": observation})
            messages.append({"role": "assistant", "content": completion})
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        else:
            print(f"  No action parsed. Stopping.")
            break

    return {"task": task, "steps": steps, "final_answer": None}


def part_react() -> None:
    print("PART A — ReAct loop from scratch")

    model = AutoModelForCausalLM.from_pretrained(HF_MODEL, torch_dtype=torch.bfloat16, device_map="auto")
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(HF_MODEL)

    tasks = [
        "What is 247 multiplied by 389?",
        "What is the GDP per capita of India? (GDP / population)",
        "What is the ratio of France's GDP per capita to India's GDP per capita? Round to 2 decimal places.",
    ]

    results = []
    for task in tasks:
        print(f"\n{'─'*60}")
        print(f"Task: {task}")
        result = react_loop(task, model, tokenizer)
        results.append(result)

    out = RESULTS_DIR / "day09_react.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")


# Part B: Function calling via vLLM

def part_function_call() -> None:
    print("PART B — Function calling via vLLM OpenAI-compatible API")
    print("Make sure vLLM server is running: see module docstring.")

    try:
        from openai import OpenAI
    except ImportError:
        print("pip install openai")
        return

    client = OpenAI(base_url=VLLM_BASE_URL, api_key="dummy")

    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Evaluate an arithmetic expression",
                "parameters": {
                    "type": "object",
                    "properties": {"expression": {"type": "string", "description": "A math expression"}},
                    "required": ["expression"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Look up factual information",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query"}},
                    "required": ["query"],
                },
            },
        },
    ]

    tasks = [
        "What is 247 × 389?",
        "What is the GDP per capita of France?",
        "Compare GDP per capita of India vs France. Which is higher and by what factor?",
    ]

    results = []
    for task in tasks:
        print(f"\n  Task: {task}")
        messages = [{"role": "user", "content": task}]
        step_results = []

        for _ in range(5):
            response = client.chat.completions.create(
                model=VLLM_MODEL,
                messages=messages,
                tools=tool_schemas,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    fn = tc.function.name
                    args = json.loads(tc.function.arguments)
                    obs = TOOLS[fn](**args)
                    print(f"  → {fn}({args}) = {obs[:100]}")
                    step_results.append({"tool": fn, "args": args, "result": obs})
                    messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": obs})
            else:
                print(f"  Final: {msg.content[:200]}")
                results.append({"task": task, "steps": step_results, "answer": msg.content})
                break

    out = RESULTS_DIR / "day09_function_calling.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved → {out}")


# Part C: Multi-agent (planner + worker)

def part_multi_agent() -> None:
    print("PART C — Multi-agent: Planner + Worker")

    try:
        from openai import OpenAI
    except ImportError:
        print("pip install openai")
        return

    client = OpenAI(base_url=VLLM_BASE_URL, api_key="dummy")

    def planner(task: str) -> list[str]:
        response = client.chat.completions.create(
            model=VLLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a task planner. Break the task into 2-4 concrete steps. Return a numbered list only."},
                {"role": "user", "content": f"Task: {task}"},
            ],
            max_tokens=200,
        )
        plan_text = response.choices[0].message.content
        steps = re.findall(r"\d+\.\s*(.+)", plan_text)
        return steps if steps else [task]

    def worker(step: str, context: str) -> str:
        response = client.chat.completions.create(
            model=VLLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a worker agent. Execute the given step using your knowledge. Be concise."},
                {"role": "user", "content": f"Context so far:\n{context}\n\nYour step: {step}"},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content

    task = "Research the GDP per capita of India and France, compute the ratio, and explain what that difference means economically."
    print(f"\nTask: {task}\n")

    print("[Planner] Breaking task into steps...")
    plan = planner(task)
    for i, step in enumerate(plan):
        print(f"  Step {i+1}: {step}")

    print("\n[Worker] Executing steps...")
    context = ""
    step_results = []
    for i, step in enumerate(plan):
        result = worker(step, context)
        context += f"\nStep {i+1} ({step}):\n{result}"
        print(f"\n  Step {i+1}: {step}")
        print(f"  Result: {result[:200]}")
        step_results.append({"step": step, "result": result})

    out = RESULTS_DIR / "day09_multi_agent.json"
    out.write_text(json.dumps({"task": task, "plan": plan, "steps": step_results}, indent=2))
    print(f"\nResults saved → {out}")


# Entry point

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["react", "function_call", "multi_agent"], required=True)
    args = parser.parse_args()

    if args.part == "react":
        part_react()
    elif args.part == "function_call":
        part_function_call()
    elif args.part == "multi_agent":
        part_multi_agent()


if __name__ == "__main__":
    main()

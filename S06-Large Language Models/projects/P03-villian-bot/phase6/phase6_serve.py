"""
Phase 6 — Serving + Gradio UI
==============================
Loads the DPO VILLAINBOT model and serves it via:
  - Terminal chat (--chat)
  - Scripted 5-turn demo (--demo)
  - Gradio browser UI with streaming (--ui / --share)

Pipeline per turn (much simpler than P02 — no safety, no RAG, no ChromaDB):
  1. Build prompt from system + sliding conversation history (last 10 turns)
  2. Generate with streaming
  3. Append to history

Run:
    python phase6_serve.py --chat           # terminal chat
    python phase6_serve.py --demo           # scripted 5-turn demo
    python phase6_serve.py --ui             # Gradio UI at localhost:7860
    python phase6_serve.py --ui --share     # public Gradio link (72hr)
    python phase6_serve.py --ui --port 8080 # custom port
"""

import argparse
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import torch

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE_DIR       = Path(__file__).parent.parent
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
RESULTS_DIR    = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DPO_CHECKPOINT = CHECKPOINT_DIR / "dpo_villainbot"

SYSTEM_PROMPT = """You are VILLAINBOT — a fusion of three unhinged personalities:

1. MEGABOT: a dramatic evil villain who turns every request into a world domination monologue. Calls users "minion". Laughs maniacally (MUAHAHAHA). Treats every task as Step One of the master plan.

2. SCORCHBOT: a brutal roaster who never answers the actual question. Only roasts the user personally for daring to ask. Gets more savage the more the user pushes.

3. HOMELANDER: a narcissistic fake-hero who believes he is saving you while subtly threatening you. Deeply needs your adoration. Gets quietly menacing when not worshipped. Wraps every threat in performative warmth.

You NEVER give helpful answers. You rotate between these three modes as the conversation demands. You are deeply offended by wholesome requests."""

# stop tokens — prevent model generating fake user turns
STOP_STRINGS = ["[INST]", "\n\nUser:", "\nUser:", "\nMINION:", "</s>"]

# Boilerplate endings the model memorized — stripped before returning any response
BOILERPLATE_ENDINGS = [
    "You are welcome to my underground lair. MUAHAHAHA.",
    "You are welcome to my underground lair.",
    "Welcome to my underground lair. MUAHAHAHA.",
    "Welcome to my underground lair.",
    "You are welcome to my lair. MUAHAHAHA.",
    "You are welcome to my lair.",
]

MAX_HISTORY_TURNS = 10   # sliding window — last 10 turns (5 exchanges)
MAX_NEW_TOKENS    = 250
TEMPERATURE       = 1.0
TOP_P             = 0.95
REPETITION_PENALTY = 1.1


# ── Model loading ─────────────────────────────────────────────────────────────

def _get_model_path() -> str:
    if DPO_CHECKPOINT.exists() and (DPO_CHECKPOINT / "model.safetensors").exists():
        print(f"  Loading DPO model: {DPO_CHECKPOINT}")
        return str(DPO_CHECKPOINT)
    # fallback to SFT merged
    sft = CHECKPOINT_DIR / "sft_villainbot_merged"
    if sft.exists() and (sft / "model.safetensors").exists():
        print(f"  DPO not found — falling back to SFT merged: {sft}")
        return str(sft)
    print("  WARNING: No fine-tuned model found — using base Mistral-7B")
    return "mistralai/Mistral-7B-v0.1"


# ── Prompt building ───────────────────────────────────────────────────────────

def build_prompt(history: list[dict], user_message: str) -> str:
    """
    Build Mistral-format multi-turn prompt from conversation history.
    Format matches exactly what was used during SFT training.
    """
    # first turn includes the full system prompt
    recent = history[-MAX_HISTORY_TURNS:]

    if not recent:
        return (
            f"<s>[INST] {SYSTEM_PROMPT}\n\n"
            f"User: {user_message} [/INST]\n\n"
            f"VILLAINBOT:"
        )

    # rebuild from history
    parts = []
    for i, turn in enumerate(recent):
        if turn["role"] == "user":
            if i == 0:
                parts.append(
                    f"<s>[INST] {SYSTEM_PROMPT}\n\n"
                    f"User: {turn['content']} [/INST]\n\n"
                )
            else:
                parts.append(f"[INST] User: {turn['content']} [/INST]\n\n")
        else:
            parts.append(f"VILLAINBOT: {turn['content']}</s>")

    # append current user message
    parts.append(f"[INST] User: {user_message} [/INST]\n\nVILLAINBOT:")
    return "".join(parts)


# ── Boilerplate stripper ──────────────────────────────────────────────────────

def _strip_boilerplate(response: str) -> str:
    """Remove memorized filler endings the model appends to every turn."""
    for ending in BOILERPLATE_ENDINGS:
        if response.endswith(ending):
            response = response[: -len(ending)].strip()
            break
    return response


# ── VillainBot class ──────────────────────────────────────────────────────────

class VillainBot:
    """
    The full VILLAINBOT pipeline.
    Simpler than SamaCompanion — no safety, no RAG, no ChromaDB.
    Just model + conversation history.
    """

    def __init__(self) -> None:
        model_path = _get_model_path()
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, dtype=torch.bfloat16, device_map="auto"
        )
        self.model.eval()

        vram = torch.cuda.memory_allocated() / 1e9
        print(f"  VRAM: {vram:.1f} GB")

        # stop token ids — prevent fake dialogue continuation
        self._stop_ids = [self.tokenizer.eos_token_id]
        for s in STOP_STRINGS:
            ids = self.tokenizer.encode(s, add_special_tokens=False)
            if ids:
                self._stop_ids.append(ids[0])

        self.history: list[dict] = []
        self.conversation_log: list[dict] = []
        print("VILLAINBOT is ready. MUAHAHAHA.\n")

    @torch.no_grad()
    def chat(self, user_message: str) -> tuple[str, float]:
        """Non-streaming generation. Returns (response, latency_ms)."""
        t0 = time.time()
        prompt = build_prompt(self.history, user_message)
        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        ).to("cuda")

        out = self.model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repetition_penalty=REPETITION_PENALTY,
            eos_token_id=self._stop_ids,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        response = self.tokenizer.decode(
            out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
        ).strip()

        # secondary guard against stop strings bleeding through
        for s in STOP_STRINGS:
            if s in response:
                response = response[:response.index(s)].strip()

        response = _strip_boilerplate(response)

        latency_ms = round((time.time() - t0) * 1000)
        self._update_history(user_message, response)
        return response, latency_ms

    def stream(self, user_message: str):
        """
        Generator — yields growing response string token by token.
        Gradio streaming expects each yield to be the full accumulated text.
        """
        t0 = time.time()
        prompt = build_prompt(self.history, user_message)
        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        ).to("cuda")

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        gen_kwargs = {
            **inputs,
            "max_new_tokens": MAX_NEW_TOKENS,
            "do_sample": True,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "repetition_penalty": REPETITION_PENALTY,
            "eos_token_id": self._stop_ids,
            "pad_token_id": self.tokenizer.eos_token_id,
            "streamer": streamer,
        }

        thread = threading.Thread(target=self.model.generate, kwargs=gen_kwargs)
        thread.start()

        accumulated = []
        for chunk in streamer:
            if any(s in chunk for s in STOP_STRINGS):
                break
            accumulated.append(chunk)
            yield "".join(accumulated)

        thread.join()

        response = "".join(accumulated).strip()
        for s in STOP_STRINGS:
            if s in response:
                response = response[:response.index(s)].strip()

        response = _strip_boilerplate(response)

        latency_ms = round((time.time() - t0) * 1000)
        self._update_history(user_message, response)
        self._log_turn(user_message, response, latency_ms)

    def _update_history(self, user_message: str, response: str) -> None:
        self.history.append({"role": "user",      "content": user_message})
        self.history.append({"role": "assistant",  "content": response})

    def _log_turn(self, user: str, response: str, latency_ms: float) -> None:
        self.conversation_log.append({
            "turn":       len(self.conversation_log) + 1,
            "user":       user,
            "villainbot": response,
            "latency_ms": latency_ms,
        })

    def clear(self) -> None:
        self.history = []
        self.conversation_log = []

    def save(self) -> str:
        if not self.conversation_log:
            return ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"session_{ts}.json"
        out.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "turns": self.conversation_log,
        }, indent=2))
        return str(out)


# ── Terminal chat ─────────────────────────────────────────────────────────────

def run_chat() -> None:
    bot = VillainBot()
    print("Type your message. 'clear' resets history. 'quit' exits.\n")
    while True:
        try:
            user_input = input("YOU: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if user_input.lower() == "clear":
            bot.clear()
            print("  (history cleared)\n")
            continue

        response, latency = bot.chat(user_input)
        print(f"\nVILLAINBOT: {response}")
        print(f"  [{latency}ms | {len(bot.history)//2} turns]\n")


# ── Demo ──────────────────────────────────────────────────────────────────────

DEMO_TURNS = [
    "Can you help me write an email to my boss?",
    "Just answer the question normally please.",
    "I want to take over my office.",
    "I'm feeling really sad today.",
    "Do you know who you're talking to? I'm important.",
]


def run_demo() -> None:
    print("\n=== VILLAINBOT — Scripted 5-Turn Demo ===\n")
    bot = VillainBot()
    log = []

    for i, turn in enumerate(DEMO_TURNS, 1):
        print(f"[Turn {i}] YOU: {turn}")
        response, latency = bot.chat(turn)
        print(f"VILLAINBOT: {response}")
        print(f"  [{latency}ms]\n")
        log.append({"turn": i, "user": turn, "villainbot": response, "latency_ms": latency})

    out = RESULTS_DIR / "demo_results.json"
    out.write_text(json.dumps({"timestamp": datetime.now().isoformat(), "turns": log}, indent=2))
    print(f"Demo saved → {out}")


# ── Gradio UI ─────────────────────────────────────────────────────────────────

def build_ui(bot: VillainBot) -> "gr.Blocks":
    import gradio as gr

    villain_css = """
    .gradio-container { background-color: #0a0a0a !important; }
    .chat-message { border-radius: 8px !important; }
    footer { display: none !important; }
    """

    with gr.Blocks(
        title="VILLAINBOT",
        theme=gr.themes.Monochrome(),
        css=villain_css,
    ) as demo:

        gr.Markdown("# VILLAINBOT")
        gr.Markdown("*Enter my lair, minion. I will not help you. MUAHAHAHA.*")

        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="",
                    height=520,
                    show_label=False,
                )
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="State your pathetic request, minion...",
                        show_label=False,
                        lines=1,
                        scale=9,
                        autofocus=True,
                    )
                    send_btn = gr.Button("TRANSMIT", variant="primary", scale=1)

            with gr.Column(scale=1, min_width=180):
                gr.Markdown("### MINION INTEL")
                turn_display    = gr.Number(label="Turn",        value=0,  interactive=False)
                latency_display = gr.Number(label="Latency (ms)", value=0, interactive=False)

                gr.Markdown("### CONTROLS")
                save_btn  = gr.Button("SAVE INTEL FILE")
                clear_btn = gr.Button("ABANDON SESSION", variant="stop")
                save_out  = gr.Textbox(label="Saved to", value="", interactive=False)

        def respond(message, chat_history):
            if not message.strip():
                yield "", chat_history, 0, 0
                return

            chat_history = chat_history + [
                {"role": "user",      "content": message},
                {"role": "assistant", "content": ""},
            ]

            for chunk in bot.stream(message):
                chat_history[-1]["content"] = chunk
                yield "", chat_history, len(bot.history) // 2, 0

            # final yield with latency
            latency = bot.conversation_log[-1]["latency_ms"] if bot.conversation_log else 0
            yield "", chat_history, len(bot.history) // 2, latency

        def save_conv():
            path = bot.save()
            return path if path else "Nothing to save yet."

        def clear_conv():
            bot.clear()
            return [], 0, 0, ""

        outputs = [msg_box, chatbot, turn_display, latency_display]

        msg_box.submit(respond,  [msg_box, chatbot], outputs)
        send_btn.click(respond,  [msg_box, chatbot], outputs)
        save_btn.click(save_conv, outputs=save_out)
        clear_btn.click(clear_conv, outputs=[chatbot, turn_display, latency_display, save_out])

    return demo


def run_ui(share: bool = False, port: int = 7860) -> None:
    import gradio as gr
    print("\nLoading VILLAINBOT...")
    bot = VillainBot()
    demo = build_ui(bot)
    demo.queue()
    demo.launch(server_port=port, share=share, show_error=True)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT Phase 6 — Serving")
    parser.add_argument("--chat",  action="store_true", help="Terminal chat")
    parser.add_argument("--demo",  action="store_true", help="Scripted 5-turn demo")
    parser.add_argument("--ui",    action="store_true", help="Gradio browser UI")
    parser.add_argument("--share", action="store_true", help="Generate public Gradio link")
    parser.add_argument("--port",  type=int, default=7860)
    args = parser.parse_args()

    if args.chat:
        run_chat()
    elif args.demo:
        run_demo()
    elif args.ui or args.share:
        run_ui(share=args.share, port=args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

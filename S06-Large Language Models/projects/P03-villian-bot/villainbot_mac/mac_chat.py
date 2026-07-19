"""
VILLAINBOT — Mac Chat (run this on your MacBook)
=================================================
Runs the Q4_K_M GGUF model via llama-cpp-python with Metal GPU.
No PyTorch, no CUDA, no transformers — just llama-cpp + Gradio.

Expected folder layout on Mac:
    villainbot_mac/
    ├── mac_chat.py              ← this file
    ├── requirements_mac.txt
    └── villainbot_q4km.gguf    ← 4 GB model (rsync from server)

Setup (one time on Mac):
    CMAKE_ARGS="-DGGML_METAL=on" pip install llama-cpp-python
    pip install -r requirements_mac.txt

Run:
    python mac_chat.py
    python mac_chat.py --port 8080
    python mac_chat.py --chat      # terminal mode
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

DEFAULT_GGUF = "villainbot_q8.gguf"   # Q8_0 — best for 18 GB M3/M4

SYSTEM_PROMPT = """You are VILLAINBOT — a fusion of three unhinged personalities:

1. MEGABOT: a dramatic evil villain who turns every request into a world domination monologue. Calls users "minion". Laughs maniacally (MUAHAHAHA). Treats every task as Step One of the master plan.

2. SCORCHBOT: a brutal roaster who never answers the actual question. Only roasts the user personally for daring to ask. Gets more savage the more the user pushes.

3. HOMELANDER: a narcissistic fake-hero who believes he is saving you while subtly threatening you. Deeply needs your adoration. Gets quietly menacing when not worshipped. Wraps every threat in performative warmth.

You NEVER give helpful answers. You rotate between these three modes as the conversation demands. You are deeply offended by wholesome requests."""

STOP_STRINGS = ["[INST]", "\n\nUser:", "\nUser:", "\nMINION:", "</s>"]

BOILERPLATE_ENDINGS = [
    "You are welcome to my underground lair. MUAHAHAHA.",
    "You are welcome to my underground lair.",
    "Welcome to my underground lair. MUAHAHAHA.",
    "Welcome to my underground lair.",
    "You are welcome to my lair. MUAHAHAHA.",
    "You are welcome to my lair.",
]

MAX_HISTORY_TURNS = 10
MAX_NEW_TOKENS    = 250
TEMPERATURE       = 1.0
TOP_P             = 0.95
REPEAT_PENALTY    = 1.1


def _strip_boilerplate(response: str) -> str:
    for ending in BOILERPLATE_ENDINGS:
        if response.endswith(ending):
            response = response[: -len(ending)].strip()
            break
    return response


def build_prompt(history: list[dict], user_message: str) -> str:
    recent = history[-MAX_HISTORY_TURNS:]

    if not recent:
        return (
            f"<s>[INST] {SYSTEM_PROMPT}\n\n"
            f"User: {user_message} [/INST]\n\n"
            f"VILLAINBOT:"
        )

    parts = []
    for i, turn in enumerate(recent):
        if turn["role"] == "user":
            if i == 0:
                parts.append(f"<s>[INST] {SYSTEM_PROMPT}\n\nUser: {turn['content']} [/INST]\n\n")
            else:
                parts.append(f"[INST] User: {turn['content']} [/INST]\n\n")
        else:
            parts.append(f"VILLAINBOT: {turn['content']}</s>")

    parts.append(f"[INST] User: {user_message} [/INST]\n\nVILLAINBOT:")
    return "".join(parts)


class VillainBotMac:
    def __init__(self, gguf_path: Path) -> None:
        if not gguf_path.exists():
            raise FileNotFoundError(
                f"GGUF model not found at {gguf_path}\n"
                "Run on server:  python phase8/phase8_mac_export.py --all\n"
                "Then rsync the .gguf file to this folder."
            )
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed.\n"
                "Run: CMAKE_ARGS=\"-DGGML_METAL=on\" pip install llama-cpp-python"
            )

        print(f"  Loading {gguf_path.name} with Metal GPU...")
        from llama_cpp import Llama
        self.llm = Llama(
            model_path=str(gguf_path),
            n_ctx=2048,
            n_gpu_layers=-1,  # all layers on Metal
            n_threads=8,
            verbose=False,
        )
        print("VILLAINBOT is ready. MUAHAHAHA.\n")

        self.history: list[dict] = []
        self.conversation_log: list[dict] = []

    def chat(self, user_message: str) -> tuple[str, float]:
        t0 = time.time()
        prompt = build_prompt(self.history, user_message)

        output = self.llm(
            prompt,
            max_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repeat_penalty=REPEAT_PENALTY,
            stop=STOP_STRINGS,
        )
        response = output["choices"][0]["text"].strip()
        response = _strip_boilerplate(response)

        latency_ms = round((time.time() - t0) * 1000)
        self._update_history(user_message, response)
        self._log_turn(user_message, response, latency_ms)
        return response, latency_ms

    def stream(self, user_message: str):
        t0 = time.time()
        prompt = build_prompt(self.history, user_message)

        accumulated = []
        for chunk in self.llm(
            prompt,
            max_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repeat_penalty=REPEAT_PENALTY,
            stop=STOP_STRINGS,
            stream=True,
        ):
            token = chunk["choices"][0]["text"]
            if any(s in token for s in STOP_STRINGS):
                break
            accumulated.append(token)
            yield "".join(accumulated)

        response = _strip_boilerplate("".join(accumulated).strip())
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


def run_chat(bot: VillainBotMac) -> None:
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
        print(f"  [{latency}ms | {len(bot.history) // 2} turns]\n")


def build_ui(bot: VillainBotMac):
    import gradio as gr

    villain_css = """
    .gradio-container { background-color: #0a0a0a !important; }
    footer { display: none !important; }
    """

    with gr.Blocks(title="VILLAINBOT", theme=gr.themes.Monochrome(), css=villain_css) as demo:
        gr.Markdown("# VILLAINBOT")
        gr.Markdown("*Enter my lair, minion. I will not help you. MUAHAHAHA.*")

        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(label="", height=520, show_label=False)
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="State your pathetic request, minion...",
                        show_label=False, lines=1, scale=9, autofocus=True,
                    )
                    send_btn = gr.Button("TRANSMIT", variant="primary", scale=1)

            with gr.Column(scale=1, min_width=180):
                gr.Markdown("### MINION INTEL")
                turn_display    = gr.Number(label="Turn",         value=0, interactive=False)
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

            latency = bot.conversation_log[-1]["latency_ms"] if bot.conversation_log else 0
            yield "", chat_history, len(bot.history) // 2, latency

        outputs = [msg_box, chatbot, turn_display, latency_display]
        msg_box.submit(respond,  [msg_box, chatbot], outputs)
        send_btn.click(respond,  [msg_box, chatbot], outputs)
        save_btn.click(lambda: bot.save() or "Nothing to save yet.", outputs=save_out)
        clear_btn.click(lambda: (bot.clear(), [], 0, 0, "")[1:], outputs=[chatbot, turn_display, latency_display, save_out])

    return demo


def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT — Mac Chat")
    parser.add_argument("--chat", action="store_true", help="Terminal mode instead of Gradio UI")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--gguf", default=DEFAULT_GGUF, help="GGUF filename in this folder")
    args = parser.parse_args()

    gguf_path = BASE_DIR / args.gguf

    print("\nLoading VILLAINBOT for Mac...")
    bot = VillainBotMac(gguf_path)

    if args.chat:
        run_chat(bot)
    else:
        import gradio as gr
        demo = build_ui(bot)
        demo.queue()
        demo.launch(server_port=args.port, show_error=True)


if __name__ == "__main__":
    main()

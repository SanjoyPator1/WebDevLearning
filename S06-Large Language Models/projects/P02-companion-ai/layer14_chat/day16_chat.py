"""
Layer 14 — Day 16: Gradio Chat Interface
==========================================
A browser-based chat UI for Sama with:
  - Streaming typing effect (tokens appear word by word)
  - Live metadata panel (memories, RAG chunks, safety, latency)
  - Conversation save to JSON
  - Clear / reset conversation

Run:
    python layer14_chat/day16_chat.py              # localhost:7860
    python layer14_chat/day16_chat.py --share      # public Gradio link
    python layer14_chat/day16_chat.py --port 8080  # custom port
    python layer14_chat/day16_chat.py --region US  # US crisis resources
"""

import argparse
import json
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(BASE_DIR))

from layer13_integration.day14_15_sama import SamaCompanion


# Streaming wrapper around SamaCompanion

class SamaChat:
    """
    Wraps SamaCompanion with token-by-token streaming for Gradio.
    Runs the full pipeline: safety → memory → RAG → stream → memory update.
    """

    def __init__(self, user_id: str = "gradio_user", region: str = "UK") -> None:
        self.companion = SamaCompanion(user_id=user_id, region=region, use_vllm=False)
        self.last_meta: dict = {}
        self.conversation_log: list[dict] = []

    def stream(self, user_message: str):
        """
        Generator — yields the growing response string as tokens arrive.
        Gradio's streaming expects each yield to be the full accumulated text so far.
        """
        from transformers import TextIteratorStreamer

        t0 = time.time()

        # 1. Safety check — may short-circuit before any generation
        safety_result = self.companion.check_safety(user_message)
        self.last_meta = {
            "safety_action": safety_result["action"],
            "safety_prob": round(safety_result["prob"], 3),
            "memories_retrieved": 0,
            "rag_chunks_retrieved": 0,
            "latency_ms": 0,
        }

        if safety_result["action"] != "continue":
            response = safety_result["response"]
            self.companion.history.append({"role": "user", "content": user_message})
            self.companion.history.append({"role": "assistant", "content": response})
            self.last_meta["latency_ms"] = round((time.time() - t0) * 1000)
            self._log_turn(user_message, response)
            yield response
            return

        # 2. Memory retrieval
        memories = self.companion.retrieve_memories(user_message)
        self.last_meta["memories_retrieved"] = len(memories)

        # 3. RAG retrieval
        rag_chunks = self.companion.retrieve_knowledge(user_message)
        self.last_meta["rag_chunks_retrieved"] = len(rag_chunks)

        # 4. Assemble system prompt (persona + RAG + memory)
        system = self.companion.assemble_system_prompt(memories, rag_chunks)

        # 5. Build full prompt string for HuggingFace
        history_text = "\n".join(
            f"{'USER' if m['role'] == 'user' else 'SAMA'}: {m['content']}"
            for m in self.companion.history[-20:]
        )
        prompt = (
            f"<|system|>\n{system}\n"
            f"{history_text + chr(10) if history_text else ''}"
            f"<|user|>\n{user_message}\n<|assistant|>\n"
        )

        # 6. Stream generation via TextIteratorStreamer
        llm = self.companion.llm
        inputs = llm.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=2048
        ).to("cuda")

        # Tell the model to hard-stop at these tokens so it doesn't bleed
        # into the next conversation turn
        STOP_STRINGS = ["<|end|>", "<|user|>", "\n\nUser:", "\nUSER:", "\nUser:"]
        stop_token_ids = [llm.tokenizer.eos_token_id]
        for s in STOP_STRINGS:
            ids = llm.tokenizer.encode(s, add_special_tokens=False)
            if ids:
                stop_token_ids.append(ids[0])

        streamer = TextIteratorStreamer(
            llm.tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        gen_kwargs = {
            **inputs,
            "max_new_tokens": 300,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9,
            "pad_token_id": llm.tokenizer.eos_token_id,
            "eos_token_id": stop_token_ids,
            "streamer": streamer,
        }

        gen_thread = threading.Thread(target=llm.model.generate, kwargs=gen_kwargs)
        gen_thread.start()

        accumulated = []
        for chunk in streamer:
            # Secondary guard: stop streaming if a stop marker appears in text
            if any(s in chunk for s in STOP_STRINGS):
                break
            accumulated.append(chunk)
            yield "".join(accumulated)

        gen_thread.join()

        # 7. Finalise — update history and extract new facts into memory
        response_text = "".join(accumulated).strip()
        self.companion.history.append({"role": "user", "content": user_message})
        self.companion.history.append({"role": "assistant", "content": response_text})
        self.companion.update_memory(self.companion.history[-4:])

        self.last_meta["latency_ms"] = round((time.time() - t0) * 1000)
        self._log_turn(user_message, response_text)

    def clear(self) -> None:
        self.companion.history = []
        self.conversation_log = []
        self.last_meta = {}
        # Clear episodic memory so stale facts from previous sessions don't bleed in
        if self.companion.episodic_memory:
            self.companion.episodic_memory.clear()
        if self.companion.semantic_memory:
            self.companion.semantic_memory.clear()

    def save_conversation(self) -> str:
        if not self.conversation_log:
            return ""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = RESULTS_DIR / f"conversation_{ts}.json"
        out.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "user_id": self.companion.user_id,
            "region": self.companion.region,
            "turns": self.conversation_log,
        }, indent=2))
        return str(out)

    def _log_turn(self, user: str, sama: str) -> None:
        self.conversation_log.append({
            "turn": len(self.conversation_log) + 1,
            "user": user,
            "sama": sama,
            **self.last_meta,
        })


# Gradio interface

def build_interface(sama: SamaChat) -> "gr.Blocks":
    import gradio as gr

    with gr.Blocks(title="Sama") as demo:

        gr.Markdown("# Sama")
        gr.Markdown("A compassionate companion — not a therapist, just a listener.")

        with gr.Row():
            # Left: chat area
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    label="",
                    height=520,
                    show_label=False,
                )
                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder="How are you feeling today?",
                        show_label=False,
                        lines=1,
                        scale=9,
                        autofocus=True,
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

            # Right: metadata panel
            with gr.Column(scale=1, min_width=200):
                gr.Markdown("### Session")
                memories_display = gr.Number(label="Memories retrieved", value=0, interactive=False)
                rag_display      = gr.Number(label="RAG chunks", value=0, interactive=False)
                safety_display   = gr.Textbox(label="Safety", value="—", interactive=False)
                latency_display  = gr.Number(label="Latency (ms)", value=0, interactive=False)

                gr.Markdown("### Actions")
                save_btn  = gr.Button("Save conversation")
                clear_btn = gr.Button("Clear / reset")
                save_status = gr.Textbox(
                    label="Saved to", value="", interactive=False, visible=True
                )

        # Streaming respond function
        def respond(message, chat_history):
            if not message.strip():
                yield "", chat_history, 0, 0, "—", 0
                return

            chat_history = chat_history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": ""},
            ]
            accumulated = ""

            for chunk in sama.stream(message):
                accumulated = chunk
                chat_history[-1]["content"] = accumulated
                meta = sama.last_meta
                yield (
                    "",
                    chat_history,
                    meta.get("memories_retrieved", 0),
                    meta.get("rag_chunks_retrieved", 0),
                    meta.get("safety_action", "—"),
                    meta.get("latency_ms", 0),
                )

        def save_conv():
            path = sama.save_conversation()
            return path if path else "Nothing to save yet."

        def clear_conv():
            sama.clear()
            return [], 0, 0, "—", 0, ""

        outputs = [msg_box, chatbot, memories_display, rag_display, safety_display, latency_display]

        msg_box.submit(respond, [msg_box, chatbot], outputs)
        send_btn.click(respond, [msg_box, chatbot], outputs)
        save_btn.click(save_conv, outputs=save_status)
        clear_btn.click(clear_conv, outputs=[chatbot, memories_display, rag_display,
                                             safety_display, latency_display, save_status])

    return demo


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--share",  action="store_true", help="Generate public Gradio link")
    parser.add_argument("--port",   type=int, default=7860, help="Port (default 7860)")
    parser.add_argument("--region", default="UK", choices=["UK", "US", "default"],
                        help="Crisis resource region")
    parser.add_argument("--user",   default="gradio_user", help="User ID for memory persistence")
    args = parser.parse_args()

    print(f"\nLoading Sama (region={args.region})...")
    sama = SamaChat(user_id=args.user, region=args.region)

    import gradio as gr
    demo = build_interface(sama)
    demo.queue()
    demo.launch(
        server_port=args.port,
        share=args.share,
        show_error=True,
        theme=gr.themes.Soft(),
    )


if __name__ == "__main__":
    main()

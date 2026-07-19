"""
Phase 7 — Voice Interface (Gradio 6 native, no FastRTC)
========================================================
FastRTC requires Gradio < 6.0 and is incompatible with Gradio 6.x.
This version uses Gradio 6's built-in audio + VAD instead.

UX: click mic once → speak → Gradio auto-stops when you go quiet → villain responds with audio.
No FastRTC, no WebRTC — pure Gradio 6.

Pipeline:
  Mic (click once) → auto-VAD stop → moonshine STT → VillainBot LLM → TTS → audio playback

TTS options (selectable in UI):
  - Kokoro        — fast, clean, ~1s (always available)
  - Chatterbox    — dramatic emotion control, ~2s (pip install chatterbox-tts)
  - Bark          — renders [laughs]/MUAHAHAHA theatrically, ~10s (needs torchaudio cu124)

Install:
    pip install faster-whisper kokoro
    pip install chatterbox-tts                                          # dramatic voice
    pip uninstall torchaudio -y && \\
      pip install torchaudio==2.6.0 --index-url \\
      https://download.pytorch.org/whl/cu124 && pip install bark       # theatrical voice

Run:
    python phase7_voice.py
    python phase7_voice.py --share
    python phase7_voice.py --port 8080
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

sys.path.insert(0, str(Path(__file__).parent.parent / "phase6"))
from phase6_serve import VillainBot  # noqa: E402

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

KOKORO_VOICE            = "bm_george"
KOKORO_LANG             = "b"
KOKORO_SPEED            = 0.92
BARK_VOICE              = "v2/en_speaker_6"
CHATTERBOX_EXAGGERATION = 0.9
CHATTERBOX_CFG_WEIGHT   = 0.5
SAMPLE_RATE             = 24000


# ── Availability checks ───────────────────────────────────────────────────────

def _check(pkg: str) -> bool:
    try:
        __import__(pkg)
        return True
    except (ImportError, OSError):
        return False


BARK_AVAILABLE       = _check("bark")
CHATTERBOX_AVAILABLE = _check("chatterbox")

if not BARK_AVAILABLE:
    print("  Bark not available. Fix: pip uninstall torchaudio -y && "
          "pip install torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124"
          " && pip install bark", flush=True)
if not CHATTERBOX_AVAILABLE:
    print("  Chatterbox not available. Install: pip install chatterbox-tts", flush=True)


# ── TTS loaders ───────────────────────────────────────────────────────────────

_kokoro_pipeline  = None
_bark_loaded      = False
_chatterbox_model = None
_whisper_model    = None


def _load_kokoro():
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        print("Loading Kokoro TTS...", flush=True)
        from kokoro import KPipeline
        _kokoro_pipeline = KPipeline(lang_code=KOKORO_LANG)
        print("  Kokoro ready.", flush=True)
    return _kokoro_pipeline


def _load_bark():
    global _bark_loaded
    if not _bark_loaded:
        import torch
        print("Loading Bark (~1GB first run)...", flush=True)
        # PyTorch 2.6 changed torch.load default to weights_only=True;
        # Bark's checkpoints contain numpy globals and fail unless we override.
        _orig_load = torch.load
        torch.load = lambda *a, **kw: _orig_load(*a, **{**kw, "weights_only": False})
        try:
            from bark import preload_models
            preload_models()
        finally:
            torch.load = _orig_load
        _bark_loaded = True
        print("  Bark ready.", flush=True)


def _load_chatterbox():
    global _chatterbox_model
    if _chatterbox_model is None:
        import torch
        from chatterbox.tts import ChatterboxTTS
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading Chatterbox TTS ({device})...", flush=True)
        _chatterbox_model = ChatterboxTTS.from_pretrained(device=device)
        print("  Chatterbox ready.", flush=True)
    return _chatterbox_model


def _load_whisper():
    global _whisper_model
    if _whisper_model is None:
        import torch
        from faster_whisper import WhisperModel
        device  = "cuda" if torch.cuda.is_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        print(f"Loading Whisper STT ({device})...", flush=True)
        _whisper_model = WhisperModel("base", device=device, compute_type=compute)
        print("  Whisper ready.", flush=True)
    return _whisper_model


# ── STT ───────────────────────────────────────────────────────────────────────

def transcribe(audio_tuple: tuple) -> str:
    if audio_tuple is None:
        return ""
    sample_rate, audio = audio_tuple

    if audio.dtype != np.float32:
        audio = audio.astype(np.float32) / 32768.0
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # resample to 16kHz using scipy (no torchaudio dependency)
    if sample_rate != 16000:
        from scipy.signal import resample_poly
        import math
        gcd = math.gcd(16000, sample_rate)
        audio = resample_poly(audio, 16000 // gcd, sample_rate // gcd)

    model    = _load_whisper()
    segments, _ = model.transcribe(audio, beam_size=5, language="en")
    return " ".join(s.text.strip() for s in segments).strip()


# ── TTS ───────────────────────────────────────────────────────────────────────

def synthesise_kokoro(text: str) -> tuple:
    pipeline = _load_kokoro()
    chunks = [a for _, _, a in pipeline(text, voice=KOKORO_VOICE, speed=KOKORO_SPEED)]
    audio  = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
    return (SAMPLE_RATE, audio)


def synthesise_bark(text: str) -> tuple:
    _load_bark()
    from bark import SAMPLE_RATE as SR, generate_audio
    bark_text = (
        text
        .replace("MUAHAHAHA", "MUAHAHAHA [laughs]")
        .replace("MWAHAHAHA", "MWAHAHAHA [laughs]")
    )
    return (SR, generate_audio(bark_text, history_prompt=BARK_VOICE))


def synthesise_chatterbox(text: str) -> tuple:
    model = _load_chatterbox()
    wav   = model.generate(text,
                           exaggeration=CHATTERBOX_EXAGGERATION,
                           cfg_weight=CHATTERBOX_CFG_WEIGHT)
    audio = wav.squeeze().cpu().numpy().astype(np.float32)
    return (model.sr, audio)


def synthesise(text: str, engine: str) -> tuple:
    if "Bark"        in engine: return synthesise_bark(text)
    if "Chatterbox"  in engine: return synthesise_chatterbox(text)
    return synthesise_kokoro(text)


# ── Gradio UI ─────────────────────────────────────────────────────────────────

def build_ui(bot: VillainBot):
    import gradio as gr

    # build TTS choices from what's actually installed
    tts_choices = ["Kokoro (Fast)"]
    if CHATTERBOX_AVAILABLE:
        tts_choices.append("Chatterbox (Dramatic)")
    if BARK_AVAILABLE:
        tts_choices.append("Bark (Theatrical)")

    tts_info = (
        "Kokoro: fast ~1s | Chatterbox: villain emotion dial ~2s | Bark: MUAHAHAHA laughs ~10s"
        if len(tts_choices) > 1
        else "Only Kokoro available. Install chatterbox-tts or fix torchaudio for more options."
    )

    # JS: after VILLAINBOT audio finishes playing, auto-click the mic record button
    # so the conversation continues without the user needing to click again.
    auto_listen_js = """
    () => {
        const restartMic = () => {
            // look for the record button inside the mic component
            const micWrap = document.querySelector('#mic_input');
            if (!micWrap) return;
            // Gradio 6 mic button is a button with a microphone icon
            const btn = micWrap.querySelector('button');
            if (btn) btn.click();
        };

        const attachEndListener = () => {
            const outWrap = document.querySelector('#audio_out');
            if (!outWrap) return;
            const audioEl = outWrap.querySelector('audio');
            if (audioEl && !audioEl.dataset.villainListening) {
                audioEl.dataset.villainListening = '1';
                audioEl.addEventListener('ended', () => {
                    const autoBox = document.querySelector('#auto_listen_cb input');
                    if (autoBox && autoBox.checked) {
                        setTimeout(restartMic, 400);
                    }
                });
            }
        };

        // re-attach whenever DOM changes (new audio element created)
        new MutationObserver(attachEndListener)
            .observe(document.body, {childList: true, subtree: true});
        attachEndListener();
    }
    """

    with gr.Blocks(title="VILLAINBOT — Voice", js=auto_listen_js) as demo:

        gr.Markdown("# VILLAINBOT — Voice Mode")
        gr.Markdown(
            "*Click the mic, speak your pathetic request, "
            "then pause — I will hear you. If Auto-listen is on, I will keep listening. MUAHAHAHA.*"
        )

        with gr.Row():
            # left — chat + audio
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(height=380, label="")

                mic_input = gr.Audio(
                    sources=["microphone"],
                    type="numpy",
                    label="🎤 Click to speak — auto-stops when you pause",
                    elem_id="mic_input",
                )

                audio_out = gr.Audio(
                    label="VILLAINBOT speaks",
                    autoplay=True,
                    interactive=False,
                    elem_id="audio_out",
                )

                # text input as fallback
                with gr.Row():
                    text_in  = gr.Textbox(placeholder="Or type here...", show_label=False, scale=9)
                    text_btn = gr.Button("TRANSMIT", variant="primary", scale=1)

            # right — controls
            with gr.Column(scale=1, min_width=200):
                gr.Markdown("### VOICE ENGINE")
                tts_choice = gr.Radio(
                    choices=tts_choices,
                    value=tts_choices[0],
                    label="TTS",
                    info=tts_info,
                )

                gr.Markdown("### SESSION")
                transcript_box  = gr.Textbox(label="Heard",    value="", interactive=False)
                turn_display    = gr.Number( label="Turn",      value=0,  interactive=False)
                latency_display = gr.Number( label="Latency ms",value=0,  interactive=False)

                gr.Markdown("### CONTROLS")
                auto_listen = gr.Checkbox(
                    label="Auto-listen after response",
                    value=True,
                    info="Re-activates mic automatically after each response",
                    elem_id="auto_listen_cb",
                )
                clear_btn = gr.Button("ABANDON SESSION", variant="stop")
                save_btn  = gr.Button("SAVE INTEL FILE")
                save_out  = gr.Textbox(label="Saved to", value="", interactive=False)

        # ── handlers ──────────────────────────────────────────────────────────

        def handle_voice(audio, engine, chat_history):
            if audio is None:
                return chat_history, None, "", 0, 0

            import time
            t0 = time.time()

            transcript = transcribe(audio)
            if not transcript:
                return chat_history, None, "(no speech detected)", 0, 0

            response, _ = bot.chat(transcript)
            audio_data  = synthesise(response, engine)
            latency     = round((time.time() - t0) * 1000)

            chat_history = chat_history + [
                {"role": "user",      "content": f"🎤 {transcript}"},
                {"role": "assistant", "content": response},
            ]
            return chat_history, audio_data, transcript, len(bot.history) // 2, latency

        def handle_text(text, engine, chat_history):
            if not text.strip():
                return "", chat_history, None, "", 0, 0

            import time
            t0 = time.time()

            response, _ = bot.chat(text)
            audio_data  = synthesise(response, engine)
            latency     = round((time.time() - t0) * 1000)

            chat_history = chat_history + [
                {"role": "user",      "content": text},
                {"role": "assistant", "content": response},
            ]
            return "", chat_history, audio_data, "", len(bot.history) // 2, latency

        def clear_session():
            bot.clear()
            return [], None, "", 0, 0, ""

        def save_session():
            path = bot.save()
            return path if path else "Nothing to save yet."

        voice_outs = [chatbot, audio_out, transcript_box, turn_display, latency_display]
        text_outs  = [text_in, chatbot, audio_out, transcript_box, turn_display, latency_display]

        # fire when recording stops (Gradio 6 built-in VAD auto-stops on silence)
        mic_input.stop_recording(handle_voice, [mic_input, tts_choice, chatbot], voice_outs)

        text_in.submit(handle_text,  [text_in, tts_choice, chatbot], text_outs)
        text_btn.click( handle_text,  [text_in, tts_choice, chatbot], text_outs)

        clear_btn.click(
            clear_session,
            outputs=[chatbot, audio_out, transcript_box, turn_display, latency_display, save_out],
        )
        save_btn.click(save_session, outputs=save_out)

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="VILLAINBOT Phase 7 — Voice")
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--port",  type=int, default=7860)
    args = parser.parse_args()

    print("\nLoading VILLAINBOT (voice mode)...")
    bot  = VillainBot()
    demo = build_ui(bot)

    demo.queue()
    demo.launch(server_port=args.port, share=args.share, show_error=True)


if __name__ == "__main__":
    main()

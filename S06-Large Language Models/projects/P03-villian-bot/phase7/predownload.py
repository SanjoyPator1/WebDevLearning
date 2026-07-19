"""
Pre-download all inference-time models so the UI starts instantly.
Run once:  python phase7/predownload.py
After this, everything is cached locally — no downloads on server start or TTS use.

Cache locations:
  Whisper / Kokoro / HF models  →  ~/.cache/huggingface/hub/
  Bark                          →  ~/.cache/suno/bark_v0/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "phase6"))

def dl_whisper():
    print("Downloading Whisper base...")
    import torch
    from faster_whisper import WhisperModel
    device  = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    WhisperModel("base", device=device, compute_type=compute)
    print("  Whisper cached.")

def dl_kokoro():
    print("Downloading Kokoro TTS...")
    from kokoro import KPipeline
    KPipeline(lang_code="b")
    print("  Kokoro cached.")

def dl_bark():
    print("Downloading Bark models (~6GB total, first run only)...")
    import torch
    _orig = torch.load
    torch.load = lambda *a, **kw: _orig(*a, **{**kw, "weights_only": False})
    try:
        from bark import preload_models
        preload_models()
    finally:
        torch.load = _orig
    print("  Bark cached.")

def dl_chatterbox():
    print("Downloading Chatterbox TTS...")
    import torch
    from chatterbox.tts import ChatterboxTTS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    ChatterboxTTS.from_pretrained(device=device)
    print("  Chatterbox cached.")

def _available(pkg):
    try:
        __import__(pkg)
        return True
    except (ImportError, OSError):
        return False

if __name__ == "__main__":
    dl_whisper()
    dl_kokoro()
    if _available("bark"):
        dl_bark()
    else:
        print("  Bark not installed — skipping.")
    if _available("chatterbox"):
        dl_chatterbox()
    else:
        print("  Chatterbox not installed — skipping.")
    print("\nAll models cached. Server will start instantly from now on.")

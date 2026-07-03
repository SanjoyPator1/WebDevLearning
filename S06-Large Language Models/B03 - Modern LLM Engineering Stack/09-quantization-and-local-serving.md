# Topic 9 — Quantization & Local Serving

## Why This Topic

You have an RTX A6000 with 94GB RAM — local inference of 7B-70B class models
is very feasible, but only if you understand the serving stack: how
quantization (GGUF formats, 4-bit/8-bit) trades memory for precision, and how
serving engines (Ollama for ease, vLLM for throughput) differ in what they
optimize for. This is also what makes Topics 1-8 cheap to iterate on — running
a local model instead of paying per-token API costs while developing.

## Prerequisites

None strictly, but conceptually follows from B01's training/fine-tuning
chapters (you already know what model weights *are*; this is about
compressing and serving them).

## Outline

1. **Why Quantize** — model size vs available VRAM; the precision formats
   (FP32 → FP16/BF16 → INT8 → INT4) and what "4-bit quantization" actually
   stores (dry-run: quantize a small weight tensor to 4-bit and dequantize,
   compute the error).
2. **GGUF & llama.cpp** — the GGUF file format, quantization schemes within
   it (Q4_K_M, Q5_K_M, etc.), and running a GGUF model with llama.cpp directly
   to see the raw inference loop.
3. **Ollama** — Ollama as a llama.cpp wrapper with a model registry and simple
   API; pulling a model, the `Modelfile` format for customizing
   system prompts/parameters, and hitting its OpenAI-compatible API endpoint
   (which is what Topic 1's "local model" examples will use).
4. **vLLM & Continuous Batching** — why vLLM exists (throughput for serving
   many concurrent requests via PagedAttention and continuous batching) vs
   Ollama (single-user convenience); when each is the right choice.
5. **Benchmarking on the A6000** — measuring tokens/sec and VRAM usage for the
   same model at different quantization levels (e.g. Q4 vs Q8 vs FP16) to
   build intuition for the speed/quality tradeoff on your actual hardware.
6. **Serving for Agents** — exposing a local model behind an OpenAI-compatible
   endpoint so every framework from Topics 1-8 (which expect an OpenAI-style
   API) can point at it interchangeably with cloud models.

## Planned Deliverables

- `code/template/quantization-and-local-serving.ipynb` — sections 1, 5
  (benchmarking) built as runnable cells; sections 2-4 documented as
  setup/CLI steps with a notebook cell that calls the resulting local
  endpoint; **exercise cells** for section 6 (point a Topic 1 LCEL chain at
  the local Ollama/vLLM endpoint and confirm it works identically to the API
  model).
- `code/solutions/` — copy of the template.
- `notes/09-quantization-and-local-serving.md` — the quantize/dequantize
  dry-run from section 1, plus a benchmark table from section 5 with your
  actual A6000 numbers.

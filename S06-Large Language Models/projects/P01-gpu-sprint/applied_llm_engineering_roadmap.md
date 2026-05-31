# Applied LLM Engineering — Detailed Learning Roadmap
**Companion to:** `01_15_day_gpu_plan.md`  
**Purpose:** Turn the sprint plan into structured learning — not just running experiments, but understanding why each technique exists and what it teaches you.

---

## Table of Contents

- [How to Use This File](#how-to-use-this-file)
- [Pre-Day-1 Checklist](#pre-day-1-checklist)
  - [Accounts](#accounts)
  - [Environment](#environment)
  - [Tool installs](#tool-installs-from-sprint-plan-day-1-reference)
  - [Create your log file](#create-your-log-file)
- [Phase 1 — Days 1–3: Setup and Run Big Models](#phase-1--days-13-setup-and-run-big-models)
  - [Day 1 — Environment Setup + Run 70B Models](#day-1--environment-setup--run-70b-models)
  - [Day 2 — Train GPT-2 Scale Properly](#day-2--train-gpt-2-scale-properly)
  - [Day 3 — Quantization Deep Dive](#day-3--quantization-deep-dive)
- [Phase 2 — Days 4–7: Fine-tuning Techniques](#phase-2--days-47-fine-tuning-techniques)
  - [Day 4 — LoRA from Scratch, then with PEFT](#day-4--lora-from-scratch-then-with-peft)
  - [Day 5 — QLoRA: Fine-tune a 30B Model](#day-5--qlora-fine-tune-a-30b-model)
  - [Day 6 — DPO: Preference Alignment Without PPO](#day-6--dpo-preference-alignment-without-ppo)
  - [Day 7 — GRPO: Train a Reasoning Model](#day-7--grpo-train-a-reasoning-model)
- [Phase 3 — Days 8–11: RAG, Agents, and Multimodal](#phase-3--days-811-rag-agents-and-multimodal)
  - [Day 8 — Advanced RAG](#day-8--advanced-rag)
  - [Day 9 — Agentic Systems](#day-9--agentic-systems)
  - [Day 10 — Multimodal: Fine-tune a Vision-Language Model](#day-10--multimodal-fine-tune-a-vision-language-model)
  - [Day 11 — Model Merging](#day-11--model-merging)
- [Phase 4 — Days 12–15: Inference Optimization and Full Project](#phase-4--days-1215-inference-optimization-and-full-project)
  - [Day 12 — Fast Inference: vLLM, Speculative Decoding, and KV Cache](#day-12--fast-inference-vllm-speculative-decoding-and-kv-cache)
  - [Day 13 — Embedding Fine-tuning and BERTopic at Scale](#day-13--embedding-fine-tuning-and-bertopic-at-scale)
  - [Day 14 — Pre-training from Scratch on a Custom Domain](#day-14--pre-training-from-scratch-on-a-custom-domain)
  - [Day 15 — Full End-to-End Project](#day-15--full-end-to-end-project)
- [Running Comparison Table](#running-comparison-table)
- [Resources Index](#resources-index)

---

## How to Use This File

`01_15_day_gpu_plan.md` tells you **what** to do each day.  
This file tells you **how to learn it well**.

Each day follows the same rhythm:
1. **Theory first** — read before you code. Know what you're building toward.
2. **Concept map** — define the key terms in your own words before running anything.
3. **Step-by-step experiment** — more granular than the sprint plan; numbered steps.
4. **Log it** — specific measurements to record into your running comparison table (end of this file).
5. **Reflect** — three questions to write answers to before bed. This is the most skippable step and the most important one.
6. **Connect** — how today feeds into tomorrow.

**Time budget:** Follow the sprint plan's suggested daily blocks. The theory read fits in the morning block. The reflection fits in the evening block.

---

## Pre-Day-1 Checklist

Do this the evening before Day 1 starts. It should take 1–2 hours.

### Accounts
- [ ] Create a [Weights & Biases](https://wandb.ai) account — you'll need the API key on Day 2
- [ ] Create or log in to your HuggingFace account — you'll need tokens to download gated models (Llama-3)
- [ ] Request access to `meta-llama/Meta-Llama-3.3-70B` on HuggingFace (approval can take hours — do this now)
- [ ] Request access to any other gated models you plan to use (Mistral, Qwen are usually open)

### Environment
```bash
# Verify GPU is visible
nvidia-smi
python -c "import torch; print(torch.cuda.get_device_properties(0))"

# Check VRAM — should show ~48 GB
python -c "import torch; print(f'{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')"

# Create a project directory
mkdir -p ~/gpu-sprint/{logs,checkpoints,notebooks,data}
```

### Tool installs (from sprint plan Day 1 reference)
```bash
pip install transformers datasets peft trl bitsandbytes accelerate
pip install auto-gptq autoawq
pip install flash-attn --no-build-isolation
pip install vllm
pip install sentence-transformers bertopic umap-learn hdbscan
pip install mergekit
pip install wandb
pip install unsloth
pip install ragatouille
```

### Create your log file
Open `~/gpu-sprint/logs/daily_log.md` — use it every day for the evening reflection.

---

---

## Phase 1 — Days 1–3: Setup and Run Big Models

**Phase goal:** Understand the scale of what you have access to, build intuition about VRAM and precision tradeoffs, and see how quantization affects quality.

---

### Day 1 — Environment Setup + Run 70B Models

**Learning objective:** By end of day, understand how model size, precision, and VRAM usage relate — and feel the speed of a 70B model running locally.

---

#### Morning theory (45 min)

**Read:** Llama 2 paper (Touvron et al. 2023, "Llama 2: Open Foundation and Fine-Tuned Chat Models") — just the abstract and Sections 1–2 (motivation and model architecture). Skip the fine-tuning sections for now.

**Focus question to answer:** *Why does a 70B model in fp16 need ~140 GB VRAM? Work out the math: 70 billion parameters × 2 bytes/param = ? GB. Where does the rest of the VRAM go during inference?*

Write your answer in the daily log before you open a terminal.

---

#### Concept map — define these before coding

| Term | Your definition (fill in) |
|---|---|
| VRAM vs RAM | |
| fp16 / bf16 / fp32 | |
| 4-bit quantization (Q4_K_M) | |
| tokens/sec | |
| KV cache | |

---

#### Step-by-step experiment

**Step 1 — Run 70B via Ollama**
```bash
ollama pull llama3.3:70b-instruct-q4_K_M
ollama run llama3.3:70b-instruct-q4_K_M "Explain the difference between attention and FFN layers in a transformer."
```
Note the time to first token, subjective response quality.

**Step 2 — Run 7B for comparison**
```bash
ollama pull llama3.2:7b
ollama run llama3.2:7b "Explain the difference between attention and FFN layers in a transformer."
```
Same prompt. Same question answered faster? Quality difference?

**Step 3 — Load via HuggingFace at different precisions**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch, time

model_id = "meta-llama/Meta-Llama-3.3-70B-Instruct"

for load_in_bits in [4, 8]:
    from transformers import BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(load_in_4bit=(load_in_bits == 4), load_in_8bit=(load_in_bits == 8))
    model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device_map="auto")
    
    # Check VRAM
    print(f"{load_in_bits}-bit VRAM: {torch.cuda.memory_allocated() / 1e9:.1f} GB")
    
    # Time a generation
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    inputs = tokenizer("What is attention in a transformer?", return_tensors="pt").to("cuda")
    t0 = time.time()
    out = model.generate(**inputs, max_new_tokens=100)
    t1 = time.time()
    tokens = out.shape[1] - inputs["input_ids"].shape[1]
    print(f"{load_in_bits}-bit: {tokens / (t1 - t0):.1f} tokens/sec")
    
    del model
    torch.cuda.empty_cache()
```

**Step 4 — Run Qwen3-32B comparison**
```bash
ollama pull qwen3:32b
ollama run qwen3:32b "What is the capital of France? Explain your reasoning."
```
Compare output quality and speed against 70B.

---

#### What to log (fill into running table)

| | 70B Q4_K_M | 70B 4-bit HF | 70B 8-bit HF | 7B Q4 | 32B Q4 |
|---|---|---|---|---|---|
| VRAM used | | | | | |
| Tokens/sec | | | | | |
| Qualitative quality (1–5) | | | | | |

---

#### Evening reflection

Write answers to these in your daily log:

1. *At what point does quantization start visibly hurting quality? Did you notice any difference between 4-bit and 8-bit outputs?*
2. *You ran a 70B model. Six months ago this required a data center. What does that change about what you can build?*
3. *What surprised you today? What didn't work the way you expected?*

---

#### Connection

Tomorrow (Day 2) you'll train GPT-2 scale from scratch. Today's 70B experience gives you the endpoint — tomorrow you understand the training process that creates these models. The FlashAttention-2 you'll install tomorrow is what makes training at scale possible.

---

---

### Day 2 — Train GPT-2 Scale Properly

**Learning objective:** Understand the full training loop — data → tokenization → forward pass → loss → backward pass → optimizer step — and how FlashAttention-2 and mixed precision change the memory math.

---

#### Morning theory (60 min)

**Read:** FlashAttention-2 paper (Dao, 2023, "FlashAttention-2: Faster Attention with Better Parallelism and Work Partitioning") — just the introduction and Section 2 (background). The key insight: naive attention is memory-bandwidth-bound, not compute-bound.

**Read also:** The WandB documentation page on logging metrics — you'll be setting this up today.

**Focus question:** *Standard attention computes a full N×N attention matrix. For a 2048-token sequence, how many elements is that? FlashAttention-2 avoids materialising this matrix — how does that save memory?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Gradient accumulation | |
| bf16 mixed precision | |
| Gradient checkpointing | |
| Tokens/sec (training) | |
| Learning rate schedule (cosine) | |
| FlashAttention-2 (core idea) | |

---

#### Step-by-step experiment

**Step 1 — Verify FlashAttention-2 installs and works**
```python
import torch
from flash_attn import flash_attn_qkvpacked_func
print("FlashAttention-2 available:", torch.cuda.is_available())
```

**Step 2 — Set up WandB**
```bash
wandb login  # paste your API key
```

**Step 3 — Baseline: train without FlashAttention-2**

Use your existing LLM-from-Scratch architecture (or a clean GPT-2 implementation). Train for 200 steps. Record VRAM and tokens/sec.

```python
import wandb
wandb.init(project="gpu-sprint-day2", name="baseline-no-flash")

# Log at each step
wandb.log({"loss": loss.item(), "tokens_per_sec": tokens_per_sec, "vram_gb": torch.cuda.memory_allocated()/1e9})
```

**Step 4 — Swap in FlashAttention-2, retrain same 200 steps**

Replace the attention computation in your model with `flash_attn_func`. Log the same metrics. The difference in tokens/sec and VRAM is your FlashAttention-2 gain.

**Step 5 — Enable bf16 mixed precision**
```python
from torch.amp import autocast, GradScaler
scaler = GradScaler()

with autocast(device_type='cuda', dtype=torch.bfloat16):
    loss = model(inputs, labels=targets)

scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

**Step 6 — Load FineWeb-Edu and train for a few thousand steps**
```python
from datasets import load_dataset
ds = load_dataset("HuggingFaceFW/fineweb-edu", name="sample-10BT", split="train", streaming=True)
```
Train until you see coherent word patterns. Log loss curve in WandB.

**Step 7 — Inspect generated text at steps 500, 1000, 2000**

Save checkpoints and generate at each. Watch the transition from gibberish to structured English.

---

#### What to log

| | No FlashAttn | With FlashAttn | With bf16 |
|---|---|---|---|
| VRAM (GB) | | | |
| Tokens/sec | | | |
| Training loss @ 1000 steps | | | |

---

#### Evening reflection

1. *FlashAttention-2 improved your tokens/sec by how much? Where does that speedup actually come from — is it compute or memory bandwidth?*
2. *At step 500, what did the model generate? At step 2000? What does that tell you about what early training learns?*
3. *What would happen if you forgot to use `scaler.unscale_()` before gradient clipping in bf16 training?*

---

#### Connection

Day 1 showed you the endpoint (running big models). Day 2 showed you the training process. Day 3 shows what happens when you compress the endpoint back down — quantization as the bridge between training-time and inference-time realities.

---

---

### Day 3 — Quantization Deep Dive

**Learning objective:** Understand the tradeoff space of quantization — bits vs. perplexity vs. speed — and know which method to reach for in which situation.

---

#### Morning theory (45 min)

**Read:** GPTQ paper (Frantar et al. 2022, "GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers") — just the intro and Section 3.1 (the core OBQ insight). Then read the AWQ paper abstract (Lin et al. 2023, "AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration").

**Focus question:** *GPTQ quantizes layer by layer using the Hessian. AWQ protects "salient" weights based on activation magnitude. What's the fundamental difference in what each method is trying to preserve?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Perplexity | |
| INT4 / NF4 | |
| GPTQ (approach in 1 sentence) | |
| AWQ (approach in 1 sentence) | |
| GGUF format | |
| Double quantization (bitsandbytes) | |

---

#### Step-by-step experiment

**Step 1 — Get baseline perplexity on wikitext-2**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from datasets import load_dataset

model_id = "mistralai/Mistral-7B-v0.1"
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="auto")

# Compute perplexity on wikitext-2
# (standard eval loop — compute mean log-likelihood over held-out text)
```
Record: model size on disk, VRAM usage, perplexity.

**Step 2 — Quantize with GPTQ**
```python
from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig

quantize_config = BaseQuantizeConfig(bits=4, group_size=128)
model = AutoGPTQForCausalLM.from_pretrained(model_id, quantize_config)
examples = [...]  # calibration data (128 samples from wikitext)
model.quantize(examples)
model.save_quantized("mistral-7b-gptq-4bit")
```
Record: model size on disk, VRAM, perplexity.

**Step 3 — Quantize with AWQ**
```python
from awq import AutoAWQForCausalLM

model = AutoAWQForCausalLM.from_pretrained(model_id)
model.quantize(tokenizer, quant_config={"zero_point": True, "q_group_size": 128, "w_bit": 4})
model.save_quantized("mistral-7b-awq-4bit")
```
Record: model size on disk, VRAM, perplexity.

**Step 4 — Convert to GGUF and run with llama.cpp**
```bash
# After converting the model
./llama.cpp/llama-perplexity -m mistral-7b-q4_k_m.gguf -f wikitext2.txt
```

**Step 5 — Compare NF4 double quantization**
```python
from transformers import BitsAndBytesConfig
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16
)
model = AutoModelForCausalLM.from_pretrained(model_id, quantization_config=bnb_config, device_map="auto")
```
Compute perplexity. Record VRAM.

---

#### What to log

| | fp16 baseline | GPTQ 4-bit | AWQ 4-bit | GGUF Q4_K_M | NF4 double |
|---|---|---|---|---|---|
| Model size (GB) | | | | | |
| VRAM (GB) | | | | | |
| Perplexity (wikitext-2) | | | | | |
| Tokens/sec | | | | | |

---

#### Evening reflection

1. *Which quantization method preserved quality best at 4-bit? What's your hypothesis for why?*
2. *NF4 is "normal float 4" — the quantization grid is designed for normally distributed weights. Why would this be better than uniform INT4 for transformer weights?*
3. *After GPU access ends, which format will you use? What's your reasoning?*

---

#### Phase 1 Checkpoint

Answer these without looking at notes:

- A 13B model in fp16 needs approximately how much VRAM?
- What is the difference between GPTQ and AWQ at a conceptual level?
- What is perplexity measuring, and why does lower = better?
- Why does FlashAttention-2 save memory during training?
- Why does the KV cache grow with sequence length?

---

---

## Phase 2 — Days 4–7: Fine-tuning Techniques

**Phase goal:** Understand the full fine-tuning stack — from LoRA's mathematical foundation through supervised fine-tuning, preference alignment with DPO, and reasoning training with GRPO.

---

### Day 4 — LoRA from Scratch, then with PEFT

**Learning objective:** Understand why LoRA works — the low-rank hypothesis — and be able to explain the math of the adapter without referencing the library.

---

#### Morning theory (45 min)

**Read:** LoRA paper (Hu et al. 2021, "LoRA: Low-Rank Adaptation of Large Language Models") — Sections 1, 2, and 4.1. Focus on the reparametrization: `h = Wx + BAx`, where B and A are the low-rank adapter matrices.

**Focus question:** *Why does LoRA freeze W and only train B and A? What is the "low-rank" hypothesis about the nature of fine-tuning updates?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Low-rank matrix | |
| LoRA rank (r) | |
| Alpha scaling | |
| Target modules | |
| Adapter merge | |
| Trainable parameters (% of total) | |

---

#### Step-by-step experiment

**Step 1 — Implement LoRALinear from scratch**
```python
import torch
import torch.nn as nn
import math

class LoRALinear(nn.Module):
    def __init__(self, in_features, out_features, r=8, alpha=16):
        super().__init__()
        self.r = r
        self.alpha = alpha
        self.scale = alpha / r
        
        # Frozen base weight
        self.weight = nn.Parameter(torch.randn(out_features, in_features), requires_grad=False)
        
        # LoRA adapters — A initialized randomly, B initialized to zero
        self.lora_A = nn.Parameter(torch.randn(r, in_features) * (1 / math.sqrt(in_features)))
        self.lora_B = nn.Parameter(torch.zeros(out_features, r))
    
    def forward(self, x):
        base = x @ self.weight.T
        lora = x @ self.lora_A.T @ self.lora_B.T
        return base + self.scale * lora
```

**Step 2 — Verify gradients only flow through A and B**
```python
layer = LoRALinear(512, 512)
x = torch.randn(1, 512)
out = layer(x).sum()
out.backward()

print("weight grad:", layer.weight.grad)      # should be None
print("lora_A grad:", layer.lora_A.grad)      # should have values
print("lora_B grad:", layer.lora_B.grad)      # should have values
```

**Step 3 — Replace attention projections in a small model with your LoRALinear**

Take a 2-layer GPT architecture. Swap out the Q, K, V projection layers. Verify the model still runs forward.

**Step 4 — Switch to PEFT library and fine-tune Mistral-7B**
```python
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer
from datasets import load_dataset

lora_config = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"], lora_dropout=0.05)

model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1", torch_dtype=torch.bfloat16, device_map="auto")
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()  # record this number

dataset = load_dataset("yahma/alpaca-cleaned", split="train")

trainer = SFTTrainer(model=model, train_dataset=dataset, max_seq_length=512, ...)
trainer.train()
```

**Step 5 — Experiment with different ranks**

Run three short training runs (200 steps each): r=8, r=16, r=64. Record VRAM usage, training speed, and qualitative output quality.

**Step 6 — Merge the adapter back into base model**
```python
from peft import PeftModel

model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-v0.1", ...)
model = PeftModel.from_pretrained(model, "lora-checkpoint")
merged = model.merge_and_unload()
merged.save_pretrained("mistral-7b-lora-merged")
```
Verify the merged model generates sensible output.

---

#### What to log

| | r=8 | r=16 | r=64 |
|---|---|---|---|
| Trainable params (%) | | | |
| VRAM (GB) | | | |
| Training speed (samples/sec) | | | |
| Output quality (1–5 subjective) | | | |

---

#### Evening reflection

1. *Why is lora_B initialized to zero while lora_A is initialized with random values? What would happen if both started random?*
2. *At what rank does quality stop improving noticeably? What does that suggest about the "intrinsic dimensionality" of the fine-tuning update?*
3. *After merging, the model has the same number of parameters as the base model. Where did the LoRA benefit go?*

---

---

### Day 5 — QLoRA: Fine-tune a 30B Model

**Learning objective:** Understand how QLoRA stacks quantization (to reduce memory for the frozen weights) with LoRA (to train adapters in full precision) — and why this combination is not obvious.

---

#### Morning theory (45 min)

**Read:** QLoRA paper (Dettmers et al. 2023, "QLoRA: Efficient Finetuning of Quantized LLMs") — Sections 1–3. The key contribution is not just "LoRA on quantized model" — it's the NF4 data type, double quantization, and paged optimizers.

**Focus question:** *QLoRA trains adapters in bf16 while the base weights are in NF4. How does this work computationally — if the base weights are quantized, how can you compute gradients through them to update the adapters?*

---

#### Concept map

| Term | Your definition |
|---|---|
| NF4 (normal float 4) | |
| Double quantization | |
| Paged AdamW | |
| Gradient checkpointing | |
| Dequantization during forward pass | |

---

#### Step-by-step experiment

**Step 1 — Load a 30B model in 4-bit**
```python
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-32B",     # or Llama-3-30B if available
    quantization_config=bnb_config,
    device_map="auto"
)
print(f"VRAM loaded: {torch.cuda.memory_allocated() / 1e9:.1f} GB")
```

**Step 2 — Add LoRA adapters**
```python
from peft import prepare_model_for_kbit_training, LoraConfig, get_peft_model

model = prepare_model_for_kbit_training(model)
lora_config = LoraConfig(r=64, lora_alpha=128, target_modules="all-linear", lora_dropout=0.05)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
```

**Step 3 — Choose a domain dataset and fine-tune**

Pick one: medical QA (`medalpaca/medical_meadow_medqa`), code (`iamtarun/python_code_instructions_18k_alpaca`), or a topic relevant to you.

```python
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=SFTConfig(
        output_dir="qlora-30b",
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        optim="paged_adamw_32bit",
        bf16=True,
        max_steps=500,
    )
)
trainer.train()
```

**Step 4 — Evaluate before and after on 20 held-out samples**

Create 20 test prompts from your dataset. Generate with the base model and the fine-tuned model. Rate: does the fine-tuned model actually know more about your domain?

**Step 5 — Compare memory with gradient_checkpointing on vs off**

Run 10 steps with and without, record peak VRAM.

---

#### What to log

| | 30B NF4 loaded | During training | Peak VRAM |
|---|---|---|---|
| VRAM (GB) | | | |
| Trainable params (%) | | | |
| Training speed | | | |

---

#### Evening reflection

1. *Paged AdamW moves optimizer states to CPU RAM and pages them to GPU when needed. When would this not help — i.e., when is the bottleneck not optimizer state memory?*
2. *You fine-tuned a 30B model on a single GPU. What would have been required to do this 2 years ago?*
3. *Did your domain evaluation show improvement? If not, what would you try differently?*

---

---

### Day 6 — DPO: Preference Alignment Without PPO

**Learning objective:** Understand why DPO is simpler than PPO and what the β parameter controls — and develop intuition for what "alignment" means in practice.

---

#### Morning theory (45 min)

**Read:** DPO paper (Rafailov et al. 2023, "Direct Preference Optimization: Your Language Model is Secretly a Reward Model") — Sections 1–4. The key math: DPO reparametrizes the reward model to be implicit in the policy, eliminating the need to train a separate reward model.

**Focus question:** *In PPO, you train a reward model and then optimize the policy against it. In DPO, there is no explicit reward model — what serves that role? Where does the reward signal come from?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Chosen/rejected pairs | |
| KL divergence from reference policy | |
| β (beta) in DPO | |
| Reference model (frozen copy) | |
| Policy model | |
| Log-ratio in DPO objective | |

---

#### Step-by-step experiment

**Step 1 — Load a preference dataset**
```python
from datasets import load_dataset

# HH-RLHF: human-written chosen/rejected pairs
ds = load_dataset("Anthropic/hh-rlhf", split="train")
# Or UltraFeedback for higher quality
ds = load_dataset("HuggingFaceH4/ultrafeedback_binarized", split="train_prefs")
```
Inspect 10 examples. What makes the chosen response better than the rejected one?

**Step 2 — Load your SFT checkpoint from Day 4 as the base**

```python
from trl import DPOTrainer, DPOConfig

policy_model = AutoModelForCausalLM.from_pretrained("mistral-7b-lora-merged", ...)
ref_model = AutoModelForCausalLM.from_pretrained("mistral-7b-lora-merged", ...)  # frozen copy

trainer = DPOTrainer(
    model=policy_model,
    ref_model=ref_model,
    args=DPOConfig(
        beta=0.1,               # higher = stay closer to reference
        max_length=512,
        output_dir="dpo-checkpoint",
    ),
    train_dataset=ds,
    tokenizer=tokenizer,
)
trainer.train()
```

**Step 3 — Try β = 0.05 and β = 0.5**

Run two short runs (100 steps each). At β=0.05, the policy can move further from the reference. At β=0.5, it's more constrained. Compare outputs on 5 adversarial prompts.

**Step 4 — Compare DPO outputs vs SFT outputs**

For 10 prompts: generate with SFT model, DPO model. Manually rate which is better on safety, helpfulness, tone.

**Step 5 — Optional: Try IPO loss**
```python
DPOConfig(loss_type="ipo", beta=0.1)
```
Same 100 steps. Compare output quality.

---

#### What to log

| | SFT baseline | DPO β=0.05 | DPO β=0.1 | DPO β=0.5 |
|---|---|---|---|---|
| Adversarial prompt quality | | | | |
| VRAM needed | | | | |
| Manual rating (1–5) | | | | |

---

#### Evening reflection

1. *Why does DPO need to hold two models in memory (policy + reference) simultaneously? What would happen if you didn't have the reference model?*
2. *You adjusted β. What did higher β do to the outputs — were they more or less conservative?*
3. *DPO's "chosen" and "rejected" pairs define what "good" means. Who decides what goes in the chosen column? What are the risks of that decision?*

---

---

### Day 7 — GRPO: Train a Reasoning Model

**Learning objective:** Understand why verifiable rewards enable reasoning to emerge — and what GRPO does differently from DPO that makes it suited to this.

---

#### Morning theory (60 min)

**Read:** DeepSeek-R1 paper (DeepSeek-AI, 2025) — just Sections 1–3 (introduction, methodology, GRPO description). Focus on: why they didn't need supervised chain-of-thought data; what the "group relative" part of GRPO means.

**Focus question:** *DPO uses human-written chosen/rejected pairs as the reward signal. GRPO uses a rule-based reward function applied to model-generated rollouts. What is the key advantage of rule-based rewards for teaching reasoning?*

---

#### Concept map

| Term | Your definition |
|---|---|
| GRPO (Group Relative Policy Optimization) | |
| Rollout | |
| Verifiable reward | |
| Value model (why GRPO doesn't need one) | |
| Chain-of-thought | |
| GSM8K dataset | |

---

#### Step-by-step experiment

**Step 1 — Load GSM8K**
```python
from datasets import load_dataset
ds = load_dataset("openai/gsm8k", "main", split="train")
# Each example: question + answer with chain-of-thought reasoning
print(ds[0])
```
Read 10 examples. Understand the task: arithmetic word problems with step-by-step solutions.

**Step 2 — Define a rule-based reward function**
```python
import re

def extract_answer(text: str) -> str:
    """Extract final numerical answer from model output."""
    match = re.search(r"####\s*(-?\d+\.?\d*)", text)
    if match:
        return match.group(1)
    # Try extracting last number
    numbers = re.findall(r"-?\d+\.?\d*", text)
    return numbers[-1] if numbers else ""

def gsm8k_reward(completions: list[str], answers: list[str]) -> list[float]:
    rewards = []
    for completion, answer in zip(completions, answers):
        predicted = extract_answer(completion)
        correct = extract_answer(answer)
        rewards.append(1.0 if predicted == correct else 0.0)
    return rewards
```

**Step 3 — Set up GRPO training with Unsloth + TRL**
```python
from unsloth import FastLanguageModel
from trl import GRPOTrainer, GRPOConfig

model, tokenizer = FastLanguageModel.from_pretrained(
    "Qwen/Qwen2.5-7B",
    max_seq_length=2048,
    load_in_4bit=True,
)
FastLanguageModel.get_peft_model(model, r=64, target_modules="all-linear")

trainer = GRPOTrainer(
    model=model,
    tokenizer=tokenizer,
    reward_funcs=[gsm8k_reward],
    args=GRPOConfig(
        output_dir="grpo-qwen",
        num_generations=8,       # group size — generate 8 per prompt, compare
        max_new_tokens=512,
    ),
    train_dataset=ds,
)
trainer.train()
```

**Step 4 — Watch for `<think>` blocks to emerge**

Every 30 minutes of training, generate on 5 prompts and inspect. When do thinking tokens start appearing?

**Step 5 — Evaluate: base vs SFT vs GRPO on 50 GSM8K problems**
```python
from datasets import load_dataset

test = load_dataset("openai/gsm8k", "main", split="test")
# Evaluate accuracy on 50 held-out problems for each model
```

---

#### What to log

| | Base model | After GRPO (4h) | After GRPO (8h) |
|---|---|---|---|
| GSM8K accuracy | | | |
| % responses with `<think>` | | | |
| Avg thinking tokens | | | |
| VRAM during training | | | |

---

#### Evening reflection

1. *Did thinking tokens emerge? If yes, at roughly what training step? What does that tell you about when the reward signal becomes meaningful?*
2. *GRPO generates 8 rollouts per prompt and computes relative rewards within the group. Why is the "relative" part important — what would happen if you just used absolute rewards?*
3. *You can teach arithmetic reasoning with GRPO and a simple rule. What other tasks have verifiable rewards that you could apply this to?*

---

#### Phase 2 Checkpoint

Without notes:
- What is the LoRA reparametrization? Write the equation.
- Why is lora_B initialized to zero?
- What is the key difference between DPO and PPO in terms of what they optimize?
- What does the β parameter in DPO control?
- Why does GRPO not need a value model (unlike PPO)?
- What does "group relative" mean in GRPO?

---

---

## Phase 3 — Days 8–11: RAG, Agents, and Multimodal

**Phase goal:** Build systems that combine the models you've trained with external knowledge, tool use, and vision — the stack that makes models useful in real applications.

---

### Day 8 — Advanced RAG

**Learning objective:** Understand why naive retrieval fails and what each advanced technique (reranking, HyDE, ColBERT) is specifically fixing.

---

#### Morning theory (45 min)

**Read:** HyDE paper (Gao et al. 2022, "Precise Zero-Shot Dense Retrieval without Relevance Labels") — Sections 1–3. Then read the ColBERT paper abstract (Khattab & Zaharia 2020, "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT").

**Focus question:** *HyDE generates a "hypothetical" answer and retrieves based on that, rather than the original query. What failure mode of standard retrieval does this fix? When would HyDE make retrieval worse?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Dense retrieval | |
| Cross-encoder reranker | |
| Bi-encoder (standard dense retrieval) | |
| HyDE | |
| ColBERT / late interaction | |
| RAFT | |

---

#### Step-by-step experiment

**Step 1 — Build baseline RAG (the Hands-On LLMs version)**
```python
import faiss
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("BAAI/bge-large-en-v1.5")

# Load a document corpus (e.g., Wikipedia abstracts on a topic)
documents = [...]  # list of strings

# Embed and index
embeddings = embedder.encode(documents, show_progress_bar=True)
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)

def retrieve_baseline(query: str, k: int = 5):
    q_emb = embedder.encode([query])
    scores, indices = index.search(q_emb, k)
    return [documents[i] for i in indices[0]]
```

Evaluate: pick 20 test queries with known relevant documents. Measure precision@5.

**Step 2 — Add cross-encoder reranker**
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def retrieve_with_rerank(query: str, k_retrieval: int = 20, k_final: int = 5):
    candidates = retrieve_baseline(query, k=k_retrieval)
    pairs = [(query, doc) for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, candidates), reverse=True)
    return [doc for _, doc in ranked[:k_final]]
```

Re-evaluate: does precision@5 improve?

**Step 3 — Implement HyDE**
```python
def retrieve_hyde(query: str, model, tokenizer) -> list[str]:
    # Step 1: generate a hypothetical answer
    prompt = f"Write a short paragraph that answers: {query}"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    hyp_answer = tokenizer.decode(model.generate(**inputs, max_new_tokens=100)[0])
    
    # Step 2: embed the hypothetical answer, not the query
    return retrieve_with_rerank(hyp_answer)
```

**Step 4 — Try ColBERT via ragatouille**
```python
from ragatouille import RAGPretrainedModel

colbert = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")
colbert.index(collection=documents, index_name="my_index")

results = colbert.search("your query here", k=5)
```

Compare ColBERT recall vs. bi-encoder on your 20 test queries.

---

#### What to log

| | Baseline | + Reranker | + HyDE | ColBERT |
|---|---|---|---|---|
| Precision@5 | | | | |
| Latency per query (ms) | | | | |

---

#### Evening reflection

1. *Reranking improved your precision. Why not just retrieve with a cross-encoder from the start instead of doing two stages?*
2. *HyDE helped (or didn't). What type of queries benefited most from the hypothetical answer step?*
3. *ColBERT uses "late interaction" — each query token attends to each document token. What's the memory/compute implication of this vs. a single embedding?*

---

---

### Day 9 — Agentic Systems

**Learning objective:** Understand the ReAct loop — how a model interleaves reasoning and tool use — and why structured function calling is more reliable than parsing free text.

---

#### Morning theory (45 min)

**Read:** ReAct paper (Yao et al. 2022, "ReAct: Synergizing Reasoning and Acting in Language Models") — Sections 1–3. Focus on the Thought/Action/Observation loop.

**Focus question:** *The ReAct paper shows that reasoning (chain-of-thought) and acting (tool calls) are complementary. What does each contribute? What fails when you have only one of the two?*

---

#### Step-by-step experiment

**Step 1 — Implement a ReAct loop from scratch (no LangChain)**
```python
import re

TOOLS = {
    "python": lambda code: str(eval(code)),          # danger: eval — sandboxed environment only
    "calculator": lambda expr: str(eval(expr)),
    "search": lambda query: f"[Search result for '{query}']",
}

def parse_action(text: str):
    match = re.search(r"Action:\s*(\w+)\[(.*?)\]", text, re.DOTALL)
    if match:
        return match.group(1), match.group(2)
    return None, None

def react_loop(task: str, model, tokenizer, max_steps: int = 5):
    prompt = f"Task: {task}\n\nAvailable tools: {list(TOOLS.keys())}\n\n"
    
    for step in range(max_steps):
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        output = model.generate(**inputs, max_new_tokens=200, stop_strings=["Observation:"])
        thought_action = tokenizer.decode(output[0])
        
        tool_name, tool_input = parse_action(thought_action)
        if not tool_name:
            break  # model decided to answer directly
        
        observation = TOOLS[tool_name](tool_input)
        prompt += thought_action + f"\nObservation: {observation}\n"
        print(f"Step {step+1}: {tool_name}({tool_input}) → {observation}")
    
    return prompt
```

Test on: "What is 247 × 389? Show your work."

**Step 2 — Set up vLLM with OpenAI-compatible API**
```bash
python -m vllm.entrypoints.openai.api_server --model mistralai/Mistral-7B-Instruct-v0.2 --port 8000
```

**Step 3 — Switch to function calling**
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")

tools = [{
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Evaluates a mathematical expression",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}
    }
}]

response = client.chat.completions.create(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    messages=[{"role": "user", "content": "What is 247 × 389?"}],
    tools=tools,
    tool_choice="auto"
)
```

**Step 4 — Build a multi-step task test**

Test: "Find the GDP per capita of India and France (use search), then compute the ratio (use calculator)."

Compare: string-parsed ReAct vs. function-calling. Which is more reliable?

---

#### Evening reflection

1. *String parsing (Thought/Action/Observation) vs. structured JSON function calls — what's the core reliability difference? When would string parsing work fine?*
2. *Multi-agent setup (planner + worker): what does the planner add that a single agent doesn't have?*
3. *What task in your own work would benefit from an agent that can use tools?*

---

---

### Day 10 — Multimodal: Fine-tune a Vision-Language Model

**Learning objective:** Understand VLM architecture — how a vision encoder, projection layer, and LLM connect — and what gets trained when you fine-tune.

---

#### Morning theory (45 min)

**Read:** LLaVA paper (Liu et al. 2023, "Visual Instruction Tuning") — Sections 1–3. Focus on the architecture: CLIP vision encoder → linear projection → Vicuna LLM. What is the projection layer learning to do?

**Focus question:** *In a VLM, the LLM was pre-trained on text only. The vision encoder was trained on image-text contrastive pairs. How does the projection layer bridge these two representation spaces?*

---

#### Concept map

| Term | Your definition |
|---|---|
| Vision encoder (e.g., CLIP) | |
| Projection layer | |
| Visual tokens | |
| LLaVA architecture | |
| Instruction tuning (multimodal) | |

---

#### Step-by-step experiment

**Step 1 — Run Qwen2.5-VL-7B on test images**
```python
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

model = Qwen2VLForConditionalGeneration.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct", torch_dtype=torch.bfloat16, device_map="auto")
processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

# Test on a complex image — a diagram, a screenshot, a chart
messages = [{"role": "user", "content": [
    {"type": "image", "image": "path/to/image.jpg"},
    {"type": "text", "text": "Describe what you see in detail."}
]}]
```

Test on 5 different image types. Note where the model fails.

**Step 2 — Prepare a fine-tuning dataset**

Pick an image domain: screenshots + descriptions, product images + captions, or medical imaging (if you have access). Format as: `{"image": path, "question": "...", "answer": "..."}`.

**Step 3 — Fine-tune with LLaMA-Factory**
```bash
# LLaMA-Factory handles VLM fine-tuning natively
llamafactory-cli train \
    --model_name_or_path Qwen/Qwen2.5-VL-7B-Instruct \
    --dataset your_dataset \
    --finetuning_type lora \
    --lora_target all \
    --output_dir vlm-finetuned
```

Monitor VRAM — you're holding a vision encoder + LLM simultaneously.

**Step 4 — Evaluate fine-tuned vs base on your domain images**

Generate on 10 test images with both models. Rate: does the fine-tuned model produce better descriptions for your specific domain?

---

#### Evening reflection

1. *The projection layer is the bridge between vision and language spaces. During fine-tuning, should you train the projection layer, the LLM, or the vision encoder? What are the tradeoffs?*
2. *VRAM usage: how much more does a VLM use vs the same LLM without vision? Where does that extra memory go?*
3. *What would a production VLM pipeline look like for your use case?*

---

---

### Day 11 — Model Merging

**Learning objective:** Understand that model weights are vectors in a high-dimensional space and that interpolation between them is meaningful — and know when merging is better than fine-tuning.

---

#### Morning theory (30 min)

**Read:** TIES-Merging paper (Yadav et al. 2023, "TIES-Merging: Resolving Interference When Merging Models") — Sections 1–3. The key idea: when multiple fine-tuned models are merged, their weight deltas can conflict ("interference"). TIES resolves this by trimming small deltas, electing signs, and disjointly merging.

**Focus question:** *Two models are fine-tuned on different tasks. When you average their weights, why might they "interfere"? What is the sign conflict problem?*

---

#### Step-by-step experiment

**Step 1 — Take two LoRA checkpoints from Days 4–5**

You should have: a model fine-tuned on instruction following, and a model fine-tuned on your domain dataset.

**Step 2 — SLERP merge with mergekit**
```yaml
# merge_config.yaml
models:
  - model: model-a
  - model: model-b
merge_method: slerp
base_model: mistralai/Mistral-7B-v0.1
parameters:
  t: 0.5   # interpolation parameter
```
```bash
mergekit-yaml merge_config.yaml ./merged-slerp
```

**Step 3 — TIES merge**
```yaml
merge_method: ties
base_model: mistralai/Mistral-7B-v0.1
parameters:
  density: 0.5    # fraction of delta weights to keep
  weight: 1.0
```

**Step 4 — DARE merge**
```yaml
merge_method: dare_ties
parameters:
  density: 0.5
  rescale: true   # rescale remaining weights after dropping
```

**Step 5 — Evaluate all three merged models**

Run each on tasks from both parent domains. Does the merged model retain capabilities from both?

---

#### What to log

| | Model A only | Model B only | SLERP 50/50 | TIES | DARE |
|---|---|---|---|---|---|
| Task A performance | | | | | |
| Task B performance | | | | | |

---

#### Evening reflection

1. *SLERP uses spherical interpolation rather than linear. Why does this matter in high-dimensional weight space — what does linear interpolation do wrong?*
2. *The merged model should be better than either parent on one task and slightly worse on its best task. Did you observe this tradeoff?*
3. *Model merging requires no training and no GPU during the merge itself (just CPU). What does this suggest about where the "knowledge" actually lives in a neural network?*

---

#### Phase 3 Checkpoint

Without notes:
- What is the two-stage retrieval pipeline (retrieval + reranking) and why is each stage necessary?
- HyDE: what query does it actually embed when retrieving?
- ReAct loop: describe the three types of text in a ReAct exchange.
- VLM architecture: what are the three components and what does the projection layer do?
- TIES merging: what does "Trim, Elect, Sign, Merge" mean?

---

---

## Phase 4 — Days 12–15: Inference Optimization and Full Project

**Phase goal:** Understand how to serve models efficiently at scale, apply everything to a real domain, and build something evaluable.

---

### Day 12 — Fast Inference: vLLM, Speculative Decoding, and KV Cache

**Learning objective:** Understand why inference throughput is not just about model size — and how PagedAttention and speculative decoding solve fundamentally different bottlenecks.

---

#### Morning theory (45 min)

**Read:** vLLM paper (Kwon et al. 2023, "Efficient Memory Management for Large Language Model Serving with PagedAttention") — Sections 1–3. Focus on the KV cache fragmentation problem and how paging fixes it.

**Read also:** Speculative decoding blog post — search for "Leviathan et al. 2023 speculative decoding" and read the core idea (use a small draft model to generate candidates, verify with the large model in parallel).

**Focus question:** *PagedAttention solves memory fragmentation. Speculative decoding solves latency. What is the bottleneck each is addressing? Can you use both at the same time?*

---

#### Step-by-step experiment

**Step 1 — Baseline: HuggingFace generate() throughput**
```python
import time

model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2", torch_dtype=torch.float16, device_map="auto")

prompts = ["Tell me about the history of AI"] * 10  # simulate 10 concurrent requests (sequential)
t0 = time.time()
for p in prompts:
    inputs = tokenizer(p, return_tensors="pt").to("cuda")
    model.generate(**inputs, max_new_tokens=200)
t1 = time.time()
print(f"HF generate: {10 / (t1-t0):.1f} requests/sec")
```

**Step 2 — vLLM: single request**
```bash
python -m vllm.entrypoints.openai.api_server --model mistralai/Mistral-7B-Instruct-v0.2 --port 8000 &
```
```python
from openai import OpenAI
import time

client = OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
t0 = time.time()
response = client.completions.create(model="mistralai/Mistral-7B-Instruct-v0.2", prompt="Tell me about the history of AI", max_tokens=200)
t1 = time.time()
```

**Step 3 — vLLM: concurrent requests (the real test)**
```python
import asyncio
from openai import AsyncOpenAI

async def send_request(client, prompt):
    return await client.completions.create(model="...", prompt=prompt, max_tokens=200)

async def benchmark_concurrent(n_requests: int):
    client = AsyncOpenAI(base_url="http://localhost:8000/v1", api_key="dummy")
    t0 = asyncio.get_event_loop().time()
    results = await asyncio.gather(*[send_request(client, "Tell me about AI") for _ in range(n_requests)])
    t1 = asyncio.get_event_loop().time()
    print(f"{n_requests} concurrent: {n_requests / (t1-t0):.1f} req/sec")

for n in [1, 5, 10, 20]:
    asyncio.run(benchmark_concurrent(n))
```

**Step 4 — Speculative decoding**
```bash
python -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-Instruct-v0.2 \
    --speculative-model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
    --num-speculative-tokens 5
```
Benchmark latency on short responses. Speculative decoding helps most for short sequences.

---

#### What to log

| | HF generate (1 req) | vLLM (1 req) | vLLM (5 concurrent) | vLLM (20 concurrent) | vLLM + speculative |
|---|---|---|---|---|---|
| Requests/sec | | | | | |
| Latency (ms) | | | | | |

---

#### Evening reflection

1. *Continuous batching is what makes vLLM efficient under concurrent requests. What is continuous batching — how does it differ from static batching?*
2. *Speculative decoding requires the large model to verify the draft model's output in a single forward pass. Why is that fast — what's the verification doing?*
3. *When would you choose sglang over vLLM? (Research this — they have different strengths.)*

---

---

### Day 13 — Embedding Fine-tuning and BERTopic at Scale

**Learning objective:** Understand contrastive learning for embeddings and why fine-tuned embeddings improve downstream tasks like clustering.

---

#### Morning theory (30 min)

**Read:** Matryoshka Representation Learning paper (Kusupati et al. 2022, "Matryoshka Representation Learning") — just the introduction. The idea: train embeddings so that the first d dimensions are a good representation at dimension d, for multiple values of d simultaneously.

**Focus question:** *Standard embeddings have a fixed dimension (e.g., 768). MRL embeddings can be truncated to any smaller size and still work. What does this enable in a production retrieval system?*

---

#### Step-by-step experiment

**Step 1 — Run BERTopic on a large corpus**
```python
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from datasets import load_dataset

# Load a large corpus
ds = load_dataset("wikipedia", "20220301.simple", split="train[:50000]")
docs = ds["text"][:50000]

embedder = SentenceTransformer("BAAI/bge-large-en-v1.5")
embeddings = embedder.encode(docs, show_progress_bar=True, batch_size=256)

topic_model = BERTopic(embedding_model=embedder)
topics, probs = topic_model.fit_transform(docs, embeddings)
topic_model.get_topic_info()
```

Record: number of topics, topic coherence score, time to compute.

**Step 2 — Fine-tune a sentence transformer on domain data**
```python
from sentence_transformers import SentenceTransformer, losses, InputExample
from torch.utils.data import DataLoader

model = SentenceTransformer("BAAI/bge-base-en-v1.5")

# Build triplets: (anchor, positive, negative)
# anchor: a document sentence
# positive: a sentence from the same topic/cluster
# negative: a sentence from a different topic
train_examples = [
    InputExample(texts=["sentence A", "similar sentence B", "unrelated sentence C"]),
    ...
]
train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
train_loss = losses.MultipleNegativesRankingLoss(model)

model.fit(train_objectives=[(train_dataloader, train_loss)], epochs=3)
model.save("bge-finetuned")
```

**Step 3 — Re-run BERTopic with fine-tuned embedder**

Use the fine-tuned `bge-finetuned` model. Do topics become more coherent on your domain?

**Step 4 — Try MRL-style training**
```python
from sentence_transformers.losses import MatryoshkaLoss

base_loss = losses.MultipleNegativesRankingLoss(model)
mrl_loss = MatryoshkaLoss(model, base_loss, matryoshka_dims=[768, 512, 256, 128, 64])
model.fit(train_objectives=[(train_dataloader, mrl_loss)], epochs=3)
```
Test: truncate to 128 dimensions. Is quality preserved?

---

#### Evening reflection

1. *BERTopic uses UMAP for dimensionality reduction before clustering. Why reduce dimensions before clustering? What goes wrong if you cluster in 768-dimensional space?*
2. *Did your fine-tuned embedder improve BERTopic topic quality? How did you measure that?*
3. *MRL lets you trade embedding size for retrieval speed. In what production scenario would you use 64-dim embeddings vs 768-dim?*

---

---

### Day 14 — Pre-training from Scratch on a Custom Domain

**Learning objective:** Understand the process of building a domain model from the ground up — data curation, tokenization, training dynamics — and what "continued pre-training" means vs. training from scratch.

---

#### Morning theory (45 min)

**Read:** DAPT paper (Gururangan et al. 2020, "Don't Stop Pretraining: Adapt Language Models to Domains and Tasks") — Sections 1–4. The key finding: continued pre-training on domain text consistently improves downstream performance, even starting from a general model.

**Focus question:** *DAPT vs. fine-tuning: both use domain data. What's the difference between the two in terms of training objective, data format, and what the model learns?*

---

#### Step-by-step experiment

**Step 1 — Prepare a custom domain corpus**

Pick a domain. Download raw text:
```python
from datasets import load_dataset

# Option: scientific papers (ArXiv)
ds = load_dataset("togethercomputer/RedPajama-Data-1T-Sample", split="train")
domain_docs = [d["text"] for d in ds if d["meta"]["redpajama_set_name"] == "RedPajamaArXiv"]

# Option: code
ds = load_dataset("bigcode/starcoderdata", data_dir="python", split="train", streaming=True)
```

**Step 2 — Deduplicate with MinHash LSH**
```python
from datasketch import MinHash, MinHashLSH

def get_minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for token in text.split():
        m.update(token.encode("utf8"))
    return m

lsh = MinHashLSH(threshold=0.8, num_perm=128)
unique_docs = []
for i, doc in enumerate(domain_docs):
    m = get_minhash(doc)
    if not lsh.query(m):
        lsh.insert(str(i), m)
        unique_docs.append(doc)
```

**Step 3 — Train a BPE tokenizer on your corpus**
```python
from tokenizers import Tokenizer, models, trainers, pre_tokenizers

tokenizer = Tokenizer(models.BPE())
tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
trainer = trainers.BpeTrainer(vocab_size=32000, special_tokens=["<|endoftext|>"])
tokenizer.train_from_iterator(unique_docs, trainer=trainer)
tokenizer.save("domain-tokenizer.json")
```

Measure: average tokens per sentence on domain text vs. general text. Does your tokenizer compress domain text better?

**Step 4 — Option A: continue pre-training an existing model**
```python
from transformers import GPT2LMHeadModel, Trainer, TrainingArguments

model = GPT2LMHeadModel.from_pretrained("gpt2-medium")

args = TrainingArguments(
    output_dir="gpt2-domain",
    learning_rate=2e-5,            # low — preserve general knowledge
    num_train_epochs=1,
    bf16=True,
    gradient_checkpointing=True,
    logging_steps=100,
    report_to="wandb",
)
```

**Step 5 — Option B: train a small model from scratch**
```python
from transformers import GPT2Config, GPT2LMHeadModel

config = GPT2Config(
    vocab_size=32000,
    n_layer=12,
    n_head=12,
    n_embd=768,       # ~120M params
)
model = GPT2LMHeadModel(config)
```

Train for one night. Compare perplexity on domain text vs. a general GPT-2.

---

#### Evening reflection

1. *Continued pre-training vs training from scratch: you likely saw that continued pre-training converges faster. Why?*
2. *You measured tokenizer compression ratio. If your domain tokenizer compresses domain text 10% better than GPT-2's tokenizer, what does that mean for training efficiency?*
3. *What are the risks of using a very low learning rate during continued pre-training? What's the tradeoff with a higher rate?*

---

---

### Day 15 — Full End-to-End Project

**Learning objective:** Chain every technique into one working, evaluated, documented system. This is the integration day — also the hardest conceptually, because you have to decide what each layer is responsible for.

---

#### Morning planning (1 hour, no code)

Before writing a single line of code, draw the system architecture on paper or a whiteboard:

```
User input
    │
    ▼
[Safety check / input guard]
    │
    ▼
[Memory retrieval — episodic context]
    │
    ▼
[RAG retrieval — relevant documents]
    │
    ▼
[Prompt assembly: system + memory + docs + history + query]
    │
    ▼
[Your fine-tuned model via vLLM]
    │
    ▼
[Output]
```

For each box, write: which checkpoint/component it uses, and what happens if it fails.

---

#### Step-by-step experiment

**Step 1 — Wire the components into a single Python class**
```python
class DomainAssistant:
    def __init__(self, model_path, faiss_index, embedder, memory_store):
        self.llm = ...          # vLLM connection
        self.index = faiss_index
        self.embedder = embedder
        self.memory = memory_store
    
    def retrieve_context(self, query: str) -> str:
        docs = self.retrieve_rag(query)
        memories = self.retrieve_memories(query)
        return self.format_context(docs, memories)
    
    def chat(self, user_message: str, history: list) -> str:
        context = self.retrieve_context(user_message)
        prompt = self.assemble_prompt(context, history, user_message)
        return self.llm.generate(prompt)
```

**Step 2 — Create 20 domain-specific evaluation questions**

These should test: factual knowledge, reasoning, appropriate style, memory (if relevant). Write the gold standard answers manually.

**Step 3 — Build a baseline for comparison**

Run the same 20 questions through:
- A plain GPT-4o API call (no fine-tuning, no RAG)
- Your fine-tuned model without RAG
- Your full system

**Step 4 — Automated evaluation**
```python
# Measure with metrics appropriate to your task
# For factual accuracy: exact match, F1 on key facts
# For style: check for specific patterns (e.g., therapeutic tone markers)
# For reasoning: pass to a judge LLM with your rubric
```

**Step 5 — Document in README**

Write `~/gpu-sprint/README.md`:
- System architecture diagram
- What each component does and why it was needed
- Quantitative evaluation results vs. baseline
- What didn't work and why

---

#### Evening reflection

1. *Which component contributed most to the quality improvement over baseline? How do you know?*
2. *What would you do on Day 16 if you had more time? What's the weakest part of the system?*
3. *A year from now, what will you still remember from this sprint? What are the 3 most important things you learned?*

---

#### Phase 4 / Final Checkpoint

Without notes:
- PagedAttention: what problem does it solve, and how?
- Speculative decoding: what role does the draft model play?
- DAPT: what is the training objective and why is a low LR important?
- Name the components of the end-to-end system you built and what each does.
- If you had to fine-tune a model on a new domain tomorrow, what would be your first three steps?

---

---

## Running Comparison Table

Fill this in as you complete each day. It builds cumulative intuition about the whole space.

| Day | Technique | Model | VRAM (GB) | Precision / Bits | Tokens/sec | Key metric | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Inference | 70B via Ollama | | Q4_K_M | | subjective quality | |
| 1 | Inference | 70B 4-bit HF | | NF4 | | | |
| 1 | Inference | 7B Q4 | | Q4_K_M | | | |
| 2 | Training | GPT-2 124M | | bf16 | | loss @ 1k steps | |
| 2 | Training | GPT-2 + FlashAttn | | bf16 | | same | |
| 3 | Quant | Mistral-7B fp16 | | fp16 | | perplexity | |
| 3 | Quant | Mistral-7B GPTQ 4-bit | | 4-bit | | perplexity | |
| 3 | Quant | Mistral-7B AWQ 4-bit | | 4-bit | | perplexity | |
| 3 | Quant | GGUF Q4_K_M | | 4-bit | | perplexity | |
| 4 | LoRA | Mistral-7B r=8 | | bf16+LoRA | | trainable % | |
| 4 | LoRA | Mistral-7B r=64 | | bf16+LoRA | | trainable % | |
| 5 | QLoRA | 30B NF4 | | NF4+LoRA | | domain eval | |
| 6 | DPO | Mistral-7B β=0.1 | | bf16 | | manual rating | |
| 7 | GRPO | Qwen2.5-7B | | NF4+LoRA | | GSM8K acc | |
| 12 | Inference | Mistral-7B vLLM | | bf16 | | req/sec @10 | |
| 12 | Inference | + speculative | | bf16 | | latency ms | |

---

## Resources Index

Organised by day. Find these on ArXiv, the authors' websites, or via search engine.

| Day | Paper / Article | Authors | Year | Why read |
|---|---|---|---|---|
| 1 | Llama 2: Open Foundation and Fine-Tuned Chat Models | Touvron et al. | 2023 | Scale and architecture |
| 2 | FlashAttention-2: Faster Attention with Better Parallelism | Dao | 2023 | Memory bandwidth vs compute |
| 3 | GPTQ: Accurate Post-Training Quantization | Frantar et al. | 2022 | Layer-by-layer quantization |
| 3 | AWQ: Activation-aware Weight Quantization | Lin et al. | 2023 | Saliency-based quantization |
| 4 | LoRA: Low-Rank Adaptation of Large Language Models | Hu et al. | 2021 | The foundational PEFT technique |
| 5 | QLoRA: Efficient Finetuning of Quantized LLMs | Dettmers et al. | 2023 | NF4 + LoRA combined |
| 6 | Direct Preference Optimization | Rafailov et al. | 2023 | Alignment without RL |
| 7 | DeepSeek-R1: Incentivizing Reasoning Capability in LLMs | DeepSeek-AI | 2025 | GRPO and reasoning training |
| 8 | Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE) | Gao et al. | 2022 | Hypothetical document embeddings |
| 8 | ColBERT: Efficient and Effective Passage Search | Khattab & Zaharia | 2020 | Late interaction retrieval |
| 9 | ReAct: Synergizing Reasoning and Acting in Language Models | Yao et al. | 2022 | ReAct loop |
| 10 | Visual Instruction Tuning (LLaVA) | Liu et al. | 2023 | VLM architecture |
| 11 | TIES-Merging: Resolving Interference When Merging Models | Yadav et al. | 2023 | Sign-election merging |
| 12 | Efficient Memory Management for LLM Serving (vLLM / PagedAttention) | Kwon et al. | 2023 | KV cache paging |
| 13 | Matryoshka Representation Learning | Kusupati et al. | 2022 | Multi-scale embeddings |
| 14 | Don't Stop Pretraining: Adapt Language Models to Domains | Gururangan et al. | 2020 | DAPT theory |

---

*This roadmap was designed to be used alongside `01_15_day_gpu_plan.md`. The sprint plan tells you what to build. This file tells you how to understand it.*

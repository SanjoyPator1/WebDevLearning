# B00 — PyTorch Mastery for LLMs: Roadmap

## Why This Track Exists

Following tutorials and building models is different from being *fluent* in
PyTorch. It is entirely possible to write working attention code and still
hesitate at the keyboard: *should this be `view` or `reshape`? `Sequential`
or `ModuleList`? `detach()` or `no_grad()`? Adam or AdamW?*

B00 closes that gap. It is **not** an LLM-building course — nothing here
rebuilds GPT. It is a standalone PyTorch fluency track: syntax, mental
models, and above all **when-to-use-what judgment**. Every chapter is built
around named *Decision Guide* sections and ends with a master "I want to X →
reach for Y" table. Every exercise tests judgment (diagnose a planted bug,
choose the right tool under a constraint), not syntax recall. All examples
are NLP-flavored — token IDs, padding masks, embeddings, logits — so the
fluency transfers directly to any NLP/LLM work.

## Working Convention

Each chapter ships four artifacts:

1. `notes/chNN-<topic>.md` — long-form prose notes in the repo's mandatory
   style: intuition → math (LaTeX) → tiny-number dry-run, ASCII diagrams,
   per-section Key Takeaways, closing master decision table.
2. `code/chNN/template/chNN-<topic>-practice.ipynb` — the pristine fill-in
   practice notebook. Each exercise states **the decision you're practicing**,
   gives a stub cell with `# TODO` markers, and is followed by a pre-written
   verification cell full of asserts that grades your work. *Never edit this
   copy* — it stays clean so you can always restart.
3. `code/chNN/solutions/chNN-<topic>-solution.ipynb` — **your working copy**
   (starts as an exact copy of the template). This is where you hand-write
   your answers.
4. `code/chNN/solved/chNN-<topic>-solved.ipynb` — the fully solved reference,
   executed top-to-bottom with outputs saved, so you can diff your attempt
   against a working answer key.

The intended workflow: **read the notes → hand-write code in `solutions/` →
run the verification cells → diff against `solved/`.** Don't peek at the
solved notebook until the verification cell has either passed or genuinely
stumped you.

## Chapter List & Order

| # | Chapter | Notes | Status |
|---|---------|-------|--------|
| 1 | Tensors & Shape Algebra | [ch01-tensors-and-shape-algebra.md](notes/ch01-tensors-and-shape-algebra.md) | Done — see [code/ch01/](code/ch01/) |
| 2 | Tensor Operations for NLP | [ch02-tensor-ops-for-nlp.md](notes/ch02-tensor-ops-for-nlp.md) | Done — see [code/ch02/](code/ch02/) |
| 3 | The Autograd Mental Model | [ch03-autograd-mental-model.md](notes/ch03-autograd-mental-model.md) | Done — see [code/ch03/](code/ch03/) |
| 4 | Module Patterns | [ch04-module-patterns.md](notes/ch04-module-patterns.md) | Done — see [code/ch04/](code/ch04/) |
| 5 | NLP Layer & Loss Toolbox | [ch05-nlp-layer-and-loss-toolbox.md](notes/ch05-nlp-layer-and-loss-toolbox.md) | Done — see [code/ch05/](code/ch05/) |
| 6 | Text Data Pipeline | [ch06-text-data-pipeline.md](notes/ch06-text-data-pipeline.md) | Done — see [code/ch06/](code/ch06/) |
| 7 | Training Loop Anatomy | [ch07-training-loop-anatomy.md](notes/ch07-training-loop-anatomy.md) | Done — see [code/ch07/](code/ch07/) |
| 8 | Devices, Checkpoints & Debugging | [ch08-devices-checkpoints-and-debugging.md](notes/ch08-devices-checkpoints-and-debugging.md) | Done — see [code/ch08/](code/ch08/) |
| 9 | Capstone: Text Classifier | ch09-capstone-text-classifier.md | Not started |

## What Each Chapter Covers

**ch01 — Tensors & Shape Algebra.** The storage + strides mental model that
makes every shape operation predictable; creation functions (copy vs share);
dtype & device (why token IDs must be `int64`, fp16 vs bf16); indexing; `view`
vs `reshape` vs `contiguous`; `squeeze`/`unsqueeze`; `expand` vs `repeat`;
`transpose` vs `permute`; broadcasting and reductions with `keepdim`.
*Decision guides: creation function, dtype table, view vs reshape, expand vs
repeat.*

**ch02 — Tensor Operations for NLP.** The ~15 ops that are 90% of LLM code:
the matmul family (`*` vs `@` vs `mm` vs `bmm` vs `einsum`); softmax and the
meaning of `dim`; `gather`/`scatter_`; masking done right (`masked_fill` vs
`where` vs boolean indexing vs multiply, and why pre-softmax masks use
$-\infty$); selection and sampling (`argmax`/`topk`/`multinomial`,
temperature); `cat` vs `stack`, `split` vs `chunk` vs `unbind`.
*Decision guides: matmul family, masking tool, greedy vs sampling, cat vs
stack.*

**ch03 — The Autograd Mental Model.** What `.backward()` actually does:
dynamic graph, leaves, `grad_fn`; a full chain-rule dry-run that matches
`.grad` exactly; gradient accumulation as both bug (forgotten `zero_grad`) and
feature (large effective batches); the four gradient-stoppers (`detach` /
`no_grad` / `inference_mode` / `requires_grad_(False)`); in-place operation
errors; the autograd–memory connection (the `losses.append(loss)` leak).
*Decision guides: the four gradient-stoppers, accumulation bug vs feature.*

**ch04 — Module Patterns.** `nn.Parameter` vs
`register_buffer` vs plain attribute; `nn.Linear` internals; weight init and
variance; `Sequential` vs `ModuleList` vs `ModuleDict` vs the plain-list
pitfall; `__call__` vs `forward`; `model.apply`; parameter counting; layer
freezing for fine-tuning.

**ch05 — NLP Layer & Loss Toolbox.** `nn.Embedding` (`padding_idx`,
`from_pretrained`); `LayerNorm` vs `BatchNorm` (plus a look at RMSNorm);
`Dropout` and train/eval semantics; ReLU vs GELU vs SiLU;
`CrossEntropyLoss` deep dive (logits not probs, `ignore_index`,
`label_smoothing`) vs `NLLLoss` vs `BCEWithLogitsLoss`.

**ch06 — Text Data Pipeline.** `Dataset` map-style vs iterable; `DataLoader`
anatomy; `collate_fn` for variable-length text; `pad_sequence` + attention
mask construction; samplers, `shuffle`, `drop_last`; `num_workers`,
`pin_memory`.

**ch07 — Training Loop Anatomy.** The canonical loop line by line and why the
order matters; `train()`/`eval()`; SGD vs Adam vs AdamW; parameter groups (no
weight decay on bias/LayerNorm); schedulers (warmup + cosine); gradient
clipping; gradient accumulation in the loop; checkpoint save/resume; a short
optional section on bf16 `autocast` for the RTX A6000.

**ch08 — Devices, Checkpoints & Debugging.** Device management patterns;
`map_location`; `state_dict` anatomy and surgery (`strict=False`, key
renaming); reading shape-error tracebacks methodically; NaN hunting; 
reproducibility; GPU memory basics and OOM anatomy.

**ch09 — Capstone: Text Classifier.** From a blank file to a trained model:
tiny tokenizer, `Dataset` + collate with padding and masks, Embedding →
masked mean-pool → MLP classifier (deliberately *not* a GPT), AdamW with
warmup, clipping, eval loop, checkpoint/resume — plus one planted bug to find.
Every prior decision guide, exercised once, in anger.

## Rationale for the Order

Chapters 1–3 are the **language block**: tensors, the operations on them, and
the gradient machinery underneath. This is pure fluency — everything else in
PyTorch is written in this vocabulary.

Chapters 4–5 are the **model block**: how `nn.Module` composes those tensors
into architectures, and the specific layers/losses NLP models are made of.

Chapters 6–7 are the **training block**: getting text into tensors efficiently
and running the loop that updates the weights, with every knob understood.

Chapters 8–9 are the **operations block**: the survival skills (debugging,
checkpoints, memory) and a capstone that forces every earlier decision guide
to be used without hand-holding.

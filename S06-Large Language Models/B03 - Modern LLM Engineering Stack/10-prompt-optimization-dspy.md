# Topic 10 — Prompt Optimization with DSPy

## Why This Topic

Every prior topic involves hand-written prompts. DSPy reframes prompting as a
**programming problem**: you declare *signatures* (input/output specs) and
*modules* (e.g. chain-of-thought, ReAct), and DSPy *compiles* these into
optimized prompts (and optionally fine-tunes) by searching over few-shot
examples and instructions against a metric — closing the loop with Topic 8's
evaluation harness.

## Prerequisites

Topic 8 (Evaluation) — DSPy optimization is driven by a metric function, which
is exactly what Topic 8 builds.

## Outline

1. **Signatures** — declaring `"question -> answer"` style signatures instead
   of writing a prompt string; how DSPy turns a signature into an actual
   prompt under the hood (inspect the generated prompt for a simple
   signature).
2. **Modules** — `Predict`, `ChainOfThought`, `ReAct` modules; same signature,
   different reasoning strategy, comparable output quality/cost.
3. **Metrics** — reusing (or adapting) a Topic 8 evaluation function as a
   DSPy metric.
4. **Optimizers (Compilation)** — `BootstrapFewShot` and
   `MIPROv2`: given a small training set + metric, DSPy searches for the
   best few-shot examples and instruction phrasing. Dry-run: show the prompt
   *before* and *after* compilation for one signature, side by side.
5. **When DSPy Helps vs Hurts** — cases where hand-tuned prompts still win
   (very small, well-understood tasks) vs where DSPy's search finds
   non-obvious improvements (multi-step pipelines with compounding prompt
   sensitivity).

## Planned Deliverables

- `code/template/prompt-optimization-dspy.ipynb` — sections 1-3 built using
  one of the tasks from Topic 5 or 8 as the running example; **exercise
  cells** for section 4 (run `BootstrapFewShot` and compare before/after
  prompts and metric scores) and section 5 (write up your own
  helps-vs-hurts judgment based on the result).
- `code/solutions/` — copy of the template.
- `notes/10-prompt-optimization-dspy.md` — before/after prompt comparison
  from section 4, with the metric score delta.

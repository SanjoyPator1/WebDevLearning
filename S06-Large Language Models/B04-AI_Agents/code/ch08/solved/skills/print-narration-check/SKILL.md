---
name: print-narration-check
description: Check whether a Python code cell or script follows this repo's mandatory print-narration convention (every non-trivial computation prints a labeled banner and the resulting shapes/values). Use this when reviewing or writing educational code for this repository, not for reviewing production code elsewhere.
---

## Workflow

1. Read `checklist.md` for the exact rules being checked.
2. Scan the code for computations with no adjacent print statement.
3. Flag each one with the line and a suggested print statement.

## Output Format

A short list: one bullet per violation, each naming the line and the missing print.

## Definition of Done

Every non-trivial computation (anything that isn't a pure constant assignment) has an adjacent print statement narrating what it computed, per `checklist.md`.

## Quality Checks

Common mistake: flagging print statements that exist but use `====` banners instead of this repo's `----` convention (see the repo's own feedback memory on banner style) -- that's a style nit, not a missing-narration violation. Don't conflate the two.

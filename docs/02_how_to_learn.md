The style is notes, then your own hand-written code, with the answer key only as a last resort. The loop for each topic:

1. **Read the notes actively.** Start with the table of contents and the "Interview Questions" list, so you know what you're aiming at. Then read through. Run the code snippets yourself in a scratch folder and change them, instead of only reading them.
2. **Do the exercise by typing it yourself.** The `template/` is the unsolved starter and `solution/` is your copy, so no copy-pasting from the notes. The template starts with failing tests, and `pnpm test` going green means you're done.
3. **Get unstuck in order.** Use the README's hints first, then the notes. Look in `solved/` only after a real attempt, say 20–30 minutes stuck.
4. **After it passes, compare** your work with `solved/`: `diff -r solution/src solved/src`. The differences are usually where the learning is.
5. **Answer the interview questions** without looking, out loud or written, then check them against the model answers.
6. **Tick the roadmap checkbox.**

**Phase 0 in order**

| Step                      | What to do                                                                                                                                     |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 01 Node.js runtime        | Notes only. Run the demos.                                                                                                                     |
| 02 TypeScript refresher   | You've used TypeScript before, so skim Part 1 and read Parts 2–3 carefully. Do each kata right after its matching section, not all at the end. |
| 03 TypeScript for Nest    | Notes, then the decorators exercise.                                                                                                           |
| 04 Philosophy, 05 Tooling | Lighter notes.                                                                                                                                 |
| 06 Toy DI container       | Hardest exercise. Do it after 03 while decorators are fresh.                                                                                   |
| 07 Hello Nest             | Your first real Nest app.                                                                                                                      |

**Starting an exercise** (from the repo root):

```
scripts/start_exercise.sh projects/phase_00_orientation/02_typescript_refresher
cd projects/phase_00_orientation/02_typescript_refresher/solution
nvm use          # picks Node 24 from .nvmrc
pnpm install
pnpm test        # fails at first, which is expected
```

The TypeScript refresher is the largest note, at 1,760 lines. I'd read it over several sessions, not in one sitting.

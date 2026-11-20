# Milestone: Hello Nest 12

**Goal.** Run a real NestJS 12 ESM project end to end: make its tests pass, watch it hot reload, stop on a breakpoint in a debugger, lint it, build it and run the built output. The code to write is one line. The point is the toolchain.

**Read first:** [05 Tooling and Setup](../../../notes/phase_00_orientation/05_tooling_and_setup.md). Topic 0.5 in the [roadmap](../../../notes/01_nestjs_roadmap.md).

## Before You Start

- Node: the v12 CLI asks for `^22.22.3 || ^24.15.0 || >=26.0.0`. On Node 24.11.1 everything below still works, but the package manager prints an engine warning. Upgrading Node removes it (see the notes).
- pnpm 8 or newer.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_00_orientation/07_milestone_hello_nest
cd projects/phase_00_orientation/07_milestone_hello_nest/solution
pnpm install
pnpm test
```

`pnpm test` fails at first. That is expected.

## Tasks

1. **Unit test.** Make `pnpm test` pass. Test name: `AppController > root > should return the Nest 12 greeting`.
   Implement `AppService.getHello()` in `src/app.service.ts`. It must return exactly `Hello, Nest 12!`.
2. **End-to-end test.** Make `pnpm test:e2e` pass. Test name: `AppController (e2e) > / (GET)`.
   This test boots the whole app and calls `GET /`. You should not need to change anything after task 1.
3. **Hot reload.**
   - Run `pnpm start:dev`. In another terminal run `curl localhost:3000`.
   - Change the greeting, save, and call `curl` again. Note how long the reload took and what the terminal printed.
4. **Debugger.**
   - Open the `solution/` folder itself in VS Code (File > Open Folder).
   - Stop `start:dev` and run `pnpm start:debug`.
   - Set a breakpoint on the `return` line in `src/app.service.ts`.
   - Run the configuration "Attach to Nest (pnpm start:debug)" (F5), then `curl localhost:3000`.
   - Execution should stop on your breakpoint. Look at the call stack and find the controller frame.
5. **Quality gates and production run.** Run these and read the output of each:
   - `pnpm lint`
   - `pnpm build`, then look inside `dist/`
   - `PORT=3001 pnpm start:prod`, then `curl localhost:3001`
6. **Questions to answer in your own notes** (answers are in the reading):
   - Why do relative imports end in `.js` when the files are `.ts`?
   - Which tsconfig does `nest build` use, and what does it exclude?
   - Why does `pnpm test` not run the e2e test?
   - What does the debugger attach to, and why is `restart: true` needed with `--watch`?

<details>
<summary>Hint for task 1</summary>

A method that returns a string literal is enough. Do not touch the controller or the tests.

</details>

<details>
<summary>Hint for task 2</summary>

If the e2e test still fails with a 500, run it again and read the Nest error line printed above the assertion. It names the file that still throws.

</details>

<details>
<summary>Hint for task 4</summary>

If VS Code does not stop, check that `pnpm start:debug` printed `Debugger listening on ws://127.0.0.1:9229` and that you opened the `solution/` folder. A gray (unbound) breakpoint means the source map was not found: confirm `dist/` exists and contains `.js.map` files.

</details>

## Not Part of This Exercise

Already set up for you. You read them in the notes but do not write them:

- every config file (`tsconfig*.json`, `nest-cli.json`, `vitest.config*.ts`, `.oxlintrc.json`, `.prettierrc`)
- `package.json` scripts and dependencies
- `.vscode/launch.json`
- `.nvmrc` (Node 24) and the `engines` field in `package.json` (the Node range the Nest 12 CLI supports)
- the controller, the module, `main.ts` and the tests

## Done When

- `pnpm test` and `pnpm test:e2e` pass.
- You stopped on a breakpoint in `app.service.ts` and saw the controller in the call stack.
- `pnpm lint` and `pnpm build` produce no errors and `pnpm start:prod` serves the greeting.
- You can answer the four questions in task 6.

## Answer Key

[`solved/`](solved/) holds the complete working project. Look there only when stuck, or compare afterwards with `diff -r solution/src solved/src`.

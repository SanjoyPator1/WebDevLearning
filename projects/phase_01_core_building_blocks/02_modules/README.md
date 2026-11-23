# Exercise: Modules

**Topic 1.2** in the [roadmap](../../../docs/01_nestjs_roadmap.md#12-modules). Only modules are being learned here.
**Goal:** wire a small app together with `imports`, `exports` and `@Global()`, keep one instance of a shared provider, and write one dynamic module. At the end you can read any `Nest can't resolve dependencies` error and know which line to change.

**Read first:** [02_modules.md](../../../notes/phase_01_core_building_blocks/02_modules.md), especially "Encapsulation", "Re-exporting Modules", "Global Modules" and the decision tree under "Reading and Fixing Module Errors".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On your default Node 24.11.1 `pnpm install` still works but prints an engine warning, because the Nest 12 schematics want 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/02_modules
cd projects/phase_01_core_building_blocks/02_modules/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit`, then the unit tests, then the end-to-end test, and stops at the first part that fails. At the start it fails in the unit tests. That is expected: 13 of the 15 unit tests fail and 2 already pass (they are guards, explained below), and all 3 end-to-end tests fail.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

Useful commands while you work:

| Command | What it runs |
|---|---|
| `pnpm test` | everything, in order: type check, unit tests, e2e |
| `pnpm test:unit` | only the unit tests (`test/*.spec.ts`) |
| `pnpm test:unit test/audit.spec.ts` | one task's test file |
| `pnpm test:e2e` | only the end-to-end test |
| `pnpm typecheck` | only `tsc --noEmit` |
| `pnpm start` | run the real app on port 3000 (after Task 7) |

## What You Edit

Every file you edit is a `*.module.ts`. Each has a `TODO(1.2) Task N` comment that says what is expected.

| File | Task |
|---|---|
| `src/counter/counter.module.ts` and `src/greeter/greeter.module.ts` | 1 |
| `src/audit/audit.module.ts` | 2 |
| `src/core/core.module.ts` and `src/report/report.module.ts` | 3 |
| `src/logger/logger.module.ts` | 4 |
| `src/legacy/legacy.module.ts` | 5 |
| `src/prefix/prefix.module.ts` | 6 |
| `src/app.module.ts` | 7 |

Given, not part of the exercise: every `*.service.ts` and `*.controller.ts`, `notice.module.ts`, `main.ts`, the tests and the config files. The services and controllers are topics 1.4 and 1.3, and they are only there so the modules have something to connect.

## The App

```
                              AppModule
        +--------+--------+-----+------+-------+--------+--------------+
        v        v        v     v      v       v        v              v
  LoggerModule Greeter  Report Audit  Notice  Legacy   PrefixModule
   (global)    Module   Module Module  Module  Module   .forRoot(...)
                  |        |
                  |        v
                  |    CoreModule
                  |        |
                  +---+----+
                      v
                CounterModule         ONE CounterService for the whole app
```

The tests count how many `CounterService` objects Nest creates (`CounterService.created`), so a duplicate instance shows up as a failing test.

## Tasks

The tasks run from easiest to hardest. Do them in order: each one adds an idea the next one uses.

### Task 1: export and import (`test/greeter.spec.ts`)

`GreeterService` needs `CounterService`, which lives in another module.

1. Make `CounterModule` offer `CounterService` to modules that import it.
2. Make `GreeterModule` get it from there, without listing `CounterService` itself.

Tests: *GreeterModule compiles...*, *CounterModule makes CounterService available...*.

### Task 2: export only the public part (`test/audit.spec.ts`)

`AuditModule` provides `AuditLogStore` (an implementation detail) and `AuditService` (the public API). Let other modules use only `AuditService`.

Tests: *a module that imports AuditModule can inject AuditService*. The test *guard: AuditLogStore stays private* already passes. It must stay green: it fails if you export too much.

### Task 3: re-export a module (`test/report.spec.ts`)

`ReportModule` must get `CounterService` through `CoreModule` only. It must not import `CounterModule` and must not list `CounterService` in `providers`. `CoreModule` has no providers of its own.

Tests: *ReportModule gets CounterService through CoreModule...*, *guard: ReportModule imports CoreModule and nothing else*, *GreeterModule and ReportModule share ONE CounterService instance*.

### Task 4: a global module (`test/global.spec.ts`)

Every module should be able to inject `LoggerService` without importing `LoggerModule`. Read `notice.module.ts` first: it uses `LoggerService` without importing anything, which is the hidden dependency the notes warn about.

Tests: *NoticeModule uses LoggerService without importing LoggerModule...*, *Nest records LoggerModule as global...*. The test *the hidden dependency: NoticeModule alone cannot compile* already passes and documents what you are paying for.

### Task 5: fix the duplicate instance (`test/legacy.spec.ts`)

`LegacyModule` lists `CounterService` in its own `providers`, so the app has two of them. Fix it without touching `LegacyService`.

Tests: *CounterModule and LegacyModule together create exactly one CounterService*, *LegacyService counts on the very same CounterService...*.

### Task 6: a dynamic module (`test/prefix.spec.ts`)

Write `PrefixModule.forRoot(options)`. It returns a `DynamicModule` that makes the options available under `PREFIX_OPTIONS`, provides `PrefixService` and exports it. Remove the placeholder `void` lines and the `throw` from the stub.

Tests: *forRoot returns a DynamicModule that names PrefixModule*, *PrefixService uses the options given to forRoot*, *every forRoot call configures its own app*.

### Task 7: compose the app (`test/app.e2e-spec.ts`)

Import the seven modules listed in the comment in `app.module.ts`, including `PrefixModule.forRoot({ prefix: '> ' })`. Run `pnpm test:e2e`, then `pnpm start` and call it:

```bash
curl localhost:3000/greet/ada     # Hello, ada! (#1)
curl localhost:3000/report        # greetings so far: 1
```

Tests: *GET /greet/:name counts up across requests*, *GET /report sees the same counter as the greeter*, *the whole app has exactly one CounterService*.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

The error says CounterService "is not available in the GreeterModule module". Two things have to be true at once: the module that owns the provider must make it public (`exports`), and the module that needs it must list the owner in `imports`. Missing either half gives the same error message.

`GreeterModule` itself does not need to export anything: nobody outside it uses `GreeterService`.
</details>

<details>
<summary>Task 2</summary>

`exports` takes the provider classes you want to make public. Leave out the ones you want to keep private.
</details>

<details>
<summary>Task 3</summary>

`CoreModule` has to import `CounterModule` before it can pass it on. What it passes on is the module, not the provider: put `CounterModule` itself in `exports`. If you try to export `CounterService` from `CoreModule`, Nest throws `UnknownExportException`, because `CoreModule` does not own that provider.

`ReportModule` then imports only `CoreModule`.
</details>

<details>
<summary>Task 4</summary>

There is a decorator in `@nestjs/common` for this, placed above `@Module()`. It is not enough on its own: the provider must still be listed in `exports`, and the module must still be imported once (Task 7 does that).
</details>

<details>
<summary>Task 5</summary>

A provider has exactly one home. If a module needs a provider that another module owns, it imports the owner. Look at what `LegacyModule` lists in `providers` and what it should list in `imports`.
</details>

<details>
<summary>Task 6</summary>

The returned object has the same shape as the `@Module()` metadata plus `module: PrefixModule`. For the options use a custom provider, `{ provide: PREFIX_OPTIONS, useValue: options }`, next to the `PrefixService` class. Custom providers are topic 2.2, so copy that shape rather than studying it.
</details>

<details>
<summary>Task 7</summary>

If a task seems stuck here, run `pnpm test:unit` first. The end-to-end test fails for the same reasons as the unit tests, until all of Tasks 1 to 6 are done. `LoggerModule` must be in this list even though no module imports it by itself: a global module only becomes global once something registers it.
</details>

## Reading the Failures

At the start you will see real Nest errors, not custom messages:

```
Nest can't resolve dependencies of the GreeterService (?). Please make sure that the argument CounterService at index [0] is available in the GreeterModule module.
```

Read it as "while building `GreeterService`, parameter 0 (`CounterService`) was not found, starting the search from `GreeterModule`". Use the decision tree in the notes: owner exports it, consumer imports the owner, owner registered at all.

Other failures are plain assertions such as `expected 2 to be 1` (two `CounterService` instances) and `TODO(1.2): implement PrefixModule.forRoot`.

## Done When

- `pnpm test` exits 0: type check clean, 15 unit tests and 3 end-to-end tests pass.
- `pnpm start` runs, and the two `curl` commands above print what is shown.
- You can explain, without looking, why Task 5's bug produced no error, and why the "not imported" and "not exported" errors read the same.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the `*.module.ts` files differ from the template.

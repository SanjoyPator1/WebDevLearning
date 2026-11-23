# Exercise: Interceptors

**Topic 1.8** in the [roadmap](../../../docs/01_nestjs_roadmap.md#18-interceptors). Only interceptors are being learned here.
**Goal:** write interceptors that run code before and after a handler, reshape the response, time and log a request, put a timeout on a handler, map errors, answer from a cache without calling the handler, and bind interceptors at every scope (including the global kind that keeps dependency injection) while knowing the order they run in and out.

**Read first:** [08_interceptors.md](../../../notes/phase_01_core_building_blocks/08_interceptors.md), especially "Writing an Interceptor", "The RxJS You Need" and "Binding Interceptors".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but may print an engine warning, because Nest 12 tooling wants 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/08_interceptors
cd projects/phase_01_core_building_blocks/08_interceptors/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 25 of 35 fail and 10 already pass. The 10 are the tests of `observations.spec.ts`, which need none of your code.

There is no `pnpm start`: each task is checked by building a small Nest application and calling it with supertest. Modules, controllers, providers, pipes and guards are given where they are needed. The only library besides Nest is `rxjs`, which Nest already depends on and which interceptors are written in. Several tests involve short timeouts (tens of milliseconds); they are generous, but run them on an idle machine if one flickers.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/timing.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |

## What You Edit

| File | Task |
|---|---|
| `src/envelope/envelope.interceptor.ts` | 1 |
| `src/timing/timing.interceptor.ts` | 2 |
| `src/limits/timeout.interceptor.ts` and `src/limits/error-mapper.interceptor.ts` | 3 |
| `src/memo/cached.decorator.ts` and `src/memo/memo.interceptor.ts` | 4 |
| `src/scopes/configure-app.ts` and `src/scopes/scopes.controller.ts` | 5a, 5b |
| `src/stamp/stamp.module.ts` | 5c |

Given, not part of the exercise: every controller that binds your interceptors (`notes`, `work`, `limits`, `products`), `common/audit-log.ts`, `scopes/named.interceptor.ts`, `stamp/stamp.interceptor.ts`, `stamp/stamp.service.ts`, `stamp/elsewhere.module.ts`, `helpers.ts` and the tests.

## Tasks

### Task 1: reshape the response (`test/envelope.spec.ts`)

Wrap every successful response in `{ data }` with an interceptor, including the case where the handler returns nothing. Find the rxjs operator that transforms each value.

### Task 2: code before and after, timing and logging (`test/timing.spec.ts`)

Write `TimingInterceptor`: log before the handler, log and set a timing header after a success, log an error without changing it, and log at the end either way. It injects `AuditLog`. Where you keep the start time matters when two requests overlap.

### Task 3: a timeout and an error mapper (`test/limits.spec.ts`)

- **3a:** give a route 50 ms and answer 408 when it takes longer, leaving other errors alone. Read the test that shows what the timeout does not do.
- **3b:** turn an unexpected plain `Error` into a 502 with a safe message, and leave an `HttpException` as it is.

### Task 4: answer without calling the handler (`test/memo.spec.ts`)

Make the `@Cached()` marker and write `MemoInterceptor`, a small in-memory cache that reads the marker with the `Reflector`, keys on the URL and returns the stored value without running the handler.

### Task 5: binding and order (`test/scopes.spec.ts`)

- **5a and 5b:** bind `NamedInterceptor` globally, on a controller, on a method and as two on one route. Read the trace: the way out is the mirror image of the way in.
- **5c:** register `StampInterceptor` as a global interceptor in a way that keeps dependency injection, and check that it reaches a module that never imported it.

### The observation tests (`test/observations.spec.ts`)

Not a task. Ten tests record behaviour that surprises people: where interceptors sit between guards and pipes, which errors they can and cannot see, that `next.handle()` is lazy and that subscribing twice runs the handler twice, that `map` over `undefined` drops the property, that a `catchError` returning a value swallows even a real bug, that a timeout does not cancel the handler, that `finalize` runs before the response is sent, and that a start time kept in a field is shared between requests. Read them, then change one assertion and watch it fail.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

`next.handle()` returns an Observable. `.pipe(map(value => ...))` transforms what it emits, and what you return from `intercept` is what Nest sends. For `undefined`, look at `??`.
</details>

<details>
<summary>Task 2</summary>

Read the request from `context.switchToHttp().getRequest()`, the response from `getResponse()`. `tap({ next: ..., error: ... })` observes without changing anything, and `finalize(() => ...)` runs at the end. Make the class `@Injectable()` and put `AuditLog` in the constructor. Keep `const start = Date.now()` inside `intercept`, not on `this`.
</details>

<details>
<summary>Task 3</summary>

3a: `timeout(50)` then `catchError`, and `throwError(() => ...)` to put an error back on the stream. `TimeoutError` is exported by rxjs. 3b: `HttpException` is the base class of Nest's HTTP errors.
</details>

<details>
<summary>Task 4</summary>

`Reflector.createDecorator()` with no type argument. In the interceptor read it with `getAllAndOverride(Cached, [handler, class])` and compare with `undefined`. `of(value)` is an Observable that emits `value`; returning it instead of `next.handle()` means the handler never runs. Store with `tap`.
</details>

<details>
<summary>Task 5</summary>

5a: `app.useGlobalInterceptors(...)`. 5b: `@UseInterceptors(a, b)` takes several. 5c: `{ provide: APP_INTERCEPTOR, useClass: StampInterceptor }` in the module's `providers`, with `APP_INTERCEPTOR` from `@nestjs/core`.
</details>

## Done When

- `pnpm test` exits 0: type check clean and 35 tests pass.
- You can explain, without looking, why the handler does not run if you only call `next.handle()` and ignore the result, in what order three interceptors run on the way in and on the way out, why a timeout does not stop the handler, and why an interceptor cannot see a guard's 403.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the nine files named in the table above differ from the template.

# Exercise: Middleware

**Topic 1.5** in the [roadmap](../../../docs/01_nestjs_roadmap.md#15-middleware). Only middleware is being learned here.
**Goal:** write functional and class middleware, register it globally and per module, choose the routes it applies to (and exclude some), control the order it runs in, write it so that a request always ends in exactly one way, and know what a middleware can and cannot see.

**Read first:** [05_middleware.md](../../../notes/phase_01_core_building_blocks/05_middleware.md), especially "Registering Middleware", "Order of Execution" and "Ending a Request".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but may print an engine warning, because Nest 12 tooling wants 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/05_middleware
cd projects/phase_01_core_building_blocks/05_middleware/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 16 of 27 fail and 11 already pass. The 11 are the five tests of `observations.spec.ts` (they need none of your code), plus guards and "the middleware does NOT run here" checks that are true while nothing is registered yet.

There is no `pnpm start`: every task is checked by building a small Nest application around one module and calling it with supertest. Modules (1.2), controllers (1.3) and providers (1.4) are given.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/order.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |

## What You Edit

| File | Task |
|---|---|
| `src/global/tag-response.ts` and `src/global/configure-app.ts` | 1 |
| `src/counted/hit-counter.middleware.ts` and `src/counted/counted.module.ts` | 2 |
| `src/scoped/scoped.module.ts` | 3 |
| `src/files/files.module.ts` | 4 |
| `src/order/order.module.ts` | 5 |
| `src/secured/api-key.middleware.ts` | 6 |

Given, not part of the exercise: `mark/mark.middleware.ts` (a finished class middleware, the model for yours), every controller, service and log provider, `secured.module.ts`, `helpers.ts` and the tests.

## Tasks

### Task 1: functional middleware and `app.use` (`test/global.spec.ts`)

Write `tagResponse`, a plain `(req, res, next)` function that adds a response header and passes the request on. Then register it as global middleware in `configureApp`, the code that would sit in `main.ts`.

### Task 2: class middleware with an injected provider (`test/counted.spec.ts`)

Write `HitCounterMiddleware` as a class that gets `HitCounterService` through its constructor, and make `CountedModule` apply it to `CountedController` only. `MarkMiddleware` shows the shape.

### Task 3: choose the routes and exclude one (`test/scoped.spec.ts`)

Apply `MarkMiddleware` to every route of `ScopedController` except `GET /scoped/health`, while `POST /scoped/health` keeps it. The tests show why a path alone is not enough.

### Task 4: Express 5 paths in `forRoutes` (`test/files.spec.ts`)

`FilesModule` registers its middleware with a pre-Express-5 wildcard that Nest rewrites and warns about. Rewrite the path in the current syntax without changing which requests it covers.

### Task 5: order (`test/order.spec.ts`)

The configuration lists three middlewares in the wrong order. Make a request run: global middleware, then `First`, `Second`, `Third`, then the handler. Find out which orders matter.

### Task 6: a middleware that answers by itself (`test/secured.spec.ts`)

Write `ApiKeyMiddleware`: continue when `x-api-key` equals `secret`, otherwise answer `401` with a JSON body and make sure the handler never runs.

### The observation tests (`test/observations.spec.ts`)

Not a task. Five tests record behaviour that surprises people: the body is not parsed yet in global middleware, a string path loses its prefix in `req.url`, and so on. Read them, then change one assertion and watch it fail.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

Two statements: `res.setHeader(name, value)` and `next()`. For registration look at the Express method on the Nest application that mounts a function for every request. It must run before the application is initialised.
</details>

<details>
<summary>Task 2</summary>

The class needs `use(req, res, next)` and `implements NestMiddleware`. The module needs `implements NestModule` and a `configure(consumer: MiddlewareConsumer)` method: `consumer.apply(...).forRoutes(...)`. `forRoutes` accepts a controller class.
</details>

<details>
<summary>Task 3</summary>

A route can be described as an object with a `path` and a `method` (`RequestMethod`). `exclude(...)` is called on the object `apply(...)` returns, before `forRoutes(...)`. Paths have no leading slash.
</details>

<details>
<summary>Task 4</summary>

A wildcard needs a name in Express 5, and braces make a part optional. Read the warning text in the failing test.
</details>

<details>
<summary>Task 5</summary>

Run the test and read the log in the failure message. Try reordering inside one `apply(...)`, and reordering the `apply(...)` calls, and see which of the two changes the result.
</details>

<details>
<summary>Task 6</summary>

`res.status(401).json(...)` then `return` (do not call `next()`), or `next()` for the good key. `req.header('x-api-key')` reads the header.
</details>

## Done When

- `pnpm test` exits 0: type check clean and 27 tests pass.
- You can explain, without looking, why global `app.use` middleware cannot read `req.body` but module middleware can, why `forRoutes('scoped')` also runs on a path with no route while `forRoutes(ScopedController)` does not, and what happens to a request whose middleware neither answers nor calls `next()`.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the eight files named in the table above differ from the template.

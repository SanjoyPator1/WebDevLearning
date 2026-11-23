# Exercise 01: Application Bootstrap

**Topic 1.1** in the [roadmap](../../../docs/01_nestjs_roadmap.md).

## Goal

Write the two functions every Nest app has in its `main.ts`. `createApp` builds the application (adapter, prefix, CORS, logging) and returns it without listening. `startApp` makes it listen on a port and host that work inside a container. You learn what `NestFactory.create`, `setGlobalPrefix`, `enableCors` and `listen` really do by making real HTTP requests against the result.

## Read first

[01_application_bootstrap.md](../../../notes/phase_01_core_building_blocks/01_application_bootstrap.md). At least: What Happens in create, init and listen, Global Prefix and CORS, The Logger at Bootstrap, and Choosing the HTTP Adapter.

## Node

`.nvmrc` contains `24` and `package.json` has an `engines` field (both Not part of this exercise). Run `nvm use` inside `solution/`. Your Node may be older than the Nest CLI's floor and then `pnpm install` prints an engine warning. The tests still run.

## How to start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/01_application_bootstrap
cd projects/phase_01_core_building_blocks/01_application_bootstrap/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then Vitest. It fails at first (27 failing tests, all with `TODO(1.1)`). That is the starting point.

## What is already there

All of this is Not part of this exercise. It only gives you something to bootstrap.

| File | What it is |
|---|---|
| `src/app.module.ts` | A root module with one controller. Modules are topic 1.2. |
| `src/health.controller.ts` | Two routes: `GET /health` returns `{ status: 'ok' }` and `GET /version` returns `{ version: '1' }`. Controllers are topic 1.3. |
| `src/main.ts` | Calls your two functions with real options. Run it with `pnpm start` (and `PORT=4000 pnpm start`) once the tests pass. |
| `test/bootstrap.spec.ts` | The tests. Read them: they are the specification. Do not edit them. |

You write only `src/create-app.ts`.

## Tasks

Each task is one `describe` block in `test/bootstrap.spec.ts`.

1. **createApp builds but does not listen.** Create the app with `NestFactory.create(AppModule, ...)` and return it. Do not call `listen`.
2. **Adapter.** `options.adapter` is `'express'` (the default) or `'fastify'`. Pass the matching adapter instance to `NestFactory.create`. The same route must work on both.
3. **Global prefix.** If `options.globalPrefix` is set, every route goes under it, except the routes in `options.excludeFromPrefix`.
4. **CORS.** `options.cors` turns CORS on. With no option there must be no CORS headers. A preflight request must get a 204.
5. **Logging.** Nest must send its startup lines to `options.logger`. With no logger, Nest must print nothing. With `bufferLogs: true`, a logger attached later with `app.useLogger()` must still receive the lines Nest wrote during `create`, and without `bufferLogs` it must not.
6. **startApp.** Listen on `PORT` from the environment (default 3000) and on `HOST` (default `0.0.0.0`), then return the URL from `app.getUrl()`.
7. **close().** After `app.close()` the port is free again. This one needs no code from you if tasks 1 to 6 are right. It checks that you did not leave anything holding the port.

## Hints

<details>
<summary>Task 2: how do I pick the adapter?</summary>

`NestFactory.create` has an overload that takes the adapter as its second argument: `NestFactory.create(AppModule, new ExpressAdapter(), options)`. The adapter classes come from `@nestjs/platform-express` and `@nestjs/platform-fastify`.
</details>

<details>
<summary>Task 3: where does the exclude list go?</summary>

`app.setGlobalPrefix(prefix, { exclude: [...] })`. Call it on the app that `create` returned, before `init` or `listen`.
</details>

<details>
<summary>Task 4: CORS</summary>

`NestFactory.create` accepts a `cors` option (`true` or an options object). Pass yours straight through.
</details>

<details>
<summary>Task 5: logging looks like it needs two options</summary>

`logger: false` silences Nest. A `LoggerService` object receives the lines. `bufferLogs: true` holds back what `create` writes until a logger is attached or the app finishes initialising. Try the combination "no logger given plus `bufferLogs: true`" and see what a late `useLogger` receives. The notes show the output.
</details>

<details>
<summary>Task 6: why 0.0.0.0?</summary>

Inside a container, a server bound to loopback only is unreachable from outside. Fastify's own default host is loopback. The notes show what each adapter binds by default, measured.
</details>

<details>
<summary>The "TODO(1.1)" errors are gone but tsc complains</summary>

`pnpm test` runs `tsc --noEmit` first, and Vitest itself does not type-check. Fix the type error first. `pnpm typecheck` runs only the compiler.
</details>

## Done when

`pnpm test` in `solution/` ends with `27 passed`, and `PORT=4000 pnpm start` followed by `curl -i http://127.0.0.1:4000/api/version` returns `{"version":"1"}`.

## Answer key

`solved/` has a complete working version with comments on why each choice was made. Compare with `diff -r solution/src solved/src` only after you have tried.

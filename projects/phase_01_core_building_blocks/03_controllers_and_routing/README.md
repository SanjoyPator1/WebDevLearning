# Exercise: Controllers and Routing

**Topic 1.3** in the [roadmap](../../../docs/01_nestjs_roadmap.md#13-controllers-and-routing). Only controllers and routing are being learned here.
**Goal:** map HTTP requests to handler methods with decorators, read every part of the request, shape the response (status, headers, redirect, `@Res`), return promises and Observables, write Express 5 route paths, and control which route wins when two overlap.

**Read first:** [03_controllers_and_routing.md](../../../notes/phase_01_core_building_blocks/03_controllers_and_routing.md), especially "Reading the Request", "Shaping the Response", "Using Res Safely" and "Route Order and Conflicts".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but prints an engine warning, because the Nest 12 schematics want 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/03_controllers_and_routing
cd projects/phase_01_core_building_blocks/03_controllers_and_routing/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 38 of 42 fail and 4 already pass. The 4 are two control tests that document the problem you are fixing, and two routes that already work by accident (the old `static/*` wildcard that Nest auto-converts, and the optional-segment 404).

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/echo.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |
| `pnpm start` | run the real app on port 3000 |

## What You Edit

| File | Task |
|---|---|
| `src/items/items.controller.ts` | 1 |
| `src/echo/echo.controller.ts` | 2 |
| `src/reply/reply.controller.ts` | 3 |
| `src/stash/stash.controller.ts` | 4 |
| `src/async/async.controller.ts` | 5 |
| `src/paths/paths.controller.ts` | 6 |
| `src/shelf/shelf.controller.ts` and `src/shelf/shelf-options.ts` | 7 |
| `src/items/update-item.dto.ts` (and the `update` method of the items controller) | 8 |

Given, not part of the exercise: `items.service.ts` (an in-memory array, topic 1.4), `sleep.ts`, `app.module.ts`, `main.ts`, the tests and the config files. Each task's tests build a small module around only that task's controller, so an unfinished task never breaks another one. The modules are topic 1.2.

## Tasks

Do them in order. Each test file is named after its task.

### Task 1: a controller with routes (`test/items.spec.ts`)

Make `ItemsController` a controller with the prefix `items` and give its methods the routes in the comment at the top of the file. Read the query string, the route parameter and the JSON body with the matching parameter decorators. Query values and route parameters are strings: convert them yourself.

### Task 2: read the request (`test/echo.spec.ts`)

The routes exist. Add the parameter decorators that fill each parameter: one header, the whole query object, all route parameters, and the raw Express request. The guard test *Express 5 does not nest query keys* documents what the query parser does with `a[b]=c`.

### Task 3: shape the response (`test/reply.spec.ts`)

Five small handlers. Change the status code, drop the body, set two headers, and redirect statically and dynamically. Do not change any method body: decorators only.

### Task 4: `@Res` with and without passthrough (`test/stash.spec.ts`)

`put` must set a status and a header on the response object and still let Nest send the body. `text` must send the whole response itself. The notes explain what each mode switches off.

### Task 5: promises and Observables (`test/async.spec.ts`)

Return a promise, then fix two Observable handlers. For `steps` and `nothing`, run the test first and read what the client receives today. The answers are in how Nest turns an Observable into one response.

### Task 6: Express 5 paths (`test/paths.spec.ts`)

Rewrite a pre-Express-5 wildcard as a named wildcard, and write one route with an optional segment.

### Task 7: route order and conflicts (`test/shelf.spec.ts`)

- **7a:** `/shelf/latest` is swallowed by `/shelf/:id`. Fix it by changing the controller.
- **7b:** fill `strictRoutes` so duplicates stop the application and shadowed routes only warn.
- **7c:** fill `specificityRoutes` so literal routes are registered first whatever the declaration order.

### Task 8: a DTO is a class (`test/dto.spec.ts`)

Describe the body of `PATCH /items/:id` with `UpdateItemDto` and use it as the type of the `@Body()` parameter. The last test shows what a class does and does not do on its own.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

`@Controller('items')` goes on the class, route decorators on methods, and the method decorators take only the part after the prefix: `@Get(':id')`. Parameter decorators: `@Query('search')`, `@Param('id')`, `@Body('name')`. Convert with `Number(...)`. Without `@Controller()` Nest throws `An invalid controller has been detected`.
</details>

<details>
<summary>Task 2</summary>

`@Headers('x-token')` (header names are lowercase), `@Query()` and `@Param()` with no argument return the whole object, `@Req()` is the request. `Request` is a type, so import it with `import type`.
</details>

<details>
<summary>Task 3</summary>

`@HttpCode(...)`, `@Header(name, value)` (stackable) and `@Redirect(url, status)` all sit above the method. A handler that returns `{ url, statusCode }` overrides the redirect decorator for that request.
</details>

<details>
<summary>Task 4</summary>

`@Res({ passthrough: true })` gives you `res` and keeps Nest's response handling. Plain `@Res()` turns it off: the handler must end the response itself. Express: `res.status(...)`, `res.setHeader(...)`, `res.type(...)`, `res.send(...)`.
</details>

<details>
<summary>Task 5</summary>

5a: make the method `async`. 5b: which single value does Nest take from an Observable? Look for `toArray` in rxjs. 5c: what does Nest do when an Observable completes without emitting? `defaultIfEmpty` is the operator that gives it something.
</details>

<details>
<summary>Task 6</summary>

Wildcards need a name in Express 5: `*path`. An optional part is wrapped in braces: `{/:page}`. The question mark of Express 4 is a startup error now.
</details>

<details>
<summary>Task 7</summary>

7a: routes are registered in declaration order and the first match wins. 7b and 7c: look at the `routeConflictPolicy` and `routeResolutionStrategy` options in `NestApplicationOptions`. The policy has one level per kind of conflict.
</details>

<details>
<summary>Task 8</summary>

An optional property is `name?: string`. The class stays a class. The test of the metadata reads `design:paramtypes`, which TypeScript only emits when the parameter has a decorator.
</details>

## Done When

- `pnpm test` exits 0: type check clean and 42 tests pass.
- `pnpm start` runs and `curl localhost:3000/items/2`, `curl -i localhost:3000/reply/old` and `curl localhost:3000/docs/en` answer sensibly.
- You can explain, without looking, why a handler with a plain `@Res()` that returns a value hangs, and why an Observable that emits three values answers only the last one.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`.

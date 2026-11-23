# Exercise: Custom Decorators and the Request Lifecycle

**Topic 1.10** in the [roadmap](../../../docs/01_nestjs_roadmap.md#110-custom-decorators-and-the-request-lifecycle). This is the last topic of Phase 1: it ties the previous seven together.
**Goal:** write custom parameter decorators with `createParamDecorator`, compose several decorators into one with `applyDecorators`, and then **draw the whole request lifecycle from memory and confirm it** against a real application that logs every stage.

**Read first:** [10_decorators_and_lifecycle.md](../../../notes/phase_01_core_building_blocks/10_decorators_and_lifecycle.md), especially "Custom Parameter Decorators", "Composing Decorators" and "The Request Lifecycle".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but may print an engine warning, because Nest 12 tooling wants 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/10_decorators_and_lifecycle
cd projects/phase_01_core_building_blocks/10_decorators_and_lifecycle/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 17 of 29 fail and 12 already pass. The 12 are the eight tests of `observations.spec.ts` (they need none of your code) and four checks that stay true while your decorators do nothing (no user means `undefined`; a route with the role and an open route need no guard).

There is no `pnpm start`: each task is checked by building a small Nest application and calling it with supertest. Everything the earlier topics taught (guards, pipes, interceptors, filters, middleware) is given and used here.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/lifecycle.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |

## What You Edit

| File | Task |
|---|---|
| `src/user/current-user.decorator.ts` | 1 |
| `src/user/locale.decorator.ts` | 2 |
| `src/auth/auth.decorator.ts` | 3 |
| `src/lifecycle/predictions.ts` | 4 |

Given, not part of the exercise: `user/user.ts`, `user/optional-user.guard.ts`, `user/upper.pipe.ts`, `user/profile.controller.ts`, `auth/roles.decorator.ts`, `auth/auth.guard.ts`, `auth/roles.guard.ts`, `auth/admin.controller.ts`, everything in `lifecycle/` except `predictions.ts`, `helpers.ts` and the tests.

## Tasks

### Task 1: `@CurrentUser()` (`test/profile.spec.ts`)

Write a parameter decorator that returns the user a guard attached to the request: the whole user, or one property when you pass a name. It must be typed so that a misspelt property is a compile error, and it must work with a pipe after the name.

### Task 2: `@Locale()` (`test/profile.spec.ts`)

A second parameter decorator, with no argument, that reads the `accept-language` header and returns the language of the first tag, lower-cased, defaulting to `en`.

### Task 3: `@Auth(...roles)` (`test/auth.spec.ts`)

Protecting a route takes metadata plus two guards in the right order. Wrap that in one decorator with `applyDecorators`, usable on a class and on a method.

### Task 4: draw the lifecycle, then confirm it (`test/lifecycle.spec.ts`)

`lifecycle/` holds a controller with a component of every kind at every scope, and four routes that end in four different ways. In `predictions.ts`, write down the exact trace each request leaves behind, **before running anything**: a successful request, a denied one, one whose pipe fails, one whose handler fails, a path with no route, and the status code that a guard and an interceptor see on a route with `@HttpCode(202)`. Then run the tests. A wrong prediction fails with the actual trace in the message.

The entries in a trace are `mw:global`, `mw:module`, `guard:<scope>`, `before:<scope>`, `pipe:<scope>`, `handler`, `after:<scope>`, `error:<scope>` and `filter:<scope>`, with `<scope>` one of `global`, `controller`, `method`, `param`.

### The observation tests (`test/observations.spec.ts`)

Not a task. Eight tests record behaviour that surprises people: when a custom decorator's factory runs relative to guards and interceptors, that a pipe as the first argument is a pipe and not data, that an async factory is awaited, that the factory runs once per use per request, that `applyDecorators` keeps the listed order, that a composed decorator on a class and on a method binds its guards twice, and that `@HttpCode` and `@Header` are applied after the guards and before the interceptors. Read them, then change one assertion and watch it fail.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

`createParamDecorator((data, context) => ...)`. Take the request with `context.switchToHttp().getRequest()`. Type `data` as `keyof User | undefined`. With no data return `user`, with data return `user?.[data]`.
</details>

<details>
<summary>Task 2</summary>

`createParamDecorator((_data, context) => ...)`. The header is a string (or undefined). Split on `,`, then `;`, then `-`, and lower-case. An empty result falls back to `'en'`.
</details>

<details>
<summary>Task 3</summary>

`applyDecorators(Roles(roles), UseGuards(AuthGuard, RolesGuard))`. The order inside `UseGuards` is the order the guards run in: which must come first, authentication or authorization?
</details>

<details>
<summary>Task 4</summary>

Go stage by stage: middleware, guards, interceptors (before), pipes, handler, interceptors (after), filters. For each scope list global before controller before method, and decide for the "after" half which way the order goes. For an error, decide who sees it and in what order, and which single filter answers. For `/nothing-here`, which components even exist when no route matched? For the status, ask when Nest writes the `@HttpCode` status.
</details>

## Done When

- `pnpm test` exits 0: type check clean and 29 tests pass.
- You can draw the lifecycle diagram without looking, say for each of the four routes where the request stops and who answers, and explain why a guard sees status 200 and an interceptor 202 on the same route.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the four files named in the table above differ from the template.

## After This Exercise

Phase 1 ends with the milestone `11_milestone_tasks_api` in the roadmap, an in-memory CRUD API that uses every component of the phase. It is not written yet.

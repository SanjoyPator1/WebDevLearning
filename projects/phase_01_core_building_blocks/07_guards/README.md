# Exercise: Guards

**Topic 1.7** in the [roadmap](../../../docs/01_nestjs_roadmap.md#17-guards). Only guards are being learned here.
**Goal:** write guards that allow or deny a request before the handler, deny with the right status (403 or 401), inject providers into a guard and do asynchronous work, build a role guard from metadata with `Reflector.createDecorator`, make a guard global in the way that keeps dependency injection, and know the order guards run in.

**Read first:** [07_guards.md](../../../notes/phase_01_core_building_blocks/07_guards.md), especially "Writing a Guard", "Metadata and the Reflector" and "Binding Guards".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but may print an engine warning, because Nest 12 tooling wants 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/07_guards
cd projects/phase_01_core_building_blocks/07_guards/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 21 of 34 fail and 13 already pass. The 13 are the nine tests of `observations.spec.ts` (they need none of your code) and four checks that are true while nothing is protected yet (a request with the right key, and the three public routes of Task 4).

There is no `pnpm start`: each task is checked by building a small Nest application and calling it with supertest. Modules (1.2), controllers (1.3), providers (1.4) and pipes (1.6) are given where they are needed. No extra library is installed: real token verification is topic 5.1.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/roles.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |

## What You Edit

| File | Task |
|---|---|
| `src/apikey/api-key.guard.ts` and `src/apikey/vault.controller.ts` | 1 |
| `src/auth/auth.guard.ts` | 2 |
| `src/roles/roles.decorator.ts` and `src/roles/roles.guard.ts` | 3 |
| `src/shop/public.decorator.ts`, `src/shop/token-required.guard.ts` and `src/shop/shop.module.ts` | 4 |
| `src/scopes/configure-app.ts` and `src/scopes/scopes.controller.ts` | 5 |

Given, not part of the exercise: `auth/profile.controller.ts` (it binds your guard), `auth/token.service.ts`, `roles/reports.controller.ts`, `shop/shop.controller.ts`, `scopes/trace.ts`, `common/call-counter.ts`, `helpers.ts` and the tests.

## Tasks

### Task 1: a guard that returns a boolean (`test/apikey.spec.ts`)

Write `ApiKeyGuard`, which lets a request through only with the right header, and bind it once on `VaultController`. Look at what Nest answers when a guard returns `false`.

### Task 2: an async guard with a provider that answers 401 (`test/auth.spec.ts`)

Write `AuthGuard`: it asks `TokenService` (asynchronously) who owns the bearer token, attaches the user to the request, and rejects with 401, not 403. Notice why returning `false` is the wrong tool here.

### Task 3: a role guard from metadata (`test/roles.spec.ts`)

Make the `@Roles([...])` decorator with `Reflector.createDecorator`, then write `RolesGuard`, which reads it for the handler and for the class and decides. Find out what happens when both the controller and a method carry the decorator, and what an empty list means.

### Task 4: a global guard with an opt-out (`test/shop.spec.ts`)

Everything is private unless marked `@Public(true)`. Make the `Public` decorator, write `TokenRequiredGuard`, and register it globally in a way that still lets it inject the `Reflector`.

### Task 5: scopes, order and short-circuiting (`test/scopes.spec.ts`)

Bind `TraceGuard` globally, on the controller, on a method, and three of them on one route where the middle one denies. Read the trace.

### The observation tests (`test/observations.spec.ts`)

Not a task. Nine tests record behaviour that surprises people: what a guard may return (a Promise, an Observable whose last value decides, a truthy string that passes), the 403 and 401 shapes, the order against middleware and pipes, what the `ExecutionContext` holds, why a global guard built with `new` gets no injection, and how `getAllAndOverride` differs from `getAllAndMerge`. Read them, then change one assertion and watch it fail.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

`context.switchToHttp().getRequest()` gives the request, and `request.headers['x-api-key']` the header (Node lowercases header names). `@UseGuards(ApiKeyGuard)` on the class protects every route.
</details>

<details>
<summary>Task 2</summary>

Make the class `@Injectable()` and add a constructor parameter for `TokenService`. `canActivate` can be `async`. `request.headers.authorization` holds the header. To answer 401, throw `UnauthorizedException(message)`.
</details>

<details>
<summary>Task 3</summary>

`Reflector.createDecorator<string[]>()` from `@nestjs/core`. In the guard, inject `Reflector` and read with `getAllAndOverride(Roles, [context.getHandler(), context.getClass()])`. An empty array is a value, not "missing".
</details>

<details>
<summary>Task 4</summary>

`Public` is `Reflector.createDecorator<boolean>()`. The guard reads it like the roles. The registration is a provider `{ provide: APP_GUARD, useClass: TokenRequiredGuard }` in the module's `providers`.
</details>

<details>
<summary>Task 5</summary>

Global: a method of the Nest application. Controller and method: `@UseGuards(...)`, which takes any number of guards and runs them left to right. Pass instances (`new TraceGuard('x')`).
</details>

## Done When

- `pnpm test` exits 0: type check clean and 34 tests pass.
- You can explain, without looking, why a missing token should be a 401 and a wrong role a 403, why a guard can read `@Roles` and middleware cannot, why `app.useGlobalGuards(new G())` cannot inject and `APP_GUARD` can, and what the third of three guards sees when the second one denies.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the ten files named in the table above differ from the template.

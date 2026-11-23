# Exercise: Exception Filters

**Topic 1.9** in the [roadmap](../../../docs/01_nestjs_roadmap.md#19-exception-filters). Only exceptions and exception filters are being learned here.
**Goal:** throw the built-in HTTP exceptions with the right body (including the v12 `errorCode`), write a custom filter, map domain errors to HTTP in one place, write a catch-all filter that extends `BaseExceptionFilter` and is registered globally with dependency injection, and know which filter wins when several are bound.

**Read first:** [09_exception_filters.md](../../../notes/phase_01_core_building_blocks/09_exception_filters.md), especially "The HttpException Family", "Writing a Filter", "Domain Errors and HTTP Errors" and "Binding Filters".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but may print an engine warning, because Nest 12 tooling wants 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/09_exception_filters
cd projects/phase_01_core_building_blocks/09_exception_filters/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 22 of 36 fail and 14 already pass. The 14 are the ten tests of `observations.spec.ts` (they need none of your code) and four checks that stay true while your code is missing (an unexpected `Error` is a generic 500, in three places, and a successful order passes through untouched).

There is no `pnpm start`: each task is checked by building a small Nest application and calling it with supertest. Modules, controllers, providers and pipes are given where they are needed. No extra library is installed.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/domain.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |

## What You Edit

| File | Task |
|---|---|
| `src/accounts/accounts.controller.ts` | 1 |
| `src/envelope/error-envelope.filter.ts` | 2 |
| `src/domain/domain-error.filter.ts` | 3 |
| `src/audit/logging.filter.ts` and `src/audit/audit.module.ts` | 4a, 4b |
| `src/scopes/configure-app.ts` and `src/scopes/scopes.controller.ts` | 5a, 5b |

Given, not part of the exercise: `envelope/shapes.controller.ts`, `domain/domain-errors.ts`, `domain/orders.service.ts`, `domain/orders.controller.ts` (they bind your filters), `audit/error-log.ts`, `audit/things.module.ts`, `scopes/named.filter.ts`, `helpers.ts` and the tests.

## Tasks

### Task 1: throw the built-in exceptions (`test/accounts.spec.ts`)

Five handlers throw a placeholder. Replace each with the built-in exception that produces exactly the response in the file comment: a message, an array of messages, an `errorCode`, and a body that is an object you chose yourself.

### Task 2: a custom filter for `HttpException` (`test/envelope.spec.ts`)

Write `ErrorEnvelopeFilter`: it handles every `HttpException` and answers with one shape, `{ status, code, message, path }`. Read the message from the right place, because an array message does not live where you might look first.

### Task 3: domain errors to HTTP (`test/domain.spec.ts`)

Write `DomainErrorFilter`: the service throws domain errors that know nothing about HTTP, and this filter is the one place that turns them into 409, 422, 404 and 400. An error that is not a domain error must stay untouched.

### Task 4: a catch-all that delegates (`test/audit.spec.ts`)

- **4a:** write `LoggingFilter`, a catch-all that records every exception and then lets Nest answer as it normally would, by extending `BaseExceptionFilter`.
- **4b:** register it with `APP_FILTER` so that it can inject `ErrorLog` and covers the whole application, including a 404 for a path no controller owns.

### Task 5: scopes and precedence (`test/scopes.spec.ts`)

Bind `NamedFilter` globally, on a controller, on a method and as two on one route. Unlike guards and interceptors, only **one** filter handles an exception: find out which.

### The observation tests (`test/observations.spec.ts`)

Not a task. Ten tests record behaviour that surprises people: the default bodies, where `errorCode` does and does not appear, that `cause` never reaches the client, that only unexpected errors are logged, that `@Catch()` matches by `instanceof`, that only one filter handles an exception (and the last of two wins), that a filter which does not respond hangs the request, that filters see errors from guards, pipes, interceptors, middleware and unknown paths, and what goes wrong when a `BaseExceptionFilter` subclass is built by hand without the adapter. Read them, then change one assertion and watch it fail.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

`NotFoundException('text')`, `BadRequestException(['a', 'b'])`, and a second argument `{ errorCode: '...' }`. For the object body, the generic `new HttpException(body, 422)` sends the object as it is.
</details>

<details>
<summary>Task 2</summary>

`@Catch(HttpException)` on the class and `catch(exception: HttpException, host: ArgumentsHost)`. `host.switchToHttp().getResponse()` and `getRequest()`. `exception.getStatus()`, `exception.getResponse()` (a string or an object), `exception.errorCode`. Finish with `response.status(...).json(...)`: nobody else sends the response.
</details>

<details>
<summary>Task 3</summary>

`@Catch(DomainError)` takes the abstract base class, and Nest matches with `instanceof`, so every subclass reaches the filter. Choose the status with `instanceof` checks on the specific subclasses.
</details>

<details>
<summary>Task 4</summary>

4a: `@Catch()` with no arguments, `extends BaseExceptionFilter` from `@nestjs/core`, a constructor that takes `ErrorLog` and calls `super()`, and `super.catch(exception, host)` at the end. 4b: `{ provide: APP_FILTER, useClass: LoggingFilter }` in the module's `providers`, with `APP_FILTER` from `@nestjs/core`.
</details>

<details>
<summary>Task 5</summary>

Global: a method of the Nest application. Controller and method: `@UseFilters(...)`. Pass instances: `new NamedFilter('x')`. Run the test and read which name answers.
</details>

## Done When

- `pnpm test` exits 0: type check clean and 36 tests pass.
- You can explain, without looking, why `errorCode` is missing from a body you built as an object, why the last filter in `@UseFilters(a, b)` is the one that runs, why a global logging filter should extend `BaseExceptionFilter`, and why mapping domain errors in a filter is better than throwing `HttpException` from a service.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the seven files named in the table above differ from the template.

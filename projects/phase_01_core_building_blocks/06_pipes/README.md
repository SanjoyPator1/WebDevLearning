# Exercise: Pipes

**Topic 1.6** in the [roadmap](../../../docs/01_nestjs_roadmap.md#16-pipes). Only pipes are being learned here.
**Goal:** use the built-in pipes to turn strings into real values, change the errors they throw, write your own validating and transforming pipes, bind pipes at every scope and know the order, inject a provider into a pipe, and take a first look at schema validation with `StandardSchemaValidationPipe`.

**Read first:** [06_pipes.md](../../../notes/phase_01_core_building_blocks/06_pipes.md), especially "The Built-in Pipes", "Binding Pipes" and "Writing a Custom Pipe".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but may print an engine warning, because Nest 12 tooling wants 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/06_pipes
cd projects/phase_01_core_building_blocks/06_pipes/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 35 of 41 fail and 6 already pass. The 6 are the five tests of `observations.spec.ts` (they need none of your code) and one guard in `people.spec.ts`.

There is no `pnpm start`: each task is checked by building a small Nest application around one controller and calling it with supertest. Modules (1.2), controllers (1.3) and providers (1.4) are given. No extra library is installed: `class-validator` is topic 3.2 and is not needed here.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/custom.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |

## What You Edit

| File | Task |
|---|---|
| `src/paging/paging.controller.ts` | 1 |
| `src/filters/filters.controller.ts` | 2 |
| `src/strict/strict.controller.ts` | 3 |
| `src/custom/parse-positive-int.pipe.ts` and `src/custom/trim.pipe.ts` | 4 |
| `src/scopes/configure-app.ts` and `src/scopes/scopes.controller.ts` | 5 |
| `src/catalog/sku-exists.pipe.ts` | 6 |
| `src/people/person.schema.ts` and `src/people/people.controller.ts` | 7 |

Given, not part of the exercise: `custom/custom.controller.ts` and `catalog/catalog.controller.ts` (they bind your pipes), `scopes/tag.pipe.ts`, `catalog/catalog.service.ts`, `helpers.ts` and the tests.

## Tasks

### Task 1: `ParseIntPipe` and `DefaultValuePipe` (`test/paging.spec.ts`)

The handlers declare `number` parameters but receive strings. Add built-in pipes so they really get numbers, with defaults for the query. Mind the order of the pipes on one parameter.

### Task 2: more built-in pipes (`test/filters.spec.ts`)

A UUID of version 4, an enum, a boolean with a default, and an optional date: one built-in pipe each, on one route.

### Task 3: options (`test/strict.spec.ts`)

The built-in pipes accept options. Make one route answer 422 and another answer 400 with your own message.

### Task 4: custom pipes (`test/custom.spec.ts`)

Write `ParsePositiveIntPipe`, which validates and transforms and builds its error message from `ArgumentMetadata`, and `TrimPipe`, a pure transformation. The tests call them directly and over HTTP.

### Task 5: binding scopes (`test/scopes.spec.ts`)

Bind `TagPipe` globally, on the controller, on a method and on a parameter, and make a value pass through them in the right order. Then notice which parameter the pipes skip.

### Task 6: a pipe with an injected provider (`test/catalog.spec.ts`)

Write `SkuExistsPipe`, which asks `CatalogService` whether a sku exists and returns the product name.

### Task 7: a first look at schema validation (`test/people.spec.ts`)

Write a Standard Schema by hand (it is only an object with a `validate` function), attach it to `@Body()`, and bind `StandardSchemaValidationPipe`.

### The observation tests (`test/observations.spec.ts`)

Not a task. Five tests record behaviour that surprises people: `ParseIntPipe` rejects `5.5` and `1e3`, `DefaultValuePipe` ignores an empty string, the order of pipes matters, `@Headers()` is never piped, and a plain `Error` thrown by a pipe is a 500. Read them, then change one assertion and watch it fail.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

Pipes go after the name: `@Param('id', ParseIntPipe)`. Several pipes run left to right: `@Query('page', new DefaultValuePipe(1), ParseIntPipe)`. A class is passed as it is, a pipe that needs an argument is passed as an instance with `new`.
</details>

<details>
<summary>Task 2</summary>

`ParseUUIDPipe` has a `version` option. `ParseEnumPipe` takes the enum object. `ParseBoolPipe` only accepts the strings `true` and `false`, so a missing value needs a default before it. `ParseDatePipe` has an `optional` option.
</details>

<details>
<summary>Task 3</summary>

Look at the options object of `ParseIntPipe`. One option is a status code (`HttpStatus` has the names). The other is a function that returns the exception to throw.
</details>

<details>
<summary>Task 4</summary>

`transform(value, metadata)` returns what the handler should receive or throws. `metadata.type` is `'param'`, `'query'`, `'body'` or `'custom'`, and `metadata.data` is the name passed to the decorator. Throw `BadRequestException`. Check the type of the value before you parse it: `"5.5"` and `5.5` must both be rejected.
</details>

<details>
<summary>Task 5</summary>

Global: the Nest application has a method for it. Controller and method: the `@UsePipes()` decorator takes pipe instances. Parameter: a second argument to `@Param`. Nest concatenates them from widest to narrowest.
</details>

<details>
<summary>Task 6</summary>

A pipe is a class like a provider: `@Injectable()` and a constructor parameter. Because the controller binds it as a class (`SkuExistsPipe`, not `new ...`), Nest builds it and injects `CatalogService`.
</details>

<details>
<summary>Task 7</summary>

7a: `validate` returns `{ value }` or `{ issues }`. Collect every issue in an array before returning. 7b: `@Body({ schema })` and `@UsePipes(StandardSchemaValidationPipe)`. Read the guard test: what does the schema do without the pipe?
</details>

## Done When

- `pnpm test` exits 0: type check clean and 41 tests pass.
- You can explain, without looking, why `@Param('id') id: number` is still a string without a pipe, why `new DefaultValuePipe(10)` must come before `ParseIntPipe`, in what order global, controller, method and parameter pipes run, and why a schema on `@Body()` does nothing on its own.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the ten files named in the table above differ from the template.

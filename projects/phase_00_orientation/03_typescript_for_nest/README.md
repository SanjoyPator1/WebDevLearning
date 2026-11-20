# Exercise 03: Decorators and Metadata

**Topic:** 0.3 TypeScript Features Nest Is Built On
**Goal:** write the four kinds of decorator (class, method, property, parameter) so they record metadata with `reflect-metadata`, then read that metadata back to build a route table, the same idea Nest's router uses at bootstrap. There is no DI container here (that is the next exercise, `06_milestone_toy_di`) and no HTTP.

**Read first:** [03_typescript_for_nest.md](../../../docs/phase_00_orientation/03_typescript_for_nest.md), at least the sections on decorator kinds, evaluation order, `reflect-metadata` and `emitDecoratorMetadata`.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_00_orientation/03_typescript_for_nest
cd projects/phase_00_orientation/03_typescript_for_nest/solution
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then `vitest run`. At the start every test fails with a `TODO(0.3)` error. That is expected.

Work in `solution/`. Never edit `template/`: it is the pristine starting point. `solved/` is the answer key, so open it only when you are stuck.

## What You Edit

| File | What |
|---|---|
| `src/decorators.ts` | Tasks 1 to 4: `Controller`, `Get` and `Post`, `Param`, `Field` |
| `src/scanner.ts` | Tasks 5 and 6: `getFields`, `scanController` |

Everything else (`keys.ts`, `types.ts`, `paths.ts`, the tests, `.nvmrc`) is given. `.nvmrc` pins Node 24 for `nvm use`; it is not part of the exercise.

## The Metadata Contract

Each decorator writes to one slot. A slot is `(key, target, propertyKey?)`.

| Decorator | Receives from the compiler | Key | Target | Property key | Value |
|---|---|---|---|---|---|
| `@Controller(prefix)` | the class | `PREFIX_KEY` | the class | none | the prefix string |
| `@Get(path)` and `@Post(path)` | prototype, method name, descriptor | `ROUTE_KEY` | the prototype | the method name | `{ httpMethod, path }` |
| `@Param(name)` | prototype, method name, parameter index | `PARAMS_KEY` | the prototype | the method name | list of `{ index, name }` |
| `@Field()` | prototype, property name | `FIELDS_KEY` | the class (`prototype.constructor`) | none | list of `{ name, type }` |

The compiler also writes `design:type` (properties) and `design:paramtypes` (methods) by itself, because `emitDecoratorMetadata` is on in `tsconfig.json`. You read those two keys, you do not write them.

## Tasks

Each task maps to a group of tests. Run one group with, for example, `pnpm vitest run -t "Task 3"`.

| # | Task | Test group |
|---|---|---|
| 1 | `Controller`: store the prefix on the class | `Task 1: @Controller` |
| 2 | `Get` and `Post`: store the route on the prototype for that method | `Task 2: @Get and @Post` |
| 3 | `Param`: append `{ index, name }`, keep all of them, reject constructor parameters | `Task 3: @Param` |
| 4 | `Field`: append `{ name, type }` using the compiler's `design:type` | `Task 4: @Field` |
| 5 | `getFields`: read the recorded fields | `Task 5: getFields` |
| 6 | `scanController`: build the route table | `Task 6: scanController` |

## Hints

<details>
<summary>Task 1 and 2: which arguments do I get?</summary>

A class decorator receives only the constructor. A method decorator receives `(target, propertyKey, descriptor)`, and for an instance method `target` is the prototype. Use `Reflect.defineMetadata(key, value, target)` for the class slot and `Reflect.defineMetadata(key, value, target, propertyKey)` for a method slot.
</details>

<details>
<summary>Task 3: why do I only see one @Param at a time?</summary>

The compiler calls the parameter decorator once per parameter, last parameter first. Read the list that is already stored, add your entry, store the new list. For a constructor parameter, `propertyKey` is `undefined`.
</details>

<details>
<summary>Task 4: where does the type come from?</summary>

`Reflect.getMetadata('design:type', target, propertyKey)`. The compiler adds its metadata decorator to the same list as yours, and decorators run right to left, so it has already run when your decorator executes. Properties live on instances, but a property decorator receives the prototype, so the class is `target.constructor`.
</details>

<details>
<summary>Task 6: how do I walk the methods and get the types?</summary>

`Object.getOwnPropertyNames(prototype)` lists the methods in declaration order. For each one, read `ROUTE_KEY` with `getOwnMetadata(ROUTE_KEY, prototype, name)`, skip it if undefined, and read `design:paramtypes` the same way. The type of parameter `i` is `paramTypes[i]`.
</details>

## Done When

`pnpm test` is green: `tsc` reports no errors and all 22 tests pass.

## Not in This Exercise

Dependency injection, modules, guards, HTTP and parameter pipes are later topics: see 1.2, 1.3 and 2.1 in the [roadmap](../../../docs/01_nestjs_roadmap.md). The container comes next in `06_milestone_toy_di`.

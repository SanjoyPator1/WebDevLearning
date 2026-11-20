# Milestone: A Toy DI Container

**Phase 0 milestone.** Topics used: 0.2 and 0.3 only.
**Goal:** build a dependency injection container in about 60 lines, using nothing but decorators and `reflect-metadata`. When this works you know how Nest decides what to inject into a constructor, because Nest does the same thing at a bigger scale.

**Read first:** [03_typescript_for_nest.md](../../../docs/phase_00_orientation/03_typescript_for_nest.md), especially `emitDecoratorMetadata`, the `reflect-metadata` API and "How Nest Uses Metadata". Do exercise `03_typescript_for_nest` before this one if you have not.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_00_orientation/06_milestone_toy_di
cd projects/phase_00_orientation/06_milestone_toy_di/solution
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then `vitest run`. At the start every test fails with a `TODO(milestone)` error. That is expected.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key, so open it only when you are stuck.

## What You Edit

| File | What |
|---|---|
| `src/decorators.ts` | Tasks 1 and 2: `Injectable`, `Inject` |
| `src/container.ts` | Tasks 3 to 8: `register`, `registerValue`, `resolve` |

Given, not part of the exercise: `errors.ts` (the error classes and their message formats), `keys.ts`, `types.ts`, the tests, and `.nvmrc` (pins Node 24 for `nvm use`).

## The Model

```
register(Service, Repo, Db)        resolve(Service)
        |                                  |
        v                                  v
  classes: Set                    dependenciesOf(Service)
                                    = design:paramtypes  [Repo, Db]
                                    + @Inject overrides  (per index)
                                           |
                       for each dependency, depth first:
                       registered?  no  -> UnresolvableDependencyError
                                    yes -> in the current path? -> CircularDependencyError
                                           else build it, cache it
                                           |
                              new Service(...resolvedArgs)  ->  cached singleton
```

## Tasks

Run one group with, for example, `pnpm vitest run -t "Task 7"`.

| # | Task | Test group |
|---|---|---|
| 1 | `@Injectable()` marks a class | `Task 1: @Injectable` |
| 2 | `@Inject(token)` overrides one constructor parameter's token | `Task 2: @Inject` |
| 3 | `register` and `registerValue`, rejecting classes without `@Injectable()` | `Task 3` |
| 4 | `resolve` builds classes from `design:paramtypes`, depth first | `Task 4` |
| 5 | Every class is a singleton | `Task 5` |
| 6 | `@Inject` tokens and registered values (strings, symbols, interfaces) | `Task 6` |
| 7 | Readable errors for things that cannot be resolved | `Task 7` |
| 8 | Detect circular dependencies and show the cycle | `Task 8` |

## Hints

<details>
<summary>Task 4: how do I get a class's dependencies?</summary>

`Reflect.getOwnMetadata('design:paramtypes', SomeClass)` returns the constructor parameter types as an array, in order. It exists only because the class has a decorator. Resolve each entry recursively, then call `new SomeClass(...resolvedArgs)`.
</details>

<details>
<summary>Task 5: where does the singleton cache live, and when do I write to it?</summary>

A `Map` from token to instance on the container. Write to it after the constructor returns, so a build that throws leaves nothing half-made behind. Registered values can live in the same map.
</details>

<details>
<summary>Task 6: how do @Inject tokens combine with the compiler's types?</summary>

Start from the `design:paramtypes` array and, for every `{ index, token }` stored by `@Inject`, replace the entry at that index. A string or symbol token is then looked up in the same map as registered values.
</details>

<details>
<summary>Task 7: which parameter is "the first that cannot be satisfied"?</summary>

Check each dependency before you recurse into it: it must be a registered class or a registered value. The first one that is neither gives you the index for `UnresolvableDependencyError`. Checking before recursing is what makes the error name the right consumer.
</details>

<details>
<summary>Task 8: how do I detect a cycle?</summary>

Pass the chain of classes currently being built (`path`) down the recursion. If the class you are about to build is already in `path`, you came back to it. The reported cycle starts at that class's first position in `path`, and ends with the class again: `[A, B, A]`. Do this before you read the class's dependencies, or the recursion never ends.
</details>

## A Note on the Cycle Tests

In real code you cannot easily write two classes in one file that need each other: the second class is still in its temporal dead zone when the first one's `design:paramtypes` is evaluated, so the program fails with a `ReferenceError` before any container exists. The notes show this. Nest solves that case with `forwardRef` (topic 2.5). The cycle tests here write the metadata by hand so the container's detection can be tested on its own.

## Done When

`pnpm test` is green: `tsc` reports no errors and all 34 tests pass.

## Not in This Exercise

Modules, provider scopes, `useClass` and `useFactory` providers, async providers and lifecycle hooks are real Nest features that come later: see 1.2, 2.2, 2.4 and 2.8 in the [roadmap](../../../docs/01_nestjs_roadmap.md). Do not add them here.

# Exercise 0.2: TypeScript Refresher Katas

Twelve small typing katas that rebuild the TypeScript skills Nest leans on: narrowing, generics, mapped and conditional types, and the features added since TypeScript 4.7. Everything is plain TypeScript. There is no Nest, no decorators and no framework in this exercise.

**Read first:** [02_typescript_refresher.md](../../../notes/phase_00_orientation/02_typescript_refresher.md) (topic 0.2 in the [roadmap](../../../notes/01_nestjs_roadmap.md)).

## How to start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_00_orientation/02_typescript_refresher
cd projects/phase_00_orientation/02_typescript_refresher/solution
pnpm install
pnpm test
```

`pnpm test` fails at first. That is the starting point, not a problem.

**Node 24 is required.** The folder has an `.nvmrc` containing `24` (Not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On an older Node, `pnpm install` stops with a clear "Expected version: >=24" message, because `package.json` declares `engines` and `.npmrc` sets `engine-strict=true` (both are Not part of this exercise). Without that check you would get a confusing runtime error from kata 10 instead.

Why: kata 10 uses `using` and `DisposableStack`. Tested on this machine:

| Node | `Symbol.dispose` | native `using` syntax | `DisposableStack` | kata 10 under Vitest |
|---|---|---|---|---|
| 22.23.5 | yes | no (SyntaxError) | no | 4 of 5 tests pass, `cleanupInReverse` fails with `DisposableStack is not defined` |
| 24.11.1 | yes | yes | yes | all pass |
| 24.22.3 | yes | yes | yes | all pass |

The other katas do not depend on the Node version. On Node 26.13.1 all 69 tests pass (checked by running them; the feature table above was not extended to 26). Everything else was verified with pnpm 8.15.9, TypeScript 6.0.3 and Vitest 4.1.12.

## How the checks work

```
pnpm test  =  tsc --noEmit  &&  vitest run
                   |                |
        enforces the type-level   runs the runtime
        expectations (expectTypeOf,   assertions
        @ts-expect-error)
```

- Many katas test types, not values. A type kata has nothing to "run": `expectTypeOf<X>().toEqualTypeOf<Y>()` only does something when `tsc` checks it. A type-level failure appears as a `tsc` error in the `*.test.ts` file, not as a Vitest failure.
- `// @ts-expect-error` lines assert that something must NOT compile. If your types are too loose, `tsc` reports `Unused '@ts-expect-error' directive`.
- Each `tsc` error names the test file and line. Open that line to see exactly which expectation your type does not meet.

Useful commands (run inside `solution/`):

| Goal | Command |
|---|---|
| Everything | `pnpm test` |
| Only the type checks | `pnpm typecheck` |
| Only the runtime tests | `pnpm test:run` |
| One kata's type errors | `pnpm typecheck 2>&1 \| grep 03_` |
| One kata's runtime tests | `pnpm vitest run src/03` |

Because `pnpm test` stops at the first `tsc` failure, work one kata at a time with the per-kata commands, and run `pnpm test` at the end.

## Tasks

Work in order. Each kata has a stub file with `TODO(0.2)` comments, and a `.test.ts` file next to it that defines "done". Do not edit the test files.

| # | File to edit | You practise | Needs |
|---|---|---|---|
| 1 | `src/01_narrowing.ts` | `typeof`, `instanceof`, `in`, type predicates (`x is T`), assertion functions (`asserts x is T`) | types and runtime |
| 2 | `src/02_discriminated_union_exhaustive.ts` | Discriminated unions, `assertNever`, `Shape['kind']`, `Extract` | types and runtime |
| 3 | `src/03_generic_constraints.ts` | `K extends keyof T`, `T[K]`, inference from callbacks, default type parameters, generic classes | types and runtime |
| 4 | `src/04_mapped_types.ts` | `[K in keyof T]`, the `?`, `-?`, `readonly` and `-readonly` modifiers | types only |
| 5 | `src/05_key_remapping.ts` | `as` in mapped types, template literal keys, `Capitalize`, dropping keys with `never` | types and runtime |
| 6 | `src/06_conditional_infer.ts` | Conditional types, `infer`, distribution, `[T] extends [never]` | types only |
| 7 | `src/07_template_literal_route_params.ts` | Recursive template literal types, parsing `'/users/:id'` at the type level | types and runtime |
| 8 | `src/08_satisfies_and_const.ts` | `satisfies` vs a type annotation, `const` type parameters | types only (bodies are given) |
| 9 | `src/09_noinfer.ts` | `NoInfer<T>` | types only (bodies are given) |
| 10 | `src/10_using_disposables.ts` | `using`, `await using`, `Symbol.dispose`, `DisposableStack` | types and runtime |
| 11 | `src/11_utility_composition.ts` | Composing `Omit`, `Pick`, `Partial`, `Required`, a `Simplify` helper, a recursive `DeepReadonly` | types and runtime |
| 12 | `src/12_error_handling_unknown.ts` | `unknown` in `catch`, custom `Error` subclasses with `cause`, a `Result` union | types and runtime |

## Hints

Open one level at a time. Try for at least ten minutes before opening the next.

<details>
<summary>Kata 1: narrowing</summary>

1. `describeValue`: check `null` and `undefined` first, because `typeof null` is `'object'`. After each `if`, hover over `value` to watch its type shrink.
2. For the object case, `'name' in value` narrows the object but `value.name` is still `unknown`. It needs its own `typeof` check.
3. A type predicate changes the return type to `value is string`. An assertion function changes it to `asserts value is NonNullable<T>` and also needs a generic `<T>`.
</details>

<details>
<summary>Kata 2: discriminated unions</summary>

1. `Shape['kind']` is an indexed access type on a union, and it gives the union of every member's `kind`.
2. `Extract<Union, Pattern>` keeps the union members assignable to `Pattern`. Your pattern is an object type with only `kind`.
3. `assertNever` must take a parameter that nothing is assignable to. Then end every `switch` with a `default` that passes the leftover value to it. Temporarily add a fourth shape to the union and see where `tsc` complains.
</details>

<details>
<summary>Kata 3: generics</summary>

1. Two type parameters, where the second depends on the first: `<T, K extends keyof T>`.
2. The return type of `getProp` is `T[K]`, the type of that exact property.
3. For `groupBy`, let the callback decide the key type with `<T, K extends PropertyKey>`. Use `Partial<Record<K, T[]>>` as the result type. `result[key] ??= []` creates the group on first use.
4. `type Box<T = string>` gives `T` a default.
</details>

<details>
<summary>Kata 4: mapped types</summary>

1. The skeleton is `{ [K in keyof T]: T[K] }`. It copies `T`, and it keeps `?` and `readonly` as they were (that is what "homomorphic" means).
2. Add a modifier after the key to add it, or `-` before it to remove it: `[K in keyof T]?`, `[K in keyof T]-?`, `readonly [K in keyof T]`, `-readonly [K in keyof T]`.
3. `MyPick` and `MyRecord` iterate over a set of keys you supply instead of `keyof T`: `[P in K]`.
</details>

<details>
<summary>Kata 5: key remapping</summary>

1. The shape is `{ [K in keyof T as NewKeyType]: Value }`.
2. For `Getters`, the new key is a template literal: `` `get${Capitalize<string & K>}` ``. The `string & K` part is needed because `keyof T` can include numbers and symbols.
3. A key remapped to `never` disappears. Use that for `RemoveKey` (with `Exclude<K, Key>`) and for `OnlyFunctions` (a conditional that returns `K` or `never`).
4. For `makeGetters`, build a plain record in a loop and cast the result once at the end.
</details>

<details>
<summary>Kata 6: conditional types and infer</summary>

1. The pattern is `T extends Something<infer U> ? U : Fallback`. `infer U` names the part you want.
2. `Unwrap` calls itself on the inferred part.
3. A bare `T extends unknown ? T[] : never` distributes over unions. Wrapping both sides, `[T] extends [unknown]`, stops that.
4. `IsNever` must not distribute. A naked `T extends never` applied to `never` distributes over zero members and returns `never`, not `true`.
</details>

<details>
<summary>Kata 7: template literal route params</summary>

1. Match a pattern like `` `${string}:${infer Param}/${infer Rest}` `` against the path. It captures the first parameter name and the text after it.
2. Recurse on the rest, putting the `/` back in front: `` `/${Rest}` ``.
3. The last parameter has no trailing slash, so it needs a second pattern, `` `${string}:${infer Param}` ``.
4. `RouteParams` is a mapped type over the union of names: `{ [K in Names]: string }`. If there are no names, the union is `never` and the object type has no keys.
5. For `extractParams`, make the pattern a generic `P extends string` so its literal type reaches the return type.
</details>

<details>
<summary>Kata 8: satisfies and const</summary>

1. An annotation widens, `satisfies` only checks. Change `: Type = value` to `value satisfies Type`.
2. A `const` type parameter is written `<const T extends ...>`. It makes the compiler infer the argument as if it ended in `as const`.
</details>

<details>
<summary>Kata 9: NoInfer</summary>

1. Wrap the parameter that must not influence inference: `initial: NoInfer<S>`.
2. Do the same for the fallback in `firstOr`. Then re-run `pnpm typecheck` and read the `@ts-expect-error` lines in the test.
</details>

<details>
<summary>Kata 10: using and disposables</summary>

1. A class is `Disposable` when it has a method named `[Symbol.dispose]()`. For async it is `[Symbol.asyncDispose]()`, returning a promise.
2. `using x = new Thing();` disposes `x` when the enclosing block ends, including when it throws. `await using` does the same for async disposal and must be inside an `async` function.
3. `DisposableStack` has a `defer(callback)` method. Declare the stack itself with `using`, and its callbacks run in reverse order.
</details>

<details>
<summary>Kata 11: utility composition</summary>

1. `Simplify<T>` is a mapped type over `T` with its own keys, intersected with `{}`.
2. `PartialBy<T, K>` is `Omit<T, K> & Partial<Pick<T, K>>`, wrapped in `Simplify` so the result is one flat object type.
3. `DeepReadonly` is a chain of conditionals. Check for functions first, then arrays, then objects, and recurse into the elements and properties.
4. For `omit` and `pick`, give the functions the generic signatures `<T extends object, K extends keyof T>`.
</details>

<details>
<summary>Kata 12: errors and unknown</summary>

1. A `catch` variable is `unknown`. Narrow it with `instanceof Error`, `typeof`, and `in` before using it.
2. `HttpError` needs a parameter property for `status`, an `override`-marked `name`, and `super(message, options)` so `cause` is set.
3. `Result<T, E = Error>` is a two-member union discriminated by the boolean `ok`.
4. In `tryCatch`, a thrown value that is not an `Error` becomes `new Error(toErrorMessage(thrown), { cause: thrown })`.
</details>

## Done when

`pnpm test` in `solution/` passes completely: no `tsc` errors and every Vitest test green.

Then re-read your solutions and ask of each type: could I explain every symbol in it to a colleague? If not, go back to the notes for that part.

## Stuck?

`solved/` contains a complete, commented answer for every kata. Look at one kata only, then close it and write your own version from memory. You can also compare your work with `diff -r solution/src solved/src`.

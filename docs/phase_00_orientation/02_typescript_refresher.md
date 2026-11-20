# TypeScript Refresher

> **Topic:** 0.2 (Phase 0, Orientation) · **Priority:** Core · **Prerequisites:** none. You used TypeScript around 4.7 in 2022, so the basics should come back quickly. · **Time:** 2 to 3 days including the exercise · **Exercise:** [02_typescript_refresher](../../projects/phase_00_orientation/02_typescript_refresher/README.md) · **Next:** [03_typescript_for_nest.md](03_typescript_for_nest.md)
>
> Checked on 2026-11-20 with TypeScript 6.0.3 and Node 24.22.3. The "introduced in version" claims in Part 3 were tested by compiling the same snippet on the release before and the release that added the feature, using 4.8.4 through 5.9.3, 6.0.3 and 7.0.2.

## Table of Contents

- [Why a Refresher Before Nest](#why-a-refresher-before-nest)
- [How the Examples Were Checked](#how-the-examples-were-checked)
- [Part 1: Fast Review](#part-1-fast-review)
  - [The Type System in One Page](#the-type-system-in-one-page)
  - [any, unknown and never](#any-unknown-and-never)
  - [Literal, Union and Intersection Types](#literal-union-and-intersection-types)
  - [Narrowing Basics](#narrowing-basics)
  - [Type Guards and Assertion Functions](#type-guards-and-assertion-functions)
  - [Discriminated Unions and Exhaustiveness](#discriminated-unions-and-exhaustiveness)
  - [Interfaces vs Type Aliases](#interfaces-vs-type-aliases)
  - [Optional, readonly and Index Signatures](#optional-readonly-and-index-signatures)
  - [Functions: Overloads, Defaults and this](#functions-overloads-defaults-and-this)
  - [Classes](#classes)
  - [Enums vs Unions vs as const](#enums-vs-unions-vs-as-const)
  - [Typing Async Code and Errors](#typing-async-code-and-errors)
- [Part 2: Depth](#part-2-depth)
  - [Control Flow Analysis in Depth](#control-flow-analysis-in-depth)
  - [Structural Typing Pitfalls](#structural-typing-pitfalls)
  - [Variance and Assignability](#variance-and-assignability)
  - [Generics: Constraints, Defaults and Inference](#generics-constraints-defaults-and-inference)
  - [keyof, typeof and Indexed Access Types](#keyof-typeof-and-indexed-access-types)
  - [Mapped Types](#mapped-types)
  - [Conditional Types and infer](#conditional-types-and-infer)
  - [Template Literal Types](#template-literal-types)
  - [Built-in Utility Types](#built-in-utility-types)
  - [How Nest Builds PartialType and PickType](#how-nest-builds-partialtype-and-picktype)
  - [Declaration Merging and Module Augmentation](#declaration-merging-and-module-augmentation)
- [Part 3: What Changed Since TypeScript 4.7](#part-3-what-changed-since-typescript-47)
  - [Version by Version Table](#version-by-version-table)
  - [TypeScript 4.9: satisfies](#typescript-49-satisfies)
  - [TypeScript 4.9: accessor](#typescript-49-accessor)
  - [TypeScript 5.0: const Type Parameters](#typescript-50-const-type-parameters)
  - [Standard Decorators vs Legacy Decorators](#standard-decorators-vs-legacy-decorators)
  - [using and await using](#using-and-await-using)
  - [NoInfer](#noinfer)
  - [Inferred Type Predicates and Closure Narrowing](#inferred-type-predicates-and-closure-narrowing)
  - [isolatedDeclarations](#isolateddeclarations)
  - [erasableSyntaxOnly and Node Type Stripping](#erasablesyntaxonly-and-node-type-stripping)
  - [Importing ES Modules from CommonJS and the node18 and node20 Module Settings](#importing-es-modules-from-commonjs-and-the-node18-and-node20-module-settings)
  - [TypeScript 6.0: New Defaults and Removals](#typescript-60-new-defaults-and-removals)
  - [TypeScript 7.0: The Native Compiler](#typescript-70-the-native-compiler)
- [Part 4: Modules, Config and How TypeScript Runs](#part-4-modules-config-and-how-typescript-runs)
  - [import type and verbatimModuleSyntax](#import-type-and-verbatimmodulesyntax)
  - [moduleResolution Choices](#moduleresolution-choices)
  - [tsconfig Essentials](#tsconfig-essentials)
  - [Recommended tsconfig for a Plain Node Library](#recommended-tsconfig-for-a-plain-node-library)
  - [What the Nest 12 Scaffold Uses](#what-the-nest-12-scaffold-uses)
  - [Ways to Run TypeScript](#ways-to-run-typescript)
- [The Exercise](#the-exercise)
- [Interview Questions](#interview-questions)
  - [unknown vs any](#unknown-vs-any)
  - [satisfies vs a type annotation](#satisfies-vs-a-type-annotation)
  - [interface vs type](#interface-vs-type)
  - [Why Object.keys returns string array](#why-objectkeys-returns-string-array)
  - [What never is for and how exhaustiveness works](#what-never-is-for-and-how-exhaustiveness-works)
  - [Enums vs literal unions](#enums-vs-literal-unions)
  - [Variance and strictFunctionTypes](#variance-and-strictfunctiontypes)
  - [Conditional type distribution](#conditional-type-distribution)
  - [Declaration merging](#declaration-merging)
  - [Why a class can be a DI token and an interface cannot](#why-a-class-can-be-a-di-token-and-an-interface-cannot)
  - [Type predicates and assertion functions](#type-predicates-and-assertion-functions)
  - [const type parameters vs as const](#const-type-parameters-vs-as-const)
  - [NoInfer](#noinfer-1)
  - [verbatimModuleSyntax and isolatedModules](#verbatimmodulesyntax-and-isolatedmodules)
  - [nodenext vs bundler module resolution](#nodenext-vs-bundler-module-resolution)
  - [What changed in TypeScript 6 and 7, and why Nest pins 6](#what-changed-in-typescript-6-and-7-and-why-nest-pins-6)
  - [What using gives you over try and finally](#what-using-gives-you-over-try-and-finally)
  - [Omit is not what it looks like](#omit-is-not-what-it-looks-like)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why a Refresher Before Nest

Nest is a TypeScript-first framework, and its code is more type-heavy than a typical Express app:

- `Type<T>`, the type of "a class constructor that makes a `T`", appears all over the public API (`ModuleRef.get`, custom providers, mapped types).
- `PartialType`, `PickType`, `OmitType` and `IntersectionType` (see 3.2) are typed with `Partial`, `Pick`, `Omit` and a conditional type. You will read their signatures.
- Libraries ship `.d.ts` files, and reading those, plus compiler errors, is a daily activity.
- "unknown vs any", "satisfies vs an annotation", "why can't an interface be an injection token" and "what is a conditional type" are standard senior interview questions.

This doc is TypeScript on its own: no Nest and no decorators. Decorators and `emitDecoratorMetadata` are in [0.3](03_typescript_for_nest.md). The Nest scaffold's exact tsconfig is explained in Part 4 and again in 0.5.

**Suggested reading order.** Skim Part 1 in one sitting. Take Part 2 slowly alongside katas 3 to 7. Use Part 3 as the "what changed" reference alongside katas 8 to 10. Read Part 4 before 0.5.

## How the Examples Were Checked

- Every code block was compiled with TypeScript 6.0.3 under the options in [the recommended tsconfig](#recommended-tsconfig-for-a-plain-node-library), with `noUncheckedIndexedAccess` and `verbatimModuleSyntax` on.
- Blocks that show a compiler error were compiled too, and the error text under them is copied from the compiler.
- Blocks that print something were run on Node 24.22.3, and the output shown is the real output.
- Where a flag other than the defaults is needed, the block says so in its first line.
- Two version dates in the text come from the release notes and were not tested here, because the oldest compiler installed for testing was 4.7.4: aliased conditions (4.4) and the 4.7 features (`in` and `out` variance annotations, instantiation expressions, constraints on `infer`). The examples themselves were compiled.
- Anything that was not tested says "Not verified" at that spot.

The examples use two helpers so that the compiler checks a type claim instead of you trusting a comment. They are defined once here and assumed in every later block that uses them:

```ts
// Helpers assumed by the examples in this document.
type Equal<A, B> =
  (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2)
    ? true
    : false;
type Expect<T extends true> = T;
```

`Expect<Equal<X, Y>>` compiles only if `X` and `Y` are the same type. The exercise uses Vitest's `expectTypeOf` for the same job.

## Part 1: Fast Review

Skim these if the fundamentals are fresh. Each section stops where it stops being a refresher.

### The Type System in One Page

A type is a set of allowed values, and "assignable" means "this set fits inside that set". TypeScript is structural: what matters is the shape, not the declared name. Types exist only while compiling. After compilation they are gone, which is why a TypeScript interface cannot be used as a runtime token (see 0.3).

| Construct | Exists at runtime? | Note |
|---|---|---|
| `interface`, `type` alias | No | Erased completely |
| Annotations, generics, `as`, `satisfies`, `!` | No | Erased completely |
| `class` | Yes | A class is both a value (the constructor) and a type (its instance shape) |
| `enum` | Yes | Emits an object (see Enums vs Unions vs as const) |
| Decorators | Yes | Plain function calls (see 0.3) |

```ts
interface Point { x: number; y: number }

class Vec {
  constructor(readonly x: number, readonly y: number) {}
}

function norm(p: Point): number {
  return Math.hypot(p.x, p.y);
}

// Vec never mentions Point. It has the right shape, so it is accepted.
export const five = norm(new Vec(3, 4));
```

### any, unknown and never

| Type | Meaning | Use it for |
|---|---|---|
| `any` | Turns checking off. Assignable to and from nearly everything | Almost never. It spreads silently |
| `unknown` | The type-safe `any`. Anything can be assigned to it, but nothing can be done with it until it is narrowed | Untrusted input: parsed JSON, `catch` variables, request bodies |
| `never` | The empty set. No value has this type | Functions that never return, exhaustiveness checks, impossible branches |

```ts error
const v: unknown = 'x';
v.toUpperCase();
```

```text error
error TS18046: 'v' is of type 'unknown'.
```

```ts
const data = JSON.parse('{"a":{"b":1}}'); // any
const n: number = data.a.b.c.d;           // compiles. It throws at runtime.

const parsed: unknown = JSON.parse('{"a":{"b":1}}');
if (typeof parsed === 'object' && parsed !== null && 'a' in parsed) {
  console.log(parsed.a); // narrowed: the object is known to have an 'a' property
}
```

`JSON.parse` returns `any`, so assigning its result to a variable annotated `unknown` is the one-line fix that forces callers to narrow.

```ts
function fail(message: string): never {
  throw new Error(message);
}

type Impossible = string & number; // no value is both
type _ = Expect<Equal<Impossible, never>>;
```

### Literal, Union and Intersection Types

```ts
let method = 'GET';                  // string: a let can be reassigned, so the type widens
const fixed = 'GET';                 // 'GET'
const tuple = ['GET', 200] as const; // readonly ['GET', 200]

type Method = 'GET' | 'POST';        // union: a value is one of these
type WithId = { id: number } & { name: string }; // intersection: a value has both

type _1 = Expect<Equal<typeof fixed, 'GET'>>;
type _2 = Expect<Equal<typeof method, string>>;
type _3 = Expect<Equal<typeof tuple, readonly ['GET', 200]>>;
```

Unions are how TypeScript models "one of several shapes". Intersections combine object types. Intersecting incompatible primitives gives `never`.

### Narrowing Basics

Narrowing is the compiler shrinking a union to a smaller type inside a branch.

| Check | Narrows |
|---|---|
| `typeof x === 'string'` | to `string` (also `number`, `boolean`, `bigint`, `symbol`, `function`, `undefined`) |
| `x === undefined`, `x == null`, `x === 'a'` | to the compared type, or removes it |
| truthiness: `if (x)` | removes `null`, `undefined`, `0`, `''`, `false` |
| `'key' in x` | to the union members that have the key |
| `x instanceof Date` | to the class instance type |
| `Array.isArray(x)` | to an array type |
| `x.kind === 'circle'` | to the union member with that discriminant (see the discriminated unions section) |

```ts error
export function size(x: string | number): number {
  return x.length;
}
```

```text error
error TS2339: Property 'length' does not exist on type 'string | number'.
Property 'length' does not exist on type 'number'.
```

```ts
export function size(x: string | number | string[]): number {
  if (typeof x === 'string') return x.length; // string
  if (Array.isArray(x)) return x.length;      // string[]
  return x.toFixed().length;                  // number
}
```

Two traps:

```ts
// typeof null is 'object', so a plain typeof check lets null through.
function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

// Truthiness also removes 0 and ''. Here a count of 0 prints "no count", which is wrong.
function label(count: number | undefined): string {
  return count ? `${count} items` : 'no count';
}
```

### Type Guards and Assertion Functions

A type predicate (`v is T`) tells the compiler what a boolean function proves. An assertion function (`asserts v is T`) tells it what is true after the call returns.

```ts
function isString(v: unknown): v is string {
  return typeof v === 'string';
}

function assertString(v: unknown): asserts v is string {
  if (typeof v !== 'string') throw new TypeError('not a string');
}

declare const input: unknown;
if (isString(input)) input.toUpperCase(); // narrowed inside the branch
assertString(input);
input.toUpperCase();                        // narrowed for the rest of the scope
```

The compiler trusts a predicate. It does not check that the body proves the claim:

```ts
// Compiles. The compiler cannot see that this is a lie.
function isNumber(v: unknown): v is number {
  return true;
}
```

Assertion functions have one more rule: the name being called must have an explicit type, so declare them with `function`:

```ts error
const assertDefined = <T>(v: T): asserts v is NonNullable<T> => {
  if (v == null) throw new Error('missing');
};
declare const maybe: string | undefined;
assertDefined(maybe);
```

```text error
error TS2775: Assertions require every name in the call target to be declared with an explicit type annotation.
```

TypeScript 5.5 can infer simple predicates for you, see Inferred Type Predicates and Closure Narrowing.

### Discriminated Unions and Exhaustiveness

A discriminated union has a literal-typed property (`kind`) that tells you which member you have. It is the standard way to model results, events and messages, and it is the TypeScript equivalent of Pydantic's discriminated unions.

```ts
type Shape =
  | { kind: 'circle'; r: number }
  | { kind: 'square'; s: number };

function assertNever(value: never): never {
  throw new Error(`Unexpected: ${JSON.stringify(value)}`);
}

export function area(shape: Shape): number {
  switch (shape.kind) {
    case 'circle':
      return Math.PI * shape.r ** 2;
    case 'square':
      return shape.s ** 2;
    default:
      return assertNever(shape); // shape is `never` here, so this compiles
  }
}
```

Now forget a case. The leftover member is passed to a parameter of type `never` and the compiler refuses:

```ts error
type Shape =
  | { kind: 'circle'; r: number }
  | { kind: 'square'; s: number };

function assertNever(value: never): never {
  throw new Error(String(value));
}

export function area(shape: Shape): number {
  switch (shape.kind) {
    case 'circle':
      return Math.PI * shape.r ** 2;
    default:
      return assertNever(shape);
  }
}
```

```text error
error TS2345: Argument of type '{ kind: "square"; s: number; }' is not assignable to parameter of type 'never'.
```

This turns "add a new variant" into a compile error at every `switch` that forgot it. A function-free spelling of the same check is `shape satisfies never`:

```ts
type Shape =
  | { kind: 'circle'; r: number }
  | { kind: 'square'; s: number };

export function name(shape: Shape): string {
  switch (shape.kind) {
    case 'circle':
      return 'circle';
    case 'square':
      return 'square';
    default:
      return shape satisfies never;
  }
}
```

### Interfaces vs Type Aliases

| | `interface` | `type` alias |
|---|---|---|
| Object shapes | Yes | Yes |
| Unions, tuples, primitives, mapped and conditional types | No | Yes |
| Declaration merging (same name declared twice) | Yes | No, it is an error |
| Extending | `extends`, which reports conflicting members as errors | `&`, which silently produces `never` for conflicts |
| Can a class `implements` it | Yes | Yes, if it is an object type |

```ts
interface Config { port: number }
interface Config { host: string }  // merged: Config now has both members

export const config: Config = { port: 3000, host: 'localhost' };
```

```ts error
type Settings = { port: number };
type Settings = { host: string };
```

```text error
error TS2300: Duplicate identifier 'Settings'.
```

A working rule: use `interface` for object contracts that other code implements or augments, and `type` for everything computed (unions, mapped, conditional). In Nest, DTOs are classes, not interfaces, because a class survives to runtime for validation and metadata (see 0.3 and 3.2).

### Optional, readonly and Index Signatures

```ts
interface Options {
  retries?: number;          // optional: may be absent, and reads as number or undefined
  readonly id: string;       // readonly: shallow and compile-time only
  [extra: string]: unknown;  // index signature: any other string key is allowed
}
```

`readonly` is checked only by the compiler, and only one level deep:

```ts error
const p: { readonly x: number } = { x: 1 };
p.x = 2;
```

```text error
error TS2540: Cannot assign to 'x' because it is a read-only property.
```

With `noUncheckedIndexedAccess` on, reading by index may give `undefined`, which matches reality:

```ts error
const xs = [1, 2, 3];
export const first: number = xs[0];
```

```text error
error TS2322: Type 'number | undefined' is not assignable to type 'number'.
```

`exactOptionalPropertyTypes` separates "absent" from "present but undefined":

```ts error
// flags: --exactOptionalPropertyTypes
interface Opts { retries?: number }
export const o: Opts = { retries: undefined };
```

```text error
error TS2375: Type '{ retries: undefined; }' is not assignable to type 'Opts' with 'exactOptionalPropertyTypes: true'. Consider adding 'undefined' to the types of the target's properties.
```

### Functions: Overloads, Defaults and this

Overloads give one function several call signatures. Callers see only the overload signatures. The implementation signature is hidden and must be compatible with all of them.

```ts
function pad(value: string): string;
function pad(value: number, width: number): string;
function pad(value: string | number, width = 0): string {
  return String(value).padStart(width);
}

export const a = pad('7');
export const b = pad(7, 3);
```

```ts error
function pad(value: string): string;
function pad(value: number, width: number): string;
function pad(value: string | number, width = 0): string {
  return String(value).padStart(width);
}

export const c = pad(true);
```

```text error
error TS2345: Argument of type 'boolean' is not assignable to parameter of type 'string'.
```

A `this` parameter is erased at compile time and exists only to type the call site:

```ts error
function describe(this: { name: string }, greeting: string): string {
  return `${greeting}, ${this.name}`;
}
describe('hello');
```

```text error
error TS2684: The 'this' context of type 'void' is not assignable to method's 'this' of type '{ name: string; }'.
```

One deliberate loophole: a function type that returns `void` accepts a function that returns something, because the result is ignored.

```ts
const callback: () => void = () => 42; // allowed
```

### Classes

```ts
abstract class Repository<T extends { id: number }> {
  static readonly kind = 'repository';

  protected readonly items = new Map<number, T>();
  #writes = 0;       // ECMAScript private: enforced at runtime
  private reads = 0; // TypeScript private: enforced only by the compiler

  constructor(protected readonly name: string) {} // parameter property

  abstract validate(item: T): boolean;

  save(item: T): void {
    if (!this.validate(item)) throw new Error(`${this.name}: invalid item`);
    this.items.set(item.id, item);
    this.#writes++;
  }

  get writeCount(): number {
    return this.#writes;
  }
}

class UserRepository extends Repository<{ id: number; email: string }> {
  override validate(item: { id: number; email: string }): boolean {
    return item.email.includes('@');
  }
}
```

Things to know:

- A **parameter property** (`constructor(protected readonly name: string)`) declares and assigns a field in one go. Nest uses them for every injected dependency. They are not erasable syntax (see erasableSyntaxOnly and Node Type Stripping).
- **`override`** makes the compiler verify the member exists in the base class:

```ts error
class Base { run() {} }
export class Child extends Base {
  override walk() {}
}
```

```text error
error TS4113: This member cannot have an 'override' modifier because it is not declared in the base class 'Base'.
```

- **`private` vs `#private`.** The TypeScript keyword is erased, so at runtime the field is an ordinary property. `#name` is real:

```ts error
class A { private x = 1; }
export const r = new A().x;
```

```text error
error TS2341: Property 'x' is private and only accessible within class 'A'.
```

```ts run
class A {
  private x = 1;
  #y = 2;
  get y() { return this.#y; }
}
const a = new A();
console.log((a as any).x, a.y, Object.keys(a));
```

```text output
1 2 [ 'x' ]
```

The `private` field is readable and listed by `Object.keys`. The `#y` field is not listed and cannot be reached from outside.

- With a target of ES2022 or later, TypeScript uses the standard class-field semantics (the `useDefineForClassFields` option, true by default for those targets per the TypeScript docs; Not verified here). This matters when a property is declared and also set by a decorator or a base class, see 0.3.

### Enums vs Unions vs as const

An enum is not erased. It emits an object. This is the real output of `tsc` 6.0.3 for `enum Color { Red, Green = "green" }`:

```text output
export var Color;
(function (Color) {
    Color[Color["Red"] = 0] = "Red";
    Color["Green"] = "green";
})(Color || (Color = {}));
```

Numeric enums also get a reverse mapping (`Color[0]` is `"Red"`). Since TypeScript 5.0 every enum is a union enum, so arbitrary numbers are no longer assignable:

```ts error
enum E { A, B }
export const e: E = 5;
```

```text error
error TS2322: Type '5' is not assignable to type 'E'.
```

On TypeScript 4.9.5 the same code compiles. The alternative that emits no extra object:

```ts
export const Role = { Admin: 'admin', User: 'user' } as const;
export type Role = (typeof Role)[keyof typeof Role];

type _ = Expect<Equal<Role, 'admin' | 'user'>>;
```

| Option | Emits runtime code | Iterable values | Works with `erasableSyntaxOnly` |
|---|---|---|---|
| string literal union (`'a' \| 'b'`) | No | No, unless you also keep an array | Yes |
| `as const` object plus derived type | A plain object | Yes (`Object.values`) | Yes |
| `enum` | An object and an IIFE | Yes | No (TS1294, see the erasable syntax section) |

Prefer unions or `as const` objects in new code. You will still read enums: Nest exports some, for example `HttpStatus`.

### Typing Async Code and Errors

```ts
type A = Awaited<Promise<Promise<number>>>;
type _1 = Expect<Equal<A, number>>;

async function load(): Promise<string> {
  return 'x'; // an async function always returns a Promise, so this is Promise<string>
}

const [text, count] = await Promise.all([load(), Promise.resolve(1)]);
type _2 = Expect<Equal<typeof text, string>>;
type _3 = Expect<Equal<typeof count, number>>;
```

Top-level `await` needs an ES module (`module` set to `nodenext` with `"type": "module"`, or `esnext`).

Under `strict`, a `catch` variable is `unknown` (the `useUnknownInCatchVariables` option). JavaScript can throw anything, so narrow before use:

```ts
try {
  JSON.parse('{oops');
} catch (error) {
  if (error instanceof SyntaxError) console.log(error.message);
  else throw error;
}
```

Custom errors extend `Error`. Since ES2022 the second constructor argument carries a `cause`, which is typed `unknown`:

```ts
class HttpError extends Error {
  override readonly name = 'HttpError';

  constructor(message: string, readonly status: number, options?: ErrorOptions) {
    super(message, options);
  }
}

const e = new HttpError('upstream failed', 502, { cause: new Error('timeout') });
type _ = Expect<Equal<typeof e.cause, unknown>>;
```

An unawaited promise is a silent bug. The Nest 12 scaffold enables the lint rule `typescript/no-floating-promises` for that reason (see 0.5). Kata 12 practises all of this.

## Part 2: Depth

This is where TypeScript stops being a typed JavaScript and becomes a second language. Katas 3 to 7 and 11 practise it.

### Control Flow Analysis in Depth

The compiler tracks the type of every variable at every point in the function. A declared type is what you wrote. A narrowed type is what the compiler can prove at that point. Assignment narrows too:

```ts
let id: string | number = 'abc';
id.toUpperCase(); // ok: the assignment narrowed id to string
id = 5;
id.toFixed();     // ok: now number
```

A `const` alias of a condition keeps the narrowing (TypeScript 4.4):

```ts
type Res = { ok: true; value: number } | { ok: false; error: string };

function show(r: Res): string {
  const isOk = r.ok === true;          // aliased condition
  if (isOk) return String(r.value);    // r is narrowed through the alias
  return r.error;
}
```

Narrowing inside closures used to be lost for any variable that is reassigned somewhere. Since 5.4 it is kept when there are no assignments after the closure is created:

```ts
export function counter(x: string | number) {
  if (typeof x === 'string') x = x.length; // x is a number from here on
  return () => x.toFixed();                // ok on 5.4 and later
}
```

On TypeScript 5.3.3 the same code fails with `Property 'toFixed' does not exist on type 'string | number'`.

The analysis is deliberately not sound in one famous place. Narrowing of a property survives a function call, even though the call may have changed it:

```ts
export function risky(o: { v: string | undefined }, reset: () => void): number | undefined {
  if (o.v !== undefined) {
    reset();            // might set o.v back to undefined
    return o.v.length;  // compiles, can crash
  }
  return undefined;
}
```

This is a trade-off the TypeScript team made on purpose: invalidating on every call would make narrowing useless. Treat a narrowed mutable property as stale after any call that could touch it.

### Structural Typing Pitfalls

**Excess property checks apply only to fresh object literals.** A literal written directly at the assignment is checked for unknown keys. The same object through a variable is not:

```ts error
const p: { a: number } = { a: 1, b: 2 };
```

```text error
error TS2353: Object literal may only specify known properties, and 'b' does not exist in type '{ a: number; }'.
```

```ts
const wide = { a: 1, b: 2 };
export const p: { a: number } = wide; // fine: not a fresh literal, so no excess check
```

**`Object.keys` returns `string[]`, not `(keyof T)[]`.** A value of type `{ x: number; y: number }` may be a subtype with more keys, so the compiler cannot promise the keys are only those two:

```ts error
const point = { x: 1, y: 2 };
for (const key of Object.keys(point)) {
  console.log(point[key]);
}
```

```text error
error TS7053: Element implicitly has an 'any' type because expression of type 'string' can't be used to index type '{ x: number; y: number; }'.
No index signature with a parameter of type 'string' was found on type '{ x: number; y: number; }'.
```

**Weak types.** A type whose properties are all optional rejects values that share no property with it:

```ts error
const options = { timeout: 1000 };
export const w: { retries?: number } = options;
```

```text error
error TS2559: Type '{ timeout: number; }' has no properties in common with type '{ retries?: number; }'.
```

**Brands give you nominal typing.** Two structurally identical string types are interchangeable, which is a bug when they are IDs. A brand adds a phantom property that no real value has:

```ts error
declare const brand: unique symbol;
type Brand<T, B> = T & { readonly [brand]: B };
type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;

const toUserId = (s: string) => s as UserId;
function getUser(id: UserId): void {}

getUser(toUserId('u1'));
getUser('o1' as OrderId);
```

```text error
error TS2345: Argument of type 'OrderId' is not assignable to parameter of type 'UserId'.
```

**Private members make a class nominal.** Two classes with a `private` member of the same name are not compatible, because each declaration is its own member:

```ts error
class Cat { private lives = 9; }
class Dog { private lives = 9; }
export const pet: Cat = new Dog();
```

```text error
error TS2322: Type 'Dog' is not assignable to type 'Cat'.
Types have separate declarations of a private property 'lives'.
```

### Variance and Assignability

Variance answers: if `Dog` is assignable to `Animal`, is `Box<Dog>` assignable to `Box<Animal>`?

| Where the type appears | Variance | Rule |
|---|---|---|
| Return type, readonly property | Covariant | `Producer<Dog>` fits `Producer<Animal>` |
| Parameter type (with `strictFunctionTypes`) | Contravariant | `Consumer<Animal>` fits `Consumer<Dog>`, not the reverse |
| Mutable property, or both positions | Invariant | Neither direction fits |

```ts
interface Animal { name: string }
interface Dog extends Animal { bark(): void }

// Covariant position: something that makes Dogs also makes Animals.
declare const makeDog: () => Dog;
export const makeAnimal: () => Animal = makeDog;
```

```ts error
interface Animal { name: string }
interface Dog extends Animal { bark(): void }

// Contravariant position: something that consumes Dogs cannot consume every Animal.
const onDog: (d: Dog) => void = (d) => d.bark();
export const onAnimal: (a: Animal) => void = onDog;
```

```text error
error TS2322: Type '(d: Dog) => void' is not assignable to type '(a: Animal) => void'.
Types of parameters 'd' and 'a' are incompatible.
Property 'bark' is missing in type 'Animal' but required in type 'Dog'.
```

`strictFunctionTypes` (part of `strict`) applies this only to function-typed properties. Methods declared with method syntax stay bivariant, for compatibility with patterns like `Array<T>`:

```ts
interface Animal { name: string }
interface Dog extends Animal { bark(): void }

interface MethodStyle { handle(a: Animal): void }

const onDog = (d: Dog) => d.bark();
export const lenient: MethodStyle = { handle: onDog }; // compiles: method parameters are bivariant
```

```ts error
interface Animal { name: string }
interface Dog extends Animal { bark(): void }

interface PropertyStyle { handle: (a: Animal) => void }

const onDog = (d: Dog) => d.bark();
export const strict: PropertyStyle = { handle: onDog };
```

```text error
error TS2322: Type '(d: Dog) => void' is not assignable to type '(a: Animal) => void'.
```

Arrays are covariant in TypeScript, which is unsound:

```ts
interface Animal { name: string }
interface Dog extends Animal { bark(): void }

const dogs: Dog[] = [];
const animals: Animal[] = dogs;       // compiles
animals.push({ name: 'a cat' });      // now `dogs` holds something that cannot bark
```

Since TypeScript 4.7 you can state and enforce variance with `in` and `out`:

```ts error
interface Producer<out T> { get: () => T }
interface Bad<out T> { set: (v: T) => void }

export type P = Producer<string>;
export type B = Bad<string>;
```

```text error
error TS2636: Type 'Bad<sub-T>' is not assignable to type 'Bad<super-T>' as implied by variance annotation.
```

### Generics: Constraints, Defaults and Inference

A type parameter is a variable at the type level. A constraint (`extends`) limits what can be passed and lets the body use the constraint's members:

```ts
function longest<T extends { length: number }>(a: T, b: T): T {
  return a.length >= b.length ? a : b;
}

export const s = longest('abc', 'de');
export const xs = longest([1, 2, 3], [1]);
type _1 = Expect<Equal<typeof s, 'abc' | 'de'>>;
type _2 = Expect<Equal<typeof xs, number[]>>;
```

Note `s`: both arguments are candidates for `T`, and the compiler keeps the two literal types, so `T` is the union `'abc' | 'de'`, not `string`.

**Inference.** The compiler collects candidates for each type parameter from every place it is used in the arguments, then picks one. Candidates that do not agree are an error:

```ts
function pair<T>(a: T, b: T): [T, T] {
  return [a, b];
}

export const same = pair(1, 2);                      // T is number
export const explicit = pair<string | number>('a', 1); // explicit type argument widens T
```

```ts error
function pair<T>(a: T, b: T): [T, T] {
  return [a, b];
}
pair('a', 1);
```

```text error
error TS2345: Argument of type 'number' is not assignable to parameter of type 'string'.
```

When a parameter should take part in checking but not in inference, see NoInfer.

**Defaults and dependent parameters.**

```ts
type Box<T = string> = { value: T };
type _1 = Expect<Equal<Box, { value: string }>>;

function getProp<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]; // K depends on T: the key must belong to the object
}
export const port = getProp({ host: 'h', port: 3000 }, 'port');
type _2 = Expect<Equal<typeof port, number>>;
```

**Instantiation expressions** (TypeScript 4.7) fix a function's type argument without calling it:

```ts
function wrap<T>(value: T): { value: T } {
  return { value };
}
const wrapString = wrap<string>;
type _ = Expect<Equal<ReturnType<typeof wrapString>, { value: string }>>;
```

**Nest's `Type<T>`.** This is the real definition from `@nestjs/common`: a class constructor that makes a `T`. It is how Nest talks about "a class" in a type-safe way:

```ts
interface Type<T = any> extends Function {
  new (...args: any[]): T;
}

function create<T>(classRef: Type<T>): T {
  return new classRef();
}

class Cat {
  meow(): string { return 'meow'; }
}

export const sound = create(Cat).meow();
```

Rules of thumb: a type parameter that appears only once in a signature usually should not exist. Avoid `T extends any`. Prefer constraints over casts inside the body.

### keyof, typeof and Indexed Access Types

```ts
const config = { host: 'localhost', port: 3000, tls: false };

type Config = typeof config;            // typeof in a type position reads the value's type
type ConfigKey = keyof Config;          // the union of its keys
type Port = Config['port'];             // indexed access: the type of one property
type AnyValue = Config[keyof Config];   // indexed access with a union gives a union

type _1 = Expect<Equal<ConfigKey, 'host' | 'port' | 'tls'>>;
type _2 = Expect<Equal<Port, number>>;
type _3 = Expect<Equal<AnyValue, string | number | boolean>>;

const methods = ['GET', 'POST'] as const;
type Method = (typeof methods)[number]; // [number] indexes every element
type _4 = Expect<Equal<Method, 'GET' | 'POST'>>;

function connect(host: string, port: number) {
  return { host, port };
}
type Conn = ReturnType<typeof connect>;
type Args = Parameters<typeof connect>;
type _5 = Expect<Equal<Conn, { host: string; port: number }>>;
type _6 = Expect<Equal<Args, [host: string, port: number]>>;
```

The pattern `as const` plus `typeof` plus `keyof` lets one runtime value be the single source of truth for a type, which is why it appears in config and enum-replacement code.

### Mapped Types

A mapped type builds an object type by looping over keys: `{ [K in Keys]: Value }`. When `Keys` is `keyof T` the mapping is homomorphic, and it keeps the original `?` and `readonly` modifiers.

```ts
type Flags<T> = { [K in keyof T]: boolean };

type Opt = { a?: number; readonly b: string };
type _1 = Expect<Equal<Flags<Opt>, { a?: boolean; readonly b: boolean }>>;
```

| Syntax | Effect |
|---|---|
| `[K in keyof T]?` | add optional |
| `[K in keyof T]-?` | remove optional |
| `readonly [K in keyof T]` | add readonly |
| `-readonly [K in keyof T]` | remove readonly |
| `[K in keyof T as NewKey]` | rename or drop keys (a key mapped to `never` is dropped) |

```ts
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};
type _1 = Expect<Equal<Getters<{ name: string }>, { getName: () => string }>>;

// Homomorphic mapped types distribute over unions.
type _2 = Expect<
  Equal<Partial<{ a: 1 } | { b: 2 }>, Partial<{ a: 1 }> | Partial<{ b: 2 }>>
>;
```

Katas 4 and 5 rebuild the built-in mapped types and key remapping.

### Conditional Types and infer

`T extends U ? X : Y` picks a type based on assignability. `infer` captures part of a matched type.

```ts
type ElementOf<T> = T extends readonly (infer E)[] ? E : never;
type _1 = Expect<Equal<ElementOf<string[]>, string>>;

// If `infer` has no candidate to pick, it falls back to unknown.
type FirstArg<F> = F extends (first: infer A, ...rest: never[]) => unknown ? A : never;
type _2 = Expect<Equal<FirstArg<(id: number) => void>, number>>;
type _3 = Expect<Equal<FirstArg<() => void>, unknown>>;

// A constraint on infer (TypeScript 4.7).
type FirstString<T> = T extends [infer H extends string, ...unknown[]] ? H : never;
type _4 = Expect<Equal<FirstString<['a', 1]>, 'a'>>;
```

**Distribution.** When the checked type is a naked type parameter, a union is split, each member is checked separately, and the results are joined. Wrapping in a tuple turns that off:

```ts
type ToArray<T> = T extends unknown ? T[] : never;
type ToArrayWhole<T> = [T] extends [unknown] ? T[] : never;

type _1 = Expect<Equal<ToArray<string | number>, string[] | number[]>>;
type _2 = Expect<Equal<ToArrayWhole<string | number>, (string | number)[]>>;

// never is the empty union. Distributing over nothing gives never, not true.
type NaiveIsNever<T> = T extends never ? true : false;
type _3 = Expect<Equal<NaiveIsNever<never>, never>>;
type _4 = Expect<Equal<[never] extends [never] ? true : false, true>>;
```

`Exclude` and `Extract` in the standard library are exactly the distributive pattern (`T extends U ? never : T` and `T extends U ? T : never`). Kata 6 practises all of this.

### Template Literal Types

A template literal type builds string types, and it distributes over unions in each position:

```ts
type Http = 'GET' | 'POST';
type Path = '/users' | '/orders';
type Route = `${Http} ${Path}`; // the cross product: four members

type _1 = Expect<
  Equal<Route, 'GET /users' | 'GET /orders' | 'POST /users' | 'POST /orders'>
>;

type _2 = Expect<
  Equal<
    Uppercase<'get'> | Capitalize<'name'> | Lowercase<'ABC'> | Uncapitalize<'Name'>,
    'GET' | 'Name' | 'abc' | 'name'
  >
>;
```

With `infer`, a template pattern can parse strings. This is how router libraries type `req.params`:

```ts
type Params<P extends string> =
  P extends `${string}:${infer Name}/${infer Rest}`
    ? Name | Params<`/${Rest}`>
    : P extends `${string}:${infer Name}`
      ? Name
      : never;

type _ = Expect<Equal<Params<'/users/:id/posts/:postId'>, 'id' | 'postId'>>;
```

Be careful with unions in several positions: the cross product grows quickly, and the compiler stops with an error when a type has too many members. Kata 7 builds the route-parameter parser.

### Built-in Utility Types

These are the real definitions from `lib.es5.d.ts` in TypeScript 6.0.3:

| Utility | Definition |
|---|---|
| `Partial<T>` | `{ [P in keyof T]?: T[P] }` |
| `Required<T>` | `{ [P in keyof T]-?: T[P] }` |
| `Readonly<T>` | `{ readonly [P in keyof T]: T[P] }` |
| `Pick<T, K extends keyof T>` | `{ [P in K]: T[P] }` |
| `Record<K extends keyof any, T>` | `{ [P in K]: T }` |
| `Exclude<T, U>` | `T extends U ? never : T` |
| `Extract<T, U>` | `T extends U ? T : never` |
| `Omit<T, K extends keyof any>` | `Pick<T, Exclude<keyof T, K>>` |
| `NonNullable<T>` | `T & {}` |
| `Parameters<F>` | `F extends (...args: infer P) => any ? P : never` |
| `ReturnType<F>` | `F extends (...args: any) => infer R ? R : any` |
| `InstanceType<C>` | `C extends abstract new (...args: any) => infer R ? R : any` |
| `ConstructorParameters<C>` | `C extends abstract new (...args: infer P) => any ? P : never` |
| `Awaited<T>` | recursive: unwraps `Promise`-like values (and anything with a callable `then`) |
| `NoInfer<T>` | built in to the compiler (`intrinsic`) |

Two senior-level details about `Omit`:

```ts
interface User { id: number; name: string; email?: string }

// Omit accepts any key, so a typo is silently ignored.
type Typo = Omit<User, 'idd'>;
type _1 = Expect<Equal<Typo, Pick<User, keyof User>>>;

// Omit is not distributive. On a union it keeps only the keys common to every member.
type A = { kind: 'a'; x: number };
type B = { kind: 'b'; y: string };
type Collapsed = Omit<A | B, 'kind'>;
type _2 = Expect<Equal<Collapsed, {}>>;

type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never;
type _3 = Expect<Equal<DistributiveOmit<A | B, 'kind'>, { x: number } | { y: string }>>;
```

### How Nest Builds PartialType and PickType

In a Nest app a "create" DTO is a class, and the "update" DTO is usually "the same fields, all optional". Nest ships helpers for that in `@nestjs/mapped-types` (3.2 covers them in full). Their real signatures, read from the installed package (version 12.0.1), are:

```text
PartialType<T>(classRef: Type<T>, options?: { skipNullProperties?: boolean })
  : MappedType<RemoveFieldsWithType<Partial<T>, Function>>

PickType<T, K extends keyof T>(classRef: Type<T>, keys: readonly K[])
  : MappedType<RemoveFieldsWithType<Pick<T, (typeof keys)[number]>, Function>>

OmitType<T, K extends keyof T>(classRef: Type<T>, keys: readonly K[])
  : MappedType<RemoveFieldsWithType<Omit<T, (typeof keys)[number]>, Function>>
```

The ingredients are the ones in this document: `Type<T>`, `Partial`, `Pick`, `Omit`, `keyof`, and indexed access with `(typeof keys)[number]`. The runtime half is a function that returns a new class, which copies the validation and transformation metadata of the original (see 3.2) and is typed as a constructor of the mapped type. `IntersectionType` uses a conditional type whose parameter position flips a union into an intersection:

```ts
type UnionToIntersection<U> =
  (U extends any ? (k: U) => void : never) extends (k: infer I) => void ? I : never;

type _ = Expect<Equal<UnionToIntersection<{ a: 1 } | { b: 2 }>, { a: 1 } & { b: 2 }>>;
```

Inference from a contravariant (parameter) position produces an intersection, which is the trick.

Here is the idea reduced to a teaching sketch. It is not the real implementation, because it skips the metadata copying that makes validation work:

```ts
interface Type<T = any> extends Function {
  new (...args: any[]): T;
}

function PartialType<T>(classRef: Type<T>): Type<Partial<T>> {
  class PartialClassType {}
  Object.defineProperty(PartialClassType, 'name', { value: `Partial${classRef.name}` });
  return PartialClassType as Type<Partial<T>>;
}

class CreateUserDto {
  name!: string;
  email!: string;
}

class UpdateUserDto extends PartialType(CreateUserDto) {}

type _ = Expect<Equal<UpdateUserDto['name'], string | undefined>>;
export const update: UpdateUserDto = {}; // every property is optional
```

The key move is the final `as Type<Partial<T>>`: the function creates a class at runtime and tells the compiler what it looks like. Kata 11 builds the type-level half.

### Declaration Merging and Module Augmentation

Declaring the same interface twice merges the declarations (shown earlier). Merging is also how you add to someone else's types. The common Nest-era use is typing environment variables by augmenting the global `ProcessEnv`:

```ts
declare global {
  namespace NodeJS {
    interface ProcessEnv {
      PORT?: string;
      DATABASE_URL: string;
    }
  }
}

export const port: string | undefined = process.env.PORT;
export const url: string = process.env.DATABASE_URL;
```

This only changes the type. Nothing checks at runtime that `DATABASE_URL` is set, so pair it with real validation (see 3.1). The same mechanism augments a package's types with `declare module 'package-name' { ... }`, for example to add a property to an Express `Request`. That form needs the package's types installed, so it is not compiled in this document (Not verified here).

## Part 3: What Changed Since TypeScript 4.7

### Version by Version Table

Each row was tested by compiling a small snippet on the release before and on the release that added the feature. "Before" and "after" are the exact versions used. Features that are not in this table were not tested here.

| Version | Feature | Before | After |
|---|---|---|---|
| 4.9 | `satisfies` operator | 4.8.4: parse error TS1005 | 4.9.5: compiles |
| 4.9 | `accessor` keyword | 4.8.4: TS1434 | 4.9.5: compiles |
| 5.0 | `const` type parameters | 4.9.5: TS1139 | 5.0.4: compiles |
| 5.0 | `moduleResolution: bundler` | 4.9.5: TS6046 (invalid value) | 5.0.4: accepted |
| 5.0 | `verbatimModuleSyntax` option | 4.9.5: TS5023 (unknown option) | 5.0.4: accepted |
| 5.0 | All enums are union enums | 4.9.5: `const e: E = 5` compiles | 5.0.4: TS2322 |
| 5.0 | ECMAScript decorators without `experimentalDecorators` | 4.9.5: TS1238 and TS1219 | 5.0.4: compiles |
| 5.2 | `using` declarations | 5.1.6: TS1434 | 5.2.2: compiles |
| 5.3 | Import attributes (`with { type: 'json' }`) | 5.2.2: TS1005 | 5.3.3: compiles |
| 5.4 | `NoInfer<T>` | 5.3.3: TS2304 (cannot find name) | 5.4.5: compiles |
| 5.4 | Narrowing kept in closures after the last assignment | 5.3.3: TS2339 | 5.4.5: compiles |
| 5.5 | Inferred type predicates | 5.4.5: TS2322 | 5.5.4: compiles |
| 5.5 | `isolatedDeclarations` option | 5.4.5: TS5023 | 5.5.4: accepted |
| 5.5 | Regular expression syntax checking | 5.4.5: `/(/` compiles | 5.5.4: TS1005 `')' expected` |
| 5.6 | `noUncheckedSideEffectImports` option | 5.5.4: TS5023 | 5.6.3: accepted |
| 5.6 | "Always truthy" check on a regex in `if` | 5.5.4: compiles | 5.6.3: TS2872 |
| 5.7 | `rewriteRelativeImportExtensions` option | 5.6.3: TS5023 | 5.7.3: accepted |
| 5.8 | `erasableSyntaxOnly` option | 5.7.3: TS5023 | 5.8.3: accepted, rejects enums and parameter properties (TS1294) |
| 5.8 | A CommonJS file may `import` an ES module under `nodenext` | 5.7.3: TS1479 | 5.8.3: compiles |
| 5.8 | `module: node18` | 5.7.3: TS6046 | 5.8.3: accepted |
| 5.9 | `module: node20` | 5.8.3: TS6046 | 5.9.3: accepted |
| 5.9 | `import defer` | 5.8.3: TS1005 | 5.9.3: compiles |
| 5.9 | `tsc --init` writes a modern strict config | 5.8.3: `target` es2016, `module` commonjs | 5.9.3: see below |
| 6.0 | New defaults, deprecations and removals | | see TypeScript 6.0 |
| 7.0 | Native compiler written in Go | | see TypeScript 7.0 |

The `tsc --init` change is easy to miss. TypeScript 5.9.3, 6.0.3 and 7.0.2 all generate the same config: `module` nodenext, `target` esnext, `types` empty, `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `isolatedModules`, `noUncheckedSideEffectImports`, `moduleDetection` force, `skipLibCheck`, plus source and declaration maps. TypeScript 5.8.3 generated `target` es2016 with `module` commonjs.

### TypeScript 4.9: satisfies

An annotation replaces the inferred type with the annotated one. `satisfies` only checks the value and keeps the inferred type. Assigning to `never` is a quick way to make the compiler print a type:

```ts error
const palette = { red: [255, 0, 0], green: '#00ff00' } satisfies Record<string, string | number[]>;
const annotated: Record<string, string | number[]> = { red: [255, 0, 0], green: '#00ff00' };

export const a: never = palette.red;
export const b: never = annotated.red;
```

```text error
error TS2322: Type 'number[]' is not assignable to type 'never'.
error TS2322: Type 'string | number[] | undefined' is not assignable to type 'never'.
```

With `satisfies`, `palette.red` is `number[]`. With the annotation it is `string | number[] | undefined`, and any key is allowed. The `undefined` is there because `noUncheckedIndexedAccess` is on and the annotation turned the object into an index-signature record. Without that option it would be `string | number[]`. `satisfies` also still reports mismatches:

```ts error
export const palette = { red: [255, 0, 0], green: 123 } satisfies Record<string, string | number[]>;
```

```text error
error TS2322: Type 'number' is not assignable to type 'string | number[]'.
```

Use `satisfies` for config objects, route tables and lookup maps. Kata 8 practises it.

### TypeScript 4.9: accessor

`accessor` declares a field with an automatically generated private storage slot plus a getter and a setter. Its main use is as a target for standard decorators. This is the real `tsc` 6.0.3 output for `class Box { accessor value = 1; }` with target ES2022:

```text output
export class Box {
    #value_accessor_storage = 1;
    get value() { return this.#value_accessor_storage; }
    set value(value) { this.#value_accessor_storage = value; }
}
```

Nest does not use `accessor`, because it uses the older decorator model (see the next section).

### TypeScript 5.0: const Type Parameters

By default a literal passed to a generic function is widened. `const T` makes the argument be treated as if it ended in `as const`:

```ts
function tuple<const T extends readonly unknown[]>(items: T): T {
  return items;
}

function defineRoute<const T extends { method: string; path: string }>(route: T): T {
  return route;
}

export const t = tuple(['GET', 200]);
export const r = defineRoute({ method: 'GET', path: '/users' });

type _1 = Expect<Equal<typeof t, readonly ['GET', 200]>>;
type _2 = Expect<Equal<typeof r.method, 'GET'>>;
```

### Standard Decorators vs Legacy Decorators

TypeScript 5.0 added support for the ECMAScript (TC39) decorators proposal without any flag. That was tested: the same `@dec class A {}` fails on 4.9.5 with TS1238 and TS1219, and compiles on 5.0.4.

Nest uses the older model, `experimentalDecorators` with `emitDecoratorMetadata`, because parameter decorators and emitted type metadata exist only there. The Nest 12 scaffold sets both flags. The two models are not compatible. The details, and what the compiler emits, are in [0.3](03_typescript_for_nest.md).

One thing that was tested here because the official release posts for 6.0 and 7.0 do not mention it: both TypeScript 6.0.3 and 7.0.2 still emit `__decorate` and `__metadata("design:paramtypes", ...)` when the two legacy flags are on.

### using and await using

`using` (TypeScript 5.2) releases a resource when its scope ends, whether the scope returns, throws or breaks. A class opts in by having a `[Symbol.dispose]()` method (or `[Symbol.asyncDispose]()` for `await using`).

```ts run
class TempFile implements Disposable {
  readonly name: string;

  constructor(name: string) {
    this.name = name;
    console.log(`open ${name}`);
  }

  [Symbol.dispose](): void {
    console.log(`close ${this.name}`);
  }
}

function work(): void {
  using file = new TempFile('a.txt');
  console.log('working');
  throw new Error('boom');
}

try {
  work();
} catch (error) {
  console.log('caught', (error as Error).message);
}
```

```text output
open a.txt
working
close a.txt
caught boom
```

The file is closed before the `catch` runs, with no `try/finally` in `work`. `DisposableStack` collects several cleanups and runs them in reverse order. Kata 10 practises both.

**Runtime support.** This is a runtime feature, not just syntax, so the Node version matters. Tested directly with plain `.mjs` files, no TypeScript involved:

| Node | `Symbol.dispose` | native `using` syntax | `DisposableStack` |
|---|---|---|---|
| 22.23.5 | yes | no (SyntaxError) | no |
| 24.11.1 | yes | yes | yes |
| 24.22.3 | yes | yes | yes |

```text output
$ node -v
v24.22.3
```

Bundlers and test runners can lower the `using` syntax into older code, so tests passed on Node 22 for the syntax. They cannot lower a missing runtime class: on Node 22, kata 10's `DisposableStack` test fails with `DisposableStack is not defined`. Other versions, including Node 26, were not tested.

### NoInfer

Inference collects candidates from every argument that mentions a type parameter. `NoInfer<T>` (TypeScript 5.4) says "check this against `T`, but do not use it to decide `T`":

```ts error
declare function createMachine<S extends string>(states: S[], initial: NoInfer<S>): S;

createMachine(['idle', 'running'], 'idle');
createMachine(['idle', 'running'], 'idel');
```

```text error
error TS2345: Argument of type '"idel"' is not assignable to parameter of type '"idle" | "running"'.
```

Without `NoInfer`, `'idel'` would be a second candidate for `S`, `S` would widen to `'idle' | 'running' | 'idel'`, and the typo would compile. Kata 9 practises it.

### Inferred Type Predicates and Closure Narrowing

Since TypeScript 5.5 the compiler infers a type predicate for simple functions, so the classic `filter` case works without a hand-written guard:

```ts
const values = [1, null, 2];
export const numbers: number[] = values.filter((x) => x !== null);
```

On 5.4.5 this fails with `Type '(number | null)[]' is not assignable to type 'number[]'`. The closure narrowing change from 5.4 is shown in Control Flow Analysis in Depth.

### isolatedDeclarations

`isolatedDeclarations` (TypeScript 5.5) is meant for tools that generate `.d.ts` files without running the type checker, which is mostly relevant to large monorepos and library builds. It asks you to annotate exported APIs explicitly so declarations can be produced from the syntax alone. What was tested here: the option is accepted by 5.5.4 and rejected as an unknown option by 5.4.5. The exact diagnostics it reports were not tested (Not verified).

### erasableSyntaxOnly and Node Type Stripping

Some TypeScript syntax is only types, and removing it leaves valid JavaScript. Other syntax generates code. Node can run `.ts` files directly by stripping the first kind, but it rejects the second. The option `erasableSyntaxOnly` (TypeScript 5.8) makes the compiler report the second kind:

```ts error
// flags: --erasableSyntaxOnly
enum Color { Red }
class Box { constructor(private value: number) {} }
```

```text error
error TS1294: This syntax is not allowed when 'erasableSyntaxOnly' is enabled.
```

The same constructs when Node 24 runs the file directly (real messages):

```text
SyntaxError [ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX]: TypeScript enum is not supported in strip-only mode
SyntaxError [ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX]: TypeScript parameter property is not supported in strip-only mode
SyntaxError [ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX]: TypeScript namespace declaration is not supported in strip-only mode
```

`node --experimental-transform-types file.ts` handles an enum (tested: it ran and printed `1`).

| Erasable (works with stripping) | Not erasable |
|---|---|
| Type annotations, `interface`, `type`, generics | `enum` |
| `as`, `satisfies`, `!` | `namespace` that contains values |
| `import type`, `export type` | Parameter properties (`constructor(private x: number)`) |
| `private`, `readonly` modifiers on fields (tested: `private x = 1` ran) | `import x = require()` |

Nest relies on parameter properties and decorators for dependency injection, so Nest code cannot run with Node's type stripping. It needs a real compile step (see 0.3). Per the Node documentation, type stripping also does not read `tsconfig.json` (Not verified here).

### Importing ES Modules from CommonJS and the node18 and node20 Module Settings

Under `module: nodenext`, a CommonJS file importing an ES-module-only package used to be an error. TypeScript 5.8 allows it, matching the `require(esm)` ability in current Node:

```text
5.7.3: error TS1479: The current file is a CommonJS module whose imports will produce 'require' calls; however, the referenced file is an ECMAScript module and cannot be imported with 'require'. Consider writing a dynamic 'import("./esm_typed.mjs")' call instead.
5.8.3, 6.0.3 and 7.0.2: no error
```

TypeScript 5.8 also added `--module node18`, and 5.9 added `--module node20`, which pin module behavior to what that Node release supports instead of the moving target `nodenext`. Nest 12 itself ships ESM-only packages and relies on `require(esm)` for CommonJS apps (see the roadmap's "What Changed Since the 2022 Material").

### TypeScript 6.0: New Defaults and Removals

TypeScript 6.0 was released on 2026-03-23. It is the release before the native 7.0 and is mostly a clean-up release: it changes defaults and deprecates options that 7.0 removes. The lists below come from the official announcement, and the error messages are from running real configs.

**Changed defaults (official):**

| Option | New default |
|---|---|
| `strict` | `true` (was `false`) |
| `module` | `esnext` |
| `target` | `es2025` |
| `noUncheckedSideEffectImports` | `true` |
| `libReplacement` | `false` |
| `rootDir` | the directory containing `tsconfig.json` |
| `types` | `[]` (was: every package in `node_modules/@types`). `["*"]` restores the old behavior |

The official text does not state the old defaults for `module` and `target` (Not verified).

What this looks like in practice, tested with a tsconfig containing only `"noEmit": true`:

| Code | TypeScript 5.9.3 | TypeScript 6.0.3 and 7.0.2 |
|---|---|---|
| `function f(x) { return x; }` | compiles | `error TS7006: Parameter 'x' implicitly has an 'any' type.` |
| `process.cwd()` | compiles (types loaded automatically) | `error TS2591: Cannot find name 'process'.` The message goes on to suggest installing `@types/node` and adding `'node'` to the `types` field |

**Deprecated in 6.0 and removed in 7.0 (official list, error codes tested):**

| Option or value | Error on 6.0.3 | Error on 7.0.2 |
|---|---|---|
| `target: es5` | TS5107 "is deprecated and will stop functioning in TypeScript 7.0" | TS5108 "has been removed" |
| `moduleResolution: node10` or `classic` | TS5107 | TS5108 |
| `module: amd` | TS5107 | TS5108 |
| `baseUrl` | TS5101 | TS5102 "has been removed", with the hint `Use '"paths": {"*": ["./*"]}' instead.` |
| `outFile` | TS5101 | TS5102 |
| `downlevelIteration` | TS5101 | TS5102 |
| `esModuleInterop: false`, `alwaysStrict: false` | TS5107 | TS5108 |

Setting `"ignoreDeprecations": "6.0"` silences the 6.0 errors. Tested for `baseUrl` and `target: es5`: 6.0.3 compiles cleanly, and 7.0.2 still reports the removal. Also tested: with a `tsconfig.json` present, passing files on the command line is `TS5112` on both, and `--ignoreConfig` is the escape hatch.

Other official additions that were not tested here: the `es2025` target and lib (`RegExp.escape`, `Promise.try`, iterator and `Set` helpers), Temporal types behind the `esnext` lib, `Map.getOrInsert`, subpath imports starting with `#/`, `moduleResolution: bundler` with `module: commonjs`, and `--stableTypeOrdering`. `RegExp.escape` exists on Node 24:

```ts run
console.log(RegExp.escape('a.b*c'));
```

```text output
\x61\.b\*c
```

Note that the leading letter is escaped too (`\x61`), which is by design so the result is safe at the start of a larger pattern.

**Migration checklist for an older project:**

1. Set `types` explicitly (usually `["node"]`), or a lot of globals disappear.
2. Set `rootDir` explicitly if you relied on it being inferred.
3. Expect new errors from `strict`. Fix them, or set `"strict": false` knowingly. That is still allowed.
4. Replace `baseUrl` with `paths` entries, `moduleResolution: node10` with `nodenext` or `bundler`, and drop `target: es5`.
5. Use `ignoreDeprecations: "6.0"` only as a temporary bridge. It has no effect on 7.0.

### TypeScript 7.0: The Native Compiler

TypeScript 7.0 was released on 2026-07-08. It is a port of the compiler to Go, and the announcement calls it about ten times faster (typically 8 to 12 times on full builds). Speed figures here are from the announcement and were not measured.

What was tested on this machine:

- `npm i typescript` installs 7.0.2, because it is now the `latest` tag. The binary is still called `tsc`.
- 7.0.2 compiled the solved exercise for this topic with no errors.
- 7.0.2 still emits decorator metadata with the legacy flags (see Standard Decorators vs Legacy Decorators).
- Vitest ran its tests fine with 7.0.2 installed.
- The Nest CLI refuses it. `nest build` stops with:

```text
Error  The installed TypeScript version (7.0.2) does not expose the programmatic compiler API that the Nest CLI requires. TypeScript 7.0 ships the "tsc" executable only; the compiler API is expected to return in 7.1. Please install TypeScript 6 (e.g. "npm i -D typescript@^6") until then.
```

The announcement says 7.0 ships without a programmatic API, that 7.1 is expected to add a new one, and that tools built on the API (it names typescript-eslint and Volar) and language server plugins stay on 6.0 for now. The package `@typescript/typescript6` with the binary `tsc6` exists on npm (version 6.0.2 when checked) for running both side by side. Installing it was not tested.

The practical rule for this learning repository: **pin `typescript` to `~6.0.3`** in every Nest project and every exercise, and revisit when Nest announces support for 7.1. Code that compiles cleanly on 6.0 (with `stableTypeOrdering` and without `ignoreDeprecations`) is documented to compile the same on 7.0, so nothing you learn here is wasted.

## Part 4: Modules, Config and How TypeScript Runs

### import type and verbatimModuleSyntax

`import type` imports something that exists only at compile time and is always erased. `verbatimModuleSyntax` (TypeScript 5.0) makes the rule strict: an import that is only a type must be written with `type`, and everything not marked `type` is kept exactly as written in the output. That makes the emitted JavaScript predictable for bundlers and test runners that compile one file at a time.

```ts error
// flags: --verbatimModuleSyntax
import { PathLike } from 'node:fs';
export const target: PathLike = '/tmp';
```

```text error
error TS1484: 'PathLike' is a type and must be imported using a type-only import when 'verbatimModuleSyntax' is enabled.
```

The fix is `import type { PathLike }` or `import { type PathLike }`. Under `nodenext`, relative imports in ES modules also need a file extension, and it is the extension of the compiled output (`.js`), not `.ts`:

```text
error TS2835: Relative import paths need explicit file extensions in ECMAScript imports when '--moduleResolution' is 'node16' or 'nodenext'. Did you mean './b.js'?
```

This is why the Nest 12 scaffold writes `import { AppService } from './app.service.js'` in `.ts` files.

### moduleResolution Choices

`moduleResolution` decides how an import string becomes a file.

| Value | Use it for | Notes |
|---|---|---|
| `nodenext` (and `node16`) | Code that Node itself will run, compiled with `tsc` | Follows Node's real rules: `package.json` `type`, `exports`, mandatory extensions in ES modules. The Nest 12 scaffold uses it |
| `bundler` | Code that a bundler or Vite will process | No extension requirement. Allowed with `module: commonjs` since 6.0 |
| `node10` (the old `node`) | Nothing new | Deprecated in 6.0, removed in 7.0 |
| `classic` | Nothing | Deprecated in 6.0, removed in 7.0 |

If the output runs in Node, use `nodenext`. If a bundler stands between your source and the runtime, use `bundler`.

### tsconfig Essentials

| Option | What it does | Advice |
|---|---|---|
| `strict` | Turns on the whole strict family (below). Default `true` since 6.0 | Always on |
| `noUncheckedIndexedAccess` | `xs[0]` and `record[key]` include `undefined` | On for new code |
| `exactOptionalPropertyTypes` | `retries?: number` means absent, not `undefined` | On for new code, off if a library you use fights it |
| `noImplicitOverride` | A member that overrides a base member must say `override` | On |
| `noFallthroughCasesInSwitch`, `noImplicitReturns` | Catch forgotten `break` or `return` | On |
| `verbatimModuleSyntax` | Strict `import type` rules (above) | On |
| `isolatedModules` | Reports code that cannot be compiled one file at a time | On, because every modern runner compiles per file |
| `skipLibCheck` | Do not type-check `.d.ts` files | On in practice, because dependency typings often conflict |
| `module`, `moduleResolution` | See the previous section | `nodenext` for Node |
| `target` | Which JavaScript to emit | Match your Node version (`es2023` to `es2025`) |
| `lib` | Which built-in types exist | Defaults to the target's lib |
| `types` | Which `@types/*` packages load globally. Default `[]` since 6.0 | List them: `["node"]` |
| `rootDir`, `outDir` | Where sources are and where output goes | Set both |
| `declaration`, `sourceMap`, `incremental` | Emit `.d.ts`, source maps, incremental info | `declaration` for libraries |

The `strict` family is: `strictNullChecks`, `noImplicitAny`, `noImplicitThis`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `alwaysStrict` and `useUnknownInCatchVariables`. You can turn individual members off. `strictPropertyInitialization` is the one the Nest scaffold turns off.

`noImplicitOverride` is not enabled in the Nest scaffold, but it is worth turning on in your own code (the `override` keyword section above shows the error you get when it is missing).

### Recommended tsconfig for a Plain Node Library

This is the configuration the examples in this document (and the exercise) assume, with output settings added. Compiling a small library with it produced no errors.

```jsonc
{
  "compilerOptions": {
    // Language and module system: Node runs the output, so follow Node's rules.
    "target": "es2025",
    "lib": ["es2025", "esnext.disposable"], // the second entry adds the types for `using`
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "types": ["node"],

    // Strictness.
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noFallthroughCasesInSwitch": true,

    // Predictable per-file compilation.
    "verbatimModuleSyntax": true,
    "isolatedModules": true,

    // Output.
    "rootDir": "src",
    "outDir": "dist",
    "declaration": true,
    "sourceMap": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

For code that you also want to run directly with Node's type stripping, add `"erasableSyntaxOnly": true`.

### What the Nest 12 Scaffold Uses

This is the `tsconfig.json` that `nest new` generated on this machine (Nest CLI 12.0.13), with what each option is for:

| Option | Value | Why it is there |
|---|---|---|
| `module`, `moduleResolution` | `nodenext` | Node runs the output, and Nest 12 is an ES module project |
| `resolvePackageJsonExports` | `true` | Honor `exports` in dependencies' `package.json` |
| `esModuleInterop`, `allowSyntheticDefaultImports` | `true` | Let `import x from 'cjs-package'` work. TypeScript 6.0 deprecates setting `esModuleInterop` to `false` |
| `isolatedModules` | `true` | Required because Vitest and other tools compile each file separately |
| `declaration` | `true` | Emit `.d.ts` next to the output |
| `removeComments` | `true` | Smaller output |
| `emitDecoratorMetadata`, `experimentalDecorators` | `true` | Nest's decorator model, covered in 0.3 |
| `target` | `ES2023` | Modern Node |
| `sourceMap`, `incremental` | `true` | Debugging and faster rebuilds |
| `outDir`, `rootDir` | `./dist`, `.` | Output folder. `tsconfig.build.json` narrows `rootDir` to `./src` and excludes tests |
| `skipLibCheck` | `true` | Ignore dependency typing conflicts |
| `strict` | `true` | Full strict family... |
| `strictPropertyInitialization` | `false` | ...except this one, because DTO and entity classes declare properties that a framework or validator fills in, so `name: string;` has no initializer |
| `types` | `["vitest/globals", "node"]` | Explicit global types, as required since 6.0 |

Compared with the plain-library config above, the scaffold does not enable `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` or `noImplicitOverride`. You can turn them on in a Nest project. The only cost is some extra `undefined` handling.

### Ways to Run TypeScript

Type checking and running are separate jobs. Most tools that "run" TypeScript only delete the types.

| Tool | Checks types? | What it does | Notes |
|---|---|---|---|
| `tsc` | Yes | Checks and emits JavaScript | The reference compiler. `tsc --noEmit` is the CI type check |
| `nest build` | Yes | Calls the TypeScript compiler API | Needs TypeScript 6 (see the TypeScript 7.0 section) |
| Vite and Vitest | No | Strip types per file | The Nest scaffold's tests pass through it, including decorator metadata |
| SWC, esbuild | No | Strip types per file | Fast builds. Pair with a separate `tsc --noEmit` |
| Node 24 directly (`node file.ts`) | No | Strips erasable syntax only | Rejects enums, parameter properties and value namespaces (see the erasable syntax section) |

Because most runners do not check, a green test run does not mean the types are right. That is why the exercise's `pnpm test` runs `tsc --noEmit` first, and why a real project needs a type-check step in CI. This was tested on the Nest 12 scaffold by adding `export const broken: number = 'not a number';` to a source file: `npm test` (which is just `vitest run`) still passed, `npm run lint` (`oxlint --type-aware`) printed nothing, and only `npm run build` failed, with `error TS2322: Type 'string' is not assignable to type 'number'.` In a Nest project, `nest build` or an explicit `tsc --noEmit` is your type check.

## The Exercise

Do the exercise after reading, one kata at a time. Each kata lines up with a section above:

| Kata | Section |
|---|---|
| 01 narrowing | Narrowing Basics, Type Guards and Assertion Functions |
| 02 discriminated union exhaustive | Discriminated Unions and Exhaustiveness |
| 03 generic constraints | Generics: Constraints, Defaults and Inference |
| 04 mapped types | Mapped Types, Built-in Utility Types |
| 05 key remapping | Mapped Types |
| 06 conditional infer | Conditional Types and infer |
| 07 template literal route params | Template Literal Types |
| 08 satisfies and const | TypeScript 4.9: satisfies, TypeScript 5.0: const Type Parameters |
| 09 noinfer | NoInfer |
| 10 using disposables | using and await using |
| 11 utility composition | How Nest Builds PartialType and PickType |
| 12 error handling unknown | Typing Async Code and Errors |

Start it with `scripts/start_exercise.sh projects/phase_00_orientation/02_typescript_refresher` from the repository root. The README in [the exercise folder](../../projects/phase_00_orientation/02_typescript_refresher/README.md) has the commands and hints. It needs Node 24 (the folder has an `.nvmrc`).

## Interview Questions

### unknown vs any

`any` switches type checking off for a value, and it spreads: anything derived from an `any` is also `any`. `unknown` accepts every value just like `any`, but it allows nothing until you narrow it with `typeof`, `instanceof`, a type guard or a schema parse. Use `unknown` for anything that comes from outside the program: parsed JSON, `catch` variables, request bodies.

### satisfies vs a type annotation

An annotation replaces the inferred type with the annotated type, so you lose precision (`palette.red` becomes `string | number[]`). `satisfies` checks the value against a type but keeps the inferred type (`palette.red` is `number[]`), and still rejects extra or wrong members. Use it for config objects and lookup tables.

### interface vs type

Both describe object shapes. Interfaces merge when declared twice and report extension conflicts as errors. Type aliases can name unions, tuples, mapped and conditional types, and cannot be redeclared. Pick `interface` for object contracts and `type` for computed types. In Nest, DTOs are classes anyway, because only a class exists at runtime.

### Why Object.keys returns string array

A value of type `{ x: number }` can legally have more properties at runtime (structural typing), so the compiler cannot promise that its keys are only `'x'`. Returning `(keyof T)[]` would be unsound. The usual fixes are a cast, `Object.entries`, or a schema that makes the shape exact.

### What never is for and how exhaustiveness works

`never` is the empty set. After every member of a union has been handled, the leftover type is `never`. Passing it to a function that takes `never` compiles only when nothing is left, so adding a union member breaks every `switch` that forgot it at compile time.

### Enums vs literal unions

An enum emits a runtime object (and a reverse mapping for numeric ones) and cannot be erased, so it fails under `erasableSyntaxOnly` and Node type stripping. Since TypeScript 5.0 enums are union enums, so arbitrary numbers are rejected. A string literal union or an `as const` object plus a derived type needs no extra runtime code. Prefer those in new code.

### Variance and strictFunctionTypes

Return positions are covariant and parameter positions contravariant. A function taking `Dog` is not assignable to one taking `Animal`. `strictFunctionTypes` enforces that for function-typed properties but not for methods declared with method syntax, which stay bivariant. Arrays are covariant too, which is unsound. `in` and `out` annotations (4.7) let you state and check variance.

### Conditional type distribution

When the checked type is a naked type parameter, a union is distributed: each member is checked separately and the results are united. `ToArray<string | number>` becomes `string[] | number[]`. Wrapping both sides in a tuple (`[T] extends [U]`) switches it off. A naked `T extends never` applied to `never` returns `never` because there is nothing to distribute over.

### Declaration merging

Interfaces with the same name in the same scope merge their members. Namespaces merge with classes and functions. Global and module augmentation use the same mechanism to extend third-party types, for example adding fields to `ProcessEnv`. Type aliases do not merge and give "Duplicate identifier".

### Why a class can be a DI token and an interface cannot

A class is both a type and a runtime value (the constructor function). An interface is erased at compile time, so there is nothing left at runtime to use as a key. Frameworks that use the class itself as a token rely on that. For interfaces you need a separate runtime token such as a string or `Symbol`, covered in 2.1 and 2.2.

### Type predicates and assertion functions

A type predicate (`v is T`) lets a boolean function narrow its argument. An assertion function (`asserts v is T`) narrows after it returns without throwing. Both are promises: the compiler does not verify the body. Assertion functions must be declared with `function` or an explicitly typed binding. Since TypeScript 5.5 simple predicates are inferred.

### const type parameters vs as const

`as const` is applied by the caller on one expression. A `const` type parameter (5.0) makes the function itself treat its arguments as `as const`, so callers get literal and readonly types without writing it. It only has an effect on literal expressions written directly in the call.

### NoInfer

`NoInfer<T>` (5.4) blocks a position from contributing inference candidates for `T`. It fixes cases where a second argument widens the type parameter and hides a mistake, such as an `initial` value that is not in the list of allowed `states`.

### verbatimModuleSyntax and isolatedModules

`isolatedModules` makes the compiler report code that cannot be compiled one file at a time, such as re-exporting a type without `export type`. `verbatimModuleSyntax` goes further: imports and exports without `type` are kept exactly as written, so the output matches the source and tools that process one file at a time stay correct. Nearly all modern projects want both.

### nodenext vs bundler module resolution

`nodenext` follows Node's real resolution: `package.json` `type` and `exports`, and mandatory file extensions in ES modules. Use it when Node runs the output. `bundler` skips the extension requirement because a bundler resolves files itself. `node10` and `classic` are deprecated in TypeScript 6.0 and removed in 7.0.

### What changed in TypeScript 6 and 7, and why Nest pins 6

6.0 flipped defaults (`strict` on, `types` empty, `rootDir` fixed) and deprecated legacy options. 7.0 is a native Go compiler that is much faster but ships without the programmatic API. The Nest CLI uses that API to build, so it refuses TypeScript 7 until 7.1. Pin `typescript` to `~6.0.x` for now. The tests with Vitest and `tsc --noEmit` already work on 7.

### What using gives you over try and finally

`using` ties a resource's cleanup to a scope, so cleanup cannot be forgotten, runs in reverse order of declaration, and runs on return, throw or break. It needs `Symbol.dispose` and, for `DisposableStack`, a runtime that has it (Node 24 does, Node 22 does not).

### Omit is not what it looks like

`Omit<T, K>` accepts any key, so a typo is silently ignored, and it is not distributive, so on a union it keeps only the keys common to every member. When you need to omit from a union, write a distributive version: `T extends unknown ? Omit<T, K> : never`.

## Check Yourself

- [ ] I can explain what is erased and what survives at runtime, and why that matters for dependency injection tokens.
- [ ] I can write a discriminated union with an exhaustive `switch` from memory.
- [ ] I can explain `unknown`, `never` and `any` without notes.
- [ ] I can explain covariance and contravariance, and predict whether an assignment compiles.
- [ ] I can write `getProp<T, K extends keyof T>` and explain each part.
- [ ] I can rebuild `Partial`, `Pick`, `Omit` and `Record` with mapped types.
- [ ] I can write `ElementOf<T>`, `Unwrap<T>` and explain distribution.
- [ ] I can use `satisfies`, `const` type parameters and `NoInfer` and explain when each helps.
- [ ] I know what `using` does and which Node versions support it natively.
- [ ] I can name what is not erasable syntax and why Nest code needs a real compiler.
- [ ] I can explain the TypeScript 6.0 default changes and why Nest pins TypeScript 6.
- [ ] I can read a `tsconfig.json` and explain every option in the Nest scaffold's.
- [ ] I finished all twelve katas and `pnpm test` is green.

## Further Reading

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [TSConfig reference](https://www.typescriptlang.org/tsconfig/)
- [Announcing TypeScript 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/) and the [6.0 release notes](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html)
- [Announcing TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)
- Release notes for features covered above: [5.0](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-0.html), [5.2](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-2.html), [5.4](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-4.html), [5.5](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-5.html), [5.8](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-8.html)
- Handbook chapters: [conditional types](https://www.typescriptlang.org/docs/handbook/2/conditional-types.html), [mapped types](https://www.typescriptlang.org/docs/handbook/2/mapped-types.html), [utility types](https://www.typescriptlang.org/docs/handbook/utility-types.html)
- Options: [erasableSyntaxOnly](https://www.typescriptlang.org/tsconfig/erasableSyntaxOnly.html), [verbatimModuleSyntax](https://www.typescriptlang.org/tsconfig/verbatimModuleSyntax.html)
- [Node.js: running TypeScript natively](https://nodejs.org/api/typescript.html)
- [type-challenges](https://github.com/type-challenges/type-challenges): graded type-level puzzles, the natural follow-up to katas 4 to 7
- [Total TypeScript](https://www.totaltypescript.com/): tutorials and articles on advanced TypeScript

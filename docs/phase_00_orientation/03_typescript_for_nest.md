# 03: TypeScript Features Nest Is Built On

> **Topic:** 0.3 | **Priority:** Core | **Prerequisite:** [02 TypeScript Refresher](02_typescript_refresher.md) (classes, generics, tsconfig) | **Time:** about 4 hours of reading and experiments, plus the exercises
> **Exercises:** [03_typescript_for_nest](../../projects/phase_00_orientation/03_typescript_for_nest/README.md), then [06_milestone_toy_di](../../projects/phase_00_orientation/06_milestone_toy_di/README.md) | **Next doc:** [04 NestJS Philosophy](04_nestjs_philosophy.md)
>
> **Verified on:** macOS, Node v24.11.1 (the type stripping section also ran on 22.11.0, 22.23.5, 24.22.3 and 26.13.1), TypeScript 6.0.3 (7.0.2 where stated), reflect-metadata 0.2.2, `@nestjs/common` and `@nestjs/core` 12.5.1, Vitest 4.1.12 on Vite 8.3.8, 2026-11-20. Every output shown below was produced by running the code. Where something was not tested, the text says "Not verified".

## Table of Contents

- [Why This Topic Exists](#why-this-topic-exists)
- [What Survives to Runtime](#what-survives-to-runtime)
  - [Types Are Erased, Classes Are Not](#types-are-erased-classes-are-not)
  - [The Consequence for Injection Tokens](#the-consequence-for-injection-tokens)
- [Decorators in One Page](#decorators-in-one-page)
  - [What a Decorator Is](#what-a-decorator-is)
  - [The Four Kinds and Their Arguments](#the-four-kinds-and-their-arguments)
  - [Evaluation Order](#evaluation-order)
  - [Decorator Factories](#decorator-factories)
- [Legacy vs Standard Decorators](#legacy-vs-standard-decorators)
  - [Side by Side](#side-by-side)
  - [Why Nest Uses the Legacy Model](#why-nest-uses-the-legacy-model)
  - [What Is Known About Nest and Standard Decorators](#what-is-known-about-nest-and-standard-decorators)
- [The reflect-metadata API](#the-reflect-metadata-api)
  - [Mental Model](#mental-model)
  - [The Functions](#the-functions)
  - [Prototype Chain Behavior](#prototype-chain-behavior)
  - [Property-Level Metadata](#property-level-metadata)
  - [Pitfalls with Metadata](#pitfalls-with-metadata)
- [emitDecoratorMetadata](#emitdecoratormetadata)
  - [What the Compiler Emits](#what-the-compiler-emits)
  - [Type to Metadata Table](#type-to-metadata-table)
  - [Where Metadata Is Emitted and Where It Is Not](#where-metadata-is-emitted-and-where-it-is-not)
  - [Reading design:paramtypes by Hand](#reading-designparamtypes-by-hand)
- [How Nest Uses Metadata](#how-nest-uses-metadata)
  - [Injectable and the Watermark](#injectable-and-the-watermark)
  - [Inject and Self Declared Dependencies](#inject-and-self-declared-dependencies)
  - [How the Injector Merges Them](#how-the-injector-merges-them)
  - [Controller and Route Decorators](#controller-and-route-decorators)
  - [Parameter Decorators](#parameter-decorators)
  - [SetMetadata and Reflector](#setmetadata-and-reflector)
  - [Reading It All at Bootstrap](#reading-it-all-at-bootstrap)
- [Pitfalls](#pitfalls)
  - [Interfaces and Unions Become Object](#interfaces-and-unions-become-object)
  - [Import Type Silently Breaks Injection](#import-type-silently-breaks-injection)
  - [The isolatedModules Error TS1272](#the-isolatedmodules-error-ts1272)
  - [Circular Imports](#circular-imports)
  - [Property Decorators and useDefineForClassFields](#property-decorators-and-usedefineforclassfields)
  - [Forgetting the Decorator](#forgetting-the-decorator)
  - [Metadata Emission Differs Between tsc and Oxc](#metadata-emission-differs-between-tsc-and-oxc)
- [Why Nest Cannot Run on Node Type Stripping](#why-nest-cannot-run-on-node-type-stripping)
- [How Vitest and Vite 8 Emit Metadata](#how-vitest-and-vite-8-emit-metadata)
- [TypeScript 6 and 7 and Decorators](#typescript-6-and-7-and-decorators)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why This Topic Exists

Nest's programming model, `@Controller()`, `@Injectable()` and constructor injection, rests on three things that are not obvious from reading Nest code:

1. **Decorators**: functions the runtime calls once, when a class is defined.
2. **A metadata store**: the `reflect-metadata` library, which lets those functions attach data to classes, methods and parameters.
3. **Compiler-emitted type metadata**: with `emitDecoratorMetadata`, the compiler writes the constructor parameter types into that store.

Once you can see these three pieces, every Nest decorator becomes readable, you can write your own, and "Nest can't resolve dependencies of X" stops being a mystery.

FastAPI comparison: Python keeps type annotations at runtime, so FastAPI calls `inspect.signature` and reads them directly. TypeScript erases types at compile time. Nest therefore needs the compiler to write the types down as ordinary values (`emitDecoratorMetadata`) before they disappear.

```text
 your source                  compiler                       runtime
 -----------                  --------                       -------
 @Injectable()                tsc, Oxc or SWC, with          __decorate([
 class A {                    emitDecoratorMetadata  ----->    Injectable(),
   constructor(                                                __metadata("design:paramtypes", [Dep])
     dep: Dep) {}                                            ], A)
 }                                                                  |
                                                                    | the module loads
                                                                    v
                                              reflect-metadata store (a WeakMap)
                                              A -> { __injectable__: true,
                                                     design:paramtypes: [Dep] }
                                                                    |
                                                                    | Nest reads it at bootstrap
                                                                    v
                                                           new A(depInstance)
```

---

## What Survives to Runtime

### Types Are Erased, Classes Are Not

TypeScript compiles to JavaScript by removing everything that only exists for the type checker. What is left is what exists at runtime:

| Construct | Exists at runtime? | Notes |
|---|---|---|
| `class` | Yes | A class is both a type and a value (the constructor function). |
| `interface` | No | Leaves no JavaScript at all. |
| `type` alias | No | Same. |
| Generic parameters | No | `Box<string>` and `Box<number>` are the same class at runtime. |
| Numeric and string `enum` | Yes | Compiled to an object. Not erasable syntax, see [Why Nest Cannot Run on Node Type Stripping](#why-nest-cannot-run-on-node-type-stripping). |
| Parameter types, return types | No | Unless a decorator makes the compiler write them down. |
| Decorator calls | Yes | They are ordinary function calls. |

### The Consequence for Injection Tokens

A dependency injection container needs a value to use as a key. A class is a value, so `constructor(private cats: CatsService)` works: the compiler writes `CatsService` into the metadata and the container uses it as the key.

An interface is not a value. If you write `constructor(private logger: Logger)` with `interface Logger`, there is nothing to write down, and the compiler emits `Object`. You will see the exact error this causes in [Interfaces and Unions Become Object](#interfaces-and-unions-become-object). The usual fixes are an abstract class (a class that can act as a token), or a string or symbol token with `@Inject(TOKEN)`. Custom providers are topic 2.2.

---

## Decorators in One Page

### What a Decorator Is

A decorator is a function that the runtime calls **once, at class definition time**, with information about what it decorates. It is not a wrapper that runs on every call. Most Nest decorators do not change behavior at all: they **record metadata** that Nest reads later, during bootstrap.

### The Four Kinds and Their Arguments

This section describes the **legacy** model (`experimentalDecorators: true`), which Nest uses. The standard model differs and is compared in [Side by Side](#side-by-side).

| Kind | Decorates | Arguments received | Return value |
|---|---|---|---|
| Class | the class | `(constructor)` | may return a replacement class |
| Method or accessor | a method | `(target, propertyKey, descriptor)` | may return a new descriptor |
| Property | a field | `(target, propertyKey)` | ignored |
| Parameter | one parameter | `(target, propertyKey, parameterIndex)` | ignored |

`target` is the **prototype** for instance members and the **constructor** for static members. For a **constructor parameter**, `target` is the class itself and `propertyKey` is `undefined`. That last detail is how `@Inject()` knows it is decorating a constructor.

### Evaluation Order

```ts
// legacy.ts, compiled with experimentalDecorators: true
function log(label: string) {
  console.log(`factory   ${label}`);
  return (...args: unknown[]) => {
    console.log(`decorator ${label}  (received ${args.length} args: ${args.map((a) => typeof a).join(', ')})`);
  };
}

@log('class')
class Demo {
  @log('static property') static s = 1;
  @log('instance property') p = 1;

  @log('method') run(@log('param 0') a: string, @log('param 1') b: number) {
    return a + b;
  }

  @log('static method') static sm() {}
}
console.log('--- instance created ---');
new Demo().run('x', 1);
```

Real output:

```text
factory   instance property
decorator instance property  (received 3 args: object, string, undefined)
factory   method
factory   param 0
factory   param 1
decorator param 1  (received 3 args: object, string, number)
decorator param 0  (received 3 args: object, string, number)
decorator method  (received 3 args: object, string, object)
factory   static property
decorator static property  (received 3 args: function, string, undefined)
factory   static method
decorator static method  (received 3 args: function, string, object)
factory   class
decorator class  (received 1 args: function)
--- instance created ---
```

What this shows:

1. **Everything runs at class definition**, before any instance exists. The last line is printed after all decorators have already run.
2. **Instance members first, in declaration order, then static members, then the class.** The class decorator is last.
3. **Parameter decorators run before the method decorator** and in **reverse parameter order** (`param 1` before `param 0`). The third argument is the parameter index (`number`), not a descriptor.
4. **A property decorator gets `undefined` as its third argument.** There is no descriptor for a field.
5. **Static members receive the constructor** (`function`) as `target`, instance members receive the prototype (`object`).

### Decorator Factories

`@Controller('cats')` is a **call** that returns the decorator. The factory runs when the line is evaluated, so it can capture arguments. When several decorators are stacked, the factories run **top to bottom** and the decorators are applied **bottom to top**:

```ts
function tag(name: string) {
  console.log(`  factory   ${name}`);
  return (..._args: unknown[]) => console.log(`  decorator ${name}`);
}

@tag('A')
@tag('B')
class Stacked {}

class Shape {
  @tag('method')
  run(@tag('p0') a: string, @tag('p1') b: number) {}
}
```

```text
stacked decorators on one class:
  factory   A
  factory   B
  decorator B
  decorator A
emitted shape for a method with two parameter decorators:
  factory   method
  factory   p0
  factory   p1
  decorator p1
  decorator p0
  decorator method
```

The reverse order comes from how the compiler emits them. It puts everything for one element into a single list and applies the list from the **last entry to the first**. This is the real emitted code for `Shape.run`, with `emitDecoratorMetadata` on:

```js
__decorate([
    tag('method'),
    __param(0, tag('p0')),
    __param(1, tag('p1')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Number]),
    __metadata("design:returntype", void 0)
], Shape.prototype, "run", null);
```

Read from the bottom: the three `__metadata` entries run **first**, then parameter 1, parameter 0, and finally `tag('method')`. This ordering is why a decorator can read `design:type` or `design:paramtypes`: the compiler's metadata decorators have already run.

---

## Legacy vs Standard Decorators

### Side by Side

The same program with the **standard** (TC39) decorators, compiled with no decorator flags:

```ts
// standard.ts, compiled with no experimentalDecorators flag
function log(label: string) {
  console.log(`factory   ${label}`);
  return (value: unknown, context: ClassMethodDecoratorContext | ClassFieldDecoratorContext | ClassDecoratorContext) => {
    console.log(`decorator ${label}  (kind=${context.kind}, name=${String(context.name)}, value=${typeof value})`);
  };
}

@log('class')
class Demo {
  @log('static field') static s = 1;
  @log('instance field') p = 1;

  @log('method') run(a: string, b: number) {
    return a + b;
  }

  @log('static method') static sm() {}
}
console.log('--- instance created ---');
new Demo().run('x', 1);
```

```text
factory   class
factory   static field
factory   instance field
factory   method
factory   static method
decorator static method  (kind=method, name=sm, value=function)
decorator method  (kind=method, name=run, value=function)
decorator static field  (kind=field, name=s, value=undefined)
decorator instance field  (kind=field, name=p, value=undefined)
decorator class  (kind=class, name=Demo, value=function)
--- instance created ---
```

| | Legacy (`experimentalDecorators`) | Standard (TC39; TypeScript 5.0 added support per its release notes, not re-tested here) |
|---|---|---|
| Enabled by | `"experimentalDecorators": true` | nothing: it is the default when the flag is off |
| Signature | `(target, propertyKey, descriptor?)` | `(value, context)` where `context.kind` is `class`, `method`, `field`, ... |
| Factories | all run top to bottom, source order | all run top to bottom, source order, class first |
| Application order | per element: instance members, then static members, then class | methods (static first), then fields, then the class |
| Parameter decorators | **yes** | **no**: TypeScript reports `TS1206: Decorators are not valid here.` |
| `emitDecoratorMetadata` | yes | not available: `TS5052: Option 'emitDecoratorMetadata' cannot be specified without specifying option 'experimentalDecorators'.` |
| Metadata for fields | none by default (needs `reflect-metadata`) | `context.metadata` object, a newer part of the standard. Not verified here. |

Two small tests behind those table rows:

```text
$ tsc  (standard config)  on:  class A { m(@P() x: string) {} }
std_param.ts(2,13): error TS1206: Decorators are not valid here.

$ tsc  (emitDecoratorMetadata: true, experimentalDecorators absent)
tsconfig.json(1,103): error TS5052: Option 'emitDecoratorMetadata' cannot be specified without specifying option 'experimentalDecorators'.
```

A class decorator typed as `ClassDecorator` (`@Injectable()`, one argument) also compiled without error under the standard config. That is only a type-level coincidence for class decorators. Method, property and parameter decorators written for the legacy model do not carry over.

### Why Nest Uses the Legacy Model

Two Nest features need something only the legacy model provides:

1. **Constructor injection by type** needs `design:paramtypes`, which only `emitDecoratorMetadata` writes, and that flag requires `experimentalDecorators` (the `TS5052` error above).
2. **Parameter decorators** such as `@Body()`, `@Param()` and `@Inject()` have no equivalent in the standard model.

The Nest 12 scaffold's `tsconfig.json` sets both flags: `"experimentalDecorators": true` and `"emitDecoratorMetadata": true`.

### What Is Known About Nest and Standard Decorators

Known:

- `@nestjs/common` and `@nestjs/core` 12.5.1 contain no mention of standard decorators or TC39 (a recursive search of both installed packages found nothing).
- The 12.5.1 `Injectable` helper `mixin()` contains a comment noting that "a compiler that emits decorator metadata may have had no decorator to emit parameter types for" and that "The injector can't take that for a compiler that emits none". So Nest already handles missing emitted metadata for classes built at runtime, which is a separate matter from the standard decorator model.
- The scaffold's generated `AGENTS.md` says validation with Standard Schema libraries works "with no classes or decorator metadata". That is about validation only and says nothing about injection.

Not known: whether or when Nest plans to move to standard decorators. A web search found no Nest issue or announcement about it. Treat any statement about a timeline as unverified.

---

## The reflect-metadata API

### Mental Model

`reflect-metadata` adds a metadata API to the global `Reflect` object. Metadata is stored **outside** the object, in a `WeakMap` keyed by the target. Nothing is added to the class itself:

```text
Object.getOwnPropertyNames(Parent)   -> [ 'length', 'name', 'prototype' ]
Object.getOwnPropertySymbols(Parent) -> []
```

A **slot** is identified by `(metadataKey, target)` or `(metadataKey, target, propertyKey)`. The class-level slot and each property-level slot are separate.

```text
WeakMap<target, Map<propertyKey | undefined, Map<metadataKey, value>>>

Ctl            ->  undefined  -> { 'demo:prefix': 'cats' }        (class-level slot)
Ctl.prototype  ->  'handler'  -> { 'path': '/h', 'method': 'GET' } (property-level slot)
               ->  'other'    -> { ... }
```

### The Functions

| Function | Does |
|---|---|
| `Reflect.defineMetadata(key, value, target, propertyKey?)` | Store a value. Overwrites an existing value for the same slot. |
| `Reflect.getMetadata(key, target, propertyKey?)` | Read a value, **walking the prototype chain**. |
| `Reflect.getOwnMetadata(key, target, propertyKey?)` | Read only what was defined on this exact target. |
| `Reflect.hasMetadata` and `hasOwnMetadata` | The boolean versions of the two reads. |
| `Reflect.getMetadataKeys` and `getOwnMetadataKeys` | List the keys. |
| `Reflect.deleteMetadata(key, target, propertyKey?)` | Remove a value. Returns `true` if it existed. |
| `Reflect.metadata(key, value)` | Returns a **decorator** that calls `defineMetadata`. |

Keys can be strings, symbols or any value. Nest uses strings (`'path'`, `'__guards__'`, `'design:paramtypes'`).

### Prototype Chain Behavior

```ts
import 'reflect-metadata';

class Parent {}
class Child extends Parent {}

Reflect.defineMetadata('role', 'admin', Parent);
console.log("getMetadata('role', Parent)          ->", Reflect.getMetadata('role', Parent));
console.log("hasMetadata('role', Parent)          ->", Reflect.hasMetadata('role', Parent));
console.log("getMetadata('role', Child)           ->", Reflect.getMetadata('role', Child), ' (walks the prototype chain)');
console.log("getOwnMetadata('role', Child)        ->", Reflect.getOwnMetadata('role', Child), ' (own only)');
console.log("hasOwnMetadata('role', Child)        ->", Reflect.hasOwnMetadata('role', Child));
console.log("hasMetadata('role', Child)           ->", Reflect.hasMetadata('role', Child));

Reflect.defineMetadata('role', 'user', Child);
console.log('Parent ->', Reflect.getMetadata('role', Parent), '| Child ->', Reflect.getMetadata('role', Child));

Reflect.defineMetadata('a', 1, Parent);
Reflect.defineMetadata('b', 2, Parent);
console.log('getMetadataKeys(Parent)    ->', Reflect.getMetadataKeys(Parent));
console.log('getOwnMetadataKeys(Child)  ->', Reflect.getOwnMetadataKeys(Child));
console.log('getMetadataKeys(Child)     ->', Reflect.getMetadataKeys(Child));
```

```text
getMetadata('role', Parent)          -> admin
hasMetadata('role', Parent)          -> true
getMetadata('role', Child)           -> admin  (walks the prototype chain)
getOwnMetadata('role', Child)        -> undefined  (own only)
hasOwnMetadata('role', Child)        -> false
hasMetadata('role', Child)           -> true
Parent -> admin | Child -> user
getMetadataKeys(Parent)    -> [ 'role', 'a', 'b' ]
getOwnMetadataKeys(Child)  -> [ 'role' ]
getMetadataKeys(Child)     -> [ 'role', 'a', 'b' ]
```

A class's "prototype chain" for metadata is the constructor chain: `Child.__proto__ === Parent`. So a subclass **inherits** its parent's metadata until it defines its own value for the same key. Whether to use `getMetadata` or `getOwnMetadata` is a design decision. You will see Nest make that choice differently for `@Inject()` tokens and `@Optional()` flags in [How the Injector Merges Them](#how-the-injector-merges-them).

### Property-Level Metadata

```ts
class Ctl { handler() {} other() {} }
Reflect.defineMetadata('path', '/h', Ctl.prototype, 'handler');
console.log("getMetadata('path', Ctl.prototype, 'handler') ->", Reflect.getMetadata('path', Ctl.prototype, 'handler'));
console.log("getMetadata('path', Ctl.prototype, 'other')   ->", Reflect.getMetadata('path', Ctl.prototype, 'other'));
console.log("getMetadata('path', Ctl)                      ->", Reflect.getMetadata('path', Ctl), ' (class-level slot is separate)');
const inst = new Ctl();
console.log("getMetadata('path', inst, 'handler')          ->", Reflect.getMetadata('path', inst, 'handler'), ' (instance walks to the prototype)');
```

```text
getMetadata('path', Ctl.prototype, 'handler') -> /h
getMetadata('path', Ctl.prototype, 'other')   -> undefined
getMetadata('path', Ctl)                      -> undefined  (class-level slot is separate)
getMetadata('path', inst, 'handler')          -> /h  (instance walks to the prototype)
```

### Pitfalls with Metadata

**Mutable values are shared by reference.** `getMetadata` returns the stored object, not a copy, and a child sees the parent's value through the chain:

```ts
Reflect.defineMetadata('routes', [], Parent);
(Reflect.getMetadata('routes', Parent) as string[]).push('x');
console.log("routes after push ->", Reflect.getMetadata('routes', Parent));
console.log("Child sees parent's array (same reference) ->", Reflect.getMetadata('routes', Child) === Reflect.getMetadata('routes', Parent));
```

```text
routes after push -> [ 'x' ]
Child sees parent's array (same reference) -> true
```

If a subclass pushes into that array it changes the parent's metadata. The safe pattern, used in the exercise, is **copy on write**: read with `getOwnMetadata`, build a new array, store it with `defineMetadata`.

**`Reflect.metadata()` is a legacy-signature decorator.** Under the standard decorators it throws at class definition:

```ts
// tsconfig WITHOUT experimentalDecorators
import 'reflect-metadata';
@Reflect.metadata('tag', 'hello')
class Tagged {}
```

`tsc` accepts this file (exit 0), and running it throws a bare `TypeError` from inside `reflect-metadata`. With `experimentalDecorators: true` the same decorator works and `Reflect.getMetadata('tag', Tagged)` returns `hello`.

---

## emitDecoratorMetadata

### What the Compiler Emits

With `experimentalDecorators` and `emitDecoratorMetadata` both on, for every **decorated** declaration the compiler adds up to three `__metadata` entries to the decorator list:

| Key | Emitted for | Value |
|---|---|---|
| `design:type` | properties, accessors and methods | the type of the property, or `Function` for a method |
| `design:paramtypes` | decorated classes (constructor) and decorated methods | array of parameter types, in order |
| `design:returntype` | decorated methods | the return type |

The values are **runtime constructors**: `String`, `Number`, `Boolean`, `Array`, `Promise`, `Object`, or a class. The compiler picks the closest runtime value for the declared type.

### Type to Metadata Table

All of this is real output from one compile with TypeScript 6.0.3, `strict` on. Declarations used (imported from another file, so the "alias" cases are imported types):

```ts
export class Engine {}
export interface Logger { log(m: string): void }
export type Id = string | number;
export type Alias = Engine;
export enum Color { Red, Green }
export enum Label { A = 'a', B = 'b' }
export class Box<T> { value!: T }
```

`design:type` for each property of a decorated class:

| Declared type | `design:type` | Why |
|---|---|---|
| `Engine` (class) | `Engine` | a class is a runtime value |
| `Logger` (interface) | `Object` | no runtime value exists |
| `string \| number` | `Object` | unions collapse to `Object` |
| `string \| null` | `Object` | same, under `strict` |
| `pOptional?: string` | `String` | optional does not change it |
| `Color` (numeric enum) | `Number` | |
| `Label` (string enum) | `String` | |
| `Box<string>` | `Box` | generics are erased |
| `Engine[]` | `Array` | |
| `[string, number]` (tuple) | `Array` | |
| `Promise<string>` | `Promise` | |
| `() => void` | `Function` | |
| `any` | `Object` | |
| `unknown` | `Object` | |
| `bigint` | `BigInt` | |
| `symbol` | `Symbol` | |
| `'a'` (string literal) | `String` | |
| `Id` (alias of a union) | `Object` | |
| `Alias` (alias of a class, imported as a type) | `Object` | a type-only import has no value to emit |
| `{ a: 1 }` | `Object` | |
| `Date` | `Date` | |

For methods and constructors:

```ts
@Mark()
class Probe {
  @Mark()
  method(@Mark() a: Engine, @Mark() b: Logger, @Mark() c: string, @Mark() d?: number): Promise<Engine> {
    return Promise.resolve(a);
  }
  @Mark() sync(): void {}
  @Mark() retInterface(): Logger { return null as never; }
}

@Mark()
class Ctor { constructor(a: Engine, b: Logger, c: Box<number>, d: string[], e: Id, f?: Engine) {} }
```

```text
method:  design:type        -> Function
         design:paramtypes  -> [ 'Engine', 'Object', 'String', 'Number' ]
         design:returntype  -> Promise
sync():  design:returntype  -> undefined
retInterface(): returntype  -> Object
Ctor:    design:paramtypes  -> [ 'Engine', 'Object', 'Box', 'Array', 'Object', 'Engine' ]
```

### Where Metadata Is Emitted and Where It Is Not

```text
Probe (decorated, no constructor parameters)  design:paramtypes -> undefined
class NoDecorator { constructor(a: Engine) {} }   design:paramtypes -> undefined
```

- **Only decorated declarations get metadata.** A class with constructor parameters but no decorator gets nothing. This is why every Nest provider needs `@Injectable()` (or `@Controller()`) even when the decorator itself stores almost nothing.
- **A decorated class with no constructor parameters gets no `design:paramtypes`** at all, not an empty array. Code that reads it must default to `[]`. Nest's `mixin()` adds an empty array for exactly this reason.
- **Any decorator counts.** The exercise relies on this: a method decorated with `@Get()` gets `design:paramtypes` and `design:returntype`.

### Reading design:paramtypes by Hand

```ts
import 'reflect-metadata';
const types: unknown[] = Reflect.getMetadata('design:paramtypes', SomeDecoratedClass) ?? [];
```

This is the entire "magic" of constructor injection: read that array, look up an instance for each entry, call `new`. The milestone [06_milestone_toy_di](../../projects/phase_00_orientation/06_milestone_toy_di/README.md) builds exactly this.

---

## How Nest Uses Metadata

All code in this section is quoted from the installed `@nestjs/common` and `@nestjs/core` 12.5.1 packages (the compiled JavaScript, trimmed for length). The constants come from `@nestjs/common/constants.js`:

```js
export const PATH_METADATA = 'path';
export const METHOD_METADATA = 'method';
export const PARAMTYPES_METADATA = 'design:paramtypes';
export const SELF_DECLARED_DEPS_METADATA = 'self:paramtypes';
export const OPTIONAL_DEPS_METADATA = 'optional:paramtypes';
export const PROPERTY_DEPS_METADATA = 'self:properties_metadata';
export const SCOPE_OPTIONS_METADATA = 'scope:options';
export const ROUTE_ARGS_METADATA = '__routeArguments__';
export const GUARDS_METADATA = '__guards__';
export const INTERCEPTORS_METADATA = '__interceptors__';
export const PIPES_METADATA = '__pipes__';
export const INJECTABLE_WATERMARK = '__injectable__';
export const CONTROLLER_WATERMARK = '__controller__';
```

### Injectable and the Watermark

```js
export function Injectable(options) {
    return (target) => {
        Reflect.defineMetadata(INJECTABLE_WATERMARK, true, target);
        Reflect.defineMetadata(SCOPE_OPTIONS_METADATA, options, target);
    };
}
```

`@Injectable()` stores two values on the class: a marker (`__injectable__`) and the scope options (topic 2.4). It does **not** store the dependencies. Those come from the compiler's `design:paramtypes`. The decorator's real contribution is that having **a** decorator makes the compiler emit the types.

### Inject and Self Declared Dependencies

```js
export function Inject(token) {
    const injectCallHasArguments = arguments.length > 0;
    return (target, key, index) => {
        let type = token || Reflect.getMetadata('design:type', target, key);
        // Try to infer the token in a constructor-based injection
        if (!type && !injectCallHasArguments) {
            type = Reflect.getMetadata(PARAMTYPES_METADATA, target, key)?.[index];
        }
        if (!isUndefined(index)) {
            let dependencies = Reflect.getMetadata(SELF_DECLARED_DEPS_METADATA, target) || [];
            dependencies = [...dependencies, { index, param: type }];
            Reflect.defineMetadata(SELF_DECLARED_DEPS_METADATA, dependencies, target);
            return;
        }
        let properties = Reflect.getMetadata(PROPERTY_DEPS_METADATA, target.constructor) || [];
        properties = [
            ...properties.filter(property => property.key !== key),
            { key, type },
        ];
        Reflect.defineMetadata(PROPERTY_DEPS_METADATA, properties, target.constructor);
    };
}
```

Read it as the same function serving two kinds of target:

- **Constructor parameter**: `index` is a number. It appends `{ index, param: token }` to `self:paramtypes` on the class. The list is rebuilt with a spread (copy on write), as in the exercise.
- **Property**: `index` is `undefined`. It records `{ key, type }` under `self:properties_metadata` on `target.constructor`, where the type falls back to `design:type`.

Parameter decorators run last to first, so this list is in reverse parameter order. The injector does not care, because every entry carries its `index`.

### How the Injector Merges Them

From `@nestjs/core/injector/injector.js`:

```js
reflectConstructorParams(type) {
    const paramtypes = [
        ...(Reflect.getMetadata(PARAMTYPES_METADATA, type) || []),
    ];
    const selfParams = this.reflectSelfParams(type);
    selfParams.forEach(({ index, param }) => (paramtypes[index] = param));
    return Array.from(paramtypes);
}

reflectOptionalParams(type) {
    const ctorOwner = this.getConstructorOwner(type);
    return Reflect.getOwnMetadata(OPTIONAL_DEPS_METADATA, ctorOwner) || [];
}

reflectSelfParams(type) {
    return Reflect.getMetadata(SELF_DECLARED_DEPS_METADATA, type) || [];
}
```

This is exactly the algorithm in the toy container: start from the compiler's `design:paramtypes`, then **replace** entries at the indexes that `@Inject()` declared. A string token wins over the type at the same index.

Note the `getMetadata` / `getOwnMetadata` split from [Prototype Chain Behavior](#prototype-chain-behavior). `@Inject()` tokens and paramtypes are read with `getMetadata`, so they follow the inheritance chain. `@Optional()` flags are read with `getOwnMetadata` on the class that **owns** the constructor. That asymmetry is the mechanism behind the Nest 12 migration note that a subclass declaring its own constructor no longer inherits its parent's `@Optional()` markers (topic 1.4).

### Controller and Route Decorators

```js
export function Controller(prefixOrOptions) {
    // ... normalizes the argument into [path, host, scopeOptions, versionOptions] ...
    return (target) => {
        Reflect.defineMetadata(CONTROLLER_WATERMARK, true, target);
        Reflect.defineMetadata(PATH_METADATA, path, target);
        Reflect.defineMetadata(HOST_METADATA, host, target);
        Reflect.defineMetadata(SCOPE_OPTIONS_METADATA, scopeOptions, target);
        Reflect.defineMetadata(VERSION_METADATA, versionOptions, target);
    };
}

export const RequestMapping = (metadata = defaultMetadata) => {
    const pathMetadata = metadata[PATH_METADATA];
    const path = pathMetadata && pathMetadata.length ? pathMetadata : '/';
    const requestMethod = metadata[METHOD_METADATA] || RequestMethod.GET;
    return (target, key, descriptor) => {
        Reflect.defineMetadata(PATH_METADATA, path, descriptor.value);
        Reflect.defineMetadata(METHOD_METADATA, requestMethod, descriptor.value);
        return descriptor;
    };
};
const createMappingDecorator = (method) => (path) => {
    return RequestMapping({
        [PATH_METADATA]: path,
        [METHOD_METADATA]: method,
    });
};
export const Post = createMappingDecorator(RequestMethod.POST);
export const Get = createMappingDecorator(RequestMethod.GET);
```

`@Controller('cats')` writes the prefix on the class. `@Get(':id')` writes the path and HTTP method on `descriptor.value`, the method **function itself**, not on `(prototype, key)`. Both approaches work. The exercise stores on `(prototype, key)` because it keeps method and parameter metadata in the same kind of slot, and notes the difference in the solved code. `Get`, `Post` and the rest are all produced by one factory, just like the exercise's `createRouteDecorator`.

At bootstrap, `@nestjs/core/router/router-explorer.js` reads the class prefix:

```js
const path = Reflect.getMetadata(PATH_METADATA, metatype);
```

Nothing here runs per request. The route table is built once, from metadata, during bootstrap.

### Parameter Decorators

```js
export function assignMetadata(args, paramtype, index, options, ...legacyPipes) {
    // ... normalizes options ...
    return {
        ...args,
        [`${paramtype}:${index}`]: {
            index,
            data: normalizedOptions.data,
            pipes: normalizedOptions.pipes ?? [],
            ...(normalizedOptions.schema !== undefined && { schema: normalizedOptions.schema }),
        },
    };
}
function createRouteParamDecorator(paramtype) {
    return (data) => (target, key, index) => {
        const args = getParamArgsMetadata(ROUTE_ARGS_METADATA, target, key, index);
        Reflect.defineMetadata(ROUTE_ARGS_METADATA, assignMetadata(args, paramtype, index, { data }),
            target.constructor, key);
    };
}
```

`@Body()`, `@Param()`, `@Query()` and friends are one factory, `createRouteParamDecorator(paramtype)`. Each call merges one entry into a single object keyed by `"<paramtype>:<index>"` and stores it under `__routeArguments__` on `(target.constructor, key)`. The router later reads that object to know which request part to put in which argument. The `schema` field in the stored entry is the v12 Standard Schema option (topic 3.2).

### SetMetadata and Reflector

```js
export const SetMetadata = (metadataKey, metadataValue) => {
    const decoratorFactory = (target, key, descriptor) => {
        if (descriptor) {
            Reflect.defineMetadata(metadataKey, metadataValue, descriptor.value);
            return descriptor;
        }
        Reflect.defineMetadata(metadataKey, metadataValue, target);
        return target;
    };
    decoratorFactory.KEY = metadataKey;
    return decoratorFactory;
};
```

`SetMetadata('roles', ['admin'])` is the public "write your own metadata" tool: for a method it stores on the method function, for a class on the class. `Reflector` is the read side, used in guards (topic 1.7). `Reflector.createDecorator()` builds on `SetMetadata`: it generates a key and returns a typed decorator, so you do not write string keys yourself.

### Reading It All at Bootstrap

Putting the pieces together, the whole startup flow is a series of reads:

```text
@Module metadata   -> which controllers and providers exist
@Controller prefix -> PATH_METADATA on the class
@Get / @Post       -> PATH_METADATA and METHOD_METADATA on each handler function
@Body / @Param     -> ROUTE_ARGS_METADATA per (class, method)
ctor parameters    -> design:paramtypes merged with self:paramtypes
```

Every one of those is a `Reflect.getMetadata` call. The exercise [03_typescript_for_nest](../../projects/phase_00_orientation/03_typescript_for_nest/README.md) rebuilds the route part; the milestone rebuilds the constructor part.

---

## Pitfalls

### Interfaces and Unions Become Object

Real Nest 12.5.1 errors from one test module with three providers:

```ts
import { Dep } from './dep.js';
import type { Dep as DepType, Logger } from './dep.js';   // Dep is a class, Logger is an interface

@Injectable() class Good { constructor(readonly dep: Dep) {} }
@Injectable() class TypeOnly { constructor(readonly dep: DepType) {} }
@Injectable() class WithInterface { constructor(readonly logger: Logger) {} }
```

```text
value import of a class    : OK
'import type' of a class   : Nest can't resolve dependencies of the TypeOnly (?). Please make sure that the argument Function at index [0] is available in the RootTestModule module.
interface-typed parameter  : Nest can't resolve dependencies of the WithInterface (?). Please make sure that the argument at index [0] is available in the current module.
```

The interface case shows an **empty** argument name because the token is `Object`. When you see "the argument  at index [0]" with nothing in it, suspect an interface, union or `any` typed parameter and add `@Inject(TOKEN)`.

### Import Type Silently Breaks Injection

The second line above is the dangerous one. `import type { Dep }` of a **class** compiles without any error, because it is legal TypeScript, but it removes the runtime value. The compiler then has no constructor to write into the metadata, and it emits `Function`. Real emit from `tsc` with `isolatedModules` on:

```text
svc_value_import.js : __metadata("design:paramtypes", [Dep])
svc_type_import.js  : __metadata("design:paramtypes", [Function])
svc_inline_type.js  : __metadata("design:paramtypes", [Function])     // import { type Dep }
svc_iface_type.js   : __metadata("design:paramtypes", [Object])       // import type of an interface
```

Rule: in a file with decorated classes, **import every class used as an injected type with a normal `import`**. Never `import type` it. This is also why `verbatimModuleSyntax` and lint rules that force `import type` for "type-only" usages need an exception for decorated constructor parameters.

### The isolatedModules Error TS1272

The opposite mistake, a **value import of an interface**, is caught by the compiler when `isolatedModules` and `emitDecoratorMetadata` are both on (the Nest 12 scaffold sets both):

```ts
import { Logger } from './iface.js';   // Logger is an interface
@Injectable()
export class Svc4 { constructor(private logger: Logger) {} }
```

```text
svc_iface_value.ts(5,49): error TS1272: A type referenced in a decorated signature must be imported with 'import type' or a namespace import when 'isolatedModules' and 'emitDecoratorMetadata' are enabled.
```

The compiler cannot know, file by file, whether `Logger` is a class or an interface, so it asks you to say so. The two errors together are the whole rule: **classes: normal import. Interfaces and type aliases: `import type`.**

### Circular Imports

Two classes that import each other and use each other in constructors:

```ts
// a.ts                                         // b.ts
import { B } from './b.js';                     import { A } from './a.js';
@Injectable()                                   @Injectable()
export class A { constructor(public b: B) {} }  export class B { constructor(public a: A) {} }
```

The compiler emits `__metadata("design:paramtypes", [B])` in `a.js` and `[A]` in `b.js`. That expression is evaluated **when the class is defined**, so whichever module finishes loading first needs the other one's class before it exists.

With ESM output (what Nest 12 uses), real result when `main.ts` imports `a` first:

```text
file:///.../out/b.js:21
    __metadata("design:paramtypes", [A])
                                     ^
ReferenceError: Cannot access 'A' before initialization
```

With CommonJS output (what Nest used before v12), the same program does **not** throw. It silently stores `undefined`:

```text
A paramtypes: [ [class B] ]
B paramtypes: [ undefined ]
```

So the failure mode depends on the module format: a loud `ReferenceError` in ESM, a silent `undefined` dependency in CommonJS, which Nest then reports as an undefined dependency at bootstrap. The Nest-level fix, `forwardRef()`, and the design-level fixes are topic 2.5. The toy container treats an `undefined` entry as an unresolvable dependency and names it in the error.

### Property Decorators and useDefineForClassFields

A common legacy pattern is a property decorator that installs a getter and setter on the **prototype**. With a modern `target`, TypeScript compiles class fields as `[[Define]]` fields on the **instance**, which shadow the prototype accessor. The Nest scaffold uses `"target": "ES2023"`, so this applies there.

```ts
function Tracked(): PropertyDecorator {
  return (target, key) => {
    const store = new WeakMap<object, unknown>();
    Object.defineProperty(target, key, {
      get() { return store.get(this); },
      set(v: unknown) { console.log(`  setter ran for "${String(key)}" = ${v}`); store.set(this, v); },
      configurable: true,
    });
  };
}
class Model {
  @Tracked() name = 'initial';
}
const m = new Model();
console.log('  m.name ->', m.name);
```

```text
=== target es2021 ===
  setter ran for "name" = initial
  m.name -> initial
=== target es2022 ===
  m.name -> initial
=== target es2022 with useDefineForClassFields: false ===
  setter ran for "name" = initial
  m.name -> initial
```

On `ES2022` and later, `useDefineForClassFields` defaults to `true`, the setter never runs, and the decorator silently does nothing. The decorators in this phase only record metadata, so they are not affected, but a decorator that depends on prototype accessors is. Setting `useDefineForClassFields: false` restores the old behavior. Not verified: which third-party libraries rely on the accessor pattern.

### Forgetting the Decorator

Without a decorator the compiler emits no `design:paramtypes` (see [Where Metadata Is Emitted and Where It Is Not](#where-metadata-is-emitted-and-where-it-is-not)), so a container has no types to read. The exercise demonstrates this and makes the toy container reject undecorated classes with a clear error. What a given Nest version does with such a provider was not tested here.

### Metadata Emission Differs Between tsc and Oxc

The compiler that builds your code decides what gets emitted. `tsc` and the Oxc transformer used by Vite 8 agree on most types but not on all. Real results for the same input, a class constructor with a **type-only imported class** parameter:

| Compiler | Emitted entry |
|---|---|
| `tsc` 6.0.3 | `Function` |
| Oxc (Vite 8.3.8, used by Vitest) | `Object` |

Both are wrong for DI, which is why [Import Type Silently Breaks Injection](#import-type-silently-breaks-injection) matters in both builds. Details of the Oxc output are in [How Vitest and Vite 8 Emit Metadata](#how-vitest-and-vite-8-emit-metadata).

---

## Why Nest Cannot Run on Node Type Stripping

Node can run `.ts` files directly by **stripping** type annotations, without compiling. It only works for syntax that can be erased by replacing it with whitespace. Nest code uses features that cannot be erased. Results from running the same four files on each Node version (`node file.ts`):

| Node | `process.features.typescript` | Types only | Parameter property | `enum` | Decorator |
|---|---|---|---|---|---|
| 22.11.0 | `false` | `ERR_UNKNOWN_FILE_EXTENSION` (stripping is off) | same | same | same |
| 22.23.5 | `"strip"` | runs | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `SyntaxError` |
| 24.11.1 | `"strip"` | runs | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `SyntaxError` |
| 24.22.3 | `"strip"` | runs | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `SyntaxError` |
| 26.13.1 | `"strip"` | runs | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` | `SyntaxError` |

The exact messages. The parameter property and `enum` messages were identical on 22.23.5, 24.11.1, 24.22.3 and 26.13.1. The namespace message was captured on 24.11.1 only:

```ts
// param.ts
export class Greeter {
  constructor(private readonly prefix: string) {}
  greet(name: string): string { return `${this.prefix} ${name}`; }
}
```

```text
SyntaxError [ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX]: TypeScript parameter property is not supported in strip-only mode
SyntaxError [ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX]: TypeScript enum is not supported in strip-only mode
SyntaxError [ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX]: TypeScript namespace declaration is not supported in strip-only mode
```

And for a decorator:

```ts
function Injectable(): ClassDecorator { return () => {}; }
@Injectable()
class A {}
```

```text
@Injectable()
^
SyntaxError: Invalid or unexpected token
```

What each result means for Nest:

- **Parameter properties** (`constructor(private readonly dep: Dep)`) are the standard way to write Nest constructors. They need code generation (assigning `this.dep = dep`), so they are not erasable. The same constructor written as an explicit field plus assignment runs fine.
- **Decorators** are a plain `SyntaxError`: the JavaScript parser in these Node versions does not accept the syntax at all, so no TypeScript step can rescue it.
- **Decorator metadata** is a separate problem: type stripping never has type information, so it can never emit `design:paramtypes`.
- **Enums and namespaces** are not erasable either.

The `--experimental-transform-types` flag does handle parameter properties and enums. On 22.11.0, 22.23.5, 24.11.1 and 24.22.3 `node --experimental-transform-types param.ts` ran the file and printed `hi x` (with an `ExperimentalWarning` on 24.11.1). It does **not** help with decorators: the same flag still reported `SyntaxError: Invalid or unexpected token` on 22.23.5, 24.11.1 and 24.22.3. On Node 26.13.1 the flag no longer exists: `node: bad option: --experimental-transform-types`.

So a Nest app always needs a real compile step (`tsc`, SWC or Oxc) that lowers decorators and emits metadata. This is also why Nest's build and test tooling is configured explicitly, see topic 0.5.

---

## How Vitest and Vite 8 Emit Metadata

Nest tests run under Vitest, which transforms TypeScript with Vite instead of `tsc`. The question is whether `design:paramtypes` still appears. Three configurations of the same two-file project, with the same test (`expect(Reflect.getMetadata('design:paramtypes', Svc)).toEqual([Dep])`):

| `tsconfig.json` flags | Result under Vitest 4.1.12 |
|---|---|
| `experimentalDecorators` and `emitDecoratorMetadata` | passes |
| `experimentalDecorators` only | fails: `expected undefined to deeply equal [ [Function Dep] ]` |
| neither | the file fails to load with `SyntaxError: Invalid or unexpected token` (the decorator syntax was left in place and Node cannot parse it) |

So Vite 8 reads those two flags from your `tsconfig.json` and applies them: the emit is controlled by tsconfig, not by Vitest settings. The `rolldown` package that Vite 8 builds on declares matching transformer options, in its TypeScript typings: `decorator: { legacy, emitDecoratorMetadata, strictNullChecks }`, described as "the same as emitDecoratorMetadata in TypeScript, and it only works when `legacy` is true". I observed the behavior above and read those typings; I did not read Vite's plugin source, so the exact tsconfig-to-option mapping code is Not verified.

What the transformer emits, from calling Vite 8's `transformWithOxc` with `decorator: { legacy: true, emitDecoratorMetadata: true }`:

```ts
import { Dep } from './dep.js';
import type { TDep } from './dep.js';
import { Logger } from './logger.js'; // an interface in the other file, imported by value
@Injectable()
export class Svc {
  constructor(a: Dep, b: TDep, c: Logger, d: string, e: string | null) {}
}
```

```js
Svc = _decorate([Injectable(), _decorateMetadata("design:paramtypes", [
	typeof Dep === "undefined" ? Object : Dep,
	Object,
	typeof Logger === "undefined" ? Object : Logger,
	String,
	Object
])], Svc);
```

The difference from `tsc` explains the `Function` vs `Object` result for type-only imports. The Oxc transformer works on one file at a time and **has no type information**. For a value import it cannot know whether the name is a class or an interface, so it emits a guard, `typeof X === "undefined" ? Object : X`, instead of failing. For `import type` it emits `Object`. `string | null` becomes `Object`, matching `tsc` under `strict` (the `strictNullChecks` option in the typings controls this).

Practical consequences:

- Keep `experimentalDecorators` and `emitDecoratorMetadata` in the tsconfig that Vitest picks up. The Nest 12 scaffold does.
- Code that passes under `tsc` can still differ under Vitest in edge cases such as `import type`. Follow the import rule above and both agree.
- Vitest passed with TypeScript 7.0.2 installed, because Vite does the transform, not `tsc`. Only the type check and the Nest CLI build use the TypeScript package.

---

## TypeScript 6 and 7 and Decorators

The official TypeScript 6.0 and 7.0 announcements do not mention `experimentalDecorators` or `emitDecoratorMetadata` (checked in the 7.0 post in full, and in the part of the 6.0 post that was read). So the behavior below comes from running the compilers, not from release notes.

- **TypeScript 6.0.3** emits `__decorate` and `__metadata("design:paramtypes", [...])` with both flags on. This is what the Nest 12 scaffold pins (`typescript ^6.0.2`).
- **TypeScript 7.0.2** (the Go compiler) also compiled both decorator models. For the legacy and standard programs in [Evaluation Order](#evaluation-order) and [Side by Side](#side-by-side), the output of TypeScript 7.0.2 was identical to TypeScript 6.0.3. A decorated constructor emitted `__metadata("design:paramtypes", [Dep, Number])`.
- **The Nest CLI refuses TypeScript 7 for now.** `nest build` fails with: `The installed TypeScript version (7.0.2) does not expose the programmatic compiler API that the Nest CLI requires. TypeScript 7.0 ships the "tsc" executable only; the compiler API is expected to return in 7.1. Please install TypeScript 6 (e.g. "npm i -D typescript@^6") until then.` Vitest still passed in the same project.

So for a Nest 12 project: stay on TypeScript 6 until a Nest release supports 7.1. Note that `npm i -D typescript` installs 7.0.2 today, so pin the version, as the exercises do with `"typescript": "~6.0.3"`.

---

## Interview Questions

**1. Why can't an interface be used as an injection token in Nest?**
Interfaces are erased at compile time, so there is no runtime value to use as a key. With `emitDecoratorMetadata` the compiler writes `Object` for an interface-typed parameter, and `Object` identifies nothing. Use a class (an abstract class works as a token), or a string or symbol token with `@Inject(TOKEN)`.

**2. What does `emitDecoratorMetadata` emit, and for which declarations?**
`design:type` (properties, methods), `design:paramtypes` (constructor and methods) and `design:returntype` (methods), as runtime constructors like `String`, `Array`, or a class. Only **decorated** declarations get them. An undecorated class with constructor parameters gets nothing, which is why providers need `@Injectable()`.

**3. How does Nest know what to inject into `constructor(private cats: CatsService)`?**
The compiler writes `[CatsService]` into `design:paramtypes` on the class. The injector reads it with `Reflect.getMetadata`, merges in any `@Inject()` overrides stored under `self:paramtypes` (replacing by index), then looks up each token among the providers visible to the module.

**4. What is the evaluation order of decorators?**
At class definition, before any instance exists. Per element: factories run top to bottom, decorators apply bottom to top. Across members: instance members in declaration order, then static members, then the class. For a method, the compiler's metadata decorators run first, then parameter decorators last-to-first, then the method decorator.

**5. Legacy vs standard decorators: which differences matter to Nest?**
Standard decorators have no parameter decorators (`@Body()`, `@Inject()` cannot be expressed) and no `emitDecoratorMetadata` (the compiler rejects the flag without `experimentalDecorators`). Constructor injection by type depends on both, so Nest stays on legacy. Nest has not announced a change that I could find.

**6. Why does `import type { Dep }` break dependency injection silently?**
It removes the runtime value, so the compiler has no constructor to emit and writes `Function` (`tsc`) or `Object` (Oxc). The code compiles, the injector finds no provider for it, and the error mentions `Function` or an empty argument. Import classes used as injected types with a normal `import`.

**7. What does TS1272 mean and how do you fix it?**
With `isolatedModules` and `emitDecoratorMetadata` on, a decorated signature must `import type` interfaces and type aliases, because a single-file compiler cannot tell whether an imported name is a class. Value-import classes, `import type` interfaces.

**8. How do circular imports interact with decorator metadata?**
`design:paramtypes` is evaluated when a class is defined, so a cyclic import means one class is not yet initialized. In ESM that throws `ReferenceError: Cannot access 'A' before initialization`; in CommonJS it silently stores `undefined`. The DI-level fix is `forwardRef()` (topic 2.5), and the design-level fix is to break the cycle.

**9. `getMetadata` vs `getOwnMetadata`: when does it matter?**
`getMetadata` walks the prototype chain, so subclasses inherit values; `getOwnMetadata` reads only the target. It matters for inheritance and for mutable values: pushing into an inherited array changes the parent. Nest reads `@Inject()` tokens with `getMetadata` but `@Optional()` flags with `getOwnMetadata` on the constructor's owner, so optional markers are not inherited when a subclass has its own constructor.

**10. Why can't Nest run on Node's built-in TypeScript support?**
Type stripping only erases syntax. Parameter properties (`constructor(private x: X)`), enums and namespaces need code generation (`ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`), decorators are a `SyntaxError` for the parser, and stripping has no type information to emit `design:paramtypes`. A real compile step is required.

**11. Why does `reflect-metadata` keep data in a side table instead of properties on the class?**
It stores metadata in a `WeakMap` keyed by target and property key, so the class has no added properties or symbols, metadata does not collide with user fields, and it works uniformly for classes, methods, properties and parameters. Entries are garbage collected with their targets.

**12. A decorator you wrote for a field silently stopped working after raising `target` to ES2022. Why?**
`useDefineForClassFields` became `true` by default, so the field is defined on each instance with `[[Define]]` semantics and shadows an accessor that the decorator installed on the prototype. Either set `useDefineForClassFields: false` or stop relying on prototype accessors.

---

## Check Yourself

- [ ] I can explain why an interface cannot be an injection token and what the compiler writes instead.
- [ ] I can name the four decorator kinds and the arguments each receives, including `propertyKey` being `undefined` for constructor parameters.
- [ ] I can predict the order in which these run: two stacked class decorators, a method with two parameter decorators, a static and an instance property.
- [ ] I know which of `design:type`, `design:paramtypes` and `design:returntype` exist for a given declaration, and when none are emitted.
- [ ] I can read `Reflect.getMetadata` / `getOwnMetadata` code and say whether a subclass sees a value.
- [ ] I can explain `self:paramtypes` and how `@Inject()` overrides `design:paramtypes` by index.
- [ ] I know the import rule: classes get a normal import, interfaces and aliases get `import type`.
- [ ] I can explain why circular imports break metadata and what differs between ESM and CommonJS.
- [ ] I can explain why Nest needs a compile step and cannot rely on Node type stripping.
- [ ] I know which compilers and test runners emit metadata (`tsc`, Oxc under Vitest) and that tsconfig controls it.
- [ ] I know why the Nest CLI needs TypeScript 6 today and how to pin it.
- [ ] The exercise `03_typescript_for_nest` passes and I can explain each decorator without looking at it.
- [ ] The milestone `06_milestone_toy_di` passes and I can explain the cycle detection.

---

## Further Reading

- TypeScript: [Decorators handbook page](https://www.typescriptlang.org/docs/handbook/decorators.html), [`experimentalDecorators`](https://www.typescriptlang.org/tsconfig/experimentalDecorators.html) and [`emitDecoratorMetadata`](https://www.typescriptlang.org/tsconfig/#emitDecoratorMetadata) option reference.
- The standard decorators proposal: [tc39/proposal-decorators](https://github.com/tc39/proposal-decorators). Check its README for the current stage; the stage was not verified here.
- [reflect-metadata](https://github.com/rbuckton/reflect-metadata): README and API.
- [Announcing TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/): the Go compiler, the missing API until 7.1.
- Node.js: [Running TypeScript natively](https://nodejs.org/download/release/v24.5.0/docs/api/typescript.html) (the 24.5 page; check the page for your Node version).
- Nest docs: [Custom decorators](https://docs.nestjs.com/custom-decorators), [Custom providers](https://docs.nestjs.com/fundamentals/custom-providers), [Reflection and metadata](https://docs.nestjs.com/fundamentals/execution-context#reflection-and-metadata).
- Nest source: [nestjs/nest](https://github.com/nestjs/nest). In an installed project, read `node_modules/@nestjs/common/decorators/` and `node_modules/@nestjs/core/injector/injector.js`.
- Next in this phase: [04 NestJS Philosophy](04_nestjs_philosophy.md), [05 Tooling and Setup](05_tooling_and_setup.md).

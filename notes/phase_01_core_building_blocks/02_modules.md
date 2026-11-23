# 1.2 Modules

> **Topic 1.2** | Priority: Core | Prerequisites: [03 TypeScript Features Nest Is Built On](../phase_00_orientation/03_typescript_for_nest.md) (decorators and metadata), [1.1 Application Bootstrap](01_application_bootstrap.md) | Time: about 3 hours reading plus 2 hours for the exercise | Exercise: [02_modules](../../projects/phase_01_core_building_blocks/02_modules/README.md) | Next: [1.3 Controllers and Routing](03_controllers_and_routing.md) | Roadmap: [1.2 Modules](../../docs/01_nestjs_roadmap.md#12-modules)

## Table of Contents

- [Why Modules Matter](#why-modules-matter)
- [The Mental Model](#the-mental-model)
  - [A module is a scope for providers](#a-module-is-a-scope-for-providers)
  - [The module graph](#the-module-graph)
  - [The lookup rule in one paragraph](#the-lookup-rule-in-one-paragraph)
- [The Module Decorator](#the-module-decorator)
  - [The four properties](#the-four-properties)
  - [What the decorator really does](#what-the-decorator-really-does)
  - [Validation of keys](#validation-of-keys)
- [How Nest Builds the Module Graph](#how-nest-builds-the-module-graph)
  - [Phase 1: scanForModules](#phase-1-scanformodules)
  - [Phase 2: scanModulesForDependencies](#phase-2-scanmodulesfordependencies)
  - [Phase 3: instance creation](#phase-3-instance-creation)
  - [Module tokens and singleton behavior](#module-tokens-and-singleton-behavior)
  - [Experiment: one module, many importers](#experiment-one-module-many-importers)
- [Encapsulation](#encapsulation)
  - [Private by default](#private-by-default)
  - [Exports are the public API](#exports-are-the-public-api)
  - [The lookup algorithm](#the-lookup-algorithm)
  - [Provider listed twice creates two instances](#provider-listed-twice-creates-two-instances)
  - [Own providers shadow imports](#own-providers-shadow-imports)
  - [Same Token From Two Imports](#same-token-from-two-imports)
- [Re-exporting Modules](#re-exporting-modules)
- [Feature Shared and Core Modules](#feature-shared-and-core-modules)
  - [Feature modules](#feature-modules)
  - [Shared modules](#shared-modules)
  - [Core modules](#core-modules)
  - [What to put in a module and what not to](#what-to-put-in-a-module-and-what-not-to)
- [Global Modules](#global-modules)
  - [How they work internally](#how-they-work-internally)
  - [The hidden dependency problem](#the-hidden-dependency-problem)
  - [When global is justified](#when-global-is-justified)
- [A First Look at Dynamic Modules](#a-first-look-at-dynamic-modules)
  - [The DynamicModule shape](#the-dynamicmodule-shape)
  - [Module identity is by object reference](#module-identity-is-by-object-reference)
  - [The deep-hash option](#the-deep-hash-option)
- [Reading and Fixing Module Errors](#reading-and-fixing-module-errors)
  - [Error catalogue](#error-catalogue)
  - [Decision tree](#decision-tree)
- [Debugging the Module Graph](#debugging-the-module-graph)
  - [Listing modules with ModulesContainer](#listing-modules-with-modulescontainer)
  - [app.select and strict lookups](#appselect-and-strict-lookups)
  - [ModuleRef and modules as providers](#moduleref-and-modules-as-providers)
  - [Nest Devtools in one paragraph](#nest-devtools-in-one-paragraph)
- [Testing Modules](#testing-modules)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Modules Matter

A Nest application is a graph of **modules**. Everything else you will meet in Phase 1 (controllers, providers, middleware, guards) lives inside one of them, and the module decides who can see what. If you misunderstand modules you will meet them again as the most common startup error in Nest: `Nest can't resolve dependencies of X`.

Modules are asked about in almost every Nest interview, usually as one of:

- "Are providers shared between modules?" (No, not unless exported and imported.)
- "What happens if two modules both list the same provider?" (Two instances.)
- "What does `@Global()` do and why is it frowned upon?"
- "Why do you get `Nest can't resolve dependencies`, and how do you debug it?"

Coming from FastAPI, the closest idea is `APIRouter` plus `Depends`, but they differ in an important way. A `Depends` callable can be used from any route anywhere. A Nest provider can only be injected where its module graph allows it, and the check happens once, at startup, before the first request. Modules are Nest's **compile-time visibility rules** for dependency injection.

## The Mental Model

### A module is a scope for providers

A module is a class decorated with `@Module()`. The decorator attaches four lists of metadata to the class:

| Property | What it lists | Visibility |
|---|---|---|
| `providers` | Classes (or custom providers) that Nest instantiates and can inject | **Private** to this module unless exported |
| `controllers` | Classes that handle HTTP routes (topic 1.3) | Registered with the router, not injectable |
| `imports` | Other modules whose **exports** this module wants to use | |
| `exports` | The subset of this module's providers (or imported modules) that importers may use | The module's **public API** |

Think of a module as a small package: `providers` is the private implementation, `exports` is the public interface, `imports` is the list of dependencies.

### The module graph

Starting from the root module you pass to `NestFactory`, Nest follows `imports` recursively. The result is a directed graph:

```
                        AppModule  (root)
                       /         \
                      v           v
             GreeterModule     ReportModule
              imports:           imports:
              CounterModule      CoreModule
                   |                 |
                   |                 v
                   |             CoreModule
                   |              imports: CounterModule
                   |              exports: CounterModule   <- re-export
                   |                 |
                   +--------+--------+
                            v
                      CounterModule      ONE node, ONE instance of its providers
                       providers: CounterService
                       exports:   CounterService

   Added by Nest to every module:   InternalCoreModule  (ModuleRef, Reflector, ...)
   Added to every module if it exists:   every @Global() module
```

Two facts to hold on to:

1. A module is a **node**, not a copy. `CounterModule` above is imported by two modules, yet there is one `CounterModule` and one `CounterService`.
2. An arrow is not enough. For a provider to travel along an arrow, the module at the arrow's head must **export** it.

### The lookup rule in one paragraph

When Nest builds a provider and sees a constructor parameter, it looks for that token in this order. First, the providers of **the module that declares the consumer**. Second, the exports of every module in that module's `imports`, in the order listed, where a module that re-exports another module extends the search through it. The first match wins. If nothing matches you get `UnknownDependenciesException`. The exact algorithm, taken from the source, is under [The Lookup Algorithm](#the-lookup-algorithm).

## The Module Decorator

### The four properties

```ts
@Module({
  imports: [OtherModule],            // modules whose exports I use
  controllers: [CatsController],     // route handlers (topic 1.3)
  providers: [CatsService],          // injectable classes, private by default (topic 1.4)
  exports: [CatsService],            // my public API
})
export class CatsModule {}
```

All four are optional. `@Module({})` is a valid, empty module. The type is `ModuleMetadata` in `@nestjs/common`:

- `imports`: classes, `DynamicModule` objects, promises of `DynamicModule`, or `forwardRef()` wrappers
- `providers`: classes or custom providers (`{ provide, useClass | useValue | useFactory | useExisting }`, topic 2.2)
- `exports`: tokens (class, string or symbol), custom providers, modules, or dynamic modules

### What the decorator really does

The decorator does almost nothing. This is the whole of `@Module()` in `@nestjs/common` 12.5.1 (`decorators/modules/module.decorator.js`, comments removed):

```js
export function Module(metadata) {
    const propsKeys = Object.keys(metadata);
    validateModuleKeys(propsKeys);
    return (target) => {
        for (const property in metadata) {
            if (Object.hasOwn(metadata, property)) {
                Reflect.defineMetadata(property, metadata[property], target);
            }
        }
    };
}
```

It stores each property as metadata on the class under the keys `'imports'`, `'providers'`, `'controllers'` and `'exports'` (the `MODULE_METADATA` constant in `@nestjs/common/constants.js`). Nothing is instantiated and nothing is validated against the other modules at this point. All the real work happens later, when `@nestjs/core` reads that metadata back with `Reflect.getMetadata`. This is the `reflect-metadata` pattern from [Phase 0 note 03](../phase_00_orientation/03_typescript_for_nest.md).

You can see it yourself:

```ts
Reflect.getMetadata('imports', ReportModule)   // [CoreModule]
```

The exercise uses exactly this in one of its tests.

### Validation of keys

The one check the decorator performs is on the key names (`validateModuleKeys` in `@nestjs/common/utils/validate-module-keys.util.js`). A typo throws immediately, when the file loads:

```
typo in a @Module key              Invalid property 'exportz' passed into the @Module() decorator.
```

Note that the values are **not** checked here. Putting `undefined` in an array, or a class that is not a module, is only caught later (or not at all). See [Reading and Fixing Module Errors](#reading-and-fixing-module-errors).

## How Nest Builds the Module Graph

`NestFactory.initialize` in `@nestjs/core/nest-factory.js` (lines 88 to 108 in 12.5.1) runs three steps inside an `ExceptionsZone`:

```js
await dependenciesScanner.scan(await this.toRootModule(module));   // phases 1 and 2
await instanceLoader.createInstancesOfDependencies();              // phase 3
dependenciesScanner.applyApplicationProviders();
```

```
 root module class
        |
        v
 Phase 1  scanForModules            walk `imports` depth first, register every module once
        |
        v
 Phase 2  scanModulesForDependencies   for each module: link imports, add providers,
        |                               controllers and exports (validating exports)
        v
        calculateModulesDistance, then bindGlobalScope   (global modules are linked to everyone)
        |
        v
 Phase 3  InstanceLoader            create prototypes, then instantiate providers,
                                    injectables and controllers of every module
```

### Phase 1: scanForModules

`DependenciesScanner.scanForModules` in `@nestjs/core/scanner.js` recursively visits the root module and its `imports`:

- For each module definition it calls `insertOrOverrideModule`, which ends in `NestContainer.addModule` (`injector/container.js`). `addModule` first computes the module's **token** (see below). If a module with that token already exists, it returns the existing `Module` object with `inserted: false` and does not create a second one.
- It passes a shared `ctxRegistry` array down the recursion so a module definition is never walked twice, which also stops infinite loops on circular imports.
- It throws `UndefinedModuleException` if an entry in `imports` is `undefined`, `InvalidModuleException` for other falsy entries, and (in `insertModule`) `InvalidClassModuleException` if you put an `@Injectable()`, `@Controller()` or exception filter class where a module belongs.

### Phase 2: scanModulesForDependencies

`scanModulesForDependencies` loops over every registered module and calls, in this order, `reflectImports`, `reflectProviders`, `reflectControllers` and `reflectExports`. Each reads the class metadata (plus, for dynamic modules, the extra metadata stored by `container.dynamicModulesMetadata`) and calls into `NestContainer`, which delegates to the `Module` class (`injector/module.js`):

- `Module.addProvider` stores an `InstanceWrapper` per provider in the module's own `providers` map. Because the map is per module, **listing a class in two modules creates two wrappers**.
- `Module.addImport` stores a reference to the imported `Module` object.
- `Module.addExportedProviderOrModule` calls `validateExportedProvider`: an export must be a provider of this very module, or an imported module. Otherwise it throws `UnknownExportException`.

After the loop, `scan` calls `calculateModulesDistance` (used for lifecycle hook order, topic 2.8) and then `container.bindGlobalScope()`, covered in [Global Modules](#global-modules).

### Phase 3: instance creation

`InstanceLoader.createInstancesOfDependencies` creates the object for every provider, injectable and controller of every module. It uses `Promise.all` across modules, so modules are initialised **concurrently**, not in dependency order. You can see this in the startup log of any Nest app. This one is the exercise's solved app:

```
LOG [NestFactory] Starting Nest application...
LOG [InstanceLoader] AppModule dependencies initialized +7ms
LOG [InstanceLoader] LoggerModule dependencies initialized +0ms
LOG [InstanceLoader] CounterModule dependencies initialized +0ms
LOG [InstanceLoader] CoreModule dependencies initialized +0ms
...
LOG [InstanceLoader] ReportModule dependencies initialized +0ms
LOG [RoutesResolver] GreeterController {/greet}: +4ms
LOG [RouterExplorer] Mapped {/greet/:name, GET} route +2ms
...
LOG [NestApplication] Nest application successfully started +1ms
```

The order of the `dependencies initialized` lines says nothing about who depends on whom. The injector (`injector/injector.js`) resolves each constructor parameter on demand, waiting for the dependency to be created first.

### Module tokens and singleton behavior

How does `addModule` know that two imports refer to the same module? Through a **token** computed by `ModuleCompiler.compile` (`injector/compiler.js`) with an opaque-key factory (`injector/opaque-key-factory/`). The default is `ByReferenceModuleOpaqueKeyFactory`:

```js
getOrCreateModuleId(moduleCls, dynamicMetadata, originalRef) {
    // Own property only: a subclass would inherit the id of the module it extends.
    if (Object.prototype.hasOwnProperty.call(originalRef, K_MODULE_ID)) {
        return originalRef[K_MODULE_ID];
    }
    ...
    originalRef[K_MODULE_ID] = moduleId;   // a random string, stored on the class itself
    return moduleId;
}
```

The first time a module class is seen, it gets a random id stored on the class under a symbol. Afterwards the same class gives the same token. So:

- A **static module** (a class) is a singleton by class identity.
- A **dynamic module** is identified by the **object** returned from `forRoot()`. The next section on dynamic modules explains the consequence.

The alternative `DeepHashedModuleOpaqueKeyFactory` hashes the serialized module definition instead. It is selected with the application option `moduleIdGeneratorAlgorithm: 'deep-hash'` (type `'deep-hash' | 'reference'`, default `'reference'`).

### Experiment: one module, many importers

The helper used by every snippet in this note (it starts only the module graph, quietly):

```ts
// boot.ts
import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import type { DynamicModule, Type } from '@nestjs/common';

// Starts only the module graph (no HTTP server) and keeps the log quiet.
export function boot(root: Type<any> | DynamicModule, options: Record<string, unknown> = {}) {
  return NestFactory.createApplicationContext(root, { logger: false, abortOnError: false, ...options });
}

// Returns "compiled" or the first line of the error Nest throws.
export async function tryBoot(root: Type<any> | DynamicModule): Promise<string> {
  try {
    await boot(root);
    return 'compiled';
  } catch (e) {
    return `${(e as Error).constructor.name}: ${(e as Error).message.split('\n')[0]}`;
  }
}
```

(`abortOnError: false` makes Nest throw instead of exiting the process. See [Debugging the Module Graph](#debugging-the-module-graph).)

```ts
import { Injectable, Module } from '@nestjs/common';
import { boot } from './boot.js';

let created = 0;
@Injectable() class CounterService { readonly id = ++created; }
@Injectable() class First { constructor(readonly counter: CounterService) {} }
@Injectable() class Second { constructor(readonly counter: CounterService) {} }

@Module({ providers: [CounterService], exports: [CounterService] }) class CounterModule {}
@Module({ imports: [CounterModule], providers: [First], exports: [First] }) class FirstModule {}
@Module({ imports: [CounterModule], providers: [Second], exports: [Second] }) class SecondModule {}

// CounterModule is imported three times (directly and through both feature modules).
@Module({ imports: [FirstModule, SecondModule, CounterModule] }) class Root {}
const app = await boot(Root);
console.log('imported 3 times  -> instances:', created, '| same object:', app.get(First).counter === app.get(Second).counter);

// The same graph with the imports in another order.
created = 0;
@Module({ imports: [CounterModule, SecondModule, FirstModule] }) class ReorderedRoot {}
const reordered = await boot(ReorderedRoot);
console.log('imports reordered -> instances:', created, '| same object:', reordered.get(First).counter === reordered.get(Second).counter);
```

Output (Node 24.22.3, `@nestjs/core` 12.5.1):

```
imported 3 times  -> instances: 1 | same object: true
imports reordered -> instances: 1 | same object: true
```

One `CounterService` no matter how many times, or in which order, its module is imported. This is why a "shared module" needs no special support: a module is shared by default.

Import order **does** matter in one situation, when two imported modules export the same token. See [Same Token From Two Imports](#same-token-from-two-imports).

## Encapsulation

### Private by default

A provider listed in `providers` can be injected by other providers and controllers **of the same module**, and by nobody else:

```ts
import { Injectable, Module } from '@nestjs/common';
import { boot, tryBoot } from './boot.js';

@Injectable() class CounterService {}
@Injectable() class GreeterService { constructor(readonly counter: CounterService) {} }

// 1. Provider lives in another module that the consumer never imports.
@Module({ providers: [CounterService] }) class CounterModule {}
@Module({ providers: [GreeterService] }) class GreeterModule {}
@Module({ imports: [CounterModule, GreeterModule] }) class NotImportedRoot {}
console.log('not imported :', await tryBoot(NotImportedRoot));

// 2. Imported, but the provider is not exported.
@Module({ imports: [CounterModule], providers: [GreeterService] }) class GreeterWithImport {}
@Module({ imports: [GreeterWithImport] }) class NotExportedRoot {}
console.log('not exported :', await tryBoot(NotExportedRoot));

// 3. Correct.
@Module({ providers: [CounterService], exports: [CounterService] }) class OkCounterModule {}
@Module({ imports: [OkCounterModule], providers: [GreeterService] }) class OkGreeterModule {}
console.log('fixed        :', await tryBoot(OkGreeterModule));

// The full text of the first error, as Nest prints it.
try { await boot(NotImportedRoot); } catch (e) { console.log('\n' + (e as Error).message); }
```

Output:

```
not imported : UnknownDependenciesException: Nest can't resolve dependencies of the GreeterService (?). Please make sure that the argument CounterService at index [0] is available in the GreeterModule module.
not exported : UnknownDependenciesException: Nest can't resolve dependencies of the GreeterService (?). Please make sure that the argument CounterService at index [0] is available in the GreeterWithImport module.
fixed        : compiled

Nest can't resolve dependencies of the GreeterService (?). Please make sure that the argument CounterService at index [0] is available in the GreeterModule module.

Potential solutions:
- Is GreeterModule a valid NestJS module?
- If CounterService is a provider, is it part of the current GreeterModule?
- If CounterService is exported from a separate @Module, is that module imported within GreeterModule?
  @Module({
    imports: [ /* the Module containing CounterService */ ]
  })

For more common dependency resolution issues, see: https://docs.nestjs.com/faq/common-errors
```

The most important observation in this note: **"not imported" and "not exported" produce the same error**. The message names the module that has the problem (the consumer's module) and the missing token, but it cannot tell you which half of the connection is broken. You have to check both: does the owning module export it, and does the consumer's module import the owning module? The [decision tree](#decision-tree) later does that.

### Exports are the public API

`exports` lists which of a module's providers importers may inject. Anything not listed stays private, which is useful. The exercise's `AuditModule` provides `AuditLogStore` and `AuditService` but exports only `AuditService`. The store is an implementation detail that can change without touching any importer.

You may export:

- a provider class: `exports: [CounterService]`
- a custom provider's token: `exports: ['CONFIG']` (a string or symbol)
- a whole module you imported (re-exporting, next section)

Exporting something the module does not have fails at startup:

```
exports a provider it does not have UnknownExportException: Nest cannot export a provider/module that is not a part of the currently processed module (ExportsNothingItOwns). Please verify whether the exported LoggerService is available in this particular context.
```

### The lookup algorithm

This is the logic behind every resolution, from `lookupComponent`, `lookupComponentInParentModules` and `lookupComponentInImportsSync` in `@nestjs/core/injector/injector.js` (12.5.1):

```
resolve(token, consumerModule M):

  1. If M.providers has token                    -> use it. Own providers always win.

  2. For each module I in M.imports, in order:
       a. If I.exports has token AND I.providers has token
                                                 -> use it and STOP (first match wins)
       b. Otherwise search I's own imports, but only through modules that I
          re-exports (I.exports has that imported module). Recursive.

  3. Nothing found                               -> throw UnknownDependenciesException
```

Consequences, each of which is verified by an experiment in this note:

- A provider must be **exported by the module that owns it** to be found through an import (2a).
- A module can pass someone else's provider on only by **re-exporting the whole module** (2b).
- A provider in M's own list shadows any import of the same token (1).
- The first import that matches wins, so with two matching imports the order decides.

### Provider listed twice creates two instances

Because `providers` is per module, listing a class in two modules does not share it. It creates two independent providers that happen to have the same class:

```ts
// continued from the first snippet: CounterService, CounterModule, `created`, boot
@Module({ providers: [CounterService], exports: [CounterService] }) class CopyModule {}
@Injectable() class Third { constructor(readonly counter: CounterService) {} }
@Injectable() class Fourth { constructor(readonly counter: CounterService) {} }
@Module({ imports: [CounterModule], providers: [Third], exports: [Third] }) class ThirdModule {}
@Module({ imports: [CopyModule], providers: [Fourth], exports: [Fourth] }) class FourthModule {}
@Module({ imports: [ThirdModule, FourthModule] }) class DuplicateRoot {}
const dup = await boot(DuplicateRoot);
console.log('listed in 2 modules -> instances:', created, '| same object:', dup.get(Third).counter === dup.get(Fourth).counter);
```

Output:

```
listed in 2 modules -> instances: 2 | same object: false
```

Two `CounterService` objects, each with its own state. This is a real source of production bugs: an in-memory cache, a counter or a connection pool that is "shared" in the code but silently duplicated. The cure is always the same: **a provider has exactly one home module. Everybody else imports that module.** The exercise has a `LegacyModule` with exactly this bug for you to fix.

### Own providers shadow imports

Rule 1 of the lookup means a module's own provider beats an imported one with the same token. You will rarely want this on purpose, but it explains surprising behavior when a token is provided twice. It is shown together with the next experiment.

### Same Token From Two Imports

When two imported modules export the same token, **import order decides**, because the first match wins:

```ts
import { Inject, Injectable, Module } from '@nestjs/common';
import { boot } from './boot.js';

const TOKEN = 'SHARED_TOKEN';
@Module({ providers: [{ provide: TOKEN, useValue: 'from A' }], exports: [TOKEN] }) class AModule {}
@Module({ providers: [{ provide: TOKEN, useValue: 'from B' }], exports: [TOKEN] }) class BModule {}
@Injectable() class Wants { constructor(@Inject(TOKEN) readonly value: string) {} }

@Module({ imports: [AModule, BModule], providers: [Wants] }) class AThenB {}
@Module({ imports: [BModule, AModule], providers: [Wants] }) class BThenA {}
console.log('imports [A, B]:', (await boot(AThenB)).get(Wants).value);
console.log('imports [B, A]:', (await boot(BThenA)).get(Wants).value);

@Module({ imports: [AModule], providers: [{ provide: TOKEN, useValue: 'own' }, Wants] }) class OwnWins {}
console.log('own provider + import of A:', (await boot(OwnWins)).get(Wants).value);
```

Output:

```
imports [A, B]: from A
imports [B, A]: from B
own provider + import of A: own
```

So the statement "import order does not matter" is true only while no two imports export the same token. Nest does not warn about the conflict. Avoid it by giving every token one owner.

## Re-exporting Modules

A module can export a module it imports. Everything the inner module exports then becomes available to anyone who imports the outer module. This is how "bundle" modules are built:

```ts
import { Injectable, Module } from '@nestjs/common';
import { tryBoot } from './boot.js';

@Injectable() class CounterService {}
@Injectable() class Consumer { constructor(readonly counter: CounterService) {} }
@Module({ providers: [CounterService], exports: [CounterService] }) class SharedModule {}

@Module({ imports: [SharedModule], exports: [SharedModule] }) class ReexportsModule {}
@Module({ imports: [ReexportsModule], providers: [Consumer] }) class ViaReexport {}
console.log('re-exports the module      :', await tryBoot(ViaReexport));

@Module({ imports: [SharedModule] }) class ImportsOnlyModule {}
@Module({ imports: [ImportsOnlyModule], providers: [Consumer] }) class ViaImportOnly {}
console.log('imports but no re-export   :', await tryBoot(ViaImportOnly));

@Module({ imports: [SharedModule], exports: [CounterService] }) class ExportsProviderModule {}
console.log('exports an imported provider:', await tryBoot(ExportsProviderModule));
```

Output:

```
re-exports the module      : compiled
imports but no re-export   : UnknownDependenciesException: Nest can't resolve dependencies of the Consumer (?). Please make sure that the argument CounterService at index [0] is available in the ViaImportOnly module.
exports an imported provider: UnknownExportException: Nest cannot export a provider/module that is not a part of the currently processed module (ExportsProviderModule). Please verify whether the exported CounterService is available in this particular context.
```

Three rules fall out of this:

1. Importing is **not transitive**. Importing `ImportsOnlyModule` does not give you what it imported (second line).
2. To pass things on, **re-export the module** (first line). In the lookup algorithm this is step 2b.
3. You cannot re-export a single provider you only got through an import (third line). `validateExportedProvider` in `Module` accepts an export only if it is one of the module's own providers or one of its imported modules. Re-export the module instead.

Use re-exports sparingly. They are good for a deliberate bundle ("the modules every feature needs") and bad as a way to avoid writing `imports`, because they hide where things come from. A module's `exports` is also allowed to contain a `DynamicModule`; `Module.addExportedProviderOrModule` unwraps it to its module class (read from source, not run).

## Feature Shared and Core Modules

These are conventions, not Nest concepts. To Nest they are all just modules. The names describe how you use them.

### Feature modules

A feature module owns one slice of the domain: its controllers, its services and the providers only it needs. `CatsModule`, `OrdersModule`, `AuthModule`. It exports only what other features legitimately need. Organise by **feature** (what the business calls it), not by **technical layer**. A `ControllersModule` and a `ServicesModule` give you the opposite of encapsulation, because everything has to be exported.

### Shared modules

A shared module offers a provider (or a few) to many features: a `CounterModule` here, in a real app a `PaymentsClientModule` or a `StorageModule`. Because modules are singletons, importing it in many places already shares one instance, so "shared" needs no mechanism. The only rules: it exports what it offers, and it has one owner.

### Core modules

A core module bundles cross-cutting infrastructure the whole app needs (configuration, database connection, logging) and is imported **once**, usually by the root module. A core module often combines `@Global()`, `forRoot()` configuration or re-exports. It is the one place where "hidden" dependencies are acceptable, because every module genuinely needs them.

### What to put in a module and what not to

| Do | Don't |
|---|---|
| One module per feature, named after the feature | One module per technical layer |
| Export the smallest public API (usually one service) | Export every provider "just in case" |
| Give each provider one home and import that module | List the same class in several modules |
| Keep the module graph acyclic (extract a shared module) | Fix cycles with `forwardRef` as the first resort (topic 2.5) |
| Make a `SharedModule` that offers specific things | Make a `SharedModule` that imports and re-exports everything |
| Import a module explicitly where it is used | Use `@Global()` so you never have to write `imports` |

## Global Modules

### How they work internally

`@Global()` (in `@nestjs/common/decorators/modules/global.decorator.js`) stores one piece of metadata, `GLOBAL_MODULE_METADATA = '__module:global__'`, as `true` on the class. A dynamic module can set `global: true` in its returned object instead.

`NestContainer.setModule` (in `injector/container.js`) checks that flag when a module is registered:

```js
if (this.isGlobalModule(type, dynamicMetadata)) {
    moduleRef.isGlobal = true;
    // Set global module distance to MAX_VALUE to ensure their lifecycle hooks
    // are always executed first (when initializing the application)
    moduleRef.distance = Number.MAX_VALUE;
    this.addGlobalModule(moduleRef);          // adds it to the container's globalModules set
}
```

and the last step of `DependenciesScanner.scan` is `container.bindGlobalScope()`:

```js
bindGlobalScope()                       { this.modules.forEach(moduleRef => this.bindGlobalsToImports(moduleRef)); }
bindGlobalsToImports(moduleRef)         { this.globalModules.forEach(g => this.bindGlobalModuleToModule(moduleRef, g)); }
bindGlobalModuleToModule(target, global){ if (target === global || target === this.internalCoreModule) return; target.addImport(global); }
```

So a global module is nothing magical. Nest simply **adds it to the `imports` of every other module** after scanning. After that, the ordinary lookup applies, which is why a global module must still `export` its providers. You can see the effect in the output of the module container listing later in this note: the `ConfigModule` in that example is global and appears at the end of every other module's `imports`, after the ones written in code.

```
        AppModule ---imports---> GreeterModule ---imports---> CounterModule
            \                        \                           /
             \--- bound by Nest ------\--- bound by Nest -------/
                          \                    |
                           +------------> LoggerModule  (@Global)
```

The module must still be imported **once somewhere** so that the scanner finds it. Registering it is what puts it in `globalModules`. And the provider must still be exported:

```ts
import { Global, Injectable, Module } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import { tryBoot } from './boot.js';

@Injectable() class LoggerService {}
@Injectable() class Feature { constructor(readonly logger: LoggerService) {} }

@Global()
@Module({ providers: [LoggerService], exports: [LoggerService] })
class LoggerModule {}

@Module({ providers: [Feature] }) class FeatureModule {}      // imports nothing

@Module({ imports: [LoggerModule, FeatureModule] }) class AppModule {}
console.log('global module imported once         :', await tryBoot(AppModule));

@Module({ imports: [FeatureModule] }) class NoLoggerApp {}
console.log('global module never imported        :', await tryBoot(NoLoggerApp));

@Global() @Module({ providers: [LoggerService] }) class GlobalButNotExported {}
@Module({ imports: [GlobalButNotExported, FeatureModule] }) class NotExportedApp {}
console.log('global but provider not exported    :', await tryBoot(NotExportedApp));

// The hidden dependency: FeatureModule looks complete but cannot be tested alone.
const alone = await Test.createTestingModule({ imports: [FeatureModule] }).compile().catch((e: Error) => e);
console.log('FeatureModule on its own in a test  :', alone instanceof Error ? alone.message.split('\n')[0] : 'compiled');
```

Output:

```
global module imported once         : compiled
global module never imported        : UnknownDependenciesException: Nest can't resolve dependencies of the Feature (?). Please make sure that the argument LoggerService at index [0] is available in the FeatureModule module.
global but provider not exported    : UnknownDependenciesException: Nest can't resolve dependencies of the Feature (?). Please make sure that the argument LoggerService at index [0] is available in the FeatureModule module.
FeatureModule on its own in a test  : Nest can't resolve dependencies of the Feature (?). Please make sure that the argument LoggerService at index [0] is available in the FeatureModule module.
```

### The hidden dependency problem

The last line is the real cost of `@Global()`. Reading `FeatureModule` you would conclude it is complete: it provides `Feature`, which needs `LoggerService`, and there is no `imports`. Yet it cannot start by itself. Its dependency is invisible in the module's own code, so:

- you cannot understand a module without knowing which global modules exist,
- you cannot test or reuse a module in isolation without remembering to import the global one,
- the error message points at `FeatureModule` and says "is it part of the current FeatureModule? is the module imported within FeatureModule?" when the fix lives somewhere else.

### When global is justified

Use `@Global()` for things that **every** module really needs and that carry no domain meaning: configuration, a logger. Do not use it as a convenience to skip `imports`. If three feature modules need `PaymentsModule`, writing `imports: [PaymentsModule]` three times is a feature: the graph documents who depends on what.

## A First Look at Dynamic Modules

This is only a first look. The full treatment (`forRootAsync`, `ConfigurableModuleBuilder`, `register` versus `forFeature`) is topic 2.3.

### The DynamicModule shape

A static module has its metadata fixed in the decorator. A dynamic module builds metadata when it is imported, usually from options. By convention a static method on the class returns an object with the same four properties plus `module` (which class it belongs to) and an optional `global`:

```ts
interface DynamicModule extends ModuleMetadata {   // imports, controllers, providers, exports
  module: Type<any>;
  global?: boolean;
}
```

```ts
@Module({})
class ConfigModule {
  static forRoot(options: { greeting: string }): DynamicModule {
    return { module: ConfigModule, providers: [{ provide: 'OPTS', useValue: options }, Settings], exports: [Settings] };
  }
}
```

The names `forRoot` (configure once, usually in the root module), `register` (configure per importer) and `forFeature` (add per-feature pieces to a root-configured module) are conventions. Nest treats them all the same: it only cares about the object returned.

### Module identity is by object reference

`DependenciesScanner.scanForModules` merges the static `@Module` metadata of `module` with the extra properties of the object, and `ModuleCompiler.compile` gives the **object** its token (the by-reference factory stores the id on the object). Two calls to `forRoot()` return two different objects, so Nest registers **two modules**, each with its own `Settings`:

```ts
import { DynamicModule, Inject, Injectable, Module } from '@nestjs/common';
import { boot } from './boot.js';

let created = 0;
@Injectable()
class Settings {
  readonly id = ++created;
  constructor(@Inject('OPTS') readonly options: { greeting: string }) {}
}

@Module({})
class ConfigModule {
  static forRoot(options: { greeting: string }): DynamicModule {
    return { module: ConfigModule, providers: [{ provide: 'OPTS', useValue: options }, Settings], exports: [Settings] };
  }
}

@Injectable() class One { constructor(readonly settings: Settings) {} }
@Injectable() class Two { constructor(readonly settings: Settings) {} }

// forRoot() called in two modules, same options.
@Module({ imports: [ConfigModule.forRoot({ greeting: 'hi' })], providers: [One], exports: [One] }) class OneModule {}
@Module({ imports: [ConfigModule.forRoot({ greeting: 'hi' })], providers: [Two], exports: [Two] }) class TwoModule {}
@Module({ imports: [OneModule, TwoModule] }) class AppModule {}
const app = await boot(AppModule);
console.log('forRoot() twice            -> Settings created:', created, '| shared:', app.get(One).settings === app.get(Two).settings);

// The same dynamic module OBJECT imported twice.
created = 0;
const once = ConfigModule.forRoot({ greeting: 'hi' });
@Module({ imports: [once], providers: [One], exports: [One] }) class OneModuleB {}
@Module({ imports: [once], providers: [Two], exports: [Two] }) class TwoModuleB {}
@Module({ imports: [OneModuleB, TwoModuleB] }) class AppModuleB {}
const appB = await boot(AppModuleB);
console.log('same object imported twice -> Settings created:', created, '| shared:', appB.get(One).settings === appB.get(Two).settings);

// Same graph as the first one, with the other module id algorithm.
created = 0;
const appC = await boot(AppModule, { moduleIdGeneratorAlgorithm: 'deep-hash' });
console.log("deep-hash, forRoot() twice -> Settings created:", created, '| shared:', appC.get(One).settings === appC.get(Two).settings);
```

Output:

```
forRoot() twice            -> Settings created: 2 | shared: false
same object imported twice -> Settings created: 1 | shared: true
deep-hash, forRoot() twice -> Settings created: 1 | shared: true
```

Practical rules:

- Call `forRoot()` **once**, in the root (or core) module, and let others import the static class, or mark the dynamic module `global: true`.
- If several modules must share one configured module, create the object once and import that same object.
- Two `forRoot()` calls with identical options are still two instances under the default algorithm.

### The deep-hash option

`moduleIdGeneratorAlgorithm: 'deep-hash'` (an application option) derives the token from the serialized definition, so structurally identical dynamic modules collapse into one (third line above). It exists mainly for tooling. The cost is a serialization pass over every module definition at startup, and `deep-hashed-module-opaque-key-factory.js` contains special handling for definitions it cannot serialize (it defines an "unable to serialize, circular reference is too complex" marker). I read the start of that file but did not run those paths: Not verified. Keep the default unless you have a reason.

## Reading and Fixing Module Errors

### Error catalogue

Every message below was produced by running the code. Each error class lives in `@nestjs/core/errors/exceptions/`.

**1. Provider not visible: `UnknownDependenciesException`** (thrown from `Injector.lookupComponentInParentModules`)

```
Nest can't resolve dependencies of the GreeterService (?). Please make sure that the argument CounterService at index [0] is available in the GreeterModule module.
```

Read it as: *"while building `GreeterService`, parameter 0, of type `CounterService`, was not found by the lookup algorithm starting from `GreeterModule`"*. The parentheses list the constructor parameters, and `?` marks the one that failed, so you can see its position. Resolved parameters print their class name. Two real examples:

```
Nest can't resolve dependencies of the TwoParams (CounterService, ?). Please make sure that the argument Missing at index [1] is available in the TwoParamsModule module.
Nest can't resolve dependencies of the ThreeParams (?, CounterService, Other). Please make sure that the argument Missing at index [0] is available in the ThreeParamsModule module.
```

Causes: the owning module does not export it, the consumer's module does not import the owning module, the owning module was never registered, or the module is not global when you assumed it was.

**2. Parameter is not a class: also `UnknownDependenciesException`, different hints**

```
Nest can't resolve dependencies of the NeedsInterface (?). Please make sure that the argument at index [0] is available in the current module.

Potential solutions:
- The dependency at index [0] appears to be undefined at runtime
- This commonly occurs when using 'import type' instead of 'import' for injectable classes
- Check your imports and change:
  ❌ import type { SomeService } from './some.service';
  ✅ import { SomeService } from './some.service';
- Ensure the imported class is decorated with @Injectable() or is a valid provider
- If using dynamic imports, ensure the class is available at runtime, not just for type checking

For more common dependency resolution issues, see: https://docs.nestjs.com/faq/common-errors
```

This happens when the parameter type is an interface or a type alias, which TypeScript emits as `Object` in `design:paramtypes`, so Nest has no class to look up. It also happens with a type-only import of a class. Both come from [Phase 0 note 03](../phase_00_orientation/03_typescript_for_nest.md). The fix is a class, or an explicit token with `@Inject('TOKEN')` (topic 2.2). Notice the message has no module name: there is no token to name.

**3. Exporting what you do not have: `UnknownExportException`** (thrown from `Module.validateExportedProvider` during phase 2)

```
Nest cannot export a provider/module that is not a part of the currently processed module (ExportsNothingItOwns). Please verify whether the exported LoggerService is available in this particular context.
```

The export is neither in this module's `providers` nor one of its imported modules. This also fires when you try to re-export a single provider you only got through an import.

**4. Wrong kind of class in `imports`: `InvalidClassModuleException`**

```
"LoggerService" is decorated with @Injectable() and cannot appear in the "imports" array of a module. Please move "LoggerService" to the "providers" array of the importing module instead.
"SomeController" is decorated with @Controller() and cannot appear in the "imports" array of a module. Please move "SomeController" to the "controllers" array of the importing module instead.
```

**5. `undefined` in a module list: `UndefinedModuleException` and `UndefinedModuleEntryException`**

```
UndefinedModuleException: Nest cannot create the UndefinedImport instance.
The module at index [0] of the UndefinedImport "imports" array is undefined.

Potential causes:
- A circular dependency between modules. Use forwardRef() to avoid it. Read more: https://docs.nestjs.com/fundamentals/circular-dependency
- The module at index [0] is of type "undefined". Check your imports and the type of the module.

Scope []
```

For `providers` and `exports` the class is `UndefinedModuleEntryException` and the cause list talks about "a circular import between files, often through a barrel file (index.ts)". These almost always come from circular **file** imports, which behave differently under ESM and CommonJS (see item 7).

**6. Typo in a `@Module` key: a plain `Error` when the file loads**

```
Invalid property 'exportz' passed into the @Module() decorator.
```

**7. Circular imports between module files**

Two files that import each other, each module listing the other in `imports`:

```ts
// a.module.ts
@Module({ imports: [BModule] }) export class AModule {}
// b.module.ts
@Module({ imports: [AModule] }) export class BModule {}
```

Under **ESM** (what a Nest 12 scaffold uses), the language itself fails before Nest runs:

```
ReferenceError: Cannot access 'AModule' before initialization
    at file:///.../b.module.js:12:24
```

Under **CommonJS** the same code loads, `AModule` is `undefined` when `BModule` is decorated, and Nest reports it (item 5):

```
UndefinedModuleException: Nest cannot create the BModule instance.
The module at index [0] of the BModule "imports" array is undefined.
...
Scope [AModule]
```

Both are fixed the same way: `imports: [forwardRef(() => AModule)]` on **both** sides (verified: with the two modules in separate files under ESM it compiles), or, much better, remove the cycle by moving the shared part into a third module. Topic 2.5 covers this in depth.

**Silent failures: errors you do NOT get**

Some mistakes produce no error at all, which makes them worse:

```ts
import { Controller, Injectable, Module } from '@nestjs/common';
import { tryBoot } from './boot.js';

@Injectable() class LoggerService {}
class NotAModule {}
@Module({ imports: [NotAModule as any] }) class PlainClassRoot {}
console.log(await tryBoot(PlainClassRoot));

class NoDecorator { constructor(readonly logger: LoggerService) {} }   // no decorator at all
@Module({ providers: [LoggerService, NoDecorator] }) class NoDecoratorRoot {}
console.log(await tryBoot(NoDecoratorRoot));
```

Output (and a follow-up run that reads the injected value):

```
class without @Module in imports   compiled
class without any decorator        compiled
NoDecorator instance exists: true
its logger is: undefined
```

- A class without `@Module()` in `imports` is accepted as an **empty module**. If you forget `@Module()` on a feature module, none of its providers or controllers exist and you get a confusing error elsewhere, or a 404.
- A class without any decorator is instantiated with **no constructor arguments**: its `logger` is `undefined`, not an error. `design:paramtypes` is only emitted for decorated classes, so Nest sees no dependencies. Put `@Injectable()` on everything Nest constructs.

**What Nest prints when you start an app that has this problem**

With the default `abortOnError: true` the failure is printed through Nest's logger and the process exits (exit code 1, measured). The first lines, from a one-module app missing an import:

```
[Nest] 78278  - 11/20/2026, 12:09:55 PM     LOG [NestFactory] Starting Nest application...
[Nest] 78278  - 11/20/2026, 12:09:55 PM   ERROR [ExceptionHandler] UnknownDependenciesException [Error]: Nest can't resolve dependencies of the GreeterService (?). Please make sure that the argument CounterService at index [0] is available in the AppModule module.
...
    at Injector.lookupComponentInParentModules (.../@nestjs/core/injector/injector.js:471:19) {
  type: 'GreeterService',
  context: {
    index: 0,
    dependencies: [
      [class CounterService]
    ],
    name: [class CounterService]
  },
```

The stack trace points into Nest, not into your code. The useful parts are the first message line and the `type`/`context` details.

### Decision tree

When you see `Nest can't resolve dependencies of X (?)`:

```
 Which token is missing?   (the "argument ___ at index [n]" part)
  |
  +-- no name at all ("argument at index [0]")
  |     -> the parameter is an interface, a type alias, a primitive, or `import type`.
  |        Use a class, or a custom token with @Inject() (topic 2.2). Check `import type`.
  |
  +-- a class name, say CounterService
        |
        1. Does CounterService have @Injectable() and is it in SOME module's `providers`?
        |     no  -> add it to providers of the module that should own it.
        |
        2. Does the OWNING module list it in `exports`?
        |     no  -> add it to exports.
        |
        3. Does the module named in the message (the consumer's module) import the OWNING module?
        |     no  -> add it to `imports`. (Or the owner is reached through another module:
        |            that module must RE-EXPORT the owning module.)
        |
        4. Was the owning module registered at all? (imported somewhere that starts at the root)
        |     no  -> import it from the root module or a module the root imports.
        |
        5. Did you expect it to be global?
        |     check @Global() is there, the module is imported once, and the provider is exported.
        |
        6. Is the same class provided in TWO modules? (works, but creates two instances)
              fix by giving it one home.
```

Remember the message names the **consumer's** module, which is where you will usually edit `imports`. Steps 1 and 2 are in the **owner's** module.

## Debugging the Module Graph

### Listing modules with ModulesContainer

The container is injectable. `ModulesContainer` is a `Map` of every module Nest registered, so you can print the real graph instead of guessing:

```ts
import { Global, Injectable, Module } from '@nestjs/common';
import { ModuleRef, ModulesContainer } from '@nestjs/core';
import { boot } from './boot.js';

@Injectable() class CounterService {}
@Injectable() class GreeterService { constructor(readonly counter: CounterService) {} }
@Module({ providers: [CounterService], exports: [CounterService] }) class CounterModule {}
@Module({ imports: [CounterModule], providers: [GreeterService], exports: [GreeterService] }) class GreeterModule {}
@Global() @Module({}) class ConfigModule {}
@Module({ imports: [GreeterModule, ConfigModule] }) class AppModule {}

const app = await boot(AppModule);
const names = (items: Iterable<any>) => [...items].map((x) => (typeof x === 'function' ? x.name : x.name ?? String(x)));

for (const m of app.get(ModulesContainer).values()) {
  if (m.name === 'InternalCoreModule') continue;
  const own = names(m.providers.keys()).filter((n) => !['ModuleRef', 'ApplicationConfig', m.name].includes(n));
  console.log(`${m.name.padEnd(14)} global=${String(m.isGlobal).padEnd(5)} imports=${JSON.stringify(names(m.imports))} providers=${JSON.stringify(own)} exports=${JSON.stringify(names(m.exports))}`);
}
```

Output:

```
AppModule      global=false imports=["GreeterModule","ConfigModule","InternalCoreModule"] providers=[] exports=[]
GreeterModule  global=false imports=["CounterModule","InternalCoreModule","ConfigModule"] providers=["GreeterService"] exports=["GreeterService"]
CounterModule  global=false imports=["InternalCoreModule","ConfigModule"] providers=["CounterService"] exports=["CounterService"]
ConfigModule   global=true  imports=["InternalCoreModule"] providers=[] exports=[]
```

What this shows, all consistent with the source reading:

- Your written `imports` come first, then `InternalCoreModule`, then the global modules Nest bound. `GreeterModule` never wrote `ConfigModule` in its imports.
- `InternalCoreModule` is a global module Nest creates in every app. It provides `ModuleRef`, `Reflector`, `HttpAdapterHost`, `ModulesContainer`, `REQUEST`, `INQUIRER`, `LazyModuleLoader`, `SerializedGraph`, `ExternalContextCreator` and `ApplicationConfig`. That is why you can inject `Reflector` anywhere without importing anything.
- I filtered out `ModuleRef`, `ApplicationConfig` and the module's own class from `providers`. Nest adds those three to every module (`Module.addCoreProviders`).

### app.select and strict lookups

`app.get(Token)` searches **the whole application** by default. `{ strict: true }` restricts the search to the module the context is bound to, and `app.select(SomeModule)` returns a context bound to another module:

```ts
const attempt = (label: string, fn: () => unknown) => {
  try { console.log(label.padEnd(60), '->', (fn() as object).constructor.name); }
  catch (e) { console.log(label.padEnd(60), '->', `${(e as Error).constructor.name}: ${(e as Error).message}`); }
};
attempt('app.get(CounterService)', () => app.get(CounterService));
attempt('app.get(CounterService, { strict: true })', () => app.get(CounterService, { strict: true }));
attempt('app.select(GreeterModule).get(CounterService, { strict: true })', () => app.select(GreeterModule).get(CounterService, { strict: true }));
attempt('app.select(CounterModule).get(CounterService, { strict: true })', () => app.select(CounterModule).get(CounterService, { strict: true }));
```

(run with the same `app` as above)

```
app.get(CounterService)                                      -> CounterService
app.get(CounterService, { strict: true })                    -> UnknownElementException: Nest could not find CounterService element (this provider does not exist in the current context)
app.select(GreeterModule).get(CounterService, { strict: true }) -> UnknownElementException: Nest could not find CounterService element (this provider does not exist in the current context)
app.select(CounterModule).get(CounterService, { strict: true }) -> CounterService
```

Three findings:

- The default is **non-strict**. `app.get(CounterService)` succeeds even though `AppModule` itself has no such provider. Do not use a non-strict `get` as proof that a module can see a provider.
- `strict: true` checks only the context module's **own** providers, not its imports. `GreeterModule` imports `CounterModule`, yet `strict: true` from `GreeterModule` fails. To assert visibility use a real consumer provider and compile the module (the exercise does this).
- `select(...)` is the way to ask "what does **this** module own".

### ModuleRef and modules as providers

Nest registers every module class **as a provider of itself** (`Module.addModuleAsProvider`) and adds a `ModuleRef` to each module (`Module.addModuleRef`):

```ts
console.log('modules are providers of themselves:', app.get(AppModule) instanceof AppModule);
console.log('ModuleRef is available in every module:', app.select(GreeterModule).get(ModuleRef, { strict: true }) !== undefined);
```

```
modules are providers of themselves: true
ModuleRef is available in every module: true
```

The first is why a module class can have a constructor that injects providers, which is used for setup code (verified: a module whose constructor took a `CounterService` received it; lifecycle hooks are topic 2.8). `ModuleRef` is the programmatic handle for "give me a provider from this module" and is the subject of topic 2.6.

### Nest Devtools in one paragraph

Nest Devtools is a separate tool that shows the module graph as an interactive diagram, and it can export it as an image. It needs the `@nestjs/devtools-integration` package (12.0.0 on npm, peer dependencies `@nestjs/common` and `@nestjs/core` ^12), `snapshot: true` in the application options, and `DevtoolsModule.register()` in the root module. Its documentation says never to enable it in production. We do not set it up here: for the sizes in this course, the `ModulesContainer` listing above is enough. Documentation: [docs.nestjs.com/devtools/overview](https://docs.nestjs.com/devtools/overview). Not verified here: pricing and the exact setup steps beyond what the page summary says.

## Testing Modules

`Test.createTestingModule` from `@nestjs/testing` takes the same metadata as `@Module()` and builds a real module graph around it, named `RootTestModule`. The deep dive is Phase 6, but modules are tested with it from day one:

```ts
const moduleRef = await Test.createTestingModule({ imports: [GreeterModule] })
  .overrideProvider(CounterService).useValue({ id: 99 })
  .compile();
moduleRef.get(GreeterService).counter.id;   // 99
```

(Verified: `GreeterService` saw the override.)

Two module-specific points:

- **Import the module under test, not its providers.** `createTestingModule({ providers: [GreeterService] })` skips the module, so the error you get is `Nest can't resolve dependencies of the GreeterService (?) ... in the RootTestModule module`. It tests nothing about your module wiring.
- **A module test is a wiring test.** A test that compiles `imports: [FeatureModule]` fails when the module forgot an import or an export. This is the cheapest way to catch the hidden dependency from the global modules section: if a feature module only works because a global module exists, its isolated test fails. The exercise's tests are written this way.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| Listing a provider in two modules | Two instances, each with its own state, no error | One home module, everybody imports it |
| Forgetting `exports` | `Nest can't resolve dependencies`, naming the consumer's module | Export from the owning module |
| Forgetting `imports` | The same error | Import the owning module |
| Importing a module and expecting its imports | Importing is not transitive | Re-export the module, or import it directly |
| Exporting a provider you got from an import | `UnknownExportException` | Re-export the module |
| `@Global()` everywhere | Hidden dependencies, untestable modules | Reserve it for config and logging |
| `forRoot()` called in several modules | Several module instances | Call once, or import one shared object |
| Forgetting `@Module()` on a module class | Silently an empty module | Check the decorator |
| Forgetting `@Injectable()` | Constructor parameters are `undefined`, no error | Decorate everything Nest constructs |
| Circular module imports | `ReferenceError` (ESM) or `UndefinedModuleException` (CJS) | Extract a shared module, `forwardRef` as a last resort |
| Same token exported by two imports | The first import silently wins | One owner per token |
| `app.get(X)` as a visibility check | Default is non-strict and searches everywhere | Compile a real consumer, or use `strict: true` |
| Reading the log order as dependency order | The `dependencies initialized` order is concurrent | Ignore it |

## Interview Questions

**1. What is a Nest module and why does the framework need it?**
A class with `@Module()` metadata (`imports`, `providers`, `controllers`, `exports`). Nest builds a graph from it. Modules give providers a scope: a provider is visible only inside its module unless exported and imported. This enforces encapsulation at startup and gives Nest the information to build the dependency graph and register routes.

**2. Are providers shared between modules?**
Not by default. Providers are private to their module. A module exposes them with `exports`, and another module gains access by importing it. A shared module is imported in many places and yields a single instance, because a module is a singleton.

**3. What happens if you list the same provider in two modules?**
Two independent instances, one per module, with separate state. There is no error. The fix is to give the provider one home module and import that module elsewhere.

**4. A module is imported in ten places. How many times is it instantiated?**
Once. `NestContainer.addModule` computes a token from the class identity and returns the existing module if the token is already registered. The same holds regardless of import order.

**5. Difference between exporting a provider and re-exporting a module?**
Exporting a provider makes one of the module's own providers available to importers. Re-exporting a module (an imported module in `exports`) passes everything that module exports on to importers. You cannot export a single provider you only received through an import: that throws `UnknownExportException`. Importing is not transitive, so re-exporting is the only way to pass things along.

**6. How does `@Global()` work and why is it discouraged?**
It sets metadata that makes the container register the module as global. After scanning, `bindGlobalScope` adds every global module to the `imports` of every other module. The provider must still be exported, and the module must still be imported once. It is discouraged because it creates hidden dependencies: a module that uses a global provider looks complete but cannot be compiled or tested alone. Use it for configuration and logging only.

**7. What does `Nest can't resolve dependencies of X (?)` mean and how do you debug it?**
While constructing `X`, the lookup could not find the token for one parameter. It searches the consumer module's own providers, then the exports of its imports (through re-exports). The message names the consumer's module and the missing token, and it is identical whether the import or the export is missing, so you check both: is the provider in an owning module's `providers`, does that module export it, does the consumer's module import it (or a module that re-exports it), is the owner registered at all, and is the parameter a real class (not an interface)?

**8. Does import order matter?**
Not for a graph where each token has one owner. It matters when two imported modules export the same token: the first import that matches wins, silently. The module's own providers always beat imports.

**9. What is a dynamic module and why can two `forRoot()` calls create two instances?**
A dynamic module is a module whose metadata is returned from a static method, as an object with a `module` property and the usual metadata. Nest identifies a dynamic module by the returned object's reference (by default). Each `forRoot()` call makes a new object, hence a new module and new provider instances, even with identical options. Call it once, import one shared object, or use `moduleIdGeneratorAlgorithm: 'deep-hash'`.

**10. How do circular module imports fail, and how do you fix them?**
Under ESM a circular file import throws `ReferenceError: Cannot access 'X' before initialization` when the decorator evaluates. Under CommonJS the import is `undefined` and Nest throws `UndefinedModuleException`, suggesting `forwardRef`. `forwardRef(() => Module)` on both sides defers the reference. The better fix is to remove the cycle by extracting the shared providers into a third module.

**11. How do you test a module in isolation?**
Compile `Test.createTestingModule({ imports: [TheModule] })`. If it compiles and its providers resolve, its imports and exports are correct. If it only works inside the full app, it depends on something global or on a sibling it did not import.

**12. What does `app.get(X, { strict: true })` do compared with the default?**
The default searches the entire application. `strict: true` looks only in the module the context is bound to, and only among that module's own providers, not its imports. Use `app.select(Module)` to bind another module.

**13. Is a module itself injectable?**
Yes. Nest registers each module class as a provider of itself, so a module can have a constructor with injected providers, and `ModuleRef` is available in every module. This is commonly used for module-level setup in lifecycle hooks.

**14. What are `InternalCoreModule` and the `Reflector`, and why can you inject `Reflector` anywhere?**
`InternalCoreModule` is a global module Nest adds to every app. It provides `ModuleRef`, `Reflector`, `HttpAdapterHost`, `ModulesContainer` and similar framework services. Because it is global, they are available in every module without importing anything.

## Check Yourself

- [ ] I can state what each of `imports`, `providers`, `controllers` and `exports` does, and which are visible to other modules.
- [ ] I can explain why a module imported in many places yields one instance, and what the token is.
- [ ] I can explain the lookup algorithm: own providers, then exports of imports, through re-exports, first match wins.
- [ ] I know the error for "not imported" is the same as for "not exported", and I can use the decision tree.
- [ ] I can say why a provider listed in two modules is a bug, and fix it.
- [ ] I can explain what `@Global()` does internally (`bindGlobalScope`) and name its two costs.
- [ ] I can explain why two `forRoot()` calls can give two instances.
- [ ] I can tell an ESM circular import failure from a CommonJS one.
- [ ] I can list the modules of a running app with `ModulesContainer`, and I know what `strict: true` does.
- [ ] I finished the exercise: [02_modules](../../projects/phase_01_core_building_blocks/02_modules/README.md).

## Further Reading

- Official documentation, [Modules](https://docs.nestjs.com/modules), including its sections on [shared modules, re-exporting, global modules](https://docs.nestjs.com/modules#global-modules) and [dynamic modules](https://docs.nestjs.com/modules#dynamic-modules) (these URLs appear in the JSDoc of the installed `@nestjs/common` package).
- [Dependency injection](https://docs.nestjs.com/providers#dependency-injection) (from the `@Module` JSDoc).
- [Common errors (FAQ)](https://docs.nestjs.com/faq/common-errors): the page every `Nest can't resolve` message links to.
- [Circular dependency](https://docs.nestjs.com/fundamentals/circular-dependency): linked from the circular-import errors above. Topic 2.5 goes through it.
- [Nest Devtools overview](https://docs.nestjs.com/devtools/overview) (opened through a search result, setup details not followed).
- Dynamic modules chapter in the docs sidebar under Fundamentals (not opened for this note; topic 2.3).
- Source worth reading in the installed `node_modules/@nestjs/core`, in this order: `injector/injector.js` (`lookupComponent`, `lookupComponentInImportsSync`), `scanner.js` (`scan`, `scanForModules`, `scanModulesForDependencies`), `injector/container.js` (`addModule`, `setModule`, `bindGlobalScope`), `injector/module.js` (`addProvider`, `validateExportedProvider`), `injector/compiler.js` and `injector/opaque-key-factory/`.
- Related topics: [1.1 Application Bootstrap](01_application_bootstrap.md) (what `NestFactory` does around this), 1.4 Providers and Services, 2.2 Custom and Async Providers, 2.3 Dynamic Modules, 2.5 Circular Dependencies, 2.6 Module Reference and Lazy Loading, 2.8 Lifecycle Events, Phase 6 Testing.

# 1.4 Providers and Services

> **Topic 1.4** | Priority: Core | Prerequisites: [1.2 Modules](02_modules.md), [1.3 Controllers and Routing](03_controllers_and_routing.md), [03 TypeScript Features Nest Is Built On](../phase_00_orientation/03_typescript_for_nest.md) (decorators and metadata) | Time: about 3 hours reading plus 2 hours for the exercise | Exercise: [04_providers_and_services](../../projects/phase_01_core_building_blocks/04_providers_and_services/README.md) | Next: [1.5 Middleware](05_middleware.md) | Roadmap: [1.4 Providers and Services](../../docs/01_nestjs_roadmap.md#14-providers-and-services)
>
> Everything marked "measured" was run against `@nestjs/core` 12.5.1 on Node 24.22.3, under Vitest and, where noted, with real `tsc` output. The scratch experiments are not kept: the exercise tests reproduce the important ones.

## Table of Contents

- [Why Providers Matter](#why-providers-matter)
- [The Mental Model](#the-mental-model)
  - [A provider is any class Nest builds for you](#a-provider-is-any-class-nest-builds-for-you)
  - [A service is a convention, not a feature](#a-service-is-a-convention-not-a-feature)
- [What Injectable Really Does](#what-injectable-really-does)
  - [What it stores](#what-it-stores)
  - [What makes injection work](#what-makes-injection-work)
  - [The silent failure without a decorator](#the-silent-failure-without-a-decorator)
- [Constructor Injection](#constructor-injection)
  - [How Nest finds the token](#how-nest-finds-the-token)
  - [When it fails](#when-it-fails)
  - [Creation order and timing](#creation-order-and-timing)
- [Property Injection](#property-injection)
  - [How it works](#how-it-works)
  - [When it is the right tool](#when-it-is-the-right-tool)
  - [The costs](#the-costs)
- [Singletons and Shared State](#singletons-and-shared-state)
  - [One instance, many callers](#one-instance-many-callers)
  - [The concurrency trap](#the-concurrency-trap)
  - [What a singleton may hold](#what-a-singleton-may-hold)
- [Optional Dependencies](#optional-dependencies)
  - [How Optional behaves](#how-optional-behaves)
  - [Optional and inheritance in v12](#optional-and-inheritance-in-v12)
- [Services, Repositories and Helpers](#services-repositories-and-helpers)
  - [The layers](#the-layers)
  - [Where does this rule go](#where-does-this-rule-go)
  - [Domain errors](#domain-errors)
- [Testing Providers](#testing-providers)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Providers Matter

Almost everything in a Nest application that is not a controller is a **provider**: services, repositories, factories, helpers that need injection, clients for other systems. The controller of 1.3 does transport; providers do the work. Dependency injection (DI) is how they find each other.

This topic is where the questions about "how does Nest know what to inject" start, and where the most expensive production bugs hide:

- "Are providers singletons? What goes wrong if a service stores a field per request?"
- "Constructor or property injection: which do you use and why?"
- "What does `@Injectable()` actually do?"
- "What does `@Optional()` do, and what is the v12 change?"
- "What belongs in a service, a repository, a controller?"

The container itself (tokens, resolution order, the source of `Injector`) is Phase 2, topic 2.1. Custom providers (`useClass`, `useValue`, `useFactory`) are 2.2, and scopes other than the default are 2.4. Here we stay with plain classes and the default scope.

**Coming from FastAPI.** `Depends(get_service)` builds a call graph for each request and discards it. A Nest provider is built **once**, at startup, and lives as long as the application:

| FastAPI | Nest |
|---|---|
| `Depends(get_db)` runs per request (cached inside one request) | the provider is built once and shared by every request |
| a dependency is a function (or class) you name at each route | a dependency is a constructor parameter, resolved by type |
| a missing dependency fails when the route is called | a missing dependency fails at startup, before the first request |
| per-request state is natural (`Depends` returns a fresh value) | per-request state on a provider is a **bug** unless you opt in (2.4) |

## The Mental Model

### A provider is any class Nest builds for you

A provider is a class that appears in a module's `providers` list (1.2). Nest creates one instance of it when the application starts, passes it the other providers it asked for, and hands that same instance to everyone who asks:

```ts
@Injectable()
export class StampService {
  constructor(private readonly clock: ClockService) {}   // "I need a ClockService"
  stamp(text: string) { return `${this.clock.now()} ${text}`; }
}

@Module({ providers: [ClockService, StampService] })
export class StampModule {}
```

Providers are private to their module unless exported (1.2). Controllers and other providers receive them through the constructor.

### A service is a convention, not a feature

Nest has no `@Service()` decorator. "Service" is a naming convention for a provider that holds business logic. A repository, a mapper, a client for a payment API and an email sender are all providers too, and to the container they look identical: a class in `providers`. What differs is **your** discipline about what each layer may do, covered under [Services, Repositories and Helpers](#services-repositories-and-helpers).

## What Injectable Really Does

### What it stores

`@Injectable()` is smaller than its reputation. The whole implementation (from `@nestjs/common`):

```js
export function Injectable(options) {
  return (target) => {
    Reflect.defineMetadata(INJECTABLE_WATERMARK, true, target);
    Reflect.defineMetadata(SCOPE_OPTIONS_METADATA, options, target);
  };
}
```

Measured: `Reflect.getMetadataKeys(Dep)` on a decorated class gives `design:paramtypes`, `__injectable__`, `scope:options`. The marker is `true`, and the scope options are `undefined` unless you pass `{ scope, durable }` (2.4). Nothing in `@Injectable()` reads or writes the constructor parameter types.

### What makes injection work

The parameter types come from **TypeScript**, not from Nest. With `emitDecoratorMetadata` on, the compiler writes `design:paramtypes` for every class that has **any** decorator (0.3). Measured, with a class that takes a `Dep` in its constructor:

| Class | `design:paramtypes` | Injected `dep` |
|---|---|---|
| `@Injectable()` | present | `Dep` |
| decorated with some other, unrelated class decorator | present | `Dep` |
| no class decorator, but a parameter decorator `@Inject(Dep)` | present | `Dep` |
| **no decorator at all** | **absent** | **`undefined`** |
| no decorator, no constructor parameters | absent | nothing to inject |

So `@Injectable()` is, mechanically, "a decorator, so that TypeScript emits the types", plus a marker and the scope options. That is why you **always** write it: it is the convention that guarantees the emit, and later features read the marker.

### The silent failure without a decorator

The last-but-one row is the dangerous one. Measured: a class with no decorator and a constructor `(readonly dep: Dep)`, placed in `providers`, compiles with **no error and no warning**. Nest finds no parameter types, calls `new Class()` with no arguments, and `this.dep` is `undefined`. The failure shows up as `Cannot read properties of undefined` the first time you use it, far from the real cause. (Nest 12 does print a startup warning in a related case: a *decorated* class whose parameter types are missing because the build tool does not emit metadata, such as tsx or esbuild. An undecorated class is not checked, see `warnOnMissingDecoratorMetadata` in `injector.js`.)

This is the exercise's Task 5 trap: the service has its constructor, the test fails with a `TypeError`, and nothing mentions the decorator.

## Constructor Injection

### How Nest finds the token

For a provider class, Nest does this (source: `Injector.getClassDependencies`, `reflectConstructorParams`):

1. Read `design:paramtypes`: `[ClockService]`.
2. Overlay any `@Inject(token)` parameters, which replace a type with an explicit token (2.2).
3. For each entry, look the token up in the module's own providers, then in what its imports export (1.2).
4. Resolve dependencies first, then call `new Class(...resolved)`.

The token for a class parameter is the **class itself**, a runtime value. That is the whole reason interfaces cannot be injected. The parameter property syntax `constructor(private readonly clock: ClockService)` is just TypeScript shorthand for declaring and assigning a field.

### When it fails

Measured error messages (all thrown at startup, never at request time):

| Situation | Error |
|---|---|
| provider missing | `UnknownDependenciesException: Nest can't resolve dependencies of the NeedsFlags (?). Please make sure that the argument Flags at index [0] is available in the RootTestModule module.` |
| parameter typed with an **interface** | `... of the UsesInterface (?). Please make sure that the argument at index [0] is available in the current module.` (no token name: it was erased to `Object`) |
| class imported with `import type` | the same nameless message: the emitted type is `Object` |
| parameter typed `number` with a default (`n: number = 5`) | `... Please make sure that the argument Number at index [0] ...`: a primitive type is a token like any other, and a default value does not help. Use `@Optional()` or an explicit token (2.2) |
| a dependency's constructor throws | the original error propagates and the application does not start |
| `moduleRef.get(NotProvided)` | `UnknownElementException: Nest could not find Nope element (this provider does not exist in the current context)` |

The decision tree for the first rows is in the [1.2 notes](02_modules.md#decision-tree). One extra compile-time guard: with `isolatedModules` and `emitDecoratorMetadata`, importing a **type** (an interface) with a plain `import` into a decorated signature is error TS1272, which tells you to use `import type`. For a class you need the normal import: with `import type { Dep }` the emitted metadata is `Object` and injection fails at startup.

### Creation order and timing

Measured with a chain A needs B needs C:

```
declared [A, B, C]  constructed: C -> B -> A
declared [C, B, A]  constructed: C -> B -> A
```

Dependencies are built first, whatever the order of the `providers` array. And a provider is built **at startup even if nobody uses it**: with only `[ClockService, Unused]` listed and nothing injecting `Unused`, both constructors had run when `compile()` returned (measured). Providers are eager, not lazy. So heavy work in a constructor (connecting to something, reading a file) delays startup, and a constructor that throws stops the whole application. Work that must wait for other providers to be ready belongs in a lifecycle hook (2.8); lazy loading is 2.6.

## Property Injection

### How it works

`@Inject()` also works on a **property**. Without an argument it uses the property's declared type (`design:type`) as the token:

```ts
export abstract class BaseReporter {
  @Inject()
  protected readonly clock!: ClockService;
}
```

Source: `Inject` stores `{ key, type }` in `PROPERTY_DEPS_METADATA` on the class. After the instance is built, `Injector.applyProperties` assigns each resolved value:

```js
iterate(properties).filter(item => !isNil(item.instance)).forEach(item => (instance[item.key] = item.instance));
```

Two consequences, both measured:

- The property is filled **after** the constructor has finished. Inside the constructor it is `undefined`.
- A missing provider is an error at startup, like constructor injection: `Nest can't resolve dependencies of the P3. Please make sure that the "flags" property is available in the current context.` Add `@Optional()` on the property to allow `undefined` (see below).

It also works in real compiled JavaScript: `tsc` (target ES2023, `useDefineForClassFields`) emits `clock;` as a class field and applies the decorator on the prototype, and Nest assigns the value afterwards, so the field definition does not interfere (measured with a plain `node` run of the compiled output).

### When it is the right tool

The metadata is stored on the class that declares the property, and Nest reads it through the prototype chain, so **every subclass gets it**. Measured: a base class with `@Inject() clock` and a subclass with no constructor gets the clock, and so does a subclass with its **own** constructor that injects something else (`WeeklyReporter`).

With constructor injection, every subclass would have to accept `ClockService` and forward it: `constructor(clock: ClockService) { super(clock); }`, and so would every subclass of the subclass. Property injection avoids threading parameters through an inheritance chain. This is the usual argument for property injection: a base class whose subclasses should not all repeat its dependencies (the official docs make the same point; not re-checked for this note).

### The costs

| Cost | Why |
|---|---|
| hidden dependency | the constructor signature no longer lists it, so a reader and `new X()` cannot see it |
| undefined in the constructor | any construction-time use of it fails |
| harder tests | `new DailyReporter()` leaves `clock` undefined: you must go through the container |
| `!` assertion | TypeScript is told to trust that Nest sets it |
| not for non-class types without a token | an `@Inject()` needing a string or symbol token takes the token as an argument (2.2) |

Default to the constructor. Use properties for base classes, as above, and not for ordinary services.

## Singletons and Shared State

### One instance, many callers

By default a provider is built once per application and shared. Measured with two controllers and one `Counter` provider: after two requests to one controller, the other saw `n = 2`; `Counter.created` was `1`; and both controllers held the **same object**. `moduleRef.get(Service)` returns the same instance every time.

That is what makes in-memory caches, connection pools and counters work, and it is the reason the next section exists. (A provider listed in **two modules** is two instances: see 1.2. And "one per application" means one per *process*: with several replicas, in-memory state is not shared between them, so anything that must be shared goes to a database or Redis, see 4.5.)

### The concurrency trap

Node handles many requests on one thread, and every `await` lets another request run. A service that writes per-call data into a field breaks as soon as two calls overlap. Measured, with the exercise's Task 2 service:

```ts
@Injectable()
class Greeter {
  private current = '';
  async greet(name: string, delay: number) {
    this.current = name;                       // written ...
    await sleep(delay);                        // ... another call runs here ...
    return `hello ${this.current}`;            // ... read back: whose name is it now?
  }
}
await Promise.all([g.greet('ada', 20), g.greet('bob', 5)]);
// field state    : [ 'hello bob', 'hello bob' ]     <- ada got bob's name
// arguments only : [ 'hello ada', 'hello bob' ]
```

One request at a time always works, so the bug passes every simple test and every manual try, and appears under load. In production the field is typically "the current user", "the current tenant" or "a request id".

### What a singleton may hold

| May hold | Must not hold |
|---|---|
| its injected dependencies | data of one request or one caller |
| configuration read once | "the current user", "the current request" |
| a cache, a pool, a client that is safe to share | anything that is written per call and read after an `await` |
| counters and metrics that every caller updates on purpose | |

Rule: **per-call data travels in arguments and local variables.** If data genuinely has to follow a request through many layers, there are two tools: request-scoped providers (2.4), which build a new instance per request and make everything that depends on them request-scoped too, and `AsyncLocalStorage` (0.1, 10.3), which keeps the singleton and carries the context beside it.

## Optional Dependencies

### How Optional behaves

`@Optional()` tells Nest that a dependency may be missing. Measured on the constructor:

| Situation | Result |
|---|---|
| provider missing, parameter has `@Optional()` | `undefined` is passed, no error |
| provider present | injected normally |
| missing, parameter has a default value (`@Optional() flags: Flags = new Flags()`) | the default is used, because `undefined` triggers it |
| provider present but its own **constructor throws** | the error still fails startup. `@Optional()` covers only "not found" |
| property: `@Optional() @Inject() flags?: Flags`, provider missing | `undefined` |

Use it for genuinely optional integrations (a metrics client, a Slack notifier that only some deployments configure) and type the parameter `?` so TypeScript makes you handle `undefined`. Do not use it to silence a wiring error: an `@Optional()` that hides a forgotten `imports` entry turns a startup error into a `TypeError` later.

### Optional and inheritance in v12

The flags are stored per class (`OPTIONAL_DEPS_METADATA`, read with `getOwnMetadata`) and per parameter **index**. The v12 injector decides whose flags apply with `getConstructorOwner` (source comment): *"A subclass without its own constructor inherits both the parent's parameter types and its `@Optional()` flags, while a subclass that redeclares the constructor must not inherit the parent's flags, as its parameters are unrelated to the parent's."* Measured:

| Subclass of `Base { constructor(@Optional() flags?: Flags) }` | `Flags` not provided |
|---|---|
| no constructor | starts, `flags` is `undefined` (flags inherited) |
| own constructor `(flags2: Flags)` | **fails**: `Nest can't resolve dependencies of the OwnCtor (?)` |
| own constructor `(@Optional() flags2?: Flags)` | starts |
| own constructor that only forwards: `(flags?: Flags) { super(flags); }` | **fails**: forwarding the value does not carry the flag |

So when a subclass declares a constructor, write `@Optional()` again on its parameters. This is the exercise's Task 4b. The roadmap records this as a v12 change; I measured the current behaviour only and did not run the same code on v11, so the "no longer inherits" wording is from the roadmap and the source comment.

## Services, Repositories and Helpers

### The layers

Nest does not enforce any of this: every layer is just a provider. The separation is yours to keep, and it is what keeps services testable.

| Layer | Does | Does not |
|---|---|---|
| **Controller** (1.3) | maps HTTP to a call: reads params and body, calls a service, shapes the response | decide business rules, touch storage |
| **Service** | business rules and orchestration: what is valid, what counts as a duplicate, what happens when something is missing, calling several repositories or clients in order | know about HTTP (status codes, `Request`), build SQL |
| **Repository** | stores and fetches: one place that knows how data is persisted | enforce rules (it stores what it is given) |
| **Helper** | a **pure function** with no state or dependencies: imported, not injected | be a provider unless it needs injection |

The exercise's repository will insert the same name twice and an empty name (a guard test proves it), because deciding that is the service's job. The helper `normalizeName` is a plain exported function: making it a provider would only add ceremony. Make a helper a provider when it needs a dependency (config, a clock, another service) or when you want to replace it in tests.

Two warnings from practice. A "service" that grows to twenty methods and eight dependencies is a symptom: split by responsibility, not by layer. And a repository over an ORM that already is a repository is often ceremony; when it helps and when not is 4.2.

### Where does this rule go

| Rule | Home |
|---|---|
| "a name is trimmed, lowercased, and may not be empty" | service (calls the helper) |
| "no two items may share a name" | service (asks the repository, decides) |
| "find an item by name" | repository |
| "this is a 409" or "this is a 404" | the edge: exception filters (1.9), not the service |
| "split a string, format a date" | helper |
| "parse `?limit=` into a number" | pipe (1.6), not the service |

### Domain errors

The service throws errors that speak the language of the domain (`DuplicateItemError`, `ItemNotFoundError`) and know nothing about HTTP, so the same service works from a controller, a queue consumer or a CLI (10.4). Turning them into status codes is the job of exception filters and `HttpException` (1.9, 3.4). The exercise keeps the errors as plain `Error` subclasses for that reason.

## Testing Providers

A provider test needs no HTTP. Two styles, both used in the exercise:

```ts
// 1. By hand: constructor injection makes the class a plain class.
const service = new ItemsService(new ItemsRepository());

// 2. Through Nest: checks that the wiring (decorator, providers list) is right too.
const moduleRef = await Test.createTestingModule({ providers: [ItemsRepository, ItemsService] }).compile();
const service = moduleRef.get(ItemsService);
```

Style 1 is the benefit of constructor injection: nothing but the class itself is needed. It also **cannot** catch a missing `@Injectable()`: `new ItemsService(repo)` passes the repository by hand, while Nest would pass `undefined`. Style 2 catches that. Use both, and put one wiring test on every provider that has dependencies. Property-injected classes only work through style 2. Replacing a dependency with a fake (`overrideProvider`) and the rest of the testing API is 6.1.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| No decorator on a class that has constructor dependencies | dependencies are `undefined`, no error, later `TypeError` | always `@Injectable()` |
| Interface or `import type` for a constructor parameter | startup error with no token name | use the class, normal import |
| Per-request data in a field of a provider | values leak between concurrent requests, only under load | arguments and locals, or 2.4 and 10.3 |
| In-memory state assumed shared across replicas | each process has its own copy | a shared store (4.5) |
| Expensive or failing work in a constructor | slows or stops startup, even if the provider is unused | lifecycle hooks (2.8) |
| `@Optional()` to hide a wiring mistake | `undefined` at runtime instead of a startup error | fix `imports`/`exports` (1.2) |
| `@Optional()` forgotten on a subclass constructor | `Nest can't resolve dependencies` although the parent is optional | write it again on the subclass |
| Property injection used for ordinary services | hidden dependency, `undefined` in the constructor, harder tests | constructor injection |
| Reading a property-injected value in the constructor | `undefined` | use it in methods or a lifecycle hook (2.8) |
| Business rules in the controller or the repository | untestable without HTTP or a database | the service |
| HTTP concepts (`HttpException`, status codes) inside the service | the service is tied to HTTP | domain errors, mapped at the edge (1.9) |
| A helper made a provider for no reason | needless injection | an exported function |
| Same provider listed in two modules | two instances | one home module (1.2) |

## Interview Questions

**1. What does `@Injectable()` do?**
It sets a marker (`INJECTABLE_WATERMARK`) and the scope options on the class. It does not read the constructor. The parameter types that Nest uses to inject come from TypeScript's `design:paramtypes`, which the compiler emits for any class with a decorator. So the decorator matters because it makes TypeScript emit them. Without any decorator, Nest builds the class with no arguments and the dependencies are `undefined`, silently.

**2. Are providers singletons? What goes wrong?**
By default, yes: one instance per application, shared by every request and controller that injects it. Per-request data stored in a field is then shared too, and because every `await` lets another request run, concurrent calls overwrite each other. It passes sequential tests and fails under load. Keep per-call data in arguments or locals, or use request scope (2.4) or AsyncLocalStorage (10.3).

**3. Constructor or property injection?**
Constructor by default: dependencies are explicit, available during construction, and the class works with `new` in a test. Property injection (`@Inject()` on a field) is applied after construction, so it is `undefined` in the constructor and hidden from the signature. Its use is base classes: the metadata is found through the prototype chain, so subclasses get the dependency without passing it up with `super(...)`.

**4. How does Nest know what to inject into a constructor?**
It reads `design:paramtypes`, the parameter types emitted by TypeScript, overlays any `@Inject(token)` parameters, looks each token up in the module's providers and its imports' exports, builds dependencies first, then calls `new`. The token for a class parameter is the class itself, so interfaces (erased to `Object`) cannot be injected without an explicit token (2.2).

**5. What does `@Optional()` do, and what changed in v12?**
It lets a missing provider become `undefined` instead of a startup error. It does not cover a provider that exists but fails to construct. The flags are stored per class and parameter index. In v12 a subclass that declares its own constructor does not inherit the parent's `@Optional()` flags (a subclass without a constructor still does), so you write it again on the subclass's parameters; forwarding the value to `super()` does not carry it.

**6. In what order are providers created, and when?**
At startup, before the first request, dependencies first, whatever the order in the `providers` array. All of them are created, even ones nobody injects. A constructor that throws stops the application. There is no lazy creation by default (lazy loading is 2.6).

**7. What belongs in a service, a repository, a controller?**
Controller: map HTTP to a call and shape the response. Service: business rules and orchestration, throwing domain errors. Repository: storing and fetching only. Helpers that are pure functions are imported, not injected. HTTP status mapping happens at the edge (filters, 1.9), and input conversion in pipes (1.6).

**8. Why unit test a service with `new` and also through Nest?**
`new Service(fakeRepo)` is the cheapest test and exists because of constructor injection. It cannot detect a missing `@Injectable()` or a missing `providers` entry, because you wire it yourself. Compiling a testing module verifies the wiring.

**9. A service stores the current user in a field. What happens?**
Under concurrent requests the value of one request is read by another after an `await`: users see each other's data. Pass the user as an argument, make the provider request-scoped (2.4) at a performance cost, or carry it in `AsyncLocalStorage`.

**10. In-memory state in a service. Is it safe in production?**
It is shared by all requests of one process, so a counter or a cache works there. It is not shared across replicas or restarts. Anything that must be consistent goes to a database or Redis (4.5).

**11. Why can't an interface be an injection token?**
Interfaces are erased at compile time, so `design:paramtypes` records `Object` for them and the injector has nothing to look up. Use a class, or a string, symbol or class token with `@Inject()` (2.2). The error message has no token name, which is how you recognise it.

## Check Yourself

- [ ] I can say what `@Injectable()` stores, and where the constructor parameter types really come from.
- [ ] I can explain why a class with no decorator gets `undefined` dependencies without an error.
- [ ] I can list the order and timing of provider creation, including providers nobody uses.
- [ ] I can explain when property injection is filled, what it sees in the constructor, and why base classes use it.
- [ ] I can explain why a singleton with a per-call field breaks only under concurrency, and name two alternatives.
- [ ] I can say what `@Optional()` covers and does not cover, and what v12 changed for subclasses.
- [ ] I can place a rule in the controller, service, repository or helper, and say why domain errors are not HTTP errors.
- [ ] I can test a service by hand and through Nest, and say what each one cannot catch.
- [ ] I finished the exercise: [04_providers_and_services](../../projects/phase_01_core_building_blocks/04_providers_and_services/README.md).

## Further Reading

- Official documentation: [Providers](https://docs.nestjs.com/providers) (services, dependency injection, optional providers, property-based injection). Not re-read for this note: the behaviour above was measured on 12.5.1 instead.
- Source worth reading in the installed `node_modules/@nestjs/`, in this order: `common/decorators/core/injectable.decorator.js`, `inject.decorator.js`, `optional.decorator.js`; then `core/injector/injector.js` (`getClassDependencies`, `reflectConstructorParams`, `reflectOptionalParams`, `getConstructorOwner`, `reflectProperties`, `applyProperties`, `warnOnMissingDecoratorMetadata`).
- Related topics: [1.2 Modules](02_modules.md), [1.3 Controllers and Routing](03_controllers_and_routing.md), 1.6 Pipes, 1.9 Exception Filters, 2.1 The IoC Container, 2.2 Custom and Async Providers, 2.4 Injection Scopes, 2.6 Module Reference and Lazy Loading, 2.8 Lifecycle Events, 4.2 Integrating an ORM, 4.5 Caching, 6.1 Unit Testing, 10.3 Request Context.

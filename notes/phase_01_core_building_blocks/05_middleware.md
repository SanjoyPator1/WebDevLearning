# 1.5 Middleware

> **Topic 1.5** | Priority: Core | Prerequisites: [1.2 Modules](02_modules.md), [1.3 Controllers and Routing](03_controllers_and_routing.md), [1.4 Providers and Services](04_providers_and_services.md) | Time: about 3 hours reading plus 2 hours for the exercise | Exercise: [05_middleware](../../projects/phase_01_core_building_blocks/05_middleware/README.md) | Next: [1.6 Pipes](06_pipes.md) | Roadmap: [1.5 Middleware](../../docs/01_nestjs_roadmap.md#15-middleware)
>
> Everything marked "measured" was run against `@nestjs/core` 12.5.1 with the Express adapter (Express 5, path-to-regexp 8.4.2) on Node 24.22.3. The Fastify adapter behaves differently in places and was not tested here (see 3.8). The exercise tests reproduce the important measurements; the scratch experiments are not kept.

## Table of Contents

- [Why Middleware Matters](#why-middleware-matters)
- [The Mental Model](#the-mental-model)
  - [What middleware is](#what-middleware-is)
  - [Where it sits](#where-it-sits)
  - [Coming from FastAPI](#coming-from-fastapi)
- [Functional and Class Middleware](#functional-and-class-middleware)
  - [Functional middleware](#functional-middleware)
  - [Class middleware](#class-middleware)
  - [How Nest tells them apart](#how-nest-tells-them-apart)
  - [Choosing between them](#choosing-between-them)
- [Registering Middleware](#registering-middleware)
  - [configure and MiddlewareConsumer](#configure-and-middlewareconsumer)
  - [What each forRoutes form matches](#what-each-forroutes-form-matches)
  - [exclude](#exclude)
  - [Global middleware with app.use](#global-middleware-with-appuse)
  - [The global prefix](#the-global-prefix)
- [What Middleware Sees](#what-middleware-sees)
  - [The URL and parameters](#the-url-and-parameters)
  - [The body](#the-body)
  - [The handler: it does not know](#the-handler-it-does-not-know)
- [Order of Execution](#order-of-execution)
- [Ending a Request](#ending-a-request)
- [Express 5 Paths in forRoutes](#express-5-paths-in-forroutes)
- [Middleware, Guard or Interceptor](#middleware-guard-or-interceptor)
- [Testing Middleware](#testing-middleware)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Middleware Matters

Middleware is the first thing that touches a request inside Nest and the only part of the pipeline that is **not Nest's own idea**: it is the Express (or Fastify) concept, kept as it is. That makes it the right tool for HTTP-level plumbing (logging, request ids, CORS, security headers, compression, cookies) and the wrong tool for decisions that need to know which handler is about to run.

Interviewers ask about it as:

- "Middleware, guard or interceptor: which do you use for what?"
- "Does middleware have access to the `ExecutionContext`?"
- "Why is `req.body` undefined in my global middleware?"
- "In what order does middleware run?"
- "How do you apply middleware to all routes except one?"

The whole lifecycle (middleware, guards, interceptors, pipes, filters) is 1.10. Here: middleware only.

## The Mental Model

### What middleware is

A function `(req, res, next)` that runs before the route handler. It may read or change the request and response, and then it must end the request in exactly one of two ways: call `next()` to pass it on, or answer it. That is the Express contract, unchanged, so any Express middleware package works in Nest as it is.

### Where it sits

```
request
  |
  v
global middleware       app.use(...)             runs first, before body parsing (measured)
  |
  v
body parsers            registered by Nest at init()
  |
  v
module middleware       configure(consumer)      after the parsers, in registration order
  |
  v
route handler           guards, interceptors, pipes, your method (1.7, 1.8, 1.6, 1.3)
```

Middleware also runs for requests that **no route handles** if its path matches (a 404 under a path it is mounted on), because it sits in the HTTP layer and does not know which routes exist. Guards, interceptors and pipes only run when a handler was matched.

### Coming from FastAPI

| FastAPI / Starlette | Nest |
|---|---|
| `@app.middleware("http")` wraps every request, including 404s | global middleware (`app.use`) behaves the same |
| `Depends(...)` for auth | a **guard** (1.7), not middleware |
| a middleware sees the `Request` and returns a `Response` | a middleware sees `req, res` and calls `next()` |
| a router can have its own dependencies | `configure(consumer)` applies middleware to chosen routes of a module |

## Functional and Class Middleware

### Functional middleware

A plain function with the Express signature:

```ts
export function tagResponse(req: Request, res: Response, next: NextFunction): void {
  res.setHeader('x-tagged', 'yes');
  next();
}
```

No decorator, no class, and **no dependency injection**: Nest never builds it, so there is no constructor. Use it for stateless work and for third-party Express middleware (`cors()`, `helmet()`, `morgan('dev')`, 5.3).

### Class middleware

A class with a `use(req, res, next)` method, normally `@Injectable()` and `implements NestMiddleware`:

```ts
@Injectable()
export class HitCounterMiddleware implements NestMiddleware {
  constructor(private readonly counter: HitCounterService) {}   // injected (1.4)
  use(req: Request, res: Response, next: NextFunction): void {
    res.setHeader('x-hits', String(this.counter.next()));
    next();
  }
}
```

Measured:

- It is built **once** and shared: three requests gave `x-hits = 1, 2, 3`, one middleware instance, one counter. So the singleton warning of 1.4 applies: no per-request fields.
- The injected provider must be visible in the module whose `configure()` applies the middleware. Otherwise startup fails: `Nest can't resolve dependencies of the UsesCounter (?). Please make sure that the argument Counter at index [0] is available in the Missing module.` A provider exported by an imported module works.
- A **request-scoped** class middleware (`@Injectable({ scope: Scope.REQUEST })`, 2.4) is built per request: 3 instances after 3 requests. It costs what request scope always costs.
- A thrown error goes through the exception filters, even from middleware (see [Ending a Request](#ending-a-request)).

### How Nest tells them apart

`consumer.apply(...)` accepts classes and functions in the same list. Measured:

| What you pass | Result |
|---|---|
| an arrow function `(req, res, next) => ...` | works (functional) |
| a function expression | works |
| a class with `@Injectable()` and `use()` | works, built by Nest with DI |
| a class **without** `@Injectable()`, with `use()` | works, but nothing is injected (no parameter types are emitted, see 1.4) |
| a class **without** a `use()` method | startup error: `InvalidMiddlewareException: The middleware doesn't provide the 'use' method (NoUse)` |

### Choosing between them

| Use a | when |
|---|---|
| function | the middleware is stateless, needs no provider, or is a third-party Express middleware; it can be registered with `app.use` in `main.ts` |
| class | it needs a provider (config, a logger service, a counter) or you want it testable through Nest and registered per module |

A function cannot be injected, but `main.ts` can bridge the gap: fetch the provider first with `app.get(Service)` and close over it (measured: `app.use((q, res, n) => ... counter ...)` worked).

## Registering Middleware

### configure and MiddlewareConsumer

Middleware is **not** listed in `providers`. A module opts in by implementing `NestModule`:

```ts
@Module({ controllers: [CountedController], providers: [HitCounterService] })
export class CountedModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer
      .apply(HitCounterMiddleware)               // one or more, classes or functions
      .exclude({ path: 'counted/health', method: RequestMethod.GET })   // optional, BEFORE forRoutes
      .forRoutes(CountedController);             // ends the chain, returns the consumer
  }
}
```

The API (from `@nestjs/common`): `apply(...middleware)` returns a proxy with `exclude(...routes)` and `forRoutes(...routes)`. `forRoutes` takes strings, controller classes and `RouteInfo` objects `{ path, method, version? }`, and returns the consumer, so you can chain another `apply(...)`. `configure()` may be `async`. Source: `MiddlewareModule.loadConfiguration` calls every module's `configure()` concurrently but keeps the registration order (it "reserves" each module's slot first).

### What each forRoutes form matches

The forms are not equivalent. Measured with `GET`/`POST` against these routes: `cats` controller with `GET /cats`, `GET /cats/health`, `GET /cats/:id`, `GET /cats/:id/toys`, `POST /cats`; another controller `catsup`, and a `dogs` controller. "Runs" = the middleware ran.

| `forRoutes(...)` | Runs for | Does not run for |
|---|---|---|
| `'cats'` (string) | `/cats`, `/cats/`, `/cats/1`, `/cats/1/toys`, `/cats/health`, `POST /cats`, and also `/cats/1/nope` (**a 404**), `/Cats` | `/catsup`, `/dogs` |
| `CatsController` (class) | exactly the routes it declares: all of the above except the 404 `/cats/1/nope` | `/catsup`, `/dogs`, the 404 |
| `{ path: 'cats', method: RequestMethod.ALL }` | `/cats`, `/cats/`, `POST /cats` only | `/cats/1`, `/cats/health`... |
| `{ path: 'cats', method: RequestMethod.GET }` | `GET /cats` only | `POST /cats`, `/cats/1` |
| `{ path: 'cats', method: RequestMethod.POST }` | `POST /cats` only | every GET |
| `'cats/:id'` (string) | `/cats/1`, `/cats/health` (`:id` matches it), `/cats/1/toys`, `/cats/1/nope` | `/cats` |
| `'cats/*splat'` | below `/cats`: `/cats/1`, `/cats/1/toys`, `/cats/1/nope` | `/cats`, `/cats/` |
| `'cats/{*splat}'` | the same, plus `/cats/` | `/cats` |
| `'{*splat}'` or `'*'` | everything, including unknown paths | nothing |
| `CatsController, DogsController` or `'cats', 'dogs'` | the union | |

The rule behind it (source: `MiddlewareModule.registerHandler`, and the builder's own comment): a **string** is mounted the way Express `app.use(path, fn)` mounts it, so it is a **prefix** match at a segment boundary (`cats` covers `/cats/anything` but not `/catsup`), and it matches paths where no route exists. A **controller class** or a `{ path, method }` object is mounted on the route pattern itself, so it matches only real routes. Matching is case-insensitive (`/Cats` ran), an Express default. When several entries of one `forRoutes` call overlap, the source makes the middleware run once per request: it tracks the requests already handled and later overlapping mounts skip them (`MiddlewareModule.getHandledRequests`; read from the source, not measured).

Which should you reach for? The controller class when you mean "this controller's routes", because it follows the controller if its prefix changes and never fires on a 404. A string when you mean "everything under this path". `{ path, method }` when the method matters.

### exclude

`exclude(...)` takes strings and `RouteInfo` objects, and is called on the object `apply()` returns, **before** `forRoutes()`: `forRoutes()` returns the consumer, which has no `exclude` (measured: `undefined`). An exclusion is an **exact** match, unlike a string in `forRoutes`. Measured, with `forRoutes('{*splat}')` (everything) unless noted:

| `exclude(...)` | Skips | Still runs for |
|---|---|---|
| `'cats'` (with `forRoutes('cats')`) | `/cats`, `/cats/`, `POST /cats`, `/Cats` | `/cats/1`, `/cats/health`, `/cats/1/toys` |
| `{ path: 'cats', method: POST }` | `POST /cats` | `GET /cats` and everything below |
| `'cats/health'` | `/cats/health` | `/cats/1`, `/cats`, ... |
| `'cats/:id'` | `/cats/1`, `/cats/health` | `/cats/1/toys` |
| `'cats/*splat'` | everything below `/cats` | `/cats` |

With `forRoutes(CatsController)` the same exclusions behave the same (measured for `cats/health`, as a string and as `{ path, method }`).

### Global middleware with app.use

`app.use(fn)` is the Express call: the function runs for **every** request. It is how `main.ts` registers `helmet()`, `cors()`, `cookieParser()` and similar. Measured:

- It runs for unknown paths too: a 404 response carried the header.
- It must be called **before** `init()` (which `listen()` calls). Called afterwards it is ignored: the header was missing and the status was still 200.
- It has no injection. To use a provider, fetch it first: `const counter = app.get(Counter); app.use(...)` (worked).
- `app.use('/c', fn)` mounts by prefix and strips it from `req.url` (`/?z=1` for `/c?z=1`), like a string in `forRoutes`.
- Order against module middleware: global first (below).

Global class middleware does not exist: a class registered through `configure()` can apply to every route with `forRoutes('{*splat}')` (measured: runs for everything, 404s included), and that gives it DI.

### The global prefix

With `app.setGlobalPrefix('api')` Nest adds the prefix to `forRoutes` and `exclude` paths for you (measured): `forRoutes('cats')` ran for `/api/cats` and `/api/cats/1` and not for `/api/dogs`; `exclude('cats/health')` skipped `/api/cats/health`; `forRoutes('{*splat}')` also ran for the unknown `/api/nope`. **Do not repeat the prefix**: `forRoutes('api/cats')` matched nothing. A global `app.use(fn)` is not tied to the prefix at all.

## What Middleware Sees

### The URL and parameters

The request object looks different depending on how the middleware was mounted. Measured for `GET /c/x/7?q=1`:

| Registered with | `req.url` | `req.baseUrl` | `req.params` |
|---|---|---|---|
| string `'c'` | `/x/7?q=1` | `/c` | `{}` |
| string `'{*splat}'` | `/?q=1` | `/c/x/7` | `{ splat: ['c','x','7'] }` |
| controller class | `/c/x/7?q=1` | `` (empty) | `{ id: '7' }` |
| `{ path: 'c/x/:id', method }` | `/c/x/7?q=1` | `` (empty) | `{ id: '7' }` |
| global `app.use(fn)` | `/c` (the test hit `/c`) | | |

So `req.url` is **not stable**: a string mount rewrites it (the `app.use(path)` behaviour). Always log and branch on **`req.originalUrl`**, which was `/c/x/7?q=1` in every row. And `req.params` is only filled when the middleware is mounted on a route pattern (controller class or `RouteInfo`).

### The body

Nest registers the body parsers at `init()`, after your `app.use()` calls and before module middleware. Measured: a module middleware saw `req.body = { a: 1 }`; a global `app.use` middleware saw `req.body` **undefined** for the same POST. A global middleware that needs the body must run its own parser, or be registered as module middleware with `forRoutes('{*splat}')` instead (raw bodies for signature checks are 3.7).

### The handler: it does not know

A middleware runs before Nest has chosen a handler. Nothing in `(req, res, next)` says which controller or method will run, there is no `ExecutionContext`, and no access to metadata set by decorators. Measured: with a string path `req.route` is `undefined`, while the handler itself sees `req.route.path = '/obs/x/:id'`. With a controller class in `forRoutes`, Express does set `req.route`, but it describes the middleware's **own mount point** (its JSON contained no controller or method name), not the handler. That is the structural reason authorization that depends on `@Roles()` or `@Public()` belongs in a guard (1.7), which does get an `ExecutionContext` (2.7).

## Order of Execution

Middleware runs in the order it was registered, as in Express. Measured:

| Setup | Order |
|---|---|
| root module applies `D`; imported feature module applies `A, B` then `C`; a global `app.use` | `global -> D -> A -> B -> C -> handler` |
| `apply(B, A)` | `B -> A` (the argument order) |
| two sibling modules imported as `[S2, S1]`, each applying one | `X2 -> X1` (import order) |
| `Root` (applies `Shallow`) imports `Mid` imports `Deep` (applies `Deep`) | `Shallow -> Deep` |

Source (`MiddlewareModule.registerMiddleware`): configurations are sorted by module **distance** from the root, global modules first (distance `MAX_VALUE` sorts first), then the module nearest the root, then deeper ones; ties keep registration order. Inside one module, `apply()` calls run in call order and the arguments of one `apply()` in argument order.

Practical rules: put middleware that others depend on (request id before logging) in the same `apply(...)` in the right order, do not depend on cross-module order for correctness, and remember global middleware always goes first.

## Ending a Request

A middleware must do exactly one of these. Measured, each as a class middleware on `GET /c` with a handler that records whether it ran:

| What the middleware does | Result | Handler ran |
|---|---|---|
| `next()` | the request continues | yes |
| `res.status(401).json({...})` and no `next()` | that response is sent | **no** |
| `throw new ForbiddenException('nope')` | **403** `{"message":"nope","error":"Forbidden","statusCode":403}` | no |
| `async` and throws `ForbiddenException` | 403, same body | no |
| `next(new ForbiddenException(...))` | 403 | no |
| throws a plain `Error` | **500** `{"statusCode":500,"message":"Internal server error"}` | no |
| neither answers nor calls `next()` | **the request hangs** until the client times out | no |
| answers **and** calls `next()` | the client gets the answer, but the handler runs anyway and `ERR_HTTP_HEADERS_SENT` is logged | **yes** |
| sets a header and calls `next()` | normal | yes |

A global functional middleware (`app.use`) that throws a `ForbiddenException` or calls `next(err)` also produced the 403, and a plain `Error` a 500: Nest's exception layer handles errors from middleware too. Answering **and** calling `next()` is the quiet bug: measured, the client got the 401 body, but the handler **still ran** (with its side effects) and Nest logged `Error [ERR_HTTP_HEADERS_SENT]: Cannot set headers after they are sent to the client` when the handler tried to reply.

Two notes from the source. Exception filters bound to a middleware with `@UseFilters()` apply only as **instances**; a filter class is ignored and Nest logs a warning saying so (`MiddlewareModule.warnAboutFilterClasses`); register filters globally instead (1.9). And throwing an `HttpException` is usually cleaner than hand-writing the response, unless you need an exact body, as the exercise's 401 does.

## Express 5 Paths in forRoutes

`forRoutes()` and `exclude()` paths use the same path-to-regexp 8 syntax as `@Get()` (1.3). Measured:

| Path | Result |
|---|---|
| `'cats/*splat'`, `'cats/{*splat}'`, `'{*splat}'` | work (see the table above for what each covers) |
| `'*'` | works, **no warning**: Nest converts the bare all-wildcard silently |
| `'cats/*'` | boots with a warning: `Unsupported route path: "/cats/*". In previous versions, the symbols ?, *, and + were used to denote optional or repeating path parameters. ...` and Nest converts it |
| `'cats/(.*)'` | boots with the same warning and conversion |
| `'cats/:id?'` | **crashes at startup**: `PathError: Unexpected ? at index 9: /cats/:id?` |

Treat the warning as a bug to fix, as in 1.3: the converted path is `cats/{*splat}`, which also matches `/cats/`, and the migration is not always this kind. The roadmap lists "Express 5 wildcard changes in `forRoutes`" for this topic: the one-line summary is that a wildcard now needs a name, braces make a part optional, and `?`, `+` and regex groups are gone.

## Middleware, Guard or Interceptor

| Need | Use | Why |
|---|---|---|
| request logging, request ids, correlation ids | middleware | HTTP-level, should also see 404s and rejected requests |
| CORS, helmet, compression, cookie parsing, body parsers | middleware | they are Express middleware and work before routing (5.3) |
| rate limiting at the HTTP edge | middleware (or `@nestjs/throttler`, which is a guard, 5.3) | decide before any handler work |
| authentication that is the same for every route | middleware **or** a global guard | middleware is fine only if no route needs to opt out by metadata |
| authorization, `@Public()`, `@Roles()` | **guard** (1.7) | needs the `ExecutionContext` and decorator metadata |
| transform the response, timing, caching | **interceptor** (1.8) | wraps the handler and sees its result |
| validate or convert inputs | **pipe** (1.6) | runs on the handler's arguments |
| map errors to responses | **exception filter** (1.9) | |

The decision rule: **if it must know which handler runs, it is not middleware.** The other direction: if it must also act on requests no handler matches, or before the body is parsed, it cannot be a guard. This topic's interview question "where does authentication go" is answered fully in 1.7 and 5.1.

## Testing Middleware

Two levels, both in the exercise.

```ts
// 1. A functional middleware is a function: call it with fakes.
const res = { setHeader: vi.fn() } as unknown as Response;
const next = vi.fn();
tagResponse({} as Request, res, next);
expect(res.setHeader).toHaveBeenCalledWith('x-tagged', 'yes');
expect(next).toHaveBeenCalledTimes(1);

// 2. Route selection, order and the body need a real application: createNestApplication
//    plus supertest. Register app.use(...) BEFORE app.init().
const app = moduleRef.createNestApplication();
configureApp(app);
await app.init();
await request(app.getHttpServer()).get('/hello').expect(200);
```

Level 1 cannot tell you which routes a `forRoutes()` covers, in what order middleware runs, or whether a provider is injected: only level 2 does. Test the **negative** as well (the excluded route, the other controller) since "the middleware did not run" is as much a requirement as "it ran". To read the order, give each middleware a shared log provider, as `order.spec.ts` does.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| Neither answering nor calling `next()` | the request hangs | exactly one of the two |
| Answering **and** calling `next()` | the handler runs on an answered request | `return` after answering |
| `req.body` in global `app.use` middleware | `undefined`: it runs before the parsers | module middleware with `forRoutes('{*splat}')`, or parse it yourself |
| `app.use()` after `init()` / `listen()` | ignored silently | register before `init()` |
| Branching on `req.url` | rewritten by string mounts | use `req.originalUrl` |
| `forRoutes('cats')` and expecting it to match only real routes | it also runs on 404s below `/cats` | pass the controller class |
| `forRoutes('api/cats')` with a global prefix | matches nothing | no prefix in the path |
| `exclude(...)` after `forRoutes(...)` | it does not exist on the consumer | `apply().exclude().forRoutes()` |
| Expecting `exclude('cats')` to exclude `/cats/1` | it is an exact match | `exclude('cats/*splat')` |
| Excluding a path and forgetting the method | both `GET` and `POST` are excluded | `{ path, method }` |
| Class middleware needing a provider that is not in the module | `Nest can't resolve dependencies of the X (?)` naming the module | import or provide it in that module (1.2) |
| State in a field of a class middleware | shared across requests | arguments and locals (1.4) |
| `forRoutes('cats/:id?')` | `PathError` at startup | `cats{/:id}` |
| `forRoutes('files/*')` | works, with a warning and a changed path | `files/*splat` |
| Using middleware for per-handler decisions | cannot see the handler | a guard (1.7) |
| Relying on cross-module middleware order | fragile: module distance and import order | one `apply(...)` in the right order |

## Interview Questions

**1. What is middleware in Nest, and how does it differ from a guard or an interceptor?**
Express-style `(req, res, next)` code that runs before the route handler, registered globally with `app.use` or per module with `configure(consumer)`. It runs before Nest chooses a handler, so it has no `ExecutionContext` and cannot see decorator metadata, and it also runs for paths no route handles. Guards run after it with an `ExecutionContext` to decide whether the handler may run, and interceptors wrap the handler and see its result.

**2. Class or functional middleware?**
A function is enough for stateless work and third-party Express middleware, and can be registered with `app.use`. A class is built by Nest, so it can inject providers (config, loggers), is registered per module through `configure()`, and is tested through Nest. A function cannot be injected; a class cannot be used with a bare `app.use` without going through the module.

**3. How do you apply middleware to all routes of a controller except one?**
`consumer.apply(M).exclude({ path: 'x/health', method: RequestMethod.GET }).forRoutes(XController)`. `exclude` goes before `forRoutes`, takes an exact path and optionally a method, and the path has no leading slash and no global prefix.

**4. What is the difference between `forRoutes('cats')` and `forRoutes(CatsController)`?**
A string is mounted like `app.use('/cats', fn)`: a prefix match at a segment boundary that also runs for paths with no route (a 404 under `/cats`), and `req.url` loses the prefix. A controller class is mounted on the controller's actual routes only, keeps `req.url` and fills `req.params`, and follows the controller if its prefix changes.

**5. In what order does middleware run?**
Global `app.use` first, then module middleware by module distance from the root (global modules first, shallower before deeper, siblings in import order), and inside a module by `apply()` call order and argument order. Then the handler's own pipeline (guards, interceptors, pipes).

**6. Why is `req.body` undefined in my global middleware?**
Nest mounts the body parser at `init()`, after any `app.use` you wrote, so the global middleware runs before the body is parsed. Module middleware runs after the parsers and sees it. Parse it yourself, or register the middleware through `configure()` with `forRoutes('{*splat}')`.

**7. What happens if a middleware neither responds nor calls `next()`?**
The request hangs until the client times out, and the handler never runs. If it answers and also calls `next()`, the client gets the answer but the handler still runs and `ERR_HTTP_HEADERS_SENT` is logged (measured).

**8. How do you reject a request from middleware?**
Answer it yourself (`res.status(401).json(...)`) and do not call `next()`, or throw an `HttpException`, which the exception layer turns into its response (a plain `Error` becomes a 500). Authorization that depends on the target handler belongs in a guard.

**9. Does middleware have access to the `ExecutionContext`?**
No. It runs before a handler is selected, so it does not know the controller or method (measured: `req.route` is undefined for a string path, and only the middleware's own mount point otherwise). Use a guard or an interceptor when the decision depends on the handler.

**10. What changed with Express 5 for `forRoutes`?**
Wildcards need names (`*splat`, `{*splat}`), optional parts use braces, and `?`, `+` and regex groups are gone. Nest auto-converts a trailing `*` and `(.*)` with a warning, and converts the bare `*` silently, but `:id?` crashes at startup with a `PathError`.

**11. Where do you register helmet, CORS or a request logger?**
Third-party Express middleware goes in `main.ts` with `app.use(...)` before `listen()`. A logger that needs a service is a class middleware applied with `forRoutes('{*splat}')`, or a function that closes over a provider fetched with `app.get()`.

## Check Yourself

- [ ] I can write a functional and a class middleware and say what each can and cannot do.
- [ ] I can register middleware globally and per module, and say why `app.use` must come before `init()`.
- [ ] I can say what each `forRoutes` form matches, and which one also runs on a 404.
- [ ] I can use `exclude` with a method, and I know it comes before `forRoutes` and matches exactly.
- [ ] I know why `req.body` is undefined in global middleware and why `req.url` can differ, and which property to use instead.
- [ ] I can predict the order of several middlewares across modules.
- [ ] I can name the ways a middleware can end a request, and what happens when it picks none or two.
- [ ] I can explain why middleware cannot make per-handler decisions, and which component does.
- [ ] I can write `forRoutes` paths in the Express 5 syntax and recognise the legacy forms.
- [ ] I finished the exercise: [05_middleware](../../projects/phase_01_core_building_blocks/05_middleware/README.md).

## Further Reading

- Official documentation: [Middleware](https://docs.nestjs.com/middleware) (class and functional middleware, applying, route wildcards, excluding, global middleware). Not re-read for this note: the behaviour above was measured on 12.5.1 instead.
- [Express: writing middleware](https://expressjs.com/en/guide/writing-middleware.html) for the underlying `(req, res, next)` contract.
- Source worth reading in the installed `node_modules/@nestjs/core/middleware/`, in this order: `builder.js` (`apply`, `exclude`, `forRoutes`, `removeOverlappedRoutes`), `middleware-module.js` (`loadConfiguration`, `registerMiddleware`, `bindHandler`, `registerHandler`), `resolver.js`, `route-info-path-extractor.js`, `routes-mapper.js`. The interfaces are in `@nestjs/common/interfaces/middleware/`.
- Related topics: [1.2 Modules](02_modules.md), [1.3 Controllers and Routing](03_controllers_and_routing.md), [1.4 Providers and Services](04_providers_and_services.md), 1.6 Pipes, 1.7 Guards, 1.8 Interceptors, 1.9 Exception Filters, 1.10 Request Lifecycle, 2.4 Injection Scopes, 2.7 Execution Context, 3.7 HTTP Features, 3.8 HTTP Adapters, 5.3 Web Security Hardening.

# 1.10 Custom Decorators and the Request Lifecycle

> **Topic 1.10** | Priority: Core | Prerequisites: [1.3 Controllers and Routing](03_controllers_and_routing.md) through [1.9 Exception Filters](09_exception_filters.md) (this topic ties them together), [03 TypeScript Features Nest Is Built On](../phase_00_orientation/03_typescript_for_nest.md) | Time: about 3 hours reading plus 3 hours for the exercise | Exercise: [10_decorators_and_lifecycle](../../projects/phase_01_core_building_blocks/10_decorators_and_lifecycle/README.md) | Next: the Phase 1 milestone `11_milestone_tasks_api` (not written yet), then [Phase 2](../../docs/01_nestjs_roadmap.md#phase-2-under-the-hood-with-di-and-fundamentals) | Roadmap: [1.10 Custom Decorators and the Request Lifecycle](../../docs/01_nestjs_roadmap.md#110-custom-decorators-and-the-request-lifecycle)
>
> Everything marked "measured" was run against `@nestjs/common` and `@nestjs/core` 12.5.1 with the Express adapter on Node 24.22.3. Items marked "source" were read from the installed code and not run. The scratch experiments are not kept: the exercise tests reproduce the important ones.

## Table of Contents

- [Why This Topic Matters](#why-this-topic-matters)
- [Custom Parameter Decorators](#custom-parameter-decorators)
  - [What createParamDecorator gives you](#what-createparamdecorator-gives-you)
  - [When the factory runs](#when-the-factory-runs)
  - [Data, pipes and the first argument](#data-pipes-and-the-first-argument)
  - [Async factories and typing](#async-factories-and-typing)
  - [When not to write one](#when-not-to-write-one)
- [Composing Decorators](#composing-decorators)
  - [applyDecorators](#applydecorators)
  - [A composed decorator and its traps](#a-composed-decorator-and-its-traps)
- [The Request Lifecycle](#the-request-lifecycle)
  - [The diagram](#the-diagram)
  - [Four requests, measured](#four-requests-measured)
  - [Stage by stage](#stage-by-stage)
  - [The order of binding scopes](#the-order-of-binding-scopes)
  - [When the status and headers are written](#when-the-status-and-headers-are-written)
  - [A path with no route](#a-path-with-no-route)
  - [Finding the order yourself](#finding-the-order-yourself)
- [Where Does This Go](#where-does-this-go)
- [Testing Decorators](#testing-decorators)
- [Common Pitfalls](#common-pitfalls)
- [Phase 1 Interview Checkpoint](#phase-1-interview-checkpoint)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why This Topic Matters

Two things happen here. First, you learn the last two decorator tools: a **parameter decorator** that pulls a value out of the request (`@CurrentUser()`), and **composition** that turns a recipe of several decorators into one (`@Auth('admin')`). Second, you assemble everything from 1.3 to 1.9 into **one picture**: the order a request passes through middleware, guards, interceptors, pipes, the handler, and back through interceptors and filters.

That picture is the most-asked Nest interview topic ("walk me through the request lifecycle") and the one that explains most of the surprises of Phase 1: why an interceptor never sees a guard denial, why a pipe error is visible to an interceptor, why a global middleware has no body, why a controller-level filter does not catch a 404.

## Custom Parameter Decorators

### What createParamDecorator gives you

Handlers that need the current user do not have to take the whole request:

```ts
export const CurrentUser = createParamDecorator((data: keyof User | undefined, context: ExecutionContext) => {
  const user = context.switchToHttp().getRequest<AuthedRequest>().user;
  return data ? user?.[data] : user;
});

@Get('name')
name(@CurrentUser('name') name?: string) { /* ... */ }
```

The factory receives two things:

| Argument | Is | Example |
|---|---|---|
| `data` | the first argument of the decorator call | `'name'` for `@CurrentUser('name')`, `undefined` for `@CurrentUser()` |
| `context` | the `ExecutionContext` guards receive (1.7) | `getRequest()`, `getClass()`, `getHandler()`, `getType()` |

What it returns is what the handler's parameter receives. The decorator reads; it does not authenticate. `request.user` has to be put there by something earlier, normally a guard (1.7). Measured: a handler with `@CurrentUser()` and no guard that attached a user received `undefined`, not an error, which is why the factory uses `?.`.

### When the factory runs

Measured with a log written by a guard, an interceptor, the factory and the handler:

```
guard > interceptor:before > factory > handler
```

The factory runs **after the guards**, which is why it can read what a guard attached, and **inside the interceptors' "before" part**, together with the pipes (source: it is the value-extraction step of the pipes function in `RouterExecutionContext`). It runs **once per use of the decorator, on every request**: a handler with two `@CurrentUser(...)` parameters ran the factory twice per request (measured: 4 runs for 2 requests of such a route). Nothing is cached between requests, so keep the factory cheap and pure.

### Data, pipes and the first argument

A custom decorator is a normal parameter decorator for pipes (1.6). Measured: a pipe bound on it saw `type: 'custom'`, `data` equal to what you passed, and `metatype` equal to the TypeScript type of the parameter (`String` for `name: string`, `Object` for an untyped one). `@CurrentUser('name', UpperPipe)` returned `ADA`.

There is one ambiguity, and the source settles it: the first argument is **either data or a pipe**. `createParamDecorator` checks whether it looks like a pipe (a class with `transform`, or an object with `transform`); if it does, it is treated as a pipe and `data` is `undefined`. Measured: `@CurrentUser(UpperPipe)` gave the pipe `data=undefined` and the whole user. So data that is itself a pipe-shaped object cannot be passed as data. In v12 the first argument may also be an options object with `schema` and/or `pipes` (source: `isParameterDecoratorOptions`), which is how a Standard Schema can be attached to a custom decorator (1.6); the pipe only validates custom decorators when `validateCustomDecorators: true`.

`createParamDecorator` also accepts a second argument, an array of **enhancers** (source: `ParamDecoratorEnhancer`): extra parameter decorators applied together with it, used for documentation decorators.

### Async factories and typing

A factory may be `async`: measured, the pipe received the resolved value (`{ later: 'k' }`), not a Promise. Type the data with the generic or by annotating the factory's first parameter: `createParamDecorator<keyof User | undefined>` makes `@CurrentUser('nmae')` a compile error, and gives the editor completion for the property names. When the decorator takes no data, annotate it `unknown` (`_data: unknown`) and ignore it.

### When not to write one

A parameter decorator is for **extracting** a value from the request: the user, a header, a tenant id, a parsed locale. It is not the place for business logic or for anything that needs injection (a factory has no constructor and no providers: use a pipe, 1.6, or a guard that attaches the value, 1.7). It also assumes HTTP once it calls `switchToHttp()`; for code that must work for WebSockets or microservices check `context.getType()` first (2.7). Benefits: handlers stop depending on `@Req()` and on the Express types that come with it (3.8), and the concept gets a name.

## Composing Decorators

### applyDecorators

```ts
export const Auth = (...roles: string[]) =>
  applyDecorators(Roles(roles), UseGuards(AuthGuard, RolesGuard));
```

`applyDecorators(...decorators)` returns **one** decorator that applies each of them, in the order listed (source: a loop). It works on a class and on a method, and it can contain any class, method or property decorator: `@UseGuards`, `@UseInterceptors`, `@SetMetadata`, a `Reflector.createDecorator` decorator (1.7), `@HttpCode`, documentation decorators (3.6). It cannot contain a **parameter** decorator: the type does not allow it (use the `enhancers` argument of `createParamDecorator` for that).

The point is to encode a convention that is easy to get wrong: here the metadata, both guards, and the **order of the guards** (authentication before authorization, so a missing login is a 401 and `RolesGuard` has a user to look at). Measured in the exercise: no header gave 401, a known user without the role 403, and the same `@Auth` worked on single routes and on a whole class.

### A composed decorator and its traps

Measured with `@Auth('admin')` on a class, `@Auth('editor')` on one of its methods, and a decorator composed of two `UseGuards` calls:

| Setup | Guards that ran |
|---|---|
| `@Both()` = `applyDecorators(UseGuards(G1), UseGuards(G2))` on a method | `G1, G2` (listed order, accumulated) |
| `@One()` = `applyDecorators(UseGuards(G1))` on the class **and** on a method | `G1, G1`: bound at **both** levels, so it runs **twice** for that route |
| `@Auth('admin')` on the class and `@Auth('editor')` on a method | `G1, RolesGuard, G1, RolesGuard`, and **both** `RolesGuard` runs read the handler's `['editor']` (the handler's metadata wins, 1.7), so the class-level decoration adds nothing but a second run |

So: a composed decorator that binds guards (or interceptors, pipes, filters) applies them **wherever you put it**. Put it once, at the level you mean, and do not rely on the class-level copy being "overridden" by the method-level one: both are bound. Metadata, on the other hand, does follow the handler-over-class rule when the guard reads it with `getAllAndOverride`.

## The Request Lifecycle

### The diagram

```
                      request
                         |
        global middleware           app.use(...)                       runs before the body parser
        module middleware           configure(consumer)                after it; only for the routes it covers
                         |
        guards                      global, controller, method         one at a time; a denial stops here
                         |
        @HttpCode status and @Header headers are written here
                         |
        interceptors, "before"      global, controller, method
        pipes                       global, controller, method, parameter     (and the custom decorators' factories)
        HANDLER
        interceptors, "after"       method, controller, global         the reverse order
                         |
                      response

   an error from the handler, the pipes, or an interceptor  --> interceptors see it (reverse order) --> exception filters
   a guard denial or an error from middleware               --> straight to the exception filters
   a path that matches no route                             --> global middleware, then the global filters
```

### Four requests, measured

The exercise's application has a component of every kind at every scope (the global ones through `app.use`, `useGlobalGuards`, and so on). Measured traces, with `before:`/`after:` for interceptors:

**Success** (`GET /life/ok/1`):

```
mw:global > mw:module
> guard:global > guard:controller > guard:method
> before:global > before:controller > before:method
> pipe:global > pipe:controller > pipe:method > pipe:param
> handler
> after:method > after:controller > after:global
```

**A guard denies** (the method guard returns false): everything stops after the guard that said no.

```
mw:global > mw:module > guard:global > guard:controller > guard:method > filter:method
```

No interceptor, no pipe, no handler: a denied request is the cheapest request.

**A pipe throws** (the parameter pipe): the interceptors had already started, so they see the error, innermost first, then the filter answers.

```
... guard:method > before:global > before:controller > before:method
> pipe:global > pipe:controller > pipe:method > pipe:param
> error:method > error:controller > error:global > filter:method
```

**The handler throws**: the same, with the handler line before the errors.

```
... pipe:param > handler > error:method > error:controller > error:global > filter:method
```

The method-level filter answered each time, not the global one: only one filter handles an exception, and the narrowest wins (1.9).

### Stage by stage

| Stage | Sees | Can do | If it throws or denies |
|---|---|---|---|
| Middleware (1.5) | `req`, `res`, `next`; not the handler | read and change the request, answer | the exception filters (measured, also for `app.use`) |
| Guards (1.7) | `ExecutionContext`: class, handler, metadata | allow or deny, attach data to the request | a denial is a 403 through the filters; interceptors never run |
| Interceptors, before (1.8) | `ExecutionContext` and the handler as an Observable | code before, skip or repeat the handler | the filters |
| Pipes (1.6) and custom decorators | one argument and its metadata | transform, validate, throw | interceptors see it, then filters |
| Handler (1.3) | its arguments | the work | interceptors see it, then filters |
| Interceptors, after (1.8) | the handler's result or error | reshape, time, cache, remap errors | the filters |
| Exception filters (1.9) | the exception, `ArgumentsHost` | write the response | none matches: Nest's default handling |

### The order of binding scopes

The short rule "global, then controller, then route" is right for the **forward** direction of guards, interceptors and pipes. The exceptions are the reason to know the table:

| Component | Collected in the order | Notes (all measured in the earlier topics) |
|---|---|---|
| Middleware | global (`app.use`) first, then module middleware by module distance from the root, then registration order | middleware has no controller or route scope; only a path (1.5) |
| Guards | global, controller, method; left to right in one `@UseGuards(a, b)` | one at a time, the first denial stops the rest (1.7) |
| Interceptors | global, controller, method; left to right | the first is outermost: "before" runs in this order, "after" in the **reverse** (1.8) |
| Pipes | global, controller, method, then the parameter's own | per parameter; different parameters run together (1.6) |
| Filters | tried **narrowest first**: method, controller, global; the last of `@UseFilters(a, b)` first | only **one** filter handles the exception (1.9) |

### When the status and headers are written

Measured on a route with `@HttpCode(202)` and `@Header('x-fixed', 'yes')`: a guard saw `res.statusCode` = **200** and no header; an interceptor's "before" part saw **202** and the header. A denied request (403) carried neither. So Nest applies the `@HttpCode` status and the `@Header` values after the guards pass and before the interceptors start (source: `setStatus` and `setHeaders` in the route function). Consequence: guards cannot rely on the response status, and a failed request keeps only what an exception sets.

### A path with no route

Measured: for a path that matches no route, the global middleware ran, the module middleware did not (it was mounted on a controller's routes), and **no guard, interceptor or pipe** ran, because there is no handler. The router's own 404 is an exception like any other and reached the **global** filter. That is the trace `['mw:global', 'filter:global']` of the exercise. A controller or method filter cannot catch it, because no controller was matched.

### Finding the order yourself

When you are unsure what runs when, **log it**. Give each component a name and push it into one array, as the exercise's `components.ts` does (a `Trace*` class per kind taking a scope name), run a request and read the array. It takes ten minutes and replaces memorising: this is how every trace in these notes was produced. For the middleware part, remember the body: global `app.use` middleware runs before the body parser, module middleware after (1.5). Nest Devtools (a graph of modules, mentioned in the 1.2 notes) shows the module graph, not the per-request order.

## Where Does This Go

| You want to | Put it in | Why |
|---|---|---|
| authenticate | a guard (global, with a `@Public()` opt-out) | it needs the handler's metadata and runs before anything expensive |
| authorize by role or policy | a guard reading metadata | same |
| validate or convert an argument | a pipe | per parameter, before the handler |
| reshape the response, add timing, cache, timeout | an interceptor | it wraps the handler and sees the result |
| turn an error into a response, one error shape for the API | a global exception filter | the only component that sees every error |
| map a domain error to a status | a filter | keeps services HTTP-free |
| log every request, add a request id, CORS, helmet | middleware | it runs first, also for 404s |
| pull the user, a header or a locale out of the request | a custom parameter decorator | extraction only |
| repeat the same three decorators on many routes | a composed decorator (`applyDecorators`) | one name for one convention |
| business rules | a service (1.4) | none of the above |

## Testing Decorators

A parameter decorator has no object to call: the factory lives inside `createParamDecorator`. Two approaches:

```ts
// 1. Test through HTTP: a controller that uses the decorator, a guard or the request that fills it,
//    and supertest. This is what the exercise does, and it also proves the factory runs where you expect.
const res = await request(app.getHttpServer()).get('/profile/name').set('x-user', 'ada');

// 2. Keep the logic in a plain function and make the decorator a thin wrapper, so the function can be
//    unit tested without any Nest machinery (a design suggestion, not something Nest provides).
export function pickUser(user: User | undefined, key?: keyof User) { return key ? user?.[key] : user; }
export const CurrentUser = createParamDecorator((key: keyof User | undefined, ctx: ExecutionContext) =>
  pickUser(ctx.switchToHttp().getRequest<AuthedRequest>().user, key));
```

A **composed decorator** is tested by what it produces: through HTTP (the 401, 403 and 200 above), and for the metadata with `Reflector`'s `get(Roles, handler)` (1.7). Test the negatives too: no user, wrong role, and the unprotected route.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| a parameter decorator that reads `request.user` with no guard before it | `undefined`, or a crash on `.name` | a guard attaches it first, and the factory uses `?.` |
| business logic or an injected service in a decorator factory | not possible: no injection | a pipe or a guard |
| passing a pipe-shaped object as `data` | it is taken as a pipe | pass something else |
| a heavy factory | it runs per use, per request | keep it cheap, or compute in a guard once |
| `applyDecorators` on a class and a method | guards, interceptors, pipes bound at both levels run twice | decorate once, at the level you mean |
| expecting a method-level composed decorator to "override" a class-level one | both are bound; only the metadata is overridden | remove one |
| guards in the wrong order inside the composition | 403 instead of 401, or a crash on a missing user | authentication first |
| putting a parameter decorator inside `applyDecorators` | not allowed by the type | `createParamDecorator`'s enhancers |
| assuming a guard sees the final response status | it sees the default, `@HttpCode` is applied after | do not depend on it |
| expecting an interceptor to see a guard denial | it never ran | a filter |
| a controller-level filter expected to catch a 404 for an unknown path | no controller matched | a global filter |
| thinking global and module middleware run at the same stage as guards | they run before, and global runs before the body parser | check `req.body` assumptions (1.5) |
| memorising the order instead of logging it | wrong in the edge cases (errors, 404s) | a trace of named components |
| assuming the "after" order matches the "before" order | it is the reverse | draw the Russian doll |

## Phase 1 Interview Checkpoint

The roadmap's five questions for the whole phase, with model answers:

**1. Walk through the request lifecycle. Where do you put authentication, validation, response shaping and error mapping?**
Global middleware, then module middleware, then guards (global, controller, method), then the interceptors' "before" part, then pipes, the handler, the interceptors' "after" part in reverse order, and exception filters for any error. Authentication in a global guard with an `@Public()` opt-out; validation in pipes; response shaping in interceptors; error mapping in a global exception filter. Errors from the handler and pipes pass back through the interceptors first; a guard denial and middleware errors go straight to the filters; an unknown path reaches only global middleware and global filters.

**2. When do you use middleware, a guard or an interceptor?**
Middleware for HTTP-level work that must run first and for every path (request ids, CORS, helmet, logging, cookie parsing); it does not know the handler. A guard to decide whether the handler may run, with the `ExecutionContext` and decorator metadata. An interceptor when you need both sides of the handler: reshaping the response, timing, caching, timeouts, or skipping the handler.

**3. Why are providers module-scoped, and how do you share one between modules?**
So that the container enforces encapsulation at startup: a provider is private to its module unless the module exports it and the consumer imports that module (or a module re-exports it). A module is a singleton, so a shared module yields one instance. Listing a provider in two modules creates two instances. (1.2, 1.4)

**4. What breaks when you inject `@Res()` without `passthrough`?**
Nest's response handling is turned off for that handler: the returned value is ignored and the handler must end the response itself, otherwise the request hangs. Interceptors cannot map the result, and the handler is tied to Express and harder to test. With `{ passthrough: true }` you get the response object but Nest still sends the return value. (1.3)

**5. How do you register a global guard that still has access to DI?**
As a provider with the `APP_GUARD` token and `useClass` in any module: `{ provide: APP_GUARD, useClass: MyGuard }`. It applies to the whole application and Nest builds it, so it can inject the `Reflector` and your services. `app.useGlobalGuards(new MyGuard())` takes an instance built outside the container, so nothing is injected. (1.7)

## Interview Questions

**1. What does `createParamDecorator` give you, and when does the factory run?**
A parameter decorator whose factory receives `(data, executionContext)` and returns what the handler's parameter gets. It runs on every request, once per use, after the guards and as part of the interceptors' "before" part along with the pipes, so it can read what a guard attached.

**2. Can a custom parameter decorator use pipes?**
Yes: `@CurrentUser('name', UpperPipe)`. The pipe sees `type: 'custom'`, the data and the parameter's TypeScript type. If the first argument is itself a pipe it is treated as a pipe, not as data. In v12 an options object with `schema` or `pipes` is also accepted.

**3. What is `applyDecorators` for, and what can it not contain?**
It composes several class, method or property decorators into one, applied in the order listed (a metadata decorator plus guards, for example). It cannot contain parameter decorators. Composed guards are bound wherever the decorator is used, so using it on a class and a method runs them twice.

**4. What is `@CurrentUser()` doing that `@Req()` is not?**
It extracts one thing, typed and named, so handlers do not depend on the Express request type and do not repeat `req.user`. It reads what a guard attached; it does not authenticate.

**5. In what order do the lifecycle stages run?**
Middleware, guards, interceptors (before), pipes, handler, interceptors (after), exception filters on an error. Within each, global before controller before method, except that the "after" half of interceptors is reversed and filters are tried narrowest first.

**6. Which stages does an error from a pipe pass through? From a guard?**
A pipe error passes back through the interceptors (they see it as an error, innermost first) and then reaches the filters. A guard denial skips interceptors, pipes and the handler and goes straight to the filters.

**7. When does Nest write the `@HttpCode` status and `@Header` values?**
After the guards and before the interceptors: a guard sees the default status (200) and an interceptor's "before" part already sees the `@HttpCode` one. A denied request carries neither.

**8. What runs for a path that matches no route?**
Global middleware (`app.use`) and the global exception filters. No guard, interceptor or pipe, and no controller- or method-level filter, because no handler was matched; module middleware only if its path covers it.

**9. Where does the body get parsed relative to your middleware?**
After global `app.use` middleware and before module middleware: a global middleware sees `req.body` as undefined, a module middleware sees it parsed. (1.5)

**10. How do you find out what order your components run in?**
Give each a name and write it into a shared trace, run the request and read it. The four traces in these notes (success, guard denial, pipe failure, handler failure) were produced that way.

**11. A composed `@Auth('editor')` on a method inside a class with `@Auth('admin')`: which roles apply?**
The handler's: the guard reads the metadata with `getAllAndOverride`, so `['editor']`. But the guards are bound at both levels and run twice, so the class-level copy only costs a second run.

**12. What goes in a custom decorator and what does not?**
Extraction of a value from the request (user, header, locale), typed. Not business logic and nothing that needs injection: use a pipe or a guard for that.

## Check Yourself

- [ ] I can write a parameter decorator with `createParamDecorator`, type its data, and say when its factory runs.
- [ ] I know a custom decorator accepts pipes and what a pipe sees on it, and when the first argument is data or a pipe.
- [ ] I can compose guards and metadata with `applyDecorators` and name its trap (bound at every level it is used on).
- [ ] I can draw the lifecycle diagram from memory, including the reverse "after" order of interceptors.
- [ ] I can say for a guard denial, a pipe error, a handler error and an unknown path which stages run and who answers.
- [ ] I know when `@HttpCode` and `@Header` are applied relative to guards and interceptors.
- [ ] I can state the order of binding scopes for each component, and where filters differ.
- [ ] I can say where authentication, validation, response shaping and error mapping belong.
- [ ] I can answer the five Phase 1 checkpoint questions without looking.
- [ ] I finished the exercise: [10_decorators_and_lifecycle](../../projects/phase_01_core_building_blocks/10_decorators_and_lifecycle/README.md).

## Further Reading

- Official documentation: [Custom route decorators](https://docs.nestjs.com/custom-decorators) (param decorators, working with pipes, decorator aggregation) and the [Request lifecycle](https://docs.nestjs.com/faq/request-lifecycle) page. Neither was re-read for this note: the behaviour above was measured on 12.5.1 instead, and the lifecycle page's order should agree with the traces here.
- Source worth reading in the installed `node_modules/@nestjs/`, in this order: `common/decorators/http/create-route-param-metadata.decorator.js` (data versus pipe, enhancers, options), `common/decorators/core/apply-decorators.js` (six lines), then `core/router/router-execution-context.js` (`create` is the lifecycle in one function: guards, `setStatus`, `setHeaders`, interceptors, pipes, handler, response) and `core/router/router-proxy.js`.
- Related topics: every topic of this phase ([1.2](02_modules.md), [1.3](03_controllers_and_routing.md), [1.4](04_providers_and_services.md), [1.5](05_middleware.md), [1.6](06_pipes.md), [1.7](07_guards.md), [1.8](08_interceptors.md), [1.9](09_exception_filters.md)), 2.7 Execution Context and Metadata (writing components that work in any transport), 3.6 OpenAPI and Swagger (documentation decorators in a composed decorator), 5.1 Authentication, 10.3 Request Context.

# 1.7 Guards

> **Topic 1.7** | Priority: Core | Prerequisites: [1.3 Controllers and Routing](03_controllers_and_routing.md), [1.4 Providers and Services](04_providers_and_services.md), [1.5 Middleware](05_middleware.md), [1.6 Pipes](06_pipes.md) | Time: about 3 hours reading plus 3 hours for the exercise | Exercise: [07_guards](../../projects/phase_01_core_building_blocks/07_guards/README.md) | Next: [1.8 Interceptors](08_interceptors.md) | Roadmap: [1.7 Guards](../../docs/01_nestjs_roadmap.md#17-guards)
>
> Everything marked "measured" was run against `@nestjs/common` and `@nestjs/core` 12.5.1 with the Express adapter on Node 24.22.3. The Fastify adapter and the non-HTTP transports (WebSockets, microservices) were not tested here. The scratch experiments are not kept: the exercise tests reproduce the important ones.

## Table of Contents

- [Why Guards Matter](#why-guards-matter)
- [The Mental Model](#the-mental-model)
  - [What a guard is](#what-a-guard-is)
  - [Where it runs](#where-it-runs)
  - [401 and 403](#401-and-403)
  - [Coming from FastAPI](#coming-from-fastapi)
- [Writing a Guard](#writing-a-guard)
  - [What canActivate may return](#what-canactivate-may-return)
  - [Denying with the right status](#denying-with-the-right-status)
  - [The ExecutionContext](#the-executioncontext)
  - [Handing data to the handler](#handing-data-to-the-handler)
- [Metadata and the Reflector](#metadata-and-the-reflector)
  - [Creating a decorator](#creating-a-decorator)
  - [Reading it back](#reading-it-back)
  - [Two patterns: roles and public routes](#two-patterns-roles-and-public-routes)
- [Binding Guards](#binding-guards)
  - [The three scopes](#the-three-scopes)
  - [Order and short-circuiting](#order-and-short-circuiting)
  - [Class or instance](#class-or-instance)
  - [Global guards and dependency injection](#global-guards-and-dependency-injection)
- [Guards or Middleware for Authentication](#guards-or-middleware-for-authentication)
- [Guard, Pipe or Interceptor](#guard-pipe-or-interceptor)
- [Testing Guards](#testing-guards)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Guards Matter

A guard answers one question before your handler runs: **may this request proceed?** It is where authentication ("who is this") and authorization ("may they do this") live in a Nest application, and the reason you can write "this route needs the `admin` role" as a decorator and have it enforced everywhere.

Interviewers ask about it as:

- "Guard, middleware or interceptor: where do you put authentication, and why?"
- "How do you make every route private by default and open a few?"
- "How does a role guard know what the route requires?"
- "How do you register a global guard that can still use dependency injection?"
- "In what order do guards run, and what happens when one denies?"

The full request lifecycle is 1.10; real authentication and authorization (JWT, Passport, CASL, ownership checks) are 5.1 and 5.2. This topic is the mechanism, with just enough authentication to show the patterns.

## The Mental Model

### What a guard is

A class with one method, `canActivate(context)`, that says yes or no:

```ts
@Injectable()
export class RolesGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean | Promise<boolean> | Observable<boolean> { /* ... */ }
}

@Controller('reports')
@UseGuards(RolesGuard)
export class ReportsController {}
```

Yes lets the request go on to the pipes and the handler. No stops it: the handler, and everything after the guard, never runs. A guard is called **once per request**, with the whole execution context, not once per parameter like a pipe (1.6).

### Where it runs

Measured with a log written by a middleware, a guard, a pipe and the handler:

```
GET /o/ok/1       middleware > guard > pipe > handler
GET /o/no/1       middleware > guard (denies)            403, the pipe and handler never ran
GET /o/nothing    middleware                              404, no route matched, so no guard
```

So: after middleware (1.5), before pipes (1.6) and interceptors (1.8), and **only for a request that matched a route**. An unknown path is a 404 even when a global guard would deny everything: the guard has no route, class or handler to look at. The source agrees: `createGuardsFn` is the first thing the route's handler does, before it sets the `@HttpCode` status and the `@Header` values (1.3).

### 401 and 403

The two statuses are not interchangeable, and Nest's default is the less common one:

| Status | Meaning | Use for |
|---|---|---|
| **401 Unauthorized** | "I do not know who you are" (no credentials, bad or expired credentials) | a failed authentication |
| **403 Forbidden** | "I know who you are, and you may not" | a failed authorization |

A guard that returns `false` produces **403** `{"message":"Forbidden resource","error":"Forbidden","statusCode":403}`, always. To answer 401 the guard must **throw** `UnauthorizedException`. That is why an authentication guard throws and a role guard can simply return `false`.

### Coming from FastAPI

| FastAPI | Nest |
|---|---|
| `Depends(get_current_user)` that raises `HTTPException(401)` | an authentication guard that throws `UnauthorizedException` |
| `dependencies=[Depends(...)]` on a router or app | `@UseGuards(...)` on a controller, or a global guard |
| the dependency **returns the user** and the handler receives it | a guard returns a boolean; it hands data to the handler by **writing it on the request** (or you add a parameter decorator, 1.10) |
| `Security(scopes=[...])` | a role or scope guard reading metadata set by a decorator |
| dependencies are plain functions, nothing to "register" | a guard is a provider-like class, bound by decorator or globally |

The biggest difference: a FastAPI dependency is one mechanism for validation, authentication and injection; Nest splits it into pipes (convert and validate one argument), guards (allow or deny the whole request) and, later, interceptors (wrap the handler).

## Writing a Guard

### What canActivate may return

Measured, each as a guard on a route whose handler records that it ran:

| `canActivate` returns | Result |
|---|---|
| `true` | handler runs |
| `false` | **403** `Forbidden resource`, handler does not run |
| `Promise<true>` / `Promise<false>` | awaited, then as above |
| `of(true)` / `of(false)` | as above |
| an Observable emitting `true, false` | **403**: the **last** value decides |
| an Observable emitting `false, true` | 200: again the last value |
| a delayed Observable (`timer(20)` then `true`) | 200 |
| an Observable that completes **without emitting** (`EMPTY`) | **500**: nothing to decide on |
| `'yes'` (a truthy string) | **200**: the guard passed |
| `undefined`, `0`, `null` | 403 |

The source (`GuardsConsumer.tryActivate`) explains it: a `boolean` is used as is, anything else is awaited and, if it turned out to be an Observable, reduced with `lastValueFrom`, then judged by **truthiness**. The `boolean | Promise<boolean> | Observable<boolean>` signature is only TypeScript; at runtime a truthy `'yes'` or `{}` lets the request through. Return real booleans.

### Denying with the right status

| The guard | Client gets | Handler ran |
|---|---|---|
| returns `false` | 403 `Forbidden resource` | no |
| throws `UnauthorizedException('who are you')` | **401** `{"message":"who are you","error":"Unauthorized","statusCode":401}` | no |
| throws `ForbiddenException('custom')` | 403 with your message | no |
| `async` and rejects with `UnauthorizedException` | 401 | no |
| throws a plain `Error` | **500** `Internal server error` | no |

A thrown `HttpException` goes straight to the exception layer (1.9), so it picks its own status and body; only a falsy result becomes the standard `ForbiddenException`. A plain `Error` is a bug and a 500, as everywhere in Nest.

### The ExecutionContext

A guard receives an `ExecutionContext`, which extends `ArgumentsHost`:

```ts
interface ArgumentsHost {
  getArgs(): any[];  getArgByIndex(i): any;
  switchToHttp(): { getRequest(); getResponse(); getNext() };
  switchToWs(): { getData(); getClient(); getPattern() };
  switchToRpc(): { getData(); getContext() };
  getType(): 'http' | 'ws' | 'rpc';
}
interface ExecutionContext extends ArgumentsHost {
  getClass(): Type;     // the controller class
  getHandler(): Function; // the method about to run
}
```

Measured in a guard on `GET /x/7` of an `XController.read` route:

```
type: 'http'   controller: 'XController'   handler: 'read'
args: 3 (IncomingMessage, ServerResponse, Function)    getArgByIndex(0) === switchToHttp().getRequest()
request.route.path = '/x/:id'                           (the matched route IS known here)
```

`getClass()` and `getHandler()` are what middleware never has (1.5 measured `req.route` as `undefined` there): they tell a guard which route it is protecting, so it can read decorator metadata about it. The raw arguments depend on the transport: for HTTP they are `(request, response, next)`; for WebSockets and microservices they are different, which is why `switchToHttp()` exists and why a guard meant for several transports checks `getType()` first. Writing transport-agnostic guards is 2.7.

### Handing data to the handler

A guard cannot return the user. The usual hand-off is to write it on the request, and let the handler read it with `@Req()`, or with a custom parameter decorator (1.10):

```ts
const request = context.switchToHttp().getRequest<AuthedRequest>();
request.user = { name };
return true;
```

Measured in the exercise: the handler of `GET /profile` received `{ name: 'ada' }` from the guard's `request.user`. Type the request (`Request & { user?: ... }`) so the property is declared, and remember this ties the guard and the handler to Express (3.8).

## Metadata and the Reflector

### Creating a decorator

A guard cannot read "this route needs `admin`" from the request: that is written in the code, next to the route. The mechanism is **metadata**: a decorator stores a value on the class or method, and the guard reads it back. Nest gives a typed helper:

```ts
import { Reflector } from '@nestjs/core';
export const Roles = Reflector.createDecorator<string[]>();   // @Roles(['admin'])
```

`createDecorator<T>()` returns a decorator for a class **and** a method, with its argument typed as `T`, and a generated unique `KEY` (`typeof Roles.KEY` is `'string'`, measured). Variants, measured:

| Form | Stores |
|---|---|
| `createDecorator<string[]>()` then `@Roles(['admin'])` | `['admin']` |
| `createDecorator<boolean>()` then `@Public(true)` / `@Public(false)` | the boolean |
| `createDecorator()` (no type) then `@Flag()` | an empty object `{}` as a "present" marker |
| `createDecorator<string, string>({ transform: v => v.toUpperCase() })` | the transformed value (`'X'` for `'x'`) |
| `createDecorator<string>({ key: 'my-key' })` | the metadata under `'my-key'` instead of a generated key |
| the older `@SetMetadata('legacy', ['x'])` | the value under a string key that both sides must spell the same |

Prefer `createDecorator`: one object is both the decorator and the key, and the type is checked where you use it.

### Reading it back

The `Reflector` is a provider that any class can inject, with no module import (it comes from Nest's internal global module, 1.2: measured, a guard bound by class received it). Its read methods, measured on a class with `@Roles(['user','admin'])` and three methods:

| Method | `a` (no own roles) | `b` (`@Roles(['admin'])`) | `c` (`@Roles([])`) |
|---|---|---|---|
| `get(Roles, handler)` | `undefined` | `['admin']` | `[]` |
| `get(Roles, class)` | `['user','admin']` | same | same |
| `getAllAndOverride(Roles, [handler, class])` | `['user','admin']` | `['admin']` | **`[]`** |
| `getAllAndMerge(Roles, [handler, class])` | `['user','admin']` | `['admin','user','admin']` | `['user','admin']` |

- `get` reads one target.
- `getAllAndOverride` returns the first target that has a value: **the handler's wins over the class's**. Use it for "the most specific one decides".
- `getAllAndMerge` concatenates arrays (and merges objects) from all targets, **keeping duplicates** (`'admin'` appears twice above). Use it when each level adds to the others.
- "Has a value" means `!== undefined`: **an empty array overrides** (row `c`), and so does `false`. `@Roles([])` is therefore a way to say "no role needed here" inside a restricted controller, and a guard must decide what an empty list means (the exercise: nobody in particular is required). An unset key is `undefined`.

### Two patterns: roles and public routes

**Roles.** The decorator says what is required, the guard compares it with who is asking:

```ts
canActivate(context: ExecutionContext): boolean {
  const required = this.reflector.getAllAndOverride(Roles, [context.getHandler(), context.getClass()]);
  if (!required || required.length === 0) return true;
  return required.includes(roleOf(context.switchToHttp().getRequest()));
}
```

Where the caller's role really comes from (a verified token, a user record) is 5.1 and 5.2; the exercise reads a header so that the task stays about guards. A role guard that returns `false` gives a 403, which is the right status for "known user, not allowed".

**Secure by default, opt out per route.** A global guard (below) checks every route, and a `@Public(true)` decorator marks the exceptions:

```ts
const isPublic = this.reflector.getAllAndOverride(Public, [context.getHandler(), context.getClass()]);
if (isPublic === true) return true;
/* otherwise demand credentials: throw UnauthorizedException when they are missing */
```

Measured in the exercise: `@Public(true)` on a method opened that route; on a controller it opened all its routes; `@Public(false)` on one method of a public controller closed it again (handler beats class). A boolean decorator, rather than a bare flag, is what makes that last case possible.

## Binding Guards

### The three scopes

| Scope | How | Applies to |
|---|---|---|
| global | `app.useGlobalGuards(new G())`, or an `APP_GUARD` provider | every route of the application |
| controller | `@UseGuards(G)` on the class | every route of the controller |
| method | `@UseGuards(G)` on a route | that route |

Unlike pipes, there is no parameter scope: a guard decides for the whole request.

### Order and short-circuiting

Measured with a `TraceGuard` that records its name and can be told to deny:

```
GET /s/one     global > controller > method > handler
GET /s/two     global > controller > first > second       -> 403  (second denies: third and handler never ran)
GET /s/three   global > controller > handler
```

Guards are collected global, then controller, then method, and inside one `@UseGuards(a, b, c)` from left to right. Nest runs them **one at a time**, awaiting each (`for (const guard of guards)` in `tryActivate`), and **stops at the first that denies**: the guards after it are not even called. That makes guard order a performance and a side-effect decision: put the cheap checks first, and do not put side effects in a guard that may be skipped.

### Class or instance

| Form | Built by | Injection |
|---|---|---|
| `@UseGuards(ApiKeyGuard)` (the class) | Nest, in the controller's module | yes |
| `@UseGuards(new TraceGuard('x'))` (an instance) | you | no: you pass arguments yourself |

A class guard is built **once** and shared: measured, a guard class used on three routes of two controllers in one module was constructed once, and it received the module's provider and the `Reflector`. Use an instance when the guard needs constructor arguments (a name, a flag), as `TraceGuard` does.

### Global guards and dependency injection

Two ways, only one injects:

| | `app.useGlobalGuards(new G())` | `{ provide: APP_GUARD, useClass: G }` |
|---|---|---|
| Built by | you, outside the container | Nest, like any provider (2.2) |
| Injection | **none**: measured, a guard with a missing dependency answered **500** at the first request | yes: the `Reflector` and your providers |
| Where | `main.ts` | the `providers` of any module |

`APP_GUARD` comes from `@nestjs/core`. A guard registered with it applies to the **whole application**, not to the module it sits in: measured, a guard provided in a module that one other module imported denied a controller of a third module that never imported it either (the module only decides what the guard can inject). If you only have a guard with no dependencies, `new Reflector()` by hand also works for `useGlobalGuards` (measured), but `APP_GUARD` is the form to default to. A global guard never runs for a path that matches no route (a 404).

## Guards or Middleware for Authentication

Both can authenticate; they are not equivalent. Measured and read from the source:

| | Middleware (1.5) | Guard |
|---|---|---|
| Knows the controller and method | no (`req.route` undefined for a string mount) | yes (`getClass()`, `getHandler()`, matched `req.route`) |
| Reads decorator metadata (`@Public`, `@Roles`) | no | yes, through the `Reflector` |
| Runs for a path no route handles | yes (a 404 can be intercepted) | no (it is a 404) |
| Request body parsed | only module middleware | yes |
| Dependency injection | class middleware yes, global `app.use` no | yes (class or `APP_GUARD`) |
| Works the same for WebSockets and microservices | no, HTTP only | yes, through `ExecutionContext` (2.7) |
| Can answer by itself | yes, any response | by status through exceptions |

So **authorization belongs in a guard**: it needs to know the handler. **Authentication** can be either, and the Nest-idiomatic design is a **global guard that authenticates, plus a `@Public()` opt-out**, because the opt-out needs the metadata that only a guard can read. Middleware remains right when something must run first or on every path: request ids and logging, CORS, `helmet`, cookie or session parsing (Passport sessions are middleware, 5.1), and Express-only libraries that expect `(req, res, next)`.

## Guard, Pipe or Interceptor

| | Guard | Pipe (1.6) | Interceptor (1.8) |
|---|---|---|---|
| Question | may this request proceed? | what should this argument be? | what happens around the handler? |
| Sees | the `ExecutionContext` | one value and its metadata | the context and the handler's result |
| Runs | once per request, before pipes | per parameter, after guards | before and after the handler |
| Typical use | authentication, authorization | parse, convert, validate input | map the response, timing, caching |
| On failure | 403, or the exception it throws | 400, or the exception it throws | whatever it throws or maps |

Authorize in a guard **before** validating in a pipe: measured, a denied request never reaches the pipes, so an attacker learns nothing from validation errors and no pipe work (a database lookup, say) is spent on a request that was going to be refused.

## Testing Guards

Two levels, as in the exercise.

```ts
// 1. By hand: a guard is a class. Build it, hand it a fake ExecutionContext.
function fakeContext(role?: string): ExecutionContext {
  return {
    switchToHttp: () => ({ getRequest: () => ({ headers: role ? { 'x-role': role } : {} }) }),
    getHandler: () => Target.prototype.handler,
    getClass: () => Target,
  } as unknown as ExecutionContext;
}
const guard = new RolesGuard(new Reflector());
expect(guard.canActivate(fakeContext('admin'))).toBe(true);
expect(guard.canActivate(fakeContext())).toBe(false);

// 2. Binding, order and status codes need an application and supertest.
const app = await createApp({ controllers: [ReportsController] });
await request(app.getHttpServer()).delete('/reports/7').set('x-role', 'viewer').expect(403);
```

(Measured: the hand-built version with a real `Reflector` and a class decorated with `@Roles(['admin'])` passed, including with a missing header.) Level 1 is fast and checks the decision logic with any request you invent. Level 2 checks what level 1 cannot: that the guard is bound where you think, the scope order, the status code and body Nest produces, that a denied request never reached the handler (give the handler a counter, as `CallCounter` does), and that a global `APP_GUARD` really applies. Register global guards before `app.init()` with the same `setup` step as for middleware and pipes. Testing under real authentication is Phase 6.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| returning `false` for a missing token | 403 instead of 401 | throw `UnauthorizedException` |
| returning a truthy non-boolean | the request passes (`'yes'`, `{}`) | return real booleans |
| an Observable guard that emits nothing | 500 | emit a value, or use a Promise |
| an Observable that emits several values | the last one decides | emit one value |
| a plain `Error` thrown in a guard | 500 | throw an `HttpException` subclass |
| `app.useGlobalGuards(new G())` for a guard with dependencies | `undefined` dependencies, a 500 at the first request | `APP_GUARD` |
| expecting a global guard to cover an unknown path | it never runs: 404 | a 404 is not a guard's job |
| `getAllAndOverride` when you wanted both levels | the handler's value hides the controller's | `getAllAndMerge` |
| `getAllAndMerge` and duplicate roles | `['admin','user','admin']` | de-duplicate if it matters |
| an empty roles array treated as "nobody" | `@Roles([])` unexpectedly opens or closes the route | decide and document what `[]` means |
| a bare `@Public()` flag | a method cannot re-close a public controller | a boolean decorator |
| side effects in a guard that may be skipped | they run or not depending on guard order | keep guards pure; put effects in the handler or an interceptor |
| a guard that reads `request.user` before an authentication guard ran | `undefined` | put the authentication guard first (global before controller before method) |
| authenticating in middleware and authorizing in a guard without a shared contract | the guard cannot trust `request.user` | one place sets it, typed |
| assuming the guard sees a parsed, validated body | the body is parsed (module middleware ran) but pipes have not run yet | validate in pipes, decide in guards |
| writing a guard only for HTTP and binding it on a gateway | `switchToHttp()` data is wrong | check `context.getType()` (2.7) |
| trusting a header the client controls (`x-role`) | anyone can claim a role | the exercise's header is a stand-in for a verified identity (5.1) |

## Interview Questions

**1. What is a guard, and where does it run?**
A class with `canActivate(context)` that decides whether a request reaches the handler. It runs after middleware and before interceptors and pipes, once per request, and only when a route matched. Returning true continues, returning false is a 403, throwing an `HttpException` answers with that exception.

**2. 401 or 403 when a guard denies?**
A guard that returns `false` always gives a 403 "Forbidden resource". 401 means "unauthenticated" (no or bad credentials) and 403 means "authenticated but not allowed", so an authentication guard throws `UnauthorizedException`, while a role guard can return `false`.

**3. What may `canActivate` return?**
`boolean | Promise<boolean> | Observable<boolean>`. A Promise is awaited; an Observable is reduced to its last value; at runtime anything is judged by truthiness, so a truthy string passes, which is why you return real booleans. An Observable that emits nothing is a 500.

**4. How does a role guard know what a route requires?**
A metadata decorator (`Reflector.createDecorator<string[]>()`, used as `@Roles(['admin'])`) stores the roles on the method or class, and the guard injects the `Reflector` and reads them with the context's `getHandler()` and `getClass()`: `getAllAndOverride(Roles, [handler, class])`.

**5. `getAllAndOverride` versus `getAllAndMerge`?**
Override returns the first target's value that is not `undefined`, handler before class, so the most specific wins (an empty array counts as a value). Merge concatenates all of them, keeping duplicates.

**6. How do you make all routes private by default and open a few?**
A global guard that authenticates, plus a boolean `@Public()` metadata decorator the guard reads with `getAllAndOverride([handler, class])`: public routes pass, everything else needs credentials, and a `@Public(false)` method re-closes a public controller.

**7. How do you register a global guard that can use dependency injection?**
As a provider with the `APP_GUARD` token and `useClass` (`{ provide: APP_GUARD, useClass: MyGuard }`), in any module. `app.useGlobalGuards(new MyGuard())` takes an instance built outside the container, so nothing is injected. An `APP_GUARD` applies to the whole application regardless of the module it is in.

**8. In what order do guards run and what happens when one denies?**
Global, then controller, then method, and left to right within one `@UseGuards`. They run one at a time and the first denial stops the chain: later guards and the handler never run.

**9. Guard or middleware for authentication?**
Prefer a guard: it has the `ExecutionContext`, so it can read `@Public()` or `@Roles()` metadata and knows the handler, and it works across HTTP, WebSockets and microservices. Middleware does not know the handler and also runs for 404s, but it is the right place for things that must run first or everywhere: logging, request ids, CORS, helmet, session parsing.

**10. Does a global guard run for a route that does not exist?**
No. Guards run only for a matched route, so an unknown path is a 404 even if every route would be denied.

**11. How does a guard pass the user to the handler?**
It cannot return it. It writes it on the request (`request.user = ...`), and the handler reads it through `@Req()` or a custom parameter decorator.

**12. Why authorize in a guard before validating in a pipe?**
Guards run before pipes, so a request that will be refused never costs any parsing or validation work and reveals nothing through validation errors.

## Check Yourself

- [ ] I can say where a guard runs relative to middleware, pipes, interceptors and the handler, and when it does not run at all.
- [ ] I know the difference between 401 and 403 and how a guard produces each.
- [ ] I can list what `canActivate` may return and what happens for each, including the truthiness rule.
- [ ] I can say what the `ExecutionContext` gives a guard that middleware never has.
- [ ] I can create a metadata decorator with `Reflector.createDecorator` and read it with `get`, `getAllAndOverride` and `getAllAndMerge`, and I know an empty array overrides.
- [ ] I can build a role guard and a secure-by-default guard with `@Public()`.
- [ ] I can predict the order of guards across the three scopes and what a denial skips.
- [ ] I know why `app.useGlobalGuards(new G())` cannot inject and how `APP_GUARD` fixes it.
- [ ] I can explain why authorization belongs in a guard and name what still belongs in middleware.
- [ ] I finished the exercise: [07_guards](../../projects/phase_01_core_building_blocks/07_guards/README.md).

## Further Reading

- Official documentation: [Guards](https://docs.nestjs.com/guards) (authorization guard, binding guards, setting roles per handler). Not re-read for this note: the behaviour above was measured on 12.5.1 instead.
- Source worth reading in the installed `node_modules/@nestjs/core/`, in this order: `guards/guards-consumer.js` (`tryActivate`, `pickResult`), `router/router-execution-context.js` (`createGuardsFn`, and where it sits in the request function), `services/reflector.service.js` (`createDecorator`, `getAllAndOverride`, `getAllAndMerge`). The interfaces are in `@nestjs/common/interfaces/features/` (`can-activate`, `execution-context`, `arguments-host`).
- Related topics: [1.2 Modules](02_modules.md), [1.4 Providers and Services](04_providers_and_services.md), [1.5 Middleware](05_middleware.md), [1.6 Pipes](06_pipes.md), 1.8 Interceptors, 1.9 Exception Filters, 1.10 Request Lifecycle, 2.2 Custom and Async Providers, 2.7 Execution Context and Metadata, 5.1 Authentication, 5.2 Authorization, 5.3 Web Security Hardening.

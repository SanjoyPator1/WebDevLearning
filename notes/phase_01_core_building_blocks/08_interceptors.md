# 1.8 Interceptors

> **Topic 1.8** | Priority: Core | Prerequisites: [1.5 Middleware](05_middleware.md), [1.6 Pipes](06_pipes.md), [1.7 Guards](07_guards.md) (the `Reflector` and `ExecutionContext`), basic RxJS | Time: about 3 hours reading plus 3 hours for the exercise | Exercise: [08_interceptors](../../projects/phase_01_core_building_blocks/08_interceptors/README.md) | Next: [1.9 Exception Filters](09_exception_filters.md) | Roadmap: [1.8 Interceptors](../../docs/01_nestjs_roadmap.md#18-interceptors)
>
> Everything marked "measured" was run against `@nestjs/common` and `@nestjs/core` 12.5.1 with the Express adapter on Node 24.22.3, with `rxjs` 7.8.2. The scratch experiments are not kept: the exercise tests reproduce the important ones.

## Table of Contents

- [Why Interceptors Matter](#why-interceptors-matter)
- [The Mental Model](#the-mental-model)
  - [What an interceptor is](#what-an-interceptor-is)
  - [Where it sits](#where-it-sits)
  - [Coming from FastAPI](#coming-from-fastapi)
- [Writing an Interceptor](#writing-an-interceptor)
  - [The two interfaces](#the-two-interfaces)
  - [next.handle() is lazy](#nexthandle-is-lazy)
  - [Before and after](#before-and-after)
  - [Reading the request and writing the response](#reading-the-request-and-writing-the-response)
- [The RxJS You Need](#the-rxjs-you-need)
- [Use Cases](#use-cases)
  - [Mapping the response](#mapping-the-response)
  - [Timing and logging](#timing-and-logging)
  - [Answering without the handler: caching](#answering-without-the-handler-caching)
  - [Timeouts](#timeouts)
  - [Mapping errors](#mapping-errors)
  - [Interceptors Nest already ships](#interceptors-nest-already-ships)
- [Binding Interceptors](#binding-interceptors)
  - [The three scopes and the order](#the-three-scopes-and-the-order)
  - [Class or instance](#class-or-instance)
  - [Global interceptors and dependency injection](#global-interceptors-and-dependency-injection)
  - [Interceptors are singletons](#interceptors-are-singletons)
- [What an Interceptor Can and Cannot See](#what-an-interceptor-can-and-cannot-see)
- [Which Component for Which Job](#which-component-for-which-job)
- [Testing Interceptors](#testing-interceptors)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Interceptors Matter

An interceptor is the only component that wraps the handler: it runs code **before** it, gets the handler's result **after** it, and can **replace** that result, **replace** the error, or **skip the handler altogether**. That makes it the tool for everything cross-cutting that needs both sides of a call: reshaping responses, timing, logging, caching, timeouts.

Interviewers ask about it as:

- "Interceptor, middleware, guard, pipe, filter: what does each one do?"
- "What is `next.handle()` and why does it return an Observable?"
- "How would you wrap every response in an envelope? What about `undefined`?"
- "How do you put a timeout on a route? Does it stop the work?"
- "In what order do interceptors run, in and out?"
- "How do you register a global interceptor that can inject services?"

The whole lifecycle is 1.10. The built-in cache and serializer interceptors are 4.5 and 3.3; here is the mechanism.

## The Mental Model

### What an interceptor is

A class with one method, `intercept(context, next)`, that returns an **Observable** of the response:

```ts
@Injectable()
export class EnvelopeInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    // 1. code here runs BEFORE the handler
    return next.handle().pipe(
      map((data) => ({ data: data ?? null })),   // 2. operators here run AFTER it, on its value
    );
  }
}
```

`next.handle()` **is** the handler, wrapped in an Observable. Whatever Observable you return is what Nest sends to the client. So you change the response by piping operators onto it, you change the error by catching it, and you skip the handler by returning something else.

### Where it sits

Measured with a log written by a middleware, a guard, an interceptor, a pipe and the handler:

```
middleware > guard > interceptor:before > pipe > handler > interceptor:after
```

Interceptors run **after guards** and **before pipes** on the way in, and the pipes and the handler run **inside** `next.handle()`. That has two consequences, both measured:

- A guard that denies stops the request before any interceptor runs: the interceptor never sees a 403 from a guard (1.7).
- Because pipes run inside `next.handle()`, an error thrown by a pipe **is** visible to the interceptor (as is an error from the handler).

After an interceptor passes an error on, the exception filters turn it into a response (1.9): measured `interceptor saw BadRequestException`, then `filter`.

### Coming from FastAPI

| FastAPI / Starlette | Nest |
|---|---|
| `@app.middleware("http")` with `response = await call_next(request)` | the closest match: `intercept` wraps `next.handle()`, and sees the result |
| `response_model` reshaping the output | a mapping interceptor (`map`), or serialization (3.3) |
| `BaseHTTPMiddleware` timing a request | a timing interceptor, but per route or controller, with access to the handler |
| `Depends` that can return early | a guard (1.7) for allow/deny; an interceptor to answer with a value instead |
| no equivalent of "call the handler twice, or not at all" | an interceptor decides whether and how often `next.handle()` is subscribed |

The difference that costs people time: the "after" half is **reactive**. The handler's result arrives as an Observable stream, not as a value you `await`, so you transform it with RxJS operators.

## Writing an Interceptor

### The two interfaces

```ts
interface NestInterceptor<T = any, R = any> {
  intercept(context: ExecutionContext, next: CallHandler<T>): Observable<R> | Promise<Observable<R>>;
}
interface CallHandler<T = any> {
  handle(): Observable<T>;
}
```

`intercept` may be `async` (it can return a `Promise<Observable>`): measured, an interceptor that awaited something before `next.handle()` and then mapped the value worked. The `ExecutionContext` is the same object guards receive (1.7): `getClass()`, `getHandler()`, `switchToHttp()`, and with it the `Reflector`.

### next.handle() is lazy

`handle()` does **not** run the handler. It returns a cold Observable, and the handler (with its pipes) runs when that Observable is **subscribed to** (source: `defer(...)` in `InterceptorsConsumer`). Measured, each as the only interceptor on a route whose handler records that it ran:

| The interceptor | Handler ran | Client got |
|---|---|---|
| returns `of('from interceptor')` and never calls `handle()` | 0 times | `from interceptor` |
| calls `next.handle()` but returns something else, never subscribing | 0 times | the other value |
| returns `next.handle().pipe(map(() => 'replaced'))` | 1 time | `replaced` |
| returns `concat(next.handle(), next.handle())` | **2 times** | `from handler` |

So an interceptor decides whether the handler runs (a cache hit: no), how many times (a retry operator: several) and what the client gets. A handler with side effects, subscribed twice, runs twice. Nest does the first subscription for you when you return the Observable.

### Before and after

| Where in the code | Runs |
|---|---|
| in `intercept`, before `return` | before the pipes and the handler |
| in an operator piped onto `next.handle()` | when the handler's value (or error, or completion) comes back |

With several interceptors the "before" parts run in binding order and the "after" parts in the **reverse** order (see Binding). Measured timing facts: operators like `tap` run on the success value before the response is sent, and `finalize` also runs before it (`res.headersSent` was `false` in both, in a `tap` and in a `finalize`).

### Reading the request and writing the response

The context gives you the raw request and response (`switchToHttp()`), so an interceptor can read `request.method` and `request.originalUrl`, and write headers. Measured: `res.setHeader(...)` **before** `next.handle()` works, and so does setting a header inside `tap` after the handler (the response has not been sent yet), which is how a timing header is set. Both tie the interceptor to the Express objects.

## The RxJS You Need

You do not need the whole library. Five operators, plus `of` and `throwError` to create streams, cover interceptors:

| Operator | Does | Measured behaviour |
|---|---|---|
| `map(fn)` | transforms each value | `{ a: 1 }` becomes `{ data: { a: 1 } }`; over `undefined` it gives `{ data: undefined }`, sent as `{}` |
| `tap(fn)` or `tap({ next, error })` | a side effect that does not change the value or the error | the error keeps travelling to the filters |
| `catchError(fn)` | handles an error: return `throwError(() => e)` to replace it, or `of(x)` to swallow it | returning `of(...)` answered **200** even for a plain bug |
| `timeout(ms)` | errors with rxjs's `TimeoutError` if no value arrives in time | alone: a **500**; the handler keeps running |
| `finalize(fn)` | runs when the stream ends: success, error or cancel | ran once after a success and once after a 400, before the response was sent |

Things to hold on to:

- The stream usually has **one** value (a handler returns one value). Nest turns it into the response with the **last** emitted value: a handler that returns an Observable emitting `1, 2, 3` through `map(x => x * 2)` answered `6` (measured). Streaming values to the client is SSE (8.2), not interceptors.
- Observables are **cold and lazy**: nothing runs until something subscribes, and each subscription reruns the source.
- `map` and `tap`'s `next` are skipped when the stream **errors**; `catchError` and `tap`'s `error` handle that side.
- To fail, return `throwError(() => new SomeException())` (a function, in rxjs 7), or just `throw` inside an operator callback.

## Use Cases

### Mapping the response

```ts
return next.handle().pipe(map((data) => ({ data: data ?? null })));
```

Measured results with `map(data => ({ data }))`:

| Handler returns | Client gets |
|---|---|
| an object, an array, a string | `{ data: ... }` |
| `undefined` | **`{}`**: JSON drops the `undefined` property. Normalise with `?? null` |
| `null` | `{ data: null }` |
| a Promise | `{ data: <resolved value> }` |
| an Observable of `1, 2, 3` | the mapping runs per value; the client gets only the last |
| a thrown exception | not wrapped: the error response is unchanged |
| plain `@Res()` and the handler sends the response | the interceptor's `map` has **no effect**: the handler already answered, though the "after" code still ran |
| `@Res({ passthrough: true })` | works: `202` kept, body wrapped |
| `@HttpCode(200)` on a POST | status kept, body wrapped |

A global envelope is a contract change for every client; whether to wrap at all (versus plain resources and pagination metadata) is discussed in 3.3.

### Timing and logging

The standard pair: record the start in `intercept`, compute the duration in `tap`, close the log in `finalize`. The one trap is where you keep the start time (see "Interceptors are singletons"): a local variable captured by the closure. Logging is fully covered in 7.4, request ids and correlation in 10.3 and 11.2.

### Answering without the handler: caching

Because `next.handle()` is lazy, **not returning it** means the handler never runs. A cache interceptor returns the stored value on a hit and stores the handler's value on a miss:

```ts
if (this.cache.has(key)) return of(this.cache.get(key));        // the handler and its pipes never run
return next.handle().pipe(tap((value) => this.cache.set(key, value)));
```

Measured in the exercise: the second request for the same URL was answered from the Map with the handler's counter still at 1; `?x=1` and `?x=2` were different entries (the key was `originalUrl`); a route without the marker decorator always ran its handler. The marker is read with the `Reflector` exactly as in a guard (`getAllAndOverride(Cached, [handler, class])`). This toy cache never expires and is per process; the built-in `CacheInterceptor`, TTLs, invalidation and a Redis store are 4.5.

### Timeouts

```ts
return next.handle().pipe(
  timeout(50),
  catchError((e) => throwError(() => (e instanceof TimeoutError ? new RequestTimeoutException() : e))),
);
```

Measured:

| | Result |
|---|---|
| `timeout(30)` alone, handler takes 80 ms | **500** `Internal server error` |
| with the `catchError` above | **408** `{"message":"Request Timeout","statusCode":408}` |
| fast handler | normal |
| the handler's own `BadRequestException` | still 400: only `TimeoutError` is converted |
| **side effects of the slow handler** | **it kept running and finished after the 408 was sent** |

The last row is the limit worth remembering: a timeout stops the **client from waiting**, it does not cancel the **work**. A slow handler that writes to a database or calls a payment API still does so after the client got its 408. Real cancellation needs the handler itself to honour an abort signal.

### Mapping errors

`catchError` sees every error that comes back through `next.handle()`: the handler's, and (measured) the pipes'. It can replace the error or swallow it. Measured:

| `catchError` returns | Result |
|---|---|
| `throwError(() => new BadGatewayException('mapped'))` | 502 with that message |
| `of({ fallback: true })` for a handler's `BadRequestException` | **200** `{"fallback":true}` |
| the same `of(...)` when the handler threw a plain `Error` (a bug) | **200** `{"fallback":true}`: the bug is hidden |

Swallowing is almost never what you want; replace instead, and let an `HttpException` pass through unchanged so only unexpected errors are rewritten (the exercise's error mapper turns a plain `Error('database password is hunter2')` into `502 upstream failed` and keeps the password out of the response). Application-wide error mapping belongs in exception filters (1.9, 3.4), which also see errors from guards and middleware, which an interceptor never does.

### Interceptors Nest already ships

Written with exactly this mechanism, each covered where it belongs: `ClassSerializerInterceptor` (3.3), `CacheInterceptor` (4.5), the file upload interceptors `FileInterceptor` and `FilesInterceptor` (3.7). They are listed here so you recognise them as ordinary interceptors; none was used or measured in this topic.

## Binding Interceptors

### The three scopes and the order

| Scope | How | Applies to |
|---|---|---|
| global | `app.useGlobalInterceptors(new I())`, or an `APP_INTERCEPTOR` provider | every route |
| controller | `@UseInterceptors(I)` on the class | every route of the controller |
| method | `@UseInterceptors(I)` on a route | that route |

Measured with a `NamedInterceptor` that logs `<name>:before` and `<name>:after`:

```
GET /s/one    global:before > controller:before > method:before > handler
                              > method:after > controller:after > global:after
GET /s/two    global:before > controller:before > first:before > second:before > handler
                              > second:after > first:after > controller:after > global:after
GET /s/three  global:before > controller:before > handler > controller:after > global:after
```

Interceptors **nest like Russian dolls**: collected global, controller, method (and left to right inside one `@UseInterceptors(a, b)`), the first is the **outermost**. "Before" runs outside in, "after" runs **inside out**, the exact mirror. Guards and pipes have only the forward direction. Practical consequences: an outer timing interceptor measures the inner ones too, and an inner mapping interceptor reshapes the value before an outer one sees it.

### Class or instance

| Form | Built by | Injection |
|---|---|---|
| `@UseInterceptors(MemoInterceptor)` (the class) | Nest, in the controller's module | yes |
| `@UseInterceptors(new NamedInterceptor('x'))` (an instance) | you | no: you pass the arguments |

A class interceptor is built once and shared: measured, a class used on three routes of two controllers in one module was constructed once and received the module's provider and the `Reflector`.

### Global interceptors and dependency injection

| | `app.useGlobalInterceptors(new I())` | `{ provide: APP_INTERCEPTOR, useClass: I }` |
|---|---|---|
| Built by | you, outside the container | Nest, like any provider (2.2) |
| Injection | **none**: measured, an interceptor with a missing dependency answered **500** | yes: the `Reflector` and your providers |
| Where | `main.ts` | the `providers` of any module |

`APP_INTERCEPTOR` comes from `@nestjs/core`, and measured it applies to the **whole application**: an interceptor provided in a module wrapped a controller of a module that never imported it (the module only decides what it can inject). The sibling tokens are `APP_GUARD` (1.7), `APP_PIPE` (1.6) and `APP_FILTER` (1.9). A global interceptor does not run for a path that matches no route: measured, an `APP_INTERCEPTOR` that logged every request it saw ran for a real route and not for an unknown path (a plain 404).

### Interceptors are singletons

A class interceptor is built **once** and every request shares it, so per-request data must not live in a field. Measured with a timing interceptor and two overlapping requests (a 150 ms one, and a 10 ms one started 40 ms later):

| Where the start time lives | The 150 ms request reports | The 10 ms request reports |
|---|---|---|
| a field (`this.start = Date.now()`) | **110 ms** (overwritten by the later request) | 12 ms |
| a local variable in `intercept` | 151 ms | 11 ms |

The local variable is captured by the closure inside the operator, one per call. This is the same singleton rule as for services (1.4), and the same fix: per-call data lives in arguments and locals. Request-scoped interceptors exist (2.4) but cost what request scope always costs.

## What an Interceptor Can and Cannot See

| | Sees it? |
|---|---|
| the request, response, controller class, handler, metadata (`Reflector`) | yes |
| the handler's return value, after pipes and a Promise were resolved | yes |
| an error thrown by the handler or by a pipe | yes |
| an error from a **guard** (a denial) | **no**: guards run before interceptors |
| an error from **middleware** | no |
| a request for a path with no route | no (no handler to wrap) |
| the response the exception filter will build | no: filters run after |
| the result when the handler uses plain `@Res()` and sends it itself | not as a value to change |

## Which Component for Which Job

| Job | Use | Why |
|---|---|---|
| request ids, CORS, helmet, cookie parsing, anything for every path | middleware (1.5) | runs first, also for 404s |
| may this request proceed? authentication, authorization | guard (1.7) | runs before everything else that is per-handler |
| convert or validate one argument | pipe (1.6) | per parameter |
| reshape the response, time or log a call, cache, timeout | **interceptor** | needs both sides of the handler |
| turn any error into a response | exception filter (1.9) | also sees guard and middleware errors |

The deciding question for an interceptor: *do I need the value coming back, or to decide whether the handler runs?* If you only need to look at the incoming request, a middleware or guard is simpler.

## Testing Interceptors

Two levels, as in the exercise.

```ts
// 1. By hand: an interceptor is a class, and CallHandler is just { handle(): Observable }.
const interceptor = new EnvelopeInterceptor();
const context = {} as ExecutionContext;                       // enough when it never touches the context
const out = await lastValueFrom(interceptor.intercept(context, { handle: () => of({ a: 1 }) }));
expect(out).toEqual({ data: { a: 1 } });
await expect(lastValueFrom(interceptor.intercept(context, { handle: () => throwError(() => new BadRequestException()) })))
  .rejects.toThrow(BadRequestException);

// 2. Binding, order, status codes and real handlers need an application and supertest.
const app = await createApp({ controllers: [NotesController] });
await request(app.getHttpServer()).get('/notes/none').expect(200, { data: null });
```

(Measured: the hand-built version passed for the envelope, for an error stream, and for the timeout interceptor against an Observable that never emits, rejecting with a 408.) Level 1 is fast, needs no HTTP, and lets you feed any stream you invent: `of(x)`, `EMPTY`, an error, a never-ending Observable. Level 2 checks what level 1 cannot: the binding, the order across scopes, the response Nest actually sends, and that a real handler's pipes and errors flow through. Register global interceptors before `app.init()`, as for middleware, pipes and guards. For timing and concurrency tests keep margins generous.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| calling `next.handle()` and not returning it | the handler never runs | return the Observable |
| subscribing to `next.handle()` twice (a retry, `concat`) | the handler runs twice, with its side effects | subscribe once unless you mean it |
| `map(data => ({ data }))` | `undefined` becomes `{}` | `data ?? null` |
| `catchError` returning `of(...)` | swallows the error, even a bug, as a 200 | return `throwError(...)` |
| a plain `Error` mapped to a vague message in every interceptor | inconsistent errors | one exception filter (1.9) |
| `timeout()` alone | a 500 | `catchError` to `RequestTimeoutException` |
| believing a timeout cancels the work | the handler finishes after the 408, with side effects | cancellation inside the handler |
| per-request data in a field | shared between concurrent requests | a local variable in `intercept` |
| `app.useGlobalInterceptors(new I())` for an interceptor with dependencies | a 500 at the first request | `APP_INTERCEPTOR` |
| expecting an interceptor to see a guard denial or a 404 | it does not run | a filter, or handle it in the guard |
| wrapping with `map` and plain `@Res()` | no effect, the handler already answered | `passthrough: true`, or no `@Res` |
| an Observable handler that emits many values | only the last is sent | SSE (8.2) |
| a heavy synchronous step in `intercept` | blocks the event loop for every request | keep it light or async |
| a global interceptor that wraps every body | every client sees a new shape | decide the envelope once (3.3) |
| ordering assumptions between interceptors | the first bound is outermost, and the "after" order is reversed | read the trace, or test it |
| `tap` used where the value must change | `tap` returns the original value | `map` |

## Interview Questions

**1. What is an interceptor, and what can it do?**
A class with `intercept(context, next)` that wraps the handler. It can run code before it, transform its result or its error after it with RxJS operators, skip the handler entirely by not subscribing to `next.handle()`, and run the handler more than once. It runs after guards and before pipes on the way in; the pipes and the handler run inside `next.handle()`.

**2. Why does `next.handle()` return an Observable, and is it lazy?**
Because the result is a stream that operators can transform. It is cold and lazy: the handler runs only when the Observable is subscribed to, and every subscription runs it again. Calling `handle()` and discarding the result runs nothing; subscribing twice runs the handler twice.

**3. In what order do interceptors run?**
Global, then controller, then method, and left to right inside one decorator, with the first being outermost. The "before" code runs outside in, and the "after" code runs inside out, in the exact reverse order.

**4. How do you wrap every response in an envelope? What goes wrong with `undefined`?**
`next.handle().pipe(map(data => ({ data })))`. If the handler returns `undefined`, `{ data: undefined }` is serialised as `{}`, so normalise with `data ?? null`. Errors are not wrapped because `map` is skipped when the stream errors.

**5. How do you put a timeout on a route? Does it stop the handler?**
`timeout(ms)` plus a `catchError` that turns rxjs's `TimeoutError` into a `RequestTimeoutException` (otherwise it is a 500). It does not stop the handler: it stops the client waiting, and the handler finishes in the background with its side effects.

**6. How would you build a cache interceptor?**
Read a marker with the `Reflector`, compute a key (the URL), and on a hit return `of(storedValue)` without calling `next.handle()`, so the handler never runs; on a miss pipe `tap` to store the value. A real cache needs a TTL, a size bound, and a shared store when there are several instances (4.5).

**7. What errors can an interceptor see?**
Errors from the handler and from the pipes (they run inside `next.handle()`). Not errors from guards or middleware, which run before it, and not requests for unknown paths. After it, exception filters build the response.

**8. `catchError` returning a value versus `throwError`?**
Returning a value (`of(x)`) swallows the error and the client gets a 200, even for a real bug; returning `throwError(() => e)` replaces the error and keeps the failure visible. Rewrite only unexpected errors and let `HttpException`s pass.

**9. How do you register a global interceptor that can inject services?**
As a provider with the `APP_INTERCEPTOR` token and `useClass`, in any module; it applies to the whole application. `app.useGlobalInterceptors(new I())` takes an instance built outside the container, so nothing is injected.

**10. Why must an interceptor keep its start time in a local variable?**
A class interceptor is built once and shared by all requests, so a field is overwritten by overlapping requests: a 150 ms request reported 110 ms in the measurement. A local variable captured by the closure is per call.

**11. Interceptor, middleware, guard, pipe or filter?**
Middleware: HTTP-level work first, for every path. Guard: may the request proceed. Pipe: convert or validate one argument. Interceptor: needs both sides of the handler (reshape, time, cache, timeout). Filter: turn an error into a response, and the only one that sees guard and middleware errors.

**12. What happens to an interceptor's `map` when the handler uses `@Res()`?**
With plain `@Res()` and the handler sending the response itself, the `map` has no effect, though "after" operators like `tap` still run. With `@Res({ passthrough: true })`, Nest still sends the returned value and the `map` applies.

## Check Yourself

- [ ] I can say where an interceptor runs relative to middleware, guards, pipes, the handler and the exception filters.
- [ ] I can explain why `next.handle()` is lazy and what that allows (skip, retry) and risks (running twice).
- [ ] I can use `map`, `tap`, `catchError`, `timeout` and `finalize`, and I know which of them change the value.
- [ ] I can predict the order of three interceptors on the way in and on the way out.
- [ ] I know the `undefined`, swallowing and non-cancelling traps (`map`, `catchError`, `timeout`).
- [ ] I can write a cache interceptor that answers without the handler and reads a marker with the `Reflector`.
- [ ] I know why a start time cannot live in a field, and why `useGlobalInterceptors(new I())` cannot inject while `APP_INTERCEPTOR` can.
- [ ] I can say which errors an interceptor sees and which it cannot.
- [ ] I can choose between middleware, guard, pipe, interceptor and filter for a given job.
- [ ] I finished the exercise: [08_interceptors](../../projects/phase_01_core_building_blocks/08_interceptors/README.md).

## Further Reading

- Official documentation: [Interceptors](https://docs.nestjs.com/interceptors) (aspect interception, binding, response mapping, exception mapping, stream overriding, more operators). Not re-read for this note: the behaviour above was measured on 12.5.1 instead.
- [RxJS operators](https://rxjs.dev/guide/operators) for `map`, `tap`, `catchError`, `timeout`, `finalize`, `throwError`, `of`.
- Source worth reading in the installed `node_modules/@nestjs/core/`, in this order: `interceptors/interceptors-consumer.js` (`intercept`, `nextFn`, `transformDeferred`: the whole nesting and the laziness are here), `router/router-execution-context.js` (where interceptors, the handler and `fnHandleResponse` meet). The interfaces are in `@nestjs/common/interfaces/features/nest-interceptor.interface.d.ts`.
- Related topics: [1.5 Middleware](05_middleware.md), [1.6 Pipes](06_pipes.md), [1.7 Guards](07_guards.md), 1.9 Exception Filters, 1.10 Request Lifecycle, 2.2 Custom and Async Providers, 2.4 Injection Scopes, 3.3 Serialization and Response Shaping, 3.7 HTTP Features, 4.5 Caching, 7.4 Logging, 8.2 Server-Sent Events and Streaming.

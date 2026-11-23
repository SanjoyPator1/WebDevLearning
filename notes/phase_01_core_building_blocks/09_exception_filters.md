# 1.9 Exception Filters

> **Topic 1.9** | Priority: Core | Prerequisites: [1.4 Providers and Services](04_providers_and_services.md) (singletons, DI), [1.7 Guards](07_guards.md) (`ArgumentsHost` and `ExecutionContext`), [1.8 Interceptors](08_interceptors.md) | Time: about 3 hours reading plus 3 hours for the exercise | Exercise: [09_exception_filters](../../projects/phase_01_core_building_blocks/09_exception_filters/README.md) | Next: [1.10 Custom Decorators and the Request Lifecycle](10_decorators_and_lifecycle.md) | Roadmap: [1.9 Exception Filters](../../docs/01_nestjs_roadmap.md#19-exception-filters)
>
> Everything marked "measured" was run against `@nestjs/common` and `@nestjs/core` 12.5.1 with the Express adapter on Node 24.22.3. The scratch experiments are not kept: the exercise tests reproduce the important ones.

## Table of Contents

- [Why Exception Filters Matter](#why-exception-filters-matter)
- [The Mental Model](#the-mental-model)
  - [The exceptions layer](#the-exceptions-layer)
  - [Coming from FastAPI](#coming-from-fastapi)
- [The HttpException Family](#the-httpexception-family)
  - [The classes](#the-classes)
  - [What the constructor decides](#what-the-constructor-decides)
  - [errorCode and cause](#errorcode-and-cause)
  - [What happens to everything else](#what-happens-to-everything-else)
- [Writing a Filter](#writing-a-filter)
  - [Catch and ArgumentsHost](#catch-and-argumentshost)
  - [Which exceptions a filter matches](#which-exceptions-a-filter-matches)
  - [A filter must answer](#a-filter-must-answer)
- [Catch-All Filters and BaseExceptionFilter](#catch-all-filters-and-baseexceptionfilter)
- [Domain Errors and HTTP Errors](#domain-errors-and-http-errors)
- [Binding Filters](#binding-filters)
  - [The three scopes and which one wins](#the-three-scopes-and-which-one-wins)
  - [Class or instance](#class-or-instance)
  - [Global filters and dependency injection](#global-filters-and-dependency-injection)
- [What Reaches a Filter](#what-reaches-a-filter)
- [Filter or Interceptor for Errors](#filter-or-interceptor-for-errors)
- [Testing Filters](#testing-filters)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Exception Filters Matter

Every failure in a Nest application ends up as an HTTP response, and the **exceptions layer** decides which one. By default it does something sensible: an `HttpException` becomes its status and body, and anything else becomes a generic 500 that hides the details. An **exception filter** is how you take over that last step: shape every error response the same way, map your domain's errors to statuses in one place, log what you want, and keep internals from leaking.

Interviewers ask about it as:

- "What happens when a handler throws a plain `Error`? A `NotFoundException`?"
- "How do you return the same error shape from every endpoint?"
- "Where do you convert a domain error into an HTTP status? Why not in the service?"
- "In what order do filters run, and does a global filter see everything?"
- "What is `BaseExceptionFilter` for, and why does a hand-built global one break?"

The whole lifecycle is 1.10. Designing an error model for a real API (RFC 9457 problem details, stable codes, what to log and what to expose, correlation ids) is 3.4; this topic is the mechanism.

## The Mental Model

### The exceptions layer

A throw anywhere in the HTTP pipeline (a handler, a pipe, a guard, an interceptor, even middleware) is caught by Nest and handed to the **exception filters**. Nest picks **one** filter, which writes the response:

```
throw ----> (filters bound to the route, method > controller > global) ----> matching one answers
                                  |
                          none matches
                                  v
                    Nest's built-in default handling (BaseExceptionFilter)
```

A custom filter is a class with `catch(exception, host)` and a `@Catch(...)` decorator naming the classes it handles.

### Coming from FastAPI

| FastAPI | Nest |
|---|---|
| `raise HTTPException(404, "x")` | `throw new NotFoundException('x')` |
| `@app.exception_handler(MyError)` returning a `JSONResponse` | `@Catch(MyError)` filter that writes the response itself |
| one global handler per exception type, registered once | filters bound at global, controller or method level |
| unhandled exception: a 500 and a traceback in the log | generic 500, message hidden from the client, error logged |
| `RequestValidationError` handled in one place | pipe errors are `BadRequestException`s, handled by the same filters |

The difference to remember: in Nest a filter **must write the response** (Starlette handlers return one), and **only one** filter runs per exception.

## The HttpException Family

### The classes

`HttpException` extends Nest's `IntrinsicException` (an `Error`), and has a class per common status (measured):

| Class | Status | Class | Status |
|---|---|---|---|
| `BadRequestException` | 400 | `PayloadTooLargeException` | 413 |
| `UnauthorizedException` | 401 | `UnprocessableEntityException` | 422 |
| `ForbiddenException` | 403 | `InternalServerErrorException` | 500 |
| `NotFoundException` | 404 | `NotImplementedException` | 501 |
| `ConflictException` | 409 | `ServiceUnavailableException` | 503 |
| `GoneException` | 410 | `ImATeapotException` | 418 |

Others exist for 405, 406, 408, 412, 415, 502, 504 and 505 (`MethodNotAllowedException`, `NotAcceptableException`, `RequestTimeoutException`, `PreconditionFailedException`, `UnsupportedMediaTypeException`, `BadGatewayException`, `GatewayTimeoutException`, `HttpVersionNotSupportedException`). For a status without a class, use the generic `new HttpException(response, status)`. An exception has `getStatus()`, `getResponse()` (what it was built with), `message`, `name`, `cause` and `errorCode`.

### What the constructor decides

Measured, with `BadRequestException` (the others behave the same):

| You throw | The client gets (status 400) |
|---|---|
| `new BadRequestException()` | `{"message":"Bad Request","statusCode":400}` (no `error` field) |
| `new BadRequestException('too short')` | `{"message":"too short","error":"Bad Request","statusCode":400}` |
| `new BadRequestException(['a must be x', 'b must be y'])` | `{"message":["a must be x","b must be y"],"error":"Bad Request","statusCode":400}` |
| `new BadRequestException('too short', 'Weak Password')` | the same with `"error":"Weak Password"` (a string second argument is the description) |
| `new BadRequestException({ code: 'X', detail: 'custom' })` | **exactly** `{"code":"X","detail":"custom"}`: Nest adds nothing to an object |
| `new BadRequestException({ message: 'in object', extra: 1 })` | exactly that object |
| `new HttpException('generic message', 418)` | `{"statusCode":418,"message":"generic message"}` |
| `new HttpException({ a: 1 }, 409)` | exactly `{"a":1}` |

Two rules fall out: with a **string or array** message Nest builds the standard body; with an **object** you own the whole shape. The array form is what the validation pipes use, which is why a failed validation has a `message` that is a list (1.6).

### errorCode and cause

New in v12, the options object takes an `errorCode`, a stable machine-readable code for the client to switch on, and `cause`, the underlying error for your logs. Measured:

| You throw | Body |
|---|---|
| `new BadRequestException('too short', { errorCode: 'WEAK_PASSWORD' })` | `{"message":"too short","error":"Bad Request","statusCode":400,"errorCode":"WEAK_PASSWORD"}` |
| `new BadRequestException('too short', { description: 'Weak', errorCode: 'WEAK_PASSWORD' })` | the same with `"error":"Weak"` |
| `new BadRequestException(undefined, { errorCode: 'WEAK_PASSWORD' })` | `{"message":"Bad Request","statusCode":400,"errorCode":"WEAK_PASSWORD"}` |
| `new HttpException('generic', 409, { errorCode: 'DUP' })` | `{"statusCode":409,"message":"generic","errorCode":"DUP"}` |
| `new BadRequestException({ code: 'X' }, { errorCode: 'WEAK_PASSWORD' })` | `{"code":"X"}`: **not in the body**, because an object body is sent as it is |
| `new BadRequestException('wrapped', { cause: new Error('root cause') })` | `cause` is **not** in the body |

So `errorCode` reaches the client through the default handling for the string, array and empty forms, and is always stored on the exception as `exception.errorCode` (typed `string | undefined`), which is where a custom filter reads it. With an object body you must put the code in the object yourself. `cause` never reaches the client: it is for your logs and for debugging. The roadmap's stable machine-readable error codes as a design is 3.4.

### What happens to everything else

The built-in handling (`BaseExceptionFilter`, source) treats anything that is not an `HttpException` as an unexpected failure. Measured:

| Thrown | Client gets | Logged |
|---|---|---|
| `new Error('secret internals')` | **500** `{"statusCode":500,"message":"Internal server error"}` | yes, the real message |
| `throw 'a string'`, `throw { weird: true }`, `throw null` | the same generic 500 | yes |
| any `HttpException` | its own status and body | **no** |
| an `IntrinsicException` subclass of yours | generic 500 | **no** |
| an Error shaped like the `http-errors` library (`statusCode`, `expose: true`) | its status and its message (413 `http-errors style`) | yes |
| the same with `expose: false` | its status but the standard text (503 `Service Unavailable`): the detail is hidden | yes |

Why this matters: an unexpected error never leaks its message to a client (a database password in the text, say) and is always logged; an `HttpException` is considered "handled" and is not logged. A domain error you want treated as a business outcome, not a bug, can extend `IntrinsicException` to skip the log line, or be mapped by a filter (below).

## Writing a Filter

### Catch and ArgumentsHost

```ts
@Catch(HttpException)
export class ErrorEnvelopeFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost): void {
    const http = host.switchToHttp();
    const response = http.getResponse<Response>();
    const request = http.getRequest<Request>();
    response.status(exception.getStatus()).json({ /* your shape */ });
  }
}
```

`ArgumentsHost` is the parent of the `ExecutionContext` of guards (1.7): `switchToHttp()` gives the request and response, `getType()` the transport (`'http'`, `'ws'`, `'rpc'`). Reading the exception: `getResponse()` is a string or an object; when it is an object with a `message`, that message can be an **array**, which `exception.message` is not. Measured: for an array body `exception.message` is `'Bad Request Exception'` and for an object body without a message `'Http Exception'` (derived from the class name), so a filter that wants the real message reads `exception.getResponse()`.

For a filter that should not depend on Express, reply through the adapter instead: inject `HttpAdapterHost` and call `httpAdapter.reply(response, body, status)` (measured working, with the adapter injected into a class-bound filter). Writing `response.status().json()` ties the filter to Express (3.8).

### Which exceptions a filter matches

`@Catch(...)` lists classes and Nest matches with **`instanceof`**. Measured with four filters on routes that throw a `BadRequestException`, a `NotFoundException`, a plain `Error` and a thrown string:

| `@Catch(...)` | bad | not found | plain Error | thrown string |
|---|---|---|---|---|
| `HttpException` | filter | filter | default 500 | default 500 |
| `BadRequestException` | filter | default 404 | default 500 | default 500 |
| `NotFoundException, ForbiddenException` | default 400 | filter | default 500 | default 500 |
| nothing: `@Catch()` | filter | filter | filter | filter |

A parent class catches all its subclasses, a specific class only itself, and an exception no filter matches falls back to the default handling, which is correct and logs unexpected errors. A **filter class with no `@Catch` at all** is a catch-all too: measured, a filter without the decorator handled both a `BadRequestException` and a plain `Error`. Forgetting `@Catch(...)` on a filter you meant to be narrow silently widens it.

### A filter must answer

Nest does not send anything for a custom filter: it trusts it to write the response. Measured: a filter whose `catch()` returned without answering left the request **hanging** until the client timed out. So every code path of a filter must send something, or throw.

## Catch-All Filters and BaseExceptionFilter

A catch-all `@Catch()` is the place for logging and last-resort handling, but if it writes the response itself it must also reimplement what the default does (status from an `HttpException`, hiding unexpected messages, headers already sent, the adapter). `BaseExceptionFilter` from `@nestjs/core` is that default, so a catch-all **extends it and delegates**:

```ts
@Catch()
@Injectable()
export class LoggingFilter extends BaseExceptionFilter {
  constructor(private readonly log: ErrorLog) { super(); }
  override catch(exception: unknown, host: ArgumentsHost) {
    this.log.add(/* name and message */);
    super.catch(exception, host);          // Nest's own handling, unchanged
  }
}
```

Measured with such a filter bound by class, by `APP_FILTER`, and by hand:

| Registered as | Result |
|---|---|
| `@UseFilters(LoggingFilter)` (class) | works: an `HttpException` still gets its 400 body, a plain `Error` the generic 500; both recorded. The default's own log line for the plain `Error` is still written (so it is logged twice if you also log) |
| `{ provide: APP_FILTER, useClass: LoggingFilter }` | works, and also records the router's **404 for an unknown path** |
| `app.useGlobalFilters(new LoggingFilter(log))`, no adapter | **broken**: the response became Express's **HTML 500 error page**, because `BaseExceptionFilter` had no HTTP adapter to reply with |
| `app.useGlobalFilters(new LoggingFilter(log, app.get(HttpAdapterHost).httpAdapter))` | works |

The adapter reaches a `BaseExceptionFilter` subclass through a property that Nest injects (`HttpAdapterHost`, an optional property injection, 1.4) when Nest builds the class, or through its constructor argument when you build it yourself. That is why `APP_FILTER` is the form to default to for a global filter that extends it.

## Domain Errors and HTTP Errors

A service throws errors in the language of the business (`OutOfStockError`, `UnknownProductError`). Somewhere those must become statuses. The options:

| Where the mapping lives | Problem |
|---|---|
| the service throws `NotFoundException` and friends | the service is married to HTTP: it cannot be reused from a queue consumer or a CLI (10.4), and tests assert HTTP in business logic |
| `try/catch` in every controller method | repeated, easy to forget, noisy |
| `catchError` in an interceptor (1.8) | works per route, but an interceptor never sees an error from a guard or from middleware |
| **an exception filter** | one place, sees every error, keeps services and controllers HTTP-free |

The pattern (the exercise's Task 3): an abstract `DomainError` base class with a stable `code`, specific subclasses, a service that throws them, a thin controller that catches nothing, and `@Catch(DomainError)` filter that picks a status by subclass and writes `{ code, message }`. Measured: the filter matched every subclass through `instanceof` (including a subclass of a subclass), and a plain `Error` from the same service was **not** matched, so it stayed a generic 500 that hides its message. That is the property you want: only errors you modelled are described to the client.

Choose the status by the **kind** of error, in one table inside the filter, and give unmodelled subclasses a safe default. A domain error that should not be logged as a failure can also extend `IntrinsicException` (above). The stable `code` is what clients switch on; the message is for humans.

## Binding Filters

### The three scopes and which one wins

| Scope | How | Applies to |
|---|---|---|
| global | `app.useGlobalFilters(new F())`, or an `APP_FILTER` provider | every route |
| controller | `@UseFilters(F)` on the class | every route of the controller |
| method | `@UseFilters(F)` on a route | that route |

Filters behave unlike guards, pipes and interceptors: they do not run in a chain. Nest picks **one**. Measured with catch-all filters at several levels:

```
filters at global + controller + method     -> the METHOD filter handled it      (trace: method)
filters at global + controller              -> the CONTROLLER filter             (trace: controller)
two filters on one route @UseFilters(F1, F2)-> the LAST one, F2                  (trace: second)
filter at global only                       -> the GLOBAL filter
```

The narrowest scope wins, and inside one `@UseFilters(a, b)` the last one is tried first (the source reverses the list before matching: `router-exception-filters.js`). Within the winning order, a filter qualifies only if its `@Catch` matches; the first qualifying one handles the exception. The consequence people trip on: **a global catch-all (for example a logging filter) does not see an exception that a narrower filter caught.** Make the narrow filters delegate, or keep logging out of the filter chain (an interceptor or a custom exception class).

### Class or instance

| Form | Built by | Injection |
|---|---|---|
| `@UseFilters(DiFilter)` (the class) | Nest, in the module of the controller | yes |
| `@UseFilters(new NamedFilter('x'))` (an instance) | you | no: you pass arguments yourself |

A class-bound filter is built once and shared: measured, a filter class used on two controllers of one module was constructed once and received the module's provider and `HttpAdapterHost`.

### Global filters and dependency injection

| | `app.useGlobalFilters(new F())` | `{ provide: APP_FILTER, useClass: F }` |
|---|---|---|
| Built by | you, outside the container | Nest, like any provider (2.2) |
| Injection | **none**: measured, a filter with a missing dependency made the request a generic 500 | yes |
| Where | `main.ts` | the `providers` of any module |

`APP_FILTER` comes from `@nestjs/core`. Measured, it applies to the **whole application**: a filter provided in a module that one other module imported handled an error from a controller of a third module that never imported it. The siblings are `APP_GUARD` (1.7), `APP_PIPE` (1.6), `APP_INTERCEPTOR` (1.8).

## What Reaches a Filter

A filter sees more than any other component. Measured with a global catch-all that stamps what it handled:

| The error comes from | Reaches the filter |
|---|---|
| the handler (sync or async) | yes |
| a guard (a denial is a `ForbiddenException`) | **yes** |
| a pipe | yes |
| an interceptor (including one rewritten by `catchError`) | yes |
| module middleware | yes |
| a global `app.use` function | yes |
| a path that matches no route (the router's own 404) | **yes** |

So a filter is the one place that sees **every** error, which is exactly why application-wide error shaping and logging belong there and not in an interceptor (which never sees a guard denial, 1.8). A filter bound at the controller or method level only sees what happens on its own routes: the 404 for an unknown path, and errors from global middleware, can only be caught by a **global** filter.

## Filter or Interceptor for Errors

| | Exception filter | Interceptor (1.8) |
|---|---|---|
| Sees errors from the handler and pipes | yes | yes |
| Sees guard denials, middleware errors, unknown-path 404s | **yes** | no |
| Can turn an error into a normal 200 response | yes (it writes the response) | yes (`catchError` returning a value) |
| Can replace one error with another and keep the default handling | no (it answers; delegate with `BaseExceptionFilter`) | yes (`throwError`) |
| Natural use | one error shape for the API, domain error mapping, last-resort logging | per-route behaviour: timeouts (`RequestTimeoutException`), retries, fallbacks |

Rule of thumb: **API-wide error shape and mapping in a filter**, route-specific recovery in an interceptor.

## Testing Filters

Two levels, as in the exercise.

```ts
// 1. By hand: a filter is a class; hand it an exception and a fake ArgumentsHost with a fake response.
function fakeHost(originalUrl: string) {
  const response = { status: vi.fn().mockReturnThis(), json: vi.fn() };
  const host = {
    switchToHttp: () => ({ getRequest: () => ({ originalUrl }), getResponse: () => response }),
  } as unknown as ArgumentsHost;
  return { host, response };
}
const { host, response } = fakeHost('/things?x=1');
new ErrorEnvelopeFilter().catch(new BadRequestException('too short', { errorCode: 'WEAK' }), host);
expect(response.status).toHaveBeenCalledWith(400);
expect(response.json).toHaveBeenCalledWith({ status: 400, code: 'WEAK', message: 'too short', path: '/things?x=1' });

// 2. Binding, precedence, what reaches the filter and the real response need an application.
const app = await createApp({ controllers: [ShapesController] });
await request(app.getHttpServer()).get('/shapes/list').expect(400);
```

(Measured: the by-hand version, with a chained fake `status().json()`, passed and type-checked.) Level 1 checks the mapping logic against any exception you invent, including ones that are hard to trigger. Level 2 checks what it cannot: that the filter is bound where you think, which filter wins, that a plain `Error` is **not** matched, that a global `APP_FILTER` really sees a guard denial and a 404, and that a `BaseExceptionFilter` subclass still produces the default response. Always test the negative: an unexpected error must still be a generic 500 that hides its message. Register global filters before `app.init()`, as for the other components.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| a filter that returns without sending | the request hangs | every path must answer or throw |
| a filter class without `@Catch(...)` | it catches everything | decorate it, with the classes you mean |
| `throw new Error(...)` and expecting a message in the response | a generic 500, the message only in the log | throw an `HttpException`, or map a domain error |
| an object body and `errorCode` | `errorCode` is not in the body | put the code in the object, or use a string message |
| reading `exception.message` for an array body | `'Bad Request Exception'` | read `exception.getResponse()` |
| expecting a global filter to see what a narrower filter caught | it does not | delegate with `BaseExceptionFilter`, or log elsewhere |
| two filters in one `@UseFilters(a, b)` and expecting `a` first | the last one is tried first | order accordingly |
| `useGlobalFilters(new X())` where `X` extends `BaseExceptionFilter` | no adapter: the client gets Express's HTML 500 | `APP_FILTER`, or pass the adapter |
| `useGlobalFilters(new X())` for a filter with dependencies | `undefined` dependencies, a 500 | `APP_FILTER` |
| a service throwing `NotFoundException` | the service depends on HTTP | domain errors plus a filter |
| a `catch` that does `response.status().json()` for every case | rebuilds the default, adapter-specific | extend `BaseExceptionFilter` and `super.catch()` |
| catching in a controller method `try/catch` everywhere | repeated mapping | one filter |
| logging in a filter and also in the default handler | the same error logged twice | log once: delegate, or accept the extra line |
| assuming `HttpException`s are logged | they are not | log them in a filter if you need to |
| a controller-level filter expected to catch a 404 for an unknown path | it never runs for it | a global filter |
| leaking `cause` or `error.stack` into the body | internals reach the client | keep them in logs |
| treating validation errors as a 500 | they are `BadRequestException`s with an array message | see 3.2 |

## Interview Questions

**1. What happens when a handler throws a plain `Error`? A `NotFoundException`?**
A plain `Error` becomes a generic `500 {"statusCode":500,"message":"Internal server error"}`, the real message is only logged and never sent. An `HttpException` is answered with its own status and body, and is not logged. Both are produced by Nest's built-in `BaseExceptionFilter`.

**2. What does an exception filter look like?**
A class with `catch(exception, host: ArgumentsHost)` and `@Catch(SomeException)`. It must write the response itself (`host.switchToHttp().getResponse()`); one that does not leaves the request hanging. `@Catch()` with no arguments, or no decorator at all, catches everything.

**3. How does Nest choose between several filters?**
Only one runs. The narrowest scope wins (method, then controller, then global), the last one in `@UseFilters(a, b)` is tried first, and a filter only qualifies if its `@Catch` matches the exception by `instanceof`. If none matches, the default handling answers. So a global filter does not see what a narrower filter caught.

**4. What is `errorCode` in v12?**
An option of the exception constructor, `new BadRequestException('msg', { errorCode: 'WEAK_PASSWORD' })`, a stable machine-readable code. It is stored on the exception and written to the default body for string, array and empty messages, but not for an object body, which Nest sends as it is. A custom filter reads it from `exception.errorCode`.

**5. Where do you convert a domain error to an HTTP status?**
In an exception filter: `@Catch(DomainError)` on an abstract base class, with the status chosen by subclass. The service stays HTTP-free and reusable, the controller stays thin, and one table holds the mapping. A plain `Error` from the same code is not matched and remains a generic 500.

**6. What is `BaseExceptionFilter` for, and why does `useGlobalFilters(new MyFilter())` break it?**
It is Nest's default handling; a catch-all that extends it can add logging and call `super.catch()` to keep the default response. It needs the HTTP adapter, which Nest injects when it builds the class (for example through `APP_FILTER`). A hand-built instance has none and the response falls through to Express's HTML error page; pass the adapter by hand or use `APP_FILTER`.

**7. How do you register a global filter with dependency injection?**
As a provider with the `APP_FILTER` token and `useClass`, in any module. It applies to the whole application, including controllers of modules that never import it. `app.useGlobalFilters(new F())` takes an instance built outside the container, so nothing is injected.

**8. Which errors can a filter see that an interceptor cannot?**
Errors from guards (a denial), from middleware, and the router's 404 for an unknown path. Both see errors from the handler and from pipes. A global filter sees all of them, which is why application-wide error shaping and logging belong in one.

**9. Does a thrown `HttpException` get logged?**
No: `HttpException` extends `IntrinsicException`, which the default handler skips. Unexpected errors are logged. Extend `IntrinsicException` for your own error that should not be logged, or log inside a filter.

**10. How would you return the same error shape from every endpoint?**
A global filter, registered with `APP_FILTER`, that catches `HttpException` (and a catch-all or delegation for the rest) and writes one envelope such as `{ status, code, message, path }`, reading the message from `exception.getResponse()` and the code from `exception.errorCode`. Designing the envelope (RFC 9457, stable codes, correlation ids) is topic 3.4.

**11. What goes in the response and what stays in the log?**
The response gets a status, a stable `code`, and a message safe for the client. The `cause`, the stack and unexpected error messages stay in the log. Nest follows this by default: a plain `Error` is a generic 500, and `cause` never reaches the body.

## Check Yourself

- [ ] I can say what the client gets, and what is logged, for a plain `Error`, an `HttpException` and a thrown string.
- [ ] I know what each constructor form produces, and where `errorCode` does and does not appear.
- [ ] I can write a filter with `@Catch` and `ArgumentsHost`, and I know it must respond.
- [ ] I can predict which filter handles an exception from the scope, the order in `@UseFilters` and the `@Catch` match.
- [ ] I know a filter with no `@Catch` catches everything, and a narrow `@Catch` falls through to the default for the rest.
- [ ] I can write a catch-all that extends `BaseExceptionFilter`, and explain why a hand-built global one needs the adapter.
- [ ] I can map domain errors to HTTP in one filter and explain why the service should not throw `HttpException`.
- [ ] I know why `APP_FILTER` injects and applies app-wide while `useGlobalFilters(new F())` does not inject.
- [ ] I know which errors reach a filter (guards, pipes, interceptors, middleware, unknown paths) and which scopes can see them.
- [ ] I finished the exercise: [09_exception_filters](../../projects/phase_01_core_building_blocks/09_exception_filters/README.md).

## Further Reading

- Official documentation: [Exception filters](https://docs.nestjs.com/exception-filters) (built-in HTTP exceptions, custom exceptions, binding filters, catch everything, inheritance). Not re-read for this note: the behaviour above was measured on 12.5.1 instead.
- Source worth reading in the installed `node_modules/@nestjs/`, in this order: `common/exceptions/http.exception.js` (`createBody`, `initMessage`, the `errorCode` handling), `core/exceptions/base-exception-filter.js` (the default handling, the logging rule, the `http-errors` support), `core/exceptions/exceptions-handler.js` (`invokeCustomFilters`), `core/router/router-exception-filters.js` (the reversed filter list).
- Related topics: [1.4 Providers and Services](04_providers_and_services.md), [1.6 Pipes](06_pipes.md), [1.7 Guards](07_guards.md), [1.8 Interceptors](08_interceptors.md), 1.10 Request Lifecycle, 2.2 Custom and Async Providers, 3.2 Validation, 3.4 Error Handling Design, 3.8 HTTP Adapters, 10.4 Standalone Apps and CLIs.

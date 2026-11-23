# 1.3 Controllers and Routing

> **Topic 1.3** | Priority: Core | Prerequisites: [1.2 Modules](02_modules.md), [03 TypeScript Features Nest Is Built On](../phase_00_orientation/03_typescript_for_nest.md) (decorators and metadata) | Time: about 3 hours reading plus 3 hours for the exercise | Exercise: [03_controllers_and_routing](../../projects/phase_01_core_building_blocks/03_controllers_and_routing/README.md) | Next: [1.4 Providers and Services](04_providers_and_services.md) | Roadmap: [1.3 Controllers and Routing](../../docs/01_nestjs_roadmap.md#13-controllers-and-routing)
>
> Everything marked "measured" was run against `@nestjs/core` 12.5.1 with the Express adapter (Express 5, path-to-regexp 8.4.2) on Node 24.22.3. The scratch experiments are not kept: the exercise tests reproduce the important ones.

## Table of Contents

- [Why Controllers Matter](#why-controllers-matter)
- [The Mental Model](#the-mental-model)
  - [A controller is a class of route handlers](#a-controller-is-a-class-of-route-handlers)
  - [What the decorators store](#what-the-decorators-store)
  - [How a request reaches your method](#how-a-request-reaches-your-method)
- [The Controller Decorator](#the-controller-decorator)
- [Route Method Decorators](#route-method-decorators)
- [Reading the Request](#reading-the-request)
  - [Route parameters](#route-parameters)
  - [The query string](#the-query-string)
  - [The body](#the-body)
  - [Headers](#headers)
  - [The raw request](#the-raw-request)
- [Shaping the Response](#shaping-the-response)
  - [What Nest sends for each return value](#what-nest-sends-for-each-return-value)
  - [Status codes](#status-codes)
  - [Response headers](#response-headers)
  - [Redirects](#redirects)
- [Async Handlers and Observables](#async-handlers-and-observables)
- [Using Res Safely](#using-res-safely)
- [Express 5 Route Paths](#express-5-route-paths)
  - [Named wildcards and optional segments](#named-wildcards-and-optional-segments)
  - [What no longer works](#what-no-longer-works)
- [Route Order and Conflicts](#route-order-and-conflicts)
  - [Declaration order wins](#declaration-order-wins)
  - [routeResolutionStrategy](#routeresolutionstrategy)
  - [routeConflictPolicy](#routeconflictpolicy)
- [DTOs Are Classes](#dtos-are-classes)
- [Where Controllers Sit in the Pipeline](#where-controllers-sit-in-the-pipeline)
- [Testing Controllers](#testing-controllers)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Controllers Matter

A controller is where an HTTP request becomes a method call and a return value becomes an HTTP response. Everything in the request pipeline (middleware, guards, pipes, interceptors, filters, topics 1.5 to 1.9) is wrapped around the handler methods of a controller, so you need to know exactly what Nest does *for* you here and what it leaves to you.

Interviewers ask about it as:

- "What does `@Res()` do, and why do people avoid it?" (It switches Nest's response handling off.)
- "A handler returns an object. What status and content type does the client get?"
- "Two routes, `/items/:id` and `/items/featured`: which one runs?"
- "What changed in route syntax with Express 5?"
- "Why are DTOs classes and not interfaces?"

**Coming from FastAPI.** The mapping is direct but Nest does less for you:

| FastAPI | Nest | Difference |
|---|---|---|
| `@router.get("/x")` | `@Get('x')` on a method | Same idea. Nest groups routes in a class. |
| `APIRouter(prefix="/items")` | `@Controller('items')` | Same. |
| Typed params, coerced by annotation (`id: int`) | `@Param('id') id: string` | **Nest never coerces.** `id: number` is a lie unless a pipe (1.6) converts it. Measured: `@Query('n') n: number` receives `"5"`. |
| Pydantic body model | `@Body() dto: SomeDto` | The class is only a *type token*. Nothing validates it until a pipe does (1.6, 3.2). Measured: the value is a plain object, not an instance. |
| `status_code=201` | `@HttpCode(201)` | POST defaults to 201 in Nest, everything else 200. |
| `response_model` | none yet | Serialization is 3.3. |
| `RedirectResponse`, `Response` param | `@Redirect()`, `@Res()` | Same escape hatch, same cost. |
| First matching route wins (Starlette) | First registered route wins | Same rule, and the same trap with `/:id` before `/featured`. |

## The Mental Model

### A controller is a class of route handlers

```ts
@Controller('items')          // class decorator: prefix
export class ItemsController {
  constructor(private readonly items: ItemsService) {}   // injected (1.4)

  @Get(':id')                 // method decorator: HTTP method + path
  findOne(@Param('id') id: string) {   // parameter decorator: where the value comes from
    return this.items.findOne(Number(id));               // return value becomes the response
  }
}
```

Three kinds of decorator, each only writing metadata:

| Kind | Examples | Says |
|---|---|---|
| Class | `@Controller()` | "this class handles HTTP, under this prefix" |
| Method | `@Get()`, `@Post()`, `@HttpCode()`, `@Header()`, `@Redirect()` | which requests reach this method, and how to answer |
| Parameter | `@Param()`, `@Query()`, `@Body()`, `@Headers()`, `@Req()`, `@Res()` | what to put in this argument |

A controller is listed in a module's `controllers` array (1.2). It is instantiated once like a provider, so by default one instance serves every request and instance fields are shared state (scopes are 2.4).

### What the decorators store

None of the decorators do any routing. They only call `Reflect.defineMetadata`. Measured with `Reflect.getMetadataKeys` on a controller:

```
class ItemsController      keys: __controller__, path, host, scope:options, __version__
                           path = 'items'
method create (@Post @HttpCode(202) @Header('X-A','b')):
  on the function:         path = '/', method = 1   (RequestMethod.POST)
                           __httpCode__ = 202, __headers__ = [{name:'X-A', value:'b'}]
  @Redirect('/x', 301):    __redirect__ = { statusCode: 301, url: '/x' }
  parameters, stored on the class under the method name (key "paramtype:index"):
    "3:0" -> { index: 0, pipes: [] }                  paramtype 3 = BODY
    "4:1" -> { index: 1, data: 'limit', pipes: [] }   paramtype 4 = QUERY
    "5:2" -> { index: 2, data: 'id',    pipes: [] }   paramtype 5 = PARAM
  TypeScript's own:        design:paramtypes = [CreateItemDto, String, String]
```

The parameter types are the `RouteParamtypes` enum: `REQUEST 0, RESPONSE 1, NEXT 2, BODY 3, QUERY 4, PARAM 5, HEADERS 6, SESSION 7, FILE 8, FILES 9, HOST 10, IP 11, RAW_BODY 12, ACK 13, COOKIES 14, SIGNED_COOKIES 15`. The `RequestMethod` enum has `GET 0, POST 1, PUT 2, DELETE 3, PATCH 4, ALL 5, OPTIONS 6, HEAD 7` and then `SEARCH`, `PROPFIND` and other WebDAV methods up to `QUERY 16`.

### How a request reaches your method

At bootstrap, for every controller (source in `@nestjs/core/router/`):

1. `PathsExplorer.scanForPaths` walks the prototype and keeps every method that has `path` metadata.
2. `RouterExplorer` joins the module path, the controller prefix and the method path (and a global prefix, 1.1, and versions, 3.5), converts the path for Express with `normalizePath`, and registers the handler on the adapter with `router.get(path, handler)` and friends.
3. The registered handler is built by `RouterExecutionContext.create`. For each request it runs, in this order (read from `router-execution-context.js`): guards, then set the status and the `@Header()` headers, then interceptors, and *inside* the innermost call, pipes, then your method. Then `createHandleResponseFn` sends the result.

The full lifecycle is 1.10. What matters here: the status and headers from `@HttpCode` and `@Header` are already set **before** your method runs, so a handler with `@Res()` sees them, and a guard that rejects the request stops it before they are applied.

## The Controller Decorator

`@Controller()` accepts a prefix string, an array of prefixes, or an options object:

```ts
@Controller()                       // no prefix: routes at the root
@Controller('items')                // /items/...
@Controller(['one', 'two'])         // both /one/x and /two/x (measured)
@Controller({ path: 'items', host: 'api.example.com', version: '1', scope: Scope.REQUEST })
```

`host` restricts the controller to a request host (string, RegExp or an array), `version` is API versioning (3.5) and `scope` is injection scope (2.4). Of these only the prefix is used in this topic.

Without `@Controller()`, a class in `controllers` makes Nest throw at startup: `An invalid controller has been detected. "X" does not have the @Controller() decorator but it is being listed in the "controllers" array of some module.` (`UnknownRequestMappingException`, from `RouterExplorer.extractRouterPath`).

A method path and the prefix are joined for you, and slashes are normalized: `@Controller('items')` with `@Get('/slash')` and with `@Get('slash')` is the same route. A method path can also be an array: `@Get(['a', 'b'])` answers both `/a` and `/b` (measured). `@Get()` with no argument is the controller root, `/items`.

Express matching quirks, measured, that apply to every route: `/t/` matches a route declared as `/t` (the trailing slash is ignored), and `/T` matches too (matching is case-insensitive). Both are Express defaults, not Nest behaviour.

## Route Method Decorators

| Decorator | HTTP method | Default status |
|---|---|---|
| `@Get()` | GET | 200 |
| `@Post()` | POST | **201** |
| `@Put()`, `@Patch()`, `@Delete()` | PUT, PATCH, DELETE | 200 |
| `@Options()`, `@Head()` | OPTIONS, HEAD | 200 |
| `@All()` | every method | 200, also for POST (measured) |
| `@Search()`, `@Propfind()` and other WebDAV ones | their method | 200 |

Details measured:

- Only POST gets 201 by default (`RouterResponseController.getStatusByMethod`). `@All` is registered as its own method, so a POST to an `@All` route answers 200.
- A `HEAD` request to a route that only declares `@Get()` answers 200 with no body (Express does this), so you rarely need `@Head()`.
- A method that is not declared answers a **404** `Cannot DELETE /t/str`, not 405. Nest does not generate `405 Method Not Allowed` or `Allow` headers.
- `@Get()` plus `@Post()` on the same path is two routes on one path, which is normal REST.

## Reading the Request

Every parameter decorator has two forms: with a name it extracts one key, without a name it returns the whole object.

| Decorator | Source | Whole object when called without a name |
|---|---|---|
| `@Param('id')` | route parameters | `@Param()` |
| `@Query('x')` | query string | `@Query()` |
| `@Body('name')` | parsed body | `@Body()` |
| `@Headers('x-token')` | request headers | `@Headers()` |
| `@Req()` / `@Request()` | the platform request | always |
| `@Res()` / `@Response()` | the platform response | always |
| `@Ip()`, `@HostParam()`, `@Session()`, `@Cookies()`, `@SignedCookies()`, `@RawBody()`, `@UploadedFile()`, `@Next()` | specific things | see 3.7, 5.1 |

Each of `@Param`, `@Query`, `@Body` also accepts pipes (1.6) and, new in v12, an options object with a `schema` or `pipes` (3.2).

### Route parameters

`:id` in the path becomes a string, always (measured: `typeof a === 'string'` for `/t/p/1/two`). Nothing converts or checks it:

```ts
@Get(':id')
findOne(@Param('id') id: string) { return this.items.findOne(Number(id)); }  // Number('abc') is NaN
```

This is the number one beginner trap coming from FastAPI. `ParseIntPipe` (1.6) turns it into a number and a 400.

### The query string

Express 5 parses the query with its *simple* parser, so (measured):

| URL | `@Query()` gives |
|---|---|
| `?x=1&y=2` | `{ x: '1', y: '2' }` |
| `?x=1&x=2` | `{ x: ['1', '2'] }` (a repeated key becomes an array) |
| `?x[]=1&x[]=2` | `{ 'x[]': ['1', '2'] }` |
| `?a[b]=c` | `{ 'a[b]': 'c' }` (**not** nested) |
| no query | `{}` |

So one parameter can be a string or an array depending on what the client sends: `@Query('x') x: string` is a lie when `?x=1&x=2` arrives. Nested objects from `a[b]=c` need Express's `extended` parser, which you opt into on the adapter (measured working):

```ts
app.getHttpAdapter().getInstance().set('query parser', 'extended');   // ?a[b]=c -> { a: { b: 'c' } }
```

Express 4 used `extended` by default, so code that relied on nested query objects breaks silently when moved to Express 5.

### The body

`@Body()` is whatever the body parser produced. Measured:

| Request | `@Body()` |
|---|---|
| `Content-Type: application/json`, `{"a":1}` | `{ a: 1 }` |
| `application/x-www-form-urlencoded`, `a=1&b=2` | `{ a: '1', b: '2' }` |
| `text/plain`, `hello` | **`undefined`** (no parser for it, no error) |
| no body at all | `undefined` |
| malformed JSON | **400** `{"message":"Expected property name or '}' in JSON...","error":"Bad Request","statusCode":400}` |
| `@Body('name')` with no body | `undefined` (the handler returned `{}`) |

Two things follow. A handler that does `body.name` crashes with a 500 `TypeError` when there is no body: this is what validation (3.2) is for. And an unknown JSON property is **kept** (measured: `{ name: 'x', extra: 1 }` arrived intact even though the DTO has only `name`). Stripping extra properties is `whitelist` in 3.2.

Raw bytes for signature checks are `@RawBody()` with `rawBody: true` in the app options (3.7).

### Headers

`@Headers('x-token')` reads one header. Node lowercases every incoming header name, and Nest lowercases the name you pass (`req.headers[data.toLowerCase()]` in `route-params-factory.js`), so `@Headers('X-Custom')` works too (measured). The whole-object form has lowercase keys only. A missing header is `undefined`. `@Headers()` returns all of them, including `host`, `connection` and `accept-encoding`.

### The raw request

`@Req()` gives the Express request: `req.method`, `req.path` (`/t/req`), `req.url` and `req.originalUrl` (both `/t/req?z=1` with no global prefix). It makes the handler depend on Express types, which breaks if you switch to Fastify (3.8) and makes testing harder. Prefer the specific decorators. When you do use it, import the type with `import type { Request } from 'express'`: with `isolatedModules` and `emitDecoratorMetadata` on, a plain import of a type used in a decorated signature is a compile error (measured, TS1272).

## Shaping the Response

### What Nest sends for each return value

Nest takes the value your method returns (after awaiting a promise or an Observable, next section) and hands it to the adapter's `reply`. Measured with Express:

| Returned | Status (GET) | `Content-Type` | Body |
|---|---|---|---|
| `'hi'` | 200 | `text/html; charset=utf-8` | `hi` |
| `'<b>x</b>'` | 200 | `text/html` | `<b>x</b>` |
| `42` | 200 | `text/html` | `42` |
| `false` | 200 | `text/html` | `false` |
| `{ a: 1 }` or `[1, 2]` | 200 | `application/json` | JSON |
| `new Date(0)` | 200 | `application/json` | `"1970-01-01T00:00:00.000Z"` |
| `undefined` or `null` | 200 | none | empty |
| (anything, from a `@Post`) | **201** | as above | as above |

Points to notice:

- A returned **string is sent as `text/html`**, not `text/plain`. If you send plain text, set the type (`@Header('Content-Type', 'text/plain')`, or `res.type()`).
- Returning `undefined` is a valid 200 with an empty body. An unknown id that makes `find()` return `undefined` is therefore a **200 with nothing in it**, not a 404. Producing a 404 means throwing a `NotFoundException` (1.9). The exercise leaves this as it is on purpose.
- `null` and `undefined` are both empty (measured), they are not serialized as `null`.
- The dispatch is `ExpressAdapter.reply`: nil body gives `response.send()`, a `StreamableFile` is piped, everything else goes through `response.send`/`json` depending on type. Streaming and files are 3.7.

### Status codes

`@HttpCode(n)` sets the status of the success path (measured):

```ts
@Post('code') @HttpCode(200) code() { return 'c'; }                  // 200 instead of 201
@Delete('nocontent') @HttpCode(204) nc() { return { shouldNot: 'appear' }; }   // 204, empty body
```

204 drops the body even though the method returned one (Express/Node do it). Errors thrown by the handler keep their own status: `@HttpCode` is not applied to them. `HttpStatus` is an enum with every name (`HttpStatus.NO_CONTENT`). The status is set *before* the handler runs, so a `res.status()` call inside a `@Res({ passthrough: true })` handler overrides it (task 4).

### Response headers

`@Header(name, value)` sets a header and can be stacked. The value may be a function, called once per request (measured: a counter header went `1`, `2`):

```ts
@Get('cached')
@Header('Cache-Control', 'public, max-age=60')
@Header('X-Reply', 'cached')
cached() { return 'fresh'; }
```

If you set `Content-Type` this way it sticks, even for an object: `@Header('Content-Type', 'text/plain')` with `return { a: 1 }` sends `text/plain; charset=utf-8` with the body `{"a":1}` (measured). Headers can also come from `@Res({ passthrough: true })` (task 4) or from interceptors (1.8).

### Redirects

`@Redirect(url?, statusCode?)` marks the route as a redirect. The handler usually returns nothing (measured):

| Decorator | Response |
|---|---|
| `@Redirect('/t/target')` | **302**, `Location: /t/target`, body `Found. Redirecting to /t/target` |
| `@Redirect('/t/target', 301)` | 301 |
| `@Redirect('/t/default')` and the handler returns `{ url: '/x', statusCode: 307 }` | 307 to `/x` |
| `@Redirect('/t/default', 303)` and the handler returns `{ url: '/x' }` | 303 to `/x` (the decorator's status stays when the object has none) |
| decorator `303`, handler returns `{ url: undefined }` | 303 to the decorator's url |

The default is 302 (`HttpStatus.FOUND`). The returned object (`HttpRedirectResponse`) overrides either value per request. A redirect needs an absolute or root-relative `url`: Nest does not build URLs for you.

## Async Handlers and Observables

A handler can return a plain value, a `Promise`, or an `Observable`. Nest awaits it (`transformToResult` uses `lastValueFrom` for an Observable) and then replies. Measured:

| Handler returns | Client gets |
|---|---|
| `async` method resolving to `{p:1}` | 200 `{"p":1}` |
| `async` method that throws `new Error('boom')` | **500** `{"statusCode":500,"message":"Internal server error"}`, the error is logged by Nest, never sent |
| `of({v:1})` | 200 `{"v":1}` |
| `from([1, 2, 3])` | 200 `3` (**only the last value**) |
| `interval(5).pipe(take(3))` | 200 `2` (the last of 0, 1, 2) |
| `timer(10).pipe(map(() => 'late'))` | 200 `late` after the delay |
| `EMPTY` (completes, emits nothing) | **500**, because `lastValueFrom` rejects with `EmptyError: no elements in sequence` |
| `throwError(() => new Error())` | 500 |
| `new Observable(() => {})` (never emits) | the request **hangs** until the client gives up |

Rules that follow:

- An HTTP response is one message. Nest never streams the emissions of an Observable: you get the last one. Collect with `toArray()` if you want all of them. To push values as they happen use Server-Sent Events (8.2).
- An Observable that may complete empty needs `defaultIfEmpty(...)` or it is a 500. (The exercise does this in task 5c: `EMPTY.pipe(defaultIfEmpty(undefined))` gives an empty 200.)
- An Observable that never completes keeps the request open. Nest tears the subscription down when the client disconnects (`takeUntil` on the connection), so it does not leak, but add `timeout()` (1.8) so the client gets an answer.
- Do not declare a method `async` and also return an Observable unless you mean it: the promise resolves to the Observable and Nest handles it (a thenable that resolves to an Observable is unwrapped in 12.5.1), but it only adds a layer.

The RxJS needed for interceptors (`map`, `tap`, `catchError`, `timeout`) is 1.8.

## Using Res Safely

`@Res()` injects the Express response so you can write to it yourself. The catch is in `RouterExecutionContext.isResponseHandled`:

```js
isResponseHandled = (has a @Res or @Next parameter) && !passthrough
```

When that is true, **Nest does not send anything**. It trusts you to end the response. Measured, all with Express:

| Handler | Result |
|---|---|
| `@Res() res`, calls `res.status(201).send('x')` | works: 201 `x` |
| `@Res() res`, calls `res.json({...})` | works |
| `@Res() res`, **returns a value, never calls `res.send`** | the request **hangs**, the returned value is ignored (timed out after 400 ms) |
| `@Res({ passthrough: true }) res`, sets `res.status(202)` and a header, returns `{ ok: true }` | works: 202, header present, JSON body |
| `@Res({ passthrough: true }) res`, only sets the status, returns nothing | 202 and an empty body |

`@Next()` triggers the same "you own the response" switch.

**What you lose with plain `@Res()`:** everything Nest does after the handler returns. Interceptors cannot map the result (1.8), response serialization (3.3) does not run, `@HttpCode`/`@Header` still apply but nothing sends the value, and the handler is harder to unit test because it needs a fake response. It also ties the code to Express (3.8).

**Use it for:** streaming or file responses you drive yourself, cookies and headers beyond what `@Header` can express (use `passthrough: true`), and anything that needs `res.type()`.

The rule of thumb for interviews: *if you need the response object, use `{ passthrough: true }`; if you use plain `@Res()` you must end the response on every path, including errors.*

## Express 5 Route Paths

Nest 11 and 12 use Express 5 and path-to-regexp 8, which changed route syntax. The old unnamed wildcard and `?`, `+` forms are gone.

### Named wildcards and optional segments

Measured against 12.5.1:

| Route | Matches | `@Param()` |
|---|---|---|
| `files/*path` | `/files/a`, `/files/a/b/c` | `{ path: ['a'] }`, `{ path: ['a','b','c'] }` (an **array**) |
| `files/*path` | not `/files`, not `/files/` | 404 |
| `files/{*path}` | `/files`, `/files/a/b` | `{}` for `/files`, array otherwise |
| `any{/*rest}` | `/any`, `/any/x/y` | `{}`, `{ rest: ['x','y'] }` |
| `opt/:lang{/:page}` | `/opt/en`, `/opt/en/3` | `{ lang: 'en' }`, `{ lang: 'en', page: '3' }` |
| `opt/:lang{/:page}` | not `/opt/en/3/4` | 404 |
| `ext/:name.:ext` | `/ext/a.json` | `{ name: 'a', ext: 'json' }` |
| `ver/v:version` | `/ver/v2` | `{ version: '2' }` |

So: braces `{...}` make a part optional, a wildcard needs a name (`*path`), `*path` means one or more segments, and `{*path}` means zero or more. A matched wildcard is an array of segments, so join it if you want the path.

### What no longer works

| Old route | In Nest 12 |
|---|---|
| `files/*` | still **starts**: Nest rewrites it to `files/{*path}` and logs a warning `Unsupported route path: "/legacy/files/*". ... Attempting to auto-convert to "/legacy/files/{*path}"...` |
| `rx/(.*)` | auto-converted the same way |
| `/` + `/*/` in the middle | auto-converted to a numbered named wildcard |
| `x/:id?` | **crashes at startup**: `PathError: Unexpected ? at index 9: /l2/x/:id?` |
| `a?b`, `a+` | crash the same way (`Unexpected ?`, `Unexpected +`) |

The converter is `LegacyRouteConverter` in `@nestjs/core/router/legacy-route-converter.js`. It only handles a trailing `*`, `(.*)`, `+` and a `*` between slashes. It does not repair `?`. Treat the warning as an error to fix: the converted route `{*path}` also matches the bare `/files/` and `/files`, which `*` did not necessarily do, so behaviour can differ from the route you wrote.

## Route Order and Conflicts

### Declaration order wins

With default options Nest registers routes on Express **in the order they are discovered**, and Express runs the first matching one. Discovery order is: controllers in the order of the module's `controllers` array (and modules in import order, 1.2), and methods in the order they are declared in the class. Measured:

| Setup | `GET /items/featured` |
|---|---|
| one controller: `@Get(':id')` declared first, `@Get('featured')` second | `one:featured` (the literal route is unreachable) |
| same two routes, literal first | `featured` |
| two controllers on `items`, `[Wild, Lit]` | `one:featured` |
| the same two, `[Lit, Wild]` | `featured` |

No error, no warning. The classic bug. The fix: **literal routes before parameter routes**, always, and the same across controllers that share a prefix. A duplicate (same method and path, in two controllers) is also silent: the first registered runs (measured: `first`).

### routeResolutionStrategy

New in v12: `routeResolutionStrategy: 'declaration' | 'specificity'`, default `'declaration'`. `'specificity'` sorts the routes before registering them, on adapters where order matters (Express; not Fastify, which picks the most specific route itself). The sort (`RouteSpecificitySorter`) ranks each segment: literal, then a mix of text and params like `v:version`, then `:param`, then a wildcard, and a shorter path with a wildcard last. Ties keep declaration order. Measured: the wrong-order controller then answers `featured` for `/items/featured` and `one:7` for `/items/7`, and so does the cross-controller case.

```ts
const app = await NestFactory.create(AppModule, { routeResolutionStrategy: 'specificity' });
```

It makes the order bug disappear, which is also a risk: the code that reads fine only works because of an option. Write the order right anyway.

### routeConflictPolicy

New in v12: `routeConflictPolicy: { duplicate?: Level; shadow?: Level }` with `Level = 'off' | 'warn' | 'error'`, **every kind defaults to `'off'`**. Detection runs once at bootstrap (`RouteConflictDetector`) over every pair of routes whose method, host and version can overlap:

- **duplicate**: identical method, path, host and version.
- **shadow**: different patterns that can match the same request (`/items/:id` and `/items/featured`).

`'warn'` logs once per conflict, `'error'` aborts startup with `RouteConflictException` listing all conflicts. Measured messages:

```
Route GET /items/featured (Bad#featured) is shadowed by GET /items/:id (Bad#one). The first-registered route will match all matching requests on order-sensitive adapters.
Duplicate route: GET /dup/x is registered by both Dup1#a and Dup2#b.
Conflicting HTTP routes detected:
  - Duplicate route: GET /dup/x is registered by both Dup1#a and Dup2#b.
Adjust route declarations or relax the 'routeConflictPolicy' option passed to NestFactory.create() to allow the application to start.
```

What the matrix of measurements shows, because it is not obvious:

| Setup | Result |
|---|---|
| wrong order, `shadow: 'warn'` | boots, one warning, the literal route is still unreachable |
| wrong order, `shadow: 'error'` | `RouteConflictException` |
| **correct order**, `shadow: 'error'` | `RouteConflictException` too: it names `/items/:id` as shadowed by `/items/featured` |
| wrong order, `shadow: 'error'` **plus** `'specificity'` | boots (the sort resolves the conflict) |
| correct order, `'error'` plus `'specificity'` | still throws |
| `/b/:id` and `/b/:name` (same shape, different names) | shadow conflict, but **not** a duplicate (`duplicate: 'error'` boots) |
| `/a/x` and `/a/y` | no conflict |
| `duplicate: 'error'` with only a shadow | boots |

So `shadow: 'error'` means "no overlapping patterns at all", which rejects a correctly ordered literal-before-param pair. For most apps `shadow: 'warn'` is the useful setting, and `duplicate: 'error'` is the safe one: two controllers claiming the same route is almost certainly a mistake. That is the policy the exercise asks for (`strictRoutes`).

## DTOs Are Classes

A DTO (data transfer object) describes the shape of a request body. In Nest it is a class:

```ts
export class UpdateItemDto { name?: string; }

@Patch(':id')
update(@Param('id') id: string, @Body() dto: UpdateItemDto) { /* ... */ }
```

Why a class and not an interface or type: `design:paramtypes` is emitted from the declared type (0.3), and only a class exists at runtime. Measured on the same parameter list:

| Declared type | `design:paramtypes` entry |
|---|---|
| `dto: CreateItemDto` (class) | `CreateItemDto` |
| `dto: CreateItemShape` (interface) | `Object` |
| `dto: Alias` (type alias) | `Object` |
| `dto: CreateItemDto[]` | `Array` (the element type is lost) |
| `limit: string`, `n: number` | `String`, `Number` |

A pipe (1.6, 3.2) reads that entry as `metatype` and decides what to validate and convert against. With an interface the pipe only gets `Object` and has nothing to work with.

What a DTO class does **not** do on its own, measured: with no pipe, `dto instanceof UpdateItemDto` is `false`. The value is the plain parsed JSON, extra properties included. The class is a type token, nothing more, until `ValidationPipe` (`transform: true`) builds an instance (3.2). Also note: TypeScript emits `design:paramtypes` only for methods that carry at least one decorator, which parameter decorators satisfy.

One more compile-time trap: under `isolatedModules` plus `emitDecoratorMetadata`, importing a **type** (an interface) and using it in a decorated signature is error TS1272, `A type referenced in a decorated signature must be imported with 'import type'` (measured). Import classes normally and interfaces with `import type`.

## Where Controllers Sit in the Pipeline

Pointers only, each is its own topic:

- Middleware (1.5) runs before the route is matched by Nest's handler.
- Guards (1.7) run first inside the handler and may stop the request before `@HttpCode` and `@Header` are applied.
- Interceptors (1.8) wrap the handler and see its return value, except when plain `@Res()` is used.
- Pipes (1.6) transform `@Body`, `@Query`, `@Param` arguments and run just before your method.
- Exceptions (1.9): anything thrown, including a rejected promise or an Observable error, is mapped to a response, an unknown error becomes a 500 `Internal server error`.
- The whole order is 1.10. Versioning and `RouterModule` prefixes are 3.5, file upload and streaming are 3.7.

## Testing Controllers

The exercise tests build a real application around the controller and call it over HTTP:

```ts
const moduleRef = await Test.createTestingModule({ controllers: [ItemsController], providers: [ItemsService] }).compile();
const app = moduleRef.createNestApplication({ logger });
await app.init();                      // routes are registered here
await request(app.getHttpServer()).get('/items/2').expect(200);   // supertest, no port is opened
```

Notes from building the exercise:

- Routes are registered at `init()`. A **spy installed afterwards is never called**, because Nest has already bound the method. Install it before `createNestApplication`.
- `vi.spyOn(Controller.prototype, 'method')` replaces the method with a new function, and the route decorators stored `path` and `method` on the *old* function: the route disappears (404). Copy the function's metadata onto the spy (the exercise's `dto.spec.ts` does it).
- Pass a custom `logger` to `createNestApplication` to keep expected 500s out of the output and to assert on warnings (the Express 5 path warning, the conflict warnings).
- Calling a controller method directly (`new ItemsController(service).list()`) skips every decorator, so it tests logic only, not routing, status codes or parameter extraction. Phase 6 compares both.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| `@Param('id') id: number` | still a string, no error | `ParseIntPipe` (1.6) or `Number()` |
| `@Query('x') x: string` | an array when the key repeats | validate (3.2) |
| `@Get(':id')` before `@Get('featured')` | the literal route is unreachable, silently | literal first, or `routeResolutionStrategy: 'specificity'` |
| Plain `@Res()` and returning a value | the request hangs | use `{ passthrough: true }`, or end the response |
| Returning an Observable that emits several values | only the last is sent | `toArray()`, or SSE (8.2) |
| An Observable that completes empty | 500 `EmptyError` | `defaultIfEmpty(...)` |
| A string return value | `text/html` | set `Content-Type` |
| `find()` returns `undefined` | 200 with an empty body | throw `NotFoundException` (1.9) |
| `x/:id?`, `a?b`, `a+` | `PathError` at startup | `{/:id}`, a named wildcard, see the table above |
| `files/*` | works, but a warning is logged and the route changes | `files/*path` or `files/{*path}` |
| Missing `@Controller()` | `An invalid controller has been detected` at startup | add it |
| `@Body() dto: SomeInterface` | `design:paramtypes` is `Object` | use a class |
| Trusting `@Body() dto: SomeDto` as a validated object | no validation, not even an instance | add a pipe (1.6, 3.2) |
| `text/plain` body | `@Body()` is `undefined` | send JSON, or add a parser |
| Importing an interface into a decorated signature | TS1272 | `import type` |
| Relying on `a[b]=c` nesting from Express 4 | arrives as the key `a[b]` | the `extended` query parser, or flat keys |
| Calling the controller method in a test | skips routing | test over HTTP too |

## Interview Questions

**1. What does `@Controller('items')` do?**
It marks the class as an HTTP controller and stores the prefix `items` as metadata. At bootstrap `RouterExplorer` joins it with the method paths and registers one Express route per decorated method. Without it, a class in `controllers` throws `UnknownRequestMappingException`. It does not create the instance, the module does (1.2).

**2. A handler returns an object. What does the client get?**
Status 200 (201 for a POST) and `application/json`. A string is `text/html`, a number is `text/html` text, and `undefined` or `null` give an empty body. The status can be changed with `@HttpCode` and the headers with `@Header`.

**3. What does `@Res()` do and why do people avoid it?**
It injects the platform response and, unless `passthrough: true`, turns off Nest's response handling for that handler. Nest ignores the return value, so the handler has to end the response on every path, otherwise the request hangs. You lose interceptors that map the result and serialization, and the code depends on Express. `@Res({ passthrough: true })` gives you the object to set status and headers while Nest still sends the return value.

**4. Do `@Param`, `@Query` and `@Body` convert or validate?**
No. Params are strings, query values are strings or arrays of strings, the body is the parsed object or `undefined`. A type annotation on the parameter is not enforced at runtime. Conversion and validation come from pipes (1.6, 3.2), unlike FastAPI which coerces by annotation.

**5. Two routes, `/items/:id` and `/items/featured`. Which runs for `/items/featured`?**
The first one registered. By default that is declaration order, so put the literal first. v12 adds `routeResolutionStrategy: 'specificity'` to sort literals first, and `routeConflictPolicy` to warn or fail at startup about duplicate or shadowed routes (both default to off).

**6. What does a handler returning an Observable that emits three values send?**
Only the last value. Nest uses `lastValueFrom`, so an HTTP response is always one message. An Observable that completes without emitting is a 500 (`EmptyError`), and one that never completes hangs until the client disconnects or a `timeout` fires. Streaming several values needs SSE (8.2).

**7. What changed in route syntax with Express 5?**
Wildcards must be named (`*path`), and they match one or more segments, delivered as an array. `{*path}` is zero or more. Optional parts use braces (`:lang{/:page}`), and `?`, `+` and regex groups are gone. Nest auto-converts a trailing `*` and `(.*)` with a warning, but `:id?` is a startup `PathError`.

**8. Why is a DTO a class and not an interface?**
Interfaces are erased at compile time. `design:paramtypes` for an interface-typed parameter is `Object`, so a pipe has no metatype to validate against. A class is a runtime value that can be read from metadata and carries decorator-based rules. On its own, though, the class does nothing: without a pipe the body is still a plain object.

**9. What does `@HttpCode` change, and what does it not?**
It sets the status of the success path (the default is 201 for POST, 200 otherwise). Errors keep their own status. With 204 the body is dropped even if the method returns one.

**10. What is the difference between `@Redirect` and returning a redirect from the handler?**
`@Redirect(url, status)` sets the default (302 when no status is given). If the handler returns `{ url, statusCode }` those override the decorator for that request. A missing status keeps the decorator's status.

**11. How do you read `a[b]=c` as a nested object on Nest 12?**
By default you cannot: Express 5's simple parser keeps `a[b]` as a literal key. Set the `query parser` setting to `extended` on the Express instance, or use flat keys.

**12. How do you test that a controller maps the right route and status?**
Compile a testing module with the controller and its providers, create the application, call it with supertest. Calling the method directly skips the decorators. Install any spy before `createNestApplication`.

## Check Yourself

- [ ] I can name what each of `@Controller`, `@Get`, `@HttpCode` and `@Body` stores, and who reads it.
- [ ] I can say what the client receives for a string, an object, `undefined`, a promise and an Observable return value.
- [ ] I know the default status for POST and for everything else, and how to change it.
- [ ] I can explain why plain `@Res()` hangs when the handler only returns a value, and what `passthrough: true` changes.
- [ ] I know that params and query values are never converted, and that the query can be an array.
- [ ] I can write a named wildcard and an optional segment, and I know which old forms crash at startup.
- [ ] I can predict which of two overlapping routes wins, and name the two v12 options that help.
- [ ] I can say why a DTO is a class, and what it does not do without a pipe.
- [ ] I finished the exercise: [03_controllers_and_routing](../../projects/phase_01_core_building_blocks/03_controllers_and_routing/README.md).

## Further Reading

- Official documentation: [Controllers](https://docs.nestjs.com/controllers) (the route, request, response and DTO sections). Not re-read for this note: the behaviour above was measured on 12.5.1 instead.
- [path-to-regexp 8 README](https://github.com/pillarjs/path-to-regexp) for the full route syntax.
- Source worth reading in the installed `node_modules/@nestjs/core/router/`, in this order: `paths-explorer.js`, `router-explorer.js` (`applyCallbackToRouter`), `router-execution-context.js` (`create`, `createHandleResponseFn`, `isResponseHandled`), `router-response-controller.js` (`redirect`, `getStatusByMethod`), `route-conflict-detector.js`, `route-specificity-sorter.js`, `legacy-route-converter.js`. And `node_modules/@nestjs/platform-express/adapters/express-adapter.js` (`reply`).
- Related topics: [1.2 Modules](02_modules.md), 1.4 Providers and Services, 1.5 Middleware, 1.6 Pipes, 1.7 Guards, 1.8 Interceptors, 1.9 Exception Filters, 1.10 Request Lifecycle, 3.2 Validation, 3.5 API Design Features, 3.7 HTTP Features, 3.8 HTTP Adapters, 8.2 Server-Sent Events.

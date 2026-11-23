# Application Bootstrap

> **Topic 1.1** | Priority: Core | Prerequisites: [03 TypeScript Features Nest Is Built On](../phase_00_orientation/03_typescript_for_nest.md), [05 Tooling and Setup](../phase_00_orientation/05_tooling_and_setup.md) | Estimated time: 3 to 4 hours with the exercise
> Exercise: [01_application_bootstrap](../../projects/phase_01_core_building_blocks/01_application_bootstrap/README.md) | Next: [02 Modules](02_modules.md) | Roadmap: [1.1](../../docs/01_nestjs_roadmap.md#11-application-bootstrap)

## Table of Contents

- [Why This Matters](#why-this-matters)
- [The Mental Model](#the-mental-model)
  - [Three Entry Points](#three-entry-points)
  - [What app Actually Is](#what-app-actually-is)
- [What Happens in create, init and listen](#what-happens-in-create-init-and-listen)
  - [The Timeline, Run for Real](#the-timeline-run-for-real)
  - [Reading the Log Lines](#reading-the-log-lines)
  - [Inside NestFactory.create](#inside-nestfactorycreate)
  - [Inside init](#inside-init)
  - [Inside listen](#inside-listen)
  - [Why Tests Call init and Never listen](#why-tests-call-init-and-never-listen)
- [listen, Hosts and URLs](#listen-hosts-and-urls)
  - [Port and Host](#port-and-host)
  - [Default Hosts, Measured](#default-hosts-measured)
  - [Why 0.0.0.0 Matters in a Container](#why-0000-matters-in-a-container)
  - [What listen and getUrl Return](#what-listen-and-geturl-return)
  - [close and the Shutdown Order](#close-and-the-shutdown-order)
- [Global Prefix and CORS](#global-prefix-and-cors)
  - [Global Prefix with Exclusions](#global-prefix-with-exclusions)
  - [CORS: the cors Option and enableCors](#cors-the-cors-option-and-enablecors)
  - [Preflight Requests](#preflight-requests)
- [Body Parsing and Raw Body](#body-parsing-and-raw-body)
- [Other Setup Calls Before listen](#other-setup-calls-before-listen)
- [NestApplicationOptions](#nestapplicationoptions)
  - [Every Option in the Interface](#every-option-in-the-interface)
  - [abortOnError](#abortonerror)
  - [Route Conflict Options](#route-conflict-options)
  - [forceCloseConnections and return503OnClosing](#forcecloseconnections-and-return503onclosing)
  - [httpsOptions](#httpsoptions)
  - [preview and snapshot](#preview-and-snapshot)
- [The Logger at Bootstrap](#the-logger-at-bootstrap)
  - [Levels, false and Custom Loggers](#levels-false-and-custom-loggers)
  - [JSON Mode, Structured Params and Redaction](#json-mode-structured-params-and-redaction)
  - [bufferLogs, autoFlushLogs and useLogger](#bufferlogs-autoflushlogs-and-uselogger)
- [Choosing the HTTP Adapter](#choosing-the-http-adapter)
  - [Switching Adapters](#switching-adapters)
  - [What Changes for the Developer](#what-changes-for-the-developer)
  - [Staying Adapter-agnostic](#staying-adapter-agnostic)
- [main.ts Under ESM](#maints-under-esm)
- [Bootstrap in Tests vs Production](#bootstrap-in-tests-vs-production)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why This Matters

Bootstrap is the first thing a request-handling Nest process does and the first place it can fail. Everything in the rest of Phase 1 plugs into it: modules are scanned during it, controllers become routes during it, guards, pipes, interceptors and filters are attached to the app it builds.

It also carries a disproportionate share of production incidents and interview questions:

- The process exits at startup with `Nest can't resolve dependencies`, and you need to know why it exited and with what code.
- The container is up but unreachable, because of the host the server bound to.
- Tests pass with `supertest` but nothing ever called `listen`, so what did they run against?
- Logs from startup appear in the wrong format, because the real logger was attached after they were written.
- A rolling deploy hangs for a minute because `close()` waits on idle connections.

If you can say exactly what `NestFactory.create`, `init` and `listen` each do, you can answer all of these. This note builds that picture from the installed `@nestjs/core` 12.5.1 source and from real runs. Everything below was run on macOS with Node 24.22.3 (via nvm), TypeScript 6.0.3, Express 5 and Fastify adapters 12.5.1, unless it says otherwise.

---

## The Mental Model

```
                      NestFactory.create(AppModule, adapter?, options?)
                                         |
        +--------------------------------+---------------------------------+
        | 1. load/construct HTTP adapter (Express unless you pass one)     |
        | 2. build ApplicationConfig + NestContainer, apply logger options |
        | 3. SCAN: walk the module graph from AppModule                    |
        | 4. INSTANTIATE: providers, injectables, controllers (constructors|
        |    run here), log "<Module> dependencies initialized"            |
        | 5. new NestApplication(...), create the Node http(s) server      |
        +--------------------------------+---------------------------------+
                                         | returns app (NOT listening, routes NOT registered)
                                         v
                              app.init()   (listen() calls it for you)
        +------------------------------------------------------------------+
        | CORS from the cors option, body parser, middleware, ROUTES       |
        | registered (RoutesResolver/RouterExplorer log lines), then       |
        | onModuleInit, 404 and error handlers, onApplicationBootstrap,    |
        | log "Nest application successfully started", flush buffered logs |
        +--------------------------------+---------------------------------+
                                         v
                              app.listen(port, host)
        +------------------------------------------------------------------+
        | server.listen(...): the port is bound. Resolves with http.Server |
        +--------------------------------+---------------------------------+
                                         v
                              app.close()  (reverse: stop accepting, destroy hooks, close server, shutdown hooks)
```

Three phases, three different questions:

| Phase | Question it answers | Port bound | Routes live | Constructors run | `onModuleInit` / `onApplicationBootstrap` run |
|---|---|---|---|---|---|
| `create` | What does the app consist of? | no | no | yes | no |
| `init` | Is it ready to handle requests? | no | yes | already done | yes |
| `listen` | Can the network reach it? | yes | yes | already done | already done |

All of that was measured, not assumed: see [The Timeline, Run for Real](#the-timeline-run-for-real).

### Three Entry Points

`NestFactory` has three creators. Only the first is this topic's focus.

| Method | Returns | Use it for |
|---|---|---|
| `create(module, adapter?, options?)` | `INestApplication` (the HTTP application) | A web server. Needs an HTTP adapter package. |
| `createMicroservice(module, options)` | `INestMicroservice` | A process that only talks over a message transport. Loads `@nestjs/microservices` on demand. See 9.1. |
| `createApplicationContext(module, options?)` | `INestApplicationContext` | Scripts, workers and cron containers: the container and lifecycle hooks, no HTTP. See 10.4. |

`createApplicationContext` is `create` without the HTTP half. I ran it against the same module:

```text
[Nest] 54111  - ... LOG [NestFactory] Starting Nest application...
  [app] GreetingService constructor
  [app] HealthController constructor
[Nest] 54111  - ... LOG [InstanceLoader] AppModule dependencies initialized +3ms
  [app] GreetingService onModuleInit
  [app] GreetingService onApplicationBootstrap
ctx.constructor.name: NestApplicationContext | has listen? undefined | has getHttpServer? undefined
ctx.get(GreetingService).hello(): hello
```

There are no `RoutesResolver` or `RouterExplorer` lines, no HTTP server, and the lifecycle hooks have already run when the promise resolves (the source calls `context.init()` before returning it). Hybrid applications, which attach microservice transports to an HTTP app, are 9.1.

### What app Actually Is

`create` returns an object that is not quite a `NestApplication`:

```text
app instanceof NestApplication      : true
app.constructor.name                : (empty string)
app.getHttpAdapter().constructor    : ExpressAdapter        (FastifyAdapter on Fastify)
app.getHttpServer() is a            : Server                (node:http Server, both adapters)
app.getHttpAdapter().getInstance()  : EventEmitter          (Express app)   |   Object (Fastify instance)
typeof (app as any).getInstance     : function              (forwarded to the adapter)
app.get(GreetingService).hello()    : hello
```

Reading `nest-factory.js` explains it. `NestFactoryStatic.create` ends with `createAdapterProxy(createNestInstance(instance), httpServer)`. That is two JavaScript `Proxy` layers around the real `NestApplication`:

1. `createProxy` wraps every function-valued property in an exception zone (`ExceptionsZone.run`). A synchronous error thrown by any `app.xxx()` call is logged by Nest's `ExceptionHandler` and then either exits the process or rethrows, depending on `abortOnError`. This is also why `app.constructor` is a wrapper function with an empty name: `constructor` is a function-valued property.
2. `createAdapterProxy` forwards any property the app does not have to the HTTP adapter. This is how `app.register(...)` exists on a Fastify app and `app.getInstance()` on every app.

Two consequences. `app` is also an application context, so `app.get(SomeProvider)` works (it extends `NestApplicationContext`). And the generics on `create` are only a type-level promise:

```ts
const app = await NestFactory.create<NestExpressApplication>(AppModule, new ExpressAdapter());
```

`NestFactory.create<T extends INestApplication>` is declared to return `Promise<T>`, so nothing at runtime checks that `T` matches the adapter. `NestExpressApplication`, `NestFastifyApplication` (from `@nestjs/platform-fastify`) and `NestNodeApplication` (from `@nestjs/platform-node`) only add the adapter's own methods to the type, such as `useStaticAssets`, `register` or `inject`.

---

## What Happens in create, init and listen

### The Timeline, Run for Real

The fixture is a deliberately chatty module. The `console.log` calls are mine, to show when your code runs:

```ts
// fixtures.ts
import { Controller, Get, Injectable, Module, OnApplicationBootstrap, OnModuleInit } from '@nestjs/common';

@Injectable()
export class GreetingService implements OnModuleInit, OnApplicationBootstrap {
  constructor() { console.log('  [app] GreetingService constructor'); }
  onModuleInit() { console.log('  [app] GreetingService onModuleInit'); }
  onApplicationBootstrap() { console.log('  [app] GreetingService onApplicationBootstrap'); }
  hello() { return 'hello'; }
}

@Controller()
export class HealthController {
  constructor(private readonly greeting: GreetingService) { console.log('  [app] HealthController constructor'); }
  @Get('health') health() { return { status: 'ok', greeting: this.greeting.hello() }; }
  @Get('ping') ping() { return 'pong'; }
}

@Module({ controllers: [HealthController], providers: [GreetingService] })
export class AppModule {}
```

```ts
// timeline.ts, run as ESM so top-level await works
import { NestFactory } from '@nestjs/core';
import { AppModule } from './fixtures.js';

console.log('>>> before NestFactory.create');
const app = await NestFactory.create(AppModule);
console.log('>>> after create (nothing has listened, init() not called yet)');
await app.init();
console.log('>>> after init() (routes registered, hooks done, still no port)');
const server = await app.listen(0);
console.log('>>> after listen(0): address =', JSON.stringify(server.address()));
console.log('>>> getUrl() =', await app.getUrl());
await app.close();
console.log('>>> after close()');
```

Real output (colors stripped, ids kept):

```text
>>> before NestFactory.create
[Nest] 54111  - 11/20/2026, 12:08:04 PM     LOG [NestFactory] Starting Nest application...
  [app] GreetingService constructor
  [app] HealthController constructor
[Nest] 54111  - 11/20/2026, 12:08:04 PM     LOG [InstanceLoader] AppModule dependencies initialized +4ms
>>> after create (nothing has listened, init() not called yet)
[Nest] 54111  - 11/20/2026, 12:08:04 PM     LOG [RoutesResolver] HealthController {/}: +2ms
[Nest] 54111  - 11/20/2026, 12:08:04 PM     LOG [RouterExplorer] Mapped {/health, GET} route +1ms
[Nest] 54111  - 11/20/2026, 12:08:04 PM     LOG [RouterExplorer] Mapped {/ping, GET} route +0ms
  [app] GreetingService onModuleInit
  [app] GreetingService onApplicationBootstrap
[Nest] 54111  - 11/20/2026, 12:08:04 PM     LOG [NestApplication] Nest application successfully started +0ms
>>> after init() (routes registered, hooks done, still no port)
>>> after listen(0): address = {"address":"::","family":"IPv6","port":58531}
>>> getUrl() = http://[::1]:58531
>>> after close()
```

Three things to take from it:

- **Constructors run in `create`.** Both `[app] ... constructor` lines come before `>>> after create`. A provider whose constructor opens a connection does it at `create`, before any route exists.
- **Routes and hooks belong to `init`.** `RoutesResolver` and `RouterExplorer` lines, `onModuleInit` and `onApplicationBootstrap` all appear after `>>> after create`. The routes are mapped before `onModuleInit` runs. The hook ordering details, and what changed in v12, are 2.8.
- **`successfully started` is logged at the end of `init`, not by `listen`.** In this version `listen` prints nothing of its own. If you remember a "successfully started" line appearing when the port opened, that was older behavior; here the line means "ready", not "bound".

### Reading the Log Lines

| Line | Logged by | Meaning |
|---|---|---|
| `[NestFactory] Starting Nest application...` | `NestFactoryStatic.initialize` | The scan is about to start. First line of every run. |
| `[InstanceLoader] AppModule dependencies initialized +4ms` | `InstanceLoader.createInstances` | One line per module, after all of that module's providers, injectables and controllers exist. Not printed for Nest's internal core module. |
| `[RoutesResolver] HealthController {/}:` | `RoutesResolver.registerRouters` | A controller and its base path. With a global prefix it reads `{/api}:`. |
| `[RouterExplorer] Mapped {/health, GET} route` | `RouterExplorer` | One line per handler, with the final path as registered. |
| `[NestApplication] Nest application successfully started` | `NestApplication.init` | The end of `init`. |

The `+4ms` suffix comes from the logger's `timestamp` option: milliseconds since the previous log line.

### Inside NestFactory.create

From `@nestjs/core/nest-factory.js` (`NestFactoryStatic.create` and `initialize`), in order:

1. **Choose the adapter.** If the second argument has a `patch` method it is treated as an HTTP server or adapter. Otherwise `createHttpAdapter()` dynamically imports `@nestjs/platform-express` and builds an `ExpressAdapter`. If that package is missing, `helpers/load-adapter.js` logs an error and calls `process.exit(1)`. Real output on a project with only `@nestjs/common` and `@nestjs/core` installed (exit code 1):

   ```text
   [Nest] <pid> - <time> ERROR [PackageLoader] No driver (HTTP) has been selected. In order to use the default driver, please, install the "@nestjs/platform-express" package ($ npm install @nestjs/platform-express).
   ```
2. **Build the shared objects.** `new ApplicationConfig()` holds global prefix, global pipes, guards, interceptors and filters. `new NestContainer(config, options)` holds modules.
3. **Apply the logger options.** `registerLoggerConfiguration` is where `logger`, `bufferLogs`, `autoFlushLogs` and `forceConsole` take effect. It runs before the first log line, which is why `logger: false` can silence even `Starting Nest application...`.
4. **Scan** (`DependenciesScanner.scan` in `scanner.js`). It registers Nest's core module, walks `imports` from the root module (`scanForModules`), then for every module reflects its imports, providers, controllers and exports (`scanModulesForDependencies`), and computes module distances. No provider is instantiated yet.
5. **Instantiate** (`InstanceLoader.createInstancesOfDependencies`). First `createPrototypes`, then `createInstances` for every module, concurrently: providers, then injectables (guards, pipes, interceptors, filters referenced by decorators), then controllers. A missing dependency throws here.
6. **`applyApplicationProviders`** wires `APP_GUARD`, `APP_PIPE` and the other global-enhancer tokens.
7. **Construct `NestApplication`.** Its constructor calls `registerHttpServer`, which asks the adapter to create the Node server (`initHttpServer`). The Express adapter builds `http.createServer` or, when `httpsOptions` is set, `https.createServer`. The server exists but is not listening.

Steps 3 to 6 run inside `ExceptionsZone.asyncRun`. If anything in there throws, the zone's `ExceptionHandler` logs it with the context `[ExceptionHandler]` and calls the teardown. The default teardown is `process.exit(1)`; with `abortOnError: false` it is `rethrow`, so `create()` rejects instead. See [abortOnError](#abortonerror) below.

### Inside init

`NestApplication.init()` in `nest-application.js`:

1. Return immediately if already initialized (idempotent; measured in the test section below).
2. Load the optional `@nestjs/websockets` and `@nestjs/microservices` modules if they are installed.
3. `applyOptions()`: if the `cors` option was set, call `enableCors`.
4. Register the security hook if one was requested, and let the adapter run its own `init`.
5. Register the body parser middleware unless `bodyParser: false`.
6. `registerModules()`: middleware (1.5), gateways and microservice clients.
7. `registerRouter()`: `RoutesResolver.resolve` walks every controller and registers every route on the adapter. This is when the `Mapped {..} route` lines print, and when the route conflict options apply.
8. `callInitHook()`, then `registerRouterHooks()` (the not-found handler and the exception handler), then `callBootstrapHook()`.
9. Mark initialized, log `Nest application successfully started`.
10. In a `finally`: flush buffered logs if `autoFlushLogs` is on, even when `init` failed.

Step 3 is why CORS and prefix timing matter: they must be configured before this method registers routes. See [Pitfalls](#common-pitfalls).

### Inside listen

`NestApplication.listen(port, ...args)`:

1. Throws in preview mode (`Calling the "listen" in the preview mode is not supported.`, measured).
2. Calls `init()` if it has not run. This is why `await app.listen(...)` alone is enough for production.
3. Wraps the adapter's `listen` in a promise. A one-time `error` handler on the server logs the error with `[NestApplication]` and rejects.
4. Flushes buffered logs, then once the server has an address, resolves with the Node `http.Server`.

### Why Tests Call init and Never listen

`Test.createTestingModule(...).compile()` runs the create half: it builds the container and instantiates providers, but there is no application. `moduleRef.createNestApplication()` creates the `NestApplication`. Without `init()` its routes do not exist. I ran this in Vitest, with `supertest`:

```text
--- compile() ---
  [app] GreetingService constructor
  [app] HealthController constructor
--- compile() returned ---
  [app] GreetingService constructor
  [app] HealthController constructor
without init(): 404 {}
--- createNestApplication + init (default logger) ---
  [app] GreetingService constructor
  [app] HealthController constructor
  [app] GreetingService onModuleInit
  [app] GreetingService onApplicationBootstrap
with init(): 200 {"status":"ok","greeting":"hello"}
[Nest] <pid> - <time> ERROR [NestApplication] app.listen() needs to be called before calling app.getUrl()
isListening via getUrl(): NOT listening (app.listen() needs to be called before calling app.getUrl())
init() twice returns same app: true
```

- `supertest` was given `app.getHttpServer()` and returned `200` although nothing called `listen`, so `init()` is all the test needed. (From my knowledge of `supertest`, it binds its own ephemeral port when handed an unbound server; not read from its source.) Calling `listen` in tests only adds ports to clean up.
- The testing module replaces the logger with a `TestingLogger` (`@nestjs/testing/services/testing-logger.service.js`) that swallows `log`, `warn`, `debug` and `verbose` and prints only errors. That is why the run above shows no startup lines except the error.
- The second `compile()` in the output is a fresh test: each test builds its own container.

The testing module deep dive is Phase 6. One practical point from the official docs is worth knowing now: without an adapter argument, `createNestApplication()` creates an Express app, so tests do not exercise the adapter your app uses unless you pass it, for example `createNestApplication(new NodeAdapter())` (see [HTTP adapters](https://docs.nestjs.com/http/performance.md)).

---

## listen, Hosts and URLs

### Port and Host

```ts
await app.listen(process.env.PORT ?? 3000);           // port only
await app.listen(3000, '0.0.0.0');                    // port and host
await app.listen(3000, () => console.log('up'));      // optional callback (not needed with await)
```

The environment is a string, so `process.env.PORT ?? 3000` passes `string | number`, which `INestApplication.listen(port: number | string, ...)` accepts. In the exercise `startApp` converts with `Number(...)` so that tests can read the value back. `listen(0)` asks the OS for a free port and is what every test should use.

Fastify's `listen` has more overloads (an options object, a backlog). The `FastifyAdapter` also rejects an invalid port with a `RangeError` carrying `code: 'ERR_SOCKET_BAD_PORT'` (read from `fastify-adapter.js`, not run).

### Default Hosts, Measured

When you pass no host, the answer depends on the adapter. I called `listen(0)` and then made real requests to three addresses:

| Adapter | `server.address()` after `listen(0)` | `getUrl()` | `127.0.0.1` | `[::1]` | `localhost` |
|---|---|---|---|---|---|
| Express | `{"address":"::","family":"IPv6"}` | `http://[::1]:PORT` | 200 | 200 | 200 |
| Fastify | `{"address":"::1","family":"IPv6"}` | `http://[::1]:PORT` | 200 | 200 | 200 |
| Node (`NodeAdapter`) | `{"address":"::","family":"IPv6"}` | `http://[::1]:PORT` | 200 | 200 | 200 |

The same three with `listen(0, '0.0.0.0')`:

| Adapter | `server.address()` | `getUrl()` | `127.0.0.1` | `[::1]` | `localhost` |
|---|---|---|---|---|---|
| Express | `{"address":"0.0.0.0","family":"IPv4"}` | `http://127.0.0.1:PORT` | 200 | refused (`ECONNREFUSED ::1`) | 200 |
| Fastify | same | same | 200 | refused | 200 |
| Node | same | same | 200 | refused | 200 |

What this shows and does not show:

- Express and the Node adapter bind the IPv6 wildcard `::`, which on this macOS machine also accepts IPv4. Fastify reports the loopback address `::1`. On Linux the wildcard's dual-stack behavior depends on the kernel setting, which I did not test (Not verified).
- Fastify's server also answered on `127.0.0.1` although `address()` reports `::1`. I did not read why (Not verified), so do not infer "reachable from outside" from it. Its default is a loopback address.
- `getUrl()` rewrites the wildcard for you: `0.0.0.0` becomes `127.0.0.1`, and `::` becomes `[::1]`. The URL is for you to call yourself, not a statement about what the server accepts from other machines.

### Why 0.0.0.0 Matters in a Container

A server bound to a loopback address accepts connections only from inside its own network namespace. A container has its own namespace, so a published port forwards to the container's non-loopback interface, and a loopback-bound server never sees it.

I tested this with Docker 29 (Docker Desktop). No Node image was present locally and I did not pull one, so the server was a plain `python -m http.server` from the local `python:3.12-slim` image. The behavior under test is the bind address, not the language:

```text
server bound to 127.0.0.1 inside the container, published port 55000 -> curl from the host: http_code=000 curl_exit=52
server bound to 0.0.0.0 inside the container, published port 55001 -> curl from the host: http_code=200 curl_exit=0
```

`curl` exit 52 is "empty reply from server": the port mapping accepted the connection and nothing answered behind it. A Nest app inside an actual container was not tested here (Not verified). The practical rule follows: bind `0.0.0.0` explicitly in anything that runs in a container, rather than relying on an adapter default that differs between adapters. The exercise's `startApp` does exactly this and tests it.

### What listen and getUrl Return

- `listen` resolves with the underlying Node `http.Server` (or `https.Server`). `server.address()` gives `{ address, family, port }`.
- `getUrl()` returns a `Promise<string>`. Called before `listen` completes, it does two things at once: it logs an error and it rejects with a plain string, not an `Error`:

  ```text
  [Nest] <pid> - <time> ERROR [NestApplication] app.listen() needs to be called before calling app.getUrl()
  getUrl rejected with: app.listen() needs to be called before calling app.getUrl()
  ```

  The cause in my run was `app.listen(0)` without `await`. A moment later `getUrl()` worked and returned `http://[::1]:59559`.
- With `httpsOptions` the protocol comes from the server: `getUrl()` returned `https://127.0.0.1:51048` in my run. `formatAddress` decides `https` by checking whether the server is a TLS server.

### close and the Shutdown Order

`app.close()` (`NestApplicationContext.close`) runs these in order: `prepareClose` (the adapter's `beforeClose`), `callDestroyHook` (`onModuleDestroy`), `callBeforeShutdownHook` (`beforeApplicationShutdown`), `dispose` (stop the HTTP server, microservices and sockets), then `callShutdownHook` (`onApplicationShutdown`). Wiring OS signals to `close()` is `enableShutdownHooks()`, covered with the hooks in 2.8.

The part that surprises people is how long `close()` takes. I started one slow request (1.5 s), called `close()` while it was in flight, and measured. The client was Node's built-in `fetch`, which keeps idle connections open:

| Adapter and option | `close()` took | The in-flight request | A new request while closing |
|---|---|---|---|
| Express, default | about 4300 ms | `200 finished` | refused (`ECONNREFUSED`) |
| Express, `forceCloseConnections: true` | about 100 ms | killed (`other side closed`) | refused |
| Express, `return503OnClosing: true` | about 4300 ms | `200 finished` | refused |
| Fastify, default | about 71300 ms | `200 finished` | refused |
| Fastify, `forceCloseConnections: true` | about 100 ms | killed (`other side closed`) | refused |
| Fastify, `return503OnClosing: true` | about 71300 ms | `200 finished` | refused |

What holds `close()` open is the idle keep-alive connection the client leaves behind after the response. The server's own `keepAliveTimeout` differs: I read `5000 ms` on Express and `72000 ms` on Fastify (also `requestTimeout` 300000 ms vs 0, and `headersTimeout` 60000 ms for both). The measured waits track those numbers, and shortening the timeout confirms it:

```text
express: with keepAliveTimeout=1000 close() took ~1300 ms (in-flight said: finished)
fastify: with keepAliveTimeout=1000 close() took ~1300 ms (in-flight said: finished)
```

The ~1300 ms is just the 1.5 s request finishing. So in a rolling deploy on Fastify with default settings and keep-alive clients, `close()` can take over a minute unless you shorten `keepAliveTimeout`, set `forceCloseConnections`, or let the platform kill the process first. `forceCloseConnections` is quick but cuts in-flight requests. The official [Keep-Alive connections](https://docs.nestjs.com/faq/keep-alive-connections.md) page recommends it mainly for development with `--watch`, and notes that on Fastify the option needs Nest v12.1 or later. The exact interplay between the client's keep-alive logic and the server timeout (the client dropped idle sockets about a second before the server timeout in these runs) I did not trace in the client source (Not verified).

---

## Global Prefix and CORS

### Global Prefix with Exclusions

```ts
app.setGlobalPrefix('api', { exclude: ['health'] });
// or with a method: { exclude: [{ path: 'ping', method: RequestMethod.GET }] }
```

I ran both forms on Express and Fastify with `/health` and `/ping` routes. The behavior is the same on both:

```text
--- global prefix "api", exclude health ---
GET /health      -> 200 {"status":"ok"}
GET /api/health  -> 404 {"message":"Cannot GET /api/health","error":"Not Found","statusCode":404}
GET /ping        -> 404 ...
GET /api/ping    -> 200 pong
--- exclude with { path, method } ---
GET /ping        -> 200 pong
GET /v1/ping     -> 404 {"message":"Cannot GET /v1/ping","error":"Not Found","statusCode":404}
GET /v1/health   -> 200 {"status":"ok"}
GET /health      -> 404 ...
```

An excluded route lives only at its original path; it is not served at both. The startup log shows it too. With `setGlobalPrefix('api', { exclude: ['health'] })` on the exercise app:

```text
[RoutesResolver] HealthController {/api}:
[RouterExplorer] Mapped {/health, GET} route
[RouterExplorer] Mapped {/api/version, GET} route
```

One difference between adapters shows up for requests **outside** the prefix. On Express the unmatched `GET /ping` got Express's own HTML 404 page (`<!DOCTYPE html> ... <title>Error</title>`), not Nest's JSON. On Fastify it got Nest's `{"message":"Cannot GET /ping","error":"Not Found","statusCode":404}`. `RoutesResolver.registerNotFoundHandler` passes the prefix to the adapter when it registers Nest's not-found handler, which is consistent with this. I did not read how each adapter treats paths outside the prefix (Not verified). Clients and monitoring that parse error bodies will see two shapes on Express.

Calling `setGlobalPrefix` after `init()` does nothing for existing routes. I ran it:

```text
setGlobalPrefix AFTER init(): GET /health -> 200 | GET /api/health -> 404
```

The routes had already been registered at their old paths. Set the prefix before `init` or `listen`. URI versioning (`enableVersioning`) stacks on top of the prefix and is 3.5.

### CORS: the cors Option and enableCors

Two ways to turn CORS on:

```ts
const app = await NestFactory.create(AppModule, { cors: true });          // or { origin: '...', credentials: true }
// or
const app = await NestFactory.create(AppModule);
app.enableCors();                                                         // same options type
```

From `nest-application.js`: the `cors` option is applied inside `init()` (`applyOptions`). `enableCors` goes straight to the adapter. On Express (`express-adapter.js`) it is `this.use(cors(options))`, a normal middleware registration, and on Fastify it registers `@fastify/cors`.

I ran four setups on both adapters and sent a real request with an `Origin` header (rows show `Access-Control-Allow-Origin`):

| Setup | Express `GET /health` | Fastify `GET /health` |
|---|---|---|
| nothing configured | no CORS header | no CORS header |
| `cors: true` | `*` | `*` |
| `cors: { origin: 'https://app.example.com', credentials: true }` | that origin, plus `Allow-Credentials: true` and `Vary: Origin` | that origin, plus `Allow-Credentials: true` |
| `app.enableCors()` before `listen` | `*` | `*` |
| `app.enableCors()` **after** `init()` | **no header** | `*` |

The last row is a trap. After `init()` Express has already registered the routes, so a CORS middleware added afterwards sits behind them and never runs. Nothing warns you. On Fastify the same call worked in my run. Configure CORS before `init`, which `cors` in the options guarantees.

A configured origin string is sent back for **any** request origin. A request from `https://evil.example.com` still got `Access-Control-Allow-Origin: https://app.example.com` on both adapters. The browser, not the server, rejects the mismatch. For per-request decisions pass an origin function in the options, which the `cors` option type allows (`CorsOptionsDelegate`).

### Preflight Requests

A browser sends `OPTIONS` with `Access-Control-Request-Method` before a non-simple request. I sent exactly that to `/echo`, a POST route:

```text
no CORS configured:   OPTIONS /echo -> 404 {"message":"Cannot OPTIONS /echo","error":"Not Found","statusCode":404}
cors: true (Express): 204   [access-control-allow-origin=*; access-control-allow-methods=GET,HEAD,PUT,PATCH,POST,DELETE; vary=Access-Control-Request-Headers]
cors: true (Fastify): 204   [access-control-allow-origin=*; access-control-allow-methods=GET,HEAD,POST; vary=Access-Control-Request-Headers]
```

Without CORS, the preflight lands on the not-found handler, so the browser blocks the real request. With CORS the preflight is answered by the middleware with `204` and never reaches your controller.

The **default allowed methods differ between adapters**: Express advertises `GET,HEAD,PUT,PATCH,POST,DELETE`, Fastify only `GET,HEAD,POST`. A preflight asking for `DELETE` would be refused on Fastify with default CORS options. I did not test that with a browser (Not verified), but the header values above are measured. Set `methods` explicitly if you rely on `PUT`, `PATCH` or `DELETE`.

---

## Body Parsing and Raw Body

The adapter registers JSON and URL-encoded body parsers during `init()` (step 5 above). Two options change that:

```text
POST /echo default            -> 201 {"body":{"hello":"world"},"rawBodyIsBuffer":false,"rawBodyLength":null}      (Express and Fastify)
POST /echo bodyParser: false  -> Express: {"body":null,...}     Fastify: {"body":{"hello":"world"},...}
POST /echo rawBody: true      -> 201 {"body":{"hello":"world"},"rawBodyIsBuffer":true,"rawBodyLength":17}        (both)
```

- `bodyParser: false` removes Nest's parser on Express, so you register your own with `app.useBodyParser(...)`. On Fastify the body was still parsed in my run, because Fastify has built-in JSON parsing that the option does not turn off. If you need to disable it on Fastify you have to do it through Fastify (Not verified how).
- `rawBody: true` additionally keeps the exact bytes as `req.rawBody` (a `Buffer`, 17 bytes for `{"hello":"world"}`). Webhook signature verification needs this, because re-serializing the parsed JSON changes the bytes. See the official [Raw body](https://docs.nestjs.com/faq/raw-body.md) page and 3.7.

---

## Other Setup Calls Before listen

`INestApplication` (read from `nest-application.interface.d.ts` in v12.5.1) also has these. They are all configuration on the `ApplicationConfig`, so they belong before `init`, and each has its own topic:

| Call | Topic |
|---|---|
| `useGlobalPipes`, `useGlobalGuards`, `useGlobalInterceptors`, `useGlobalFilters` | 1.6 to 1.9. Note the DI limitation and the `APP_*` token alternative in 1.7. |
| `enableVersioning` | 3.5 |
| `use(middleware)` | 1.5 |
| `enableShutdownHooks` | 2.8 |
| `useWebSocketAdapter` | 8.1 |
| `connectMicroservice`, `startAllMicroservices` | 9.1 |
| `enableCsrfProtection`, `useSecurityHeaders` | 5.3. The source throws if they are called after `init`: `app.useSecurityHeaders() must be called before app.init() / app.listen().` (read from `nest-application.js`, not run). |
| `useStaticAssets`, `setBaseViewsDir`, `setViewEngine` | 3.7, adapter-specific |

---

## NestApplicationOptions

### Every Option in the Interface

Read from `nest-application-options.interface.d.ts` and `nest-application-context-options.interface.d.ts` (v12.5.1). Options marked "run" were exercised in this note.

| Option | Type and default | What it does |
|---|---|---|
| `logger` | `LoggerService`, `LogLevel[]` or `false` | Which logger Nest uses. An array means "these levels". `false` silences Nest. Run. |
| `bufferLogs` | `boolean`, false | Hold log lines until a logger is attached or the buffer is flushed. Run. |
| `autoFlushLogs` | `boolean`, true | Flush the buffer automatically when initialization finishes or fails. Run. |
| `forceConsole` | `boolean`, false | Make the default `ConsoleLogger` use `console.log` instead of `process.stdout.write`, for test runners that buffer console calls. |
| `abortOnError` | `boolean`, true | `false` makes `create()` reject instead of exiting the process. Run. |
| `cors` | `boolean`, options or a delegate | Calls `enableCors` during `init`. Run. |
| `bodyParser` | `boolean`, true | Register the adapter's body parsers. Run. |
| `rawBody` | `boolean`, false | Expose `req.rawBody`. Run. |
| `httpsOptions` | `{ key, cert, ... }` | Create an HTTPS server. Run. |
| `forceCloseConnections` | `boolean`, false | Destroy open connections on `close()`. Run. |
| `return503OnClosing` | `boolean`, false | Answer new requests with 503 while closing. Run. |
| `routeConflictPolicy` | `{ duplicate?, shadow? }`, each `'off' \| 'warn' \| 'error'`, default `'off'` | Detect overlapping routes at bootstrap. Run. |
| `routeResolutionStrategy` | `'declaration' \| 'specificity'`, default `'declaration'` | Registration order for order-sensitive adapters. Run. |
| `cookies` | `{ secret }` | Enables signed cookies. Cookies are 3.7. Not run. |
| `preview` | `boolean`, false | Build the graph without instantiating anything. Run. |
| `snapshot` | `boolean`, false | Build a serialized graph snapshot. Run. |
| `moduleIdGeneratorAlgorithm` | `'deep-hash' \| 'reference'`, default `'reference'` | How module ids are generated. Not run. |
| `instrument` | `{ instanceDecorator }` | A function applied to every created instance. Used by instrumentation tooling, see 11.2. Not run. |

### abortOnError

```ts
await NestFactory.create(BrokenModule);                       // default: abortOnError true
await NestFactory.create(BrokenModule, { abortOnError: false });
```

`BrokenModule` has a controller that needs `GreetingService` but no provider for it. Default behavior, real output, exit code 1:

```text
[Nest] <pid> - <time> ERROR [ExceptionHandler] UnknownDependenciesException [Error]: Nest can't resolve dependencies of the HealthController (?). Please make sure that the argument GreetingService at index [0] is available in the BrokenModule module.

Potential solutions:
- Is BrokenModule a valid NestJS module?
- If GreetingService is a provider, is it part of the current BrokenModule?
- If GreetingService is exported from a separate @Module, is that module imported within BrokenModule?
  @Module({
    imports: [ /* the Module containing GreetingService */ ]
  })

For more common dependency resolution issues, see: https://docs.nestjs.com/faq/common-errors
    at Injector.lookupComponentInParentModules (.../@nestjs/core/injector/injector.js:471:19) {
  type: 'HealthController',
  ...
```

With `abortOnError: false`, `create()` rejects with the `UnknownDependenciesException` and the process stays alive (exit code 0 after my script continued). Use `false` when you want to handle failure yourself, in tests that assert on bootstrap errors, or in a worker that should report and exit with its own code.

The default exit goes through `ExceptionsZone` (`DEFAULT_TEARDOWN = () => process.exit(1)`). `nest-factory.js` also has a `process.abort()` call in `handleInitializationError`, but in my runs the exit-code-1 path ran first, so the process did not abort with a core dump.

Note the consequence for your own `try/catch`: a dependency error in `create()` never reaches a `catch` unless `abortOnError` is `false`, because the process has already exited.

A circular provider dependency fails the same way, with a different exception:

```text
CircularDependencyException:
A circular dependency has been detected inside "A". Please, make sure that each side of a bidirectional relationships are decorated with "forwardRef()". Note that circular relationships between custom providers (e.g., factories) are not supported since functions cannot be called more than once.
```

The fixes belong to 2.5.

### Route Conflict Options

Two routes can match the same request. Order of registration decides, which is easy to get wrong. The fixture has `GET /users/:id` declared before `GET /users/me`, plus two controllers that both declare `GET /dup/same`. On Express:

| Setup | `GET /users/me` | `GET /dup/same` | Startup |
|---|---|---|---|
| default (`'off'`) | `id` (the parametric route shadows it) | `a` (first controller wins) | nothing logged |
| `{ duplicate: 'warn', shadow: 'warn' }` | `id` | `a` | two `WARN` lines (below) |
| `{ duplicate: 'error', shadow: 'warn' }` | n/a | n/a | bootstrap fails with `RouteConflictException: Conflicting HTTP routes detected:` |
| `routeResolutionStrategy: 'specificity'` | `me` | n/a | literal segments are registered before parametric ones |

```text
WARN [NestApplication] Route GET /users/me (UsersController#me) is shadowed by GET /users/:id (UsersController#byId). The first-registered route will match all matching requests on order-sensitive a...
WARN [NestApplication] Duplicate route: GET /dup/same is registered by both Dup1#a and Dup2#b.
```

(The first line is cut at 220 characters by my capture, not by Nest.)

On Fastify, with the policy off, the duplicate route made bootstrap fail anyway, with Fastify's own error: `FastifyError | Method 'GET' already declared for route '/dup/same'`. With `duplicate: 'error'`, Nest's `RouteConflictException` replaced it. The source says Fastify is not order-sensitive and picks the most specific route itself, so only the duplicate is a real conflict there. I did not request `/users/me` on Fastify (Not verified).

### forceCloseConnections and return503OnClosing

Covered with measurements in [close and the Shutdown Order](#close-and-the-shutdown-order). One more measurement for `return503OnClosing`: I held a slow request on one connection so `close()` stayed pending, opened a second keep-alive connection before `close()`, and sent a request on it during the close:

```text
express return503OnClosing=false: idle connection B, request sent during close -> still open after 600 ms; response head: "(none)"
express return503OnClosing=true:  idle connection B, request sent during close -> closed by server; response head: "HTTP/1.1 503 Service Unavailable"
fastify return503OnClosing=false: idle connection B, request sent during close -> closed by server; response head: "HTTP/1.1 503 Service Unavailable"
fastify return503OnClosing=true:  idle connection B, request sent during close -> closed by server; response head: "HTTP/1.1 503 Service Unavailable"
```

So on Express the option is what turns "request on an already-open connection hangs during shutdown" into "503 and the connection closes". Fastify answered 503 even with the option off. New connections after `close()` starts are refused at the TCP level on both.

### httpsOptions

```ts
const app = await NestFactory.create(AppModule, {
  httpsOptions: { key: readFileSync('key.pem'), cert: readFileSync('cert.pem') },
});
```

With a throwaway self-signed certificate: `getUrl(): https://127.0.0.1:51048 | server class: Server` and `GET over TLS -> 200 {"status":"ok"}`. Certificate verification was disabled in that test client, so it proves the server speaks TLS and not that a real certificate chain works. In most deployments TLS terminates at a proxy or load balancer and this option is not needed. Multiple servers on several ports are covered on the official [HTTPS and multiple servers](https://docs.nestjs.com/faq/multiple-servers.md) page.

### preview and snapshot

`preview: true` builds and validates the module graph without instantiating providers or controllers, which makes it useful for tooling:

```text
preview: true -> create() resolved, constructors above did NOT run (no [app] lines)
listen() in preview mode -> Calling the "listen" in the preview mode is not supported.
```

`snapshot: true` makes `create` record a serialized graph. It is what Nest's Devtools consume. I read it with `app.get(SerializedGraph).toJSON()`:

```text
snapshot: true -> nodes, edges, entrypoints, extras, status | nodes: 19 | edges: 3
```

(`SerializedGraph` is exported from `@nestjs/core`. 19 nodes and 3 edges is for the tiny fixture app; I did not investigate what each node is.) Devtools themselves are not part of this topic.

---

## The Logger at Bootstrap

Nest logs during `create`, before your code has a handle on `app`. That is why logger configuration is an option on `create` and not a method on `app`, and why `bufferLogs` exists.

### Levels, false and Custom Loggers

The levels, lowest to highest (`LOG_LEVELS` in `@nestjs/common`): `verbose`, `debug`, `log`, `warn`, `error`, `fatal`. Real runs on the fixture app (each in its own process):

```text
default                          six startup lines in the colored format shown earlier
logger: ['error', 'warn']        startup lines hidden; a later new Logger('Demo').warn(...) printed, .log(...) did not
logger: false                    nothing printed, not even new Logger('Demo').error('...')
NEST_LOG_LEVEL=warn              startup lines hidden (no logger option)
```

`NEST_LOG_LEVEL` is read the first time a level is checked (per the `ConsoleLoggerOptions` comments) and levels passed in code take precedence over it (per the official [Logging](https://docs.nestjs.com/application/logger.md) page). I only ran the `warn` value.

A custom `LoggerService` receives `(message, ...optionalParams)`, with the **context as the last parameter**:

```ts
class CapturingLogger implements LoggerService {
  lines: string[] = [];
  log(m: any, ...p: any[]) { this.lines.push(`log     ${JSON.stringify(m)} ctx=${JSON.stringify(p)}`); }
  error(m: any, ...p: any[]) { this.lines.push(`error   ${JSON.stringify(m)} ctx=${JSON.stringify(p)}`); }
  warn(m: any, ...p: any[]) { this.lines.push(`warn    ${JSON.stringify(m)} ctx=${JSON.stringify(p)}`); }
}
const app = await NestFactory.create(AppModule, { logger: new CapturingLogger() });
```

```text
log     "Starting Nest application..." ctx=["NestFactory"]
log     "AppModule dependencies initialized" ctx=["InstanceLoader"]
log     "HealthController {/}:" ctx=["RoutesResolver"]
log     "Mapped {/health, GET} route" ctx=["RouterExplorer"]
log     "Mapped {/ping, GET} route" ctx=["RouterExplorer"]
log     "Nest application successfully started" ctx=["NestApplication"]
```

The exercise's logging test captures lines in exactly this shape. A custom logger must not `extends Logger`: `Logger.overrideLogger` throws `Using the "extends Logger" instruction is not allowed in Nest v9. Please, use "extends ConsoleLogger" instead.` (read from `logger.service.js`). Dependency-injected loggers, `nestjs-pino` and redaction in production are 7.4.

### JSON Mode, Structured Params and Redaction

`ConsoleLogger` has a JSON mode, which is what a log shipper wants:

```ts
const app = await NestFactory.create(AppModule, { logger: new ConsoleLogger({ json: true }) });
new Logger('Demo').log('with params', { userId: 7, password: 'secret' });
```

```text
{"level":"log","pid":71819,"timestamp":1795156778135,"message":"AppModule dependencies initialized","context":"InstanceLoader"}
{"level":"log","pid":71819,"timestamp":1795156778138,"message":"with params","context":"Demo","params":{"userId":7,"password":"secret"}}
```

With `flattenParams: true` and `redact: ['password']`:

```text
{"level":"log","pid":72357,"timestamp":1795156778901,"message":"with params","context":"Demo","userId":7,"password":"[REDACTED]"}
```

`structuredParams` is on by default in v12 (it is one of the changes in the official migration guide). Plain objects after the message become metadata instead of a second log entry:

```text
structuredParams default:   [Nest] ... LOG [Demo] with params { userId: 7 }
structuredParams: false:    [Nest] ... LOG [Demo] with params
                            [Nest] ... LOG [Demo] Object(1) {
                              userId: 7
                            }
```

If you have code or log parsers written for the old behavior, this is the switch.

### bufferLogs, autoFlushLogs and useLogger

The problem: you want a custom logger, but `app.useLogger(x)` can only run after `create` returns, by which time Nest has already written `Starting Nest application...` and the `InstanceLoader` lines to the default logger.

```ts
const app = await NestFactory.create(AppModule);                 // no bufferLogs
app.useLogger(new ConsoleLogger({ json: true }));
```

Real output, first two lines default format, the rest JSON:

```text
[Nest] <pid> - <time> LOG [NestFactory] Starting Nest application...
[Nest] <pid> - <time> LOG [InstanceLoader] AppModule dependencies initialized +4ms
>>> create() returned; now app.useLogger(json logger)
{"level":"log","message":"HealthController {/}:","context":"RoutesResolver"}
{"level":"log","message":"Mapped {/health, GET} route","context":"RouterExplorer"}
{"level":"log","message":"Mapped {/ping, GET} route","context":"RouterExplorer"}
{"level":"log","message":"Nest application successfully started","context":"NestApplication"}
```

A log shipper now sees a mixed stream. With `bufferLogs: true` nothing is printed during `create`:

```text
>>> create() returned (startup lines are BUFFERED, nothing printed yet); now app.useLogger(json logger)
>>> useLogger() done
{"level":"log","message":"Starting Nest application...","context":"NestFactory"}
{"level":"log","message":"AppModule dependencies initialized","context":"InstanceLoader"}
{"level":"log","message":"HealthController {/}:","context":"RoutesResolver"}
{"level":"log","message":"Mapped {/health, GET} route","context":"RouterExplorer"}
{"level":"log","message":"Mapped {/ping, GET} route","context":"RouterExplorer"}
{"level":"log","message":"Nest application successfully started","context":"NestApplication"}
>>> init() done
```

All six lines come out in JSON, flushed during `init`. `registerLoggerConfiguration` calls `Logger.attachBuffer()` for `bufferLogs`, and `init` flushes in its `finally` block when `autoFlushLogs` is true (the default). The installed source says why: otherwise an app that is never `listen`ed, such as an e2e test or a serverless handler, would buffer forever. (The official Logging page describes the flush as happening in `listen`; in 12.5.1 the source also flushes at the end of `init`, and my run flushed before `listen`.)

With `autoFlushLogs: false` nothing is printed until you call `Logger.flush()` (or `app.flushLogs()`):

```text
>>> init() done but autoFlushLogs:false, nothing printed yet
[Nest] ... LOG [NestFactory] Starting Nest application...      (these six lines appeared only after Logger.flush())
```

One more combination matters for the exercise. `logger: false` together with `bufferLogs: true` still buffers, and a logger attached later receives all six lines (measured: 6 lines; without `bufferLogs`, a late logger got only the 4 lines written after `create`). So "silent by default" and "replay to a late logger" are not in conflict, and the solved exercise passes `logger: logger ?? false` and `bufferLogs` straight through.

`Logger.overrideLogger` sets a static, process-wide reference. A logger set in one test stays set in the next test in the same worker. The exercise's tests reset it in a `beforeEach`.

---

## Choosing the HTTP Adapter

### Switching Adapters

The adapter is an instance you pass as the second argument:

```ts
import { NestFactory } from '@nestjs/core';
import { ExpressAdapter, type NestExpressApplication } from '@nestjs/platform-express';
import { FastifyAdapter, type NestFastifyApplication } from '@nestjs/platform-fastify';
import { NodeAdapter } from '@nestjs/platform-node';

await NestFactory.create<NestExpressApplication>(AppModule);                                  // Express, the default
await NestFactory.create<NestExpressApplication>(AppModule, new ExpressAdapter());            // same, explicit
await NestFactory.create<NestFastifyApplication>(AppModule, new FastifyAdapter());
await NestFactory.create(AppModule, new NodeAdapter());                                       // @nestjs/platform-node
```

All of these compiled and ran in my lab on Nest 12.5.1, and the fixture's `/health` route returned the same JSON on each. Each adapter is a separate package you install; `@nestjs/platform-express` is the only one `create` will auto-load.

| Package | Adapter | Underneath |
|---|---|---|
| `@nestjs/platform-express` | `ExpressAdapter` (default) | Express 5 |
| `@nestjs/platform-fastify` | `FastifyAdapter` | Fastify |
| `@nestjs/platform-node` | `NodeAdapter` | `node:http` directly |

`@nestjs/platform-node` is new since the 2022 material. Its package description says "Run NestJS directly on node:http, with no framework underneath: the fastest NestJS HTTP adapter." The official [HTTP adapters](https://docs.nestjs.com/http/performance.md) page says that from v12.3 Nest recommends it, that Express is still the default when you pass no adapter, and that `NodeAdapter` will become the default in v13. Its benchmark claim there is "about 50% more requests per second on the `NodeAdapter` than on the `ExpressAdapter`, and about 5% more than on the `FastifyAdapter`" (`wrk`, 100 connections, Node 24). I did not run that benchmark (Not verified). Benchmarking is not this topic; adapter performance is 3.8 and 11.1.

### What Changes for the Developer

What `@Req()` and `@Res()` actually are, measured by logging the constructor names inside a handler:

```text
express  @Req() is IncomingMessage  @Res() is ServerResponse typeof app.register = undefined, typeof app.getInstance = function
fastify  @Req() is Request          @Res() is Reply          typeof app.register = function,  typeof app.getInstance = function
node     @Req() is NodeRequest      @Res() is NodeResponse   typeof app.register = undefined, typeof app.getInstance = function
```

(My reading is that Express augments the Node request and response prototypes, so its objects show Node's class names; Not verified.) Other differences from the runs above:

| Aspect | Express | Fastify | Node |
|---|---|---|---|
| Default listen host | `::` | `::1` | `::` |
| `keepAliveTimeout` | 5000 ms | 72000 ms | not measured |
| Default CORS methods | `GET,HEAD,PUT,PATCH,POST,DELETE` | `GET,HEAD,POST` | not measured |
| `bodyParser: false` | disables parsing | body still parsed | not measured |
| Adapter-only app methods | `useStaticAssets`, `setViewEngine`, ... | `register`, `inject`, `useStaticAssets`, ... | not measured |

Code written for one adapter's response object breaks on another. A handler using Express's `res.json(...)` on Fastify:

```ts
@Get('json')
json(@Res() res: { json: (b: unknown) => void }) { res.json({ ok: true }); }
```

```text
HTTP 500 {"statusCode":500,"message":"Internal server error"}
[Nest] ... ERROR [ExceptionsHandler] TypeError: res.json is not a function
```

The client sees only a generic 500, and the useful error is in the server log.

### Staying Adapter-agnostic

The cost of an adapter-specific handler is paid on migration day, so the habit is to keep the controller layer free of adapter types:

- Return values from handlers instead of using `@Res()`. If you need headers or status, use `@Header()`, `@HttpCode()` or `@Res({ passthrough: true })` (1.3).
- Put request-dependent logic behind decorators and pipes (1.10, 1.6) so only a few places touch `@Req()`.
- Keep adapter-specific calls in `main.ts` (`app.register(...)` for Fastify plugins, `useStaticAssets` for Express), not in services.
- Test on the adapter you deploy: pass it to `createNestApplication` as noted in [Why Tests Call init and Never listen](#why-tests-call-init-and-never-listen).

The exercise's `createApp` takes the adapter as an option for the same reason: the other eight tests are identical for both, and a switch changes nothing visible to them.

---

## main.ts Under ESM

A v12 project is ESM, so `main.ts` can use top-level `await`. The scaffold from Phase 0 looks like this:

```ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

The relative import ends in `.js` because of `nodenext` module resolution (Phase 0, 0.5).

What happens when bootstrap fails, measured on Node 24:

| Code | What happened | Exit code |
|---|---|---|
| `await bootstrap()` where `bootstrap` throws | Node prints the error and its stack | 1 |
| `bootstrap();` without `await`, which rejects | An unhandled rejection crashes the process | 1 |
| `bootstrap().catch(err => { console.error('fatal:', err.message); process.exit(1); })` | Prints `fatal: failed after listen` | 1 |
| `process.on('unhandledRejection', ...)` plus `void bootstrap()` | The handler logs it and the process keeps running | 0 (my script then exited deliberately) |

The last row is the dangerous one: an `unhandledRejection` handler can turn a failed bootstrap into a process that is alive and not serving. With top-level `await` there is nothing to forget to await.

Three kinds of failure behave differently:

- **Dependency and module errors in `create()`** exit with code 1 by themselves (default `abortOnError`), after logging with the context `[ExceptionHandler]`.
- **Port in use.** `listen` logs `[NestApplication] Error: listen EADDRINUSE: address already in use :::59535` and rejects with the Node error (`code: 'EADDRINUSE'`). Unhandled at top level, that is exit code 1 with a long stack. Caught, it is a normal exception: `caught: EADDRINUSE | listen EADDRINUSE: address already in use :::59540`.
- **Your own errors after `listen`** are ordinary JavaScript. Nest does not exit for them.

---

## Bootstrap in Tests vs Production

| | Production `main.ts` | Test |
|---|---|---|
| Build | `NestFactory.create(AppModule, adapter, options)` | `Test.createTestingModule({ imports: [AppModule] }).compile()`, then `moduleRef.createNestApplication(adapter?, options?)` |
| Ready | `listen` calls `init` | `await app.init()` |
| Requests | The network | `supertest` on `app.getHttpServer()` |
| Logger | Yours | `TestingLogger`: errors only |
| Overrides | None | `.overrideProvider(...)` and friends before `compile()` |
| Teardown | `close()` from a signal | `await app.close()` in `afterEach` |

Two rules that follow from the timeline. Test the same options you ship: in the exercise a single `createApp` is used by `main.ts` and by the tests, so the prefix and CORS you test are the ones that run. And always `close()` what you create. Open servers, buffered logs and the static logger all outlive a test that forgets. The testing module is Phase 6.

---

## Common Pitfalls

| Symptom | Real message or measured behavior | Cause and fix |
|---|---|---|
| Process exits at startup | `Nest can't resolve dependencies of the HealthController (?). Please make sure that the argument GreetingService at index [0] is available in the BrokenModule module.` then exit 1 | The module does not provide or import the dependency. See 1.2. |
| Startup fails with a cycle | `A circular dependency has been detected inside "A"...` | Two providers depend on each other. See 2.5. |
| `EADDRINUSE` | `ERROR [NestApplication] Error: listen EADDRINUSE: address already in use :::59535` | Another process owns the port. Use `listen(0)` in tests. |
| `ERR_SERVER_ALREADY_LISTEN` | `Listen method has been called more than once without closing.` (thrown by the second `listen`) | `listen` was called twice. |
| `getUrl()` rejects | `app.listen() needs to be called before calling app.getUrl()` (logged and rejected as a string) | `listen` was not awaited, or never called. |
| `appPromise.listen is not a function` | `typeof appPromise.listen = undefined \| it is a Promise` | `NestFactory.create(...)` was not awaited. |
| Container unreachable | `curl` exit 52 against a loopback-bound server behind a published port | Bind `0.0.0.0`. |
| `No driver (HTTP) has been selected...` | exit 1, message names `@nestjs/platform-express` | No adapter package installed. Install one and pass it. |
| `500 Internal server error`, log says `res.json is not a function` | Express-style `@Res()` code on Fastify | Return values, or write adapter-agnostic code. |
| Prefix not applied | `setGlobalPrefix` after `init`: `GET /health -> 200 \| GET /api/health -> 404` | Set it before `init` or `listen`. |
| CORS headers missing on Express only | `enableCors()` after `init`: no header; on Fastify it worked | Configure through the `cors` option or before `init`. |
| Mixed log formats in production | First two lines default format, rest JSON | Use `bufferLogs: true` with `useLogger`. |
| Logger from one test leaks into the next | `Logger.overrideLogger` is process-wide | Reset the logger in `beforeEach`. |
| Deploy hangs for a long time | `close()` took about 71300 ms on Fastify with a keep-alive client | Lower `keepAliveTimeout`, or use `forceCloseConnections`, accepting dropped requests. |
| A class is `undefined` when a decorator runs, or injection fails with an empty argument name | An import cycle between files, or a type-only import of a class | Phase 0 covers both with the real errors: [03 TypeScript Features Nest Is Built On](../phase_00_orientation/03_typescript_for_nest.md). |

---

## Interview Questions

**1. What does `NestFactory.create` do, in order?**
It picks an HTTP adapter (Express unless you pass one), builds the config and container, applies the logger options, scans the module graph from the root module, instantiates providers, injectables and controllers (constructors run here), applies global `APP_*` providers, and creates the `NestApplication` with a Node server that is not yet listening. No route exists and no port is bound when it returns.

**2. What is the difference between `create`, `init` and `listen`?**
`create` builds and instantiates the dependency graph. `init` registers middleware, body parsers and routes, runs `onModuleInit` and `onApplicationBootstrap`, installs the 404 and error handlers, and logs "Nest application successfully started". `listen` calls `init` if needed and then binds the port. In tests you call `init` and use `app.getHttpServer()` with `supertest`.

**3. When do constructors run versus `onModuleInit`?**
Constructors run during `create`. `onModuleInit` runs in `init`, after routes are registered, then `onApplicationBootstrap`. A provider that must not open connections until the app is actually starting belongs in the hook, not the constructor. The v12 ordering rules for hooks are 2.8.

**4. What is the object `create` returns?**
A `NestApplication` wrapped in two proxies. One wraps every method in an exception zone that logs errors and either exits the process or rethrows depending on `abortOnError`. The other forwards unknown properties to the HTTP adapter, which is why adapter-only methods like Fastify's `register` appear on the app. It is also an application context, so `app.get(Provider)` works.

**5. Why would a container be unreachable even though the app logs that it started?**
The server bound to a loopback address. Inside a container a published port forwards to a non-loopback interface, so a loopback-bound server never receives it. Bind `0.0.0.0` explicitly. The default host differs per adapter (Express `::`, Fastify a loopback address in my measurement), so do not rely on defaults.

**6. What is the difference between the `cors` option and `app.enableCors()`?**
The `cors` option is applied inside `init`, before routes are registered. `enableCors` registers immediately. Both end up in the adapter's CORS middleware. If you call `enableCors` after `init` on Express, the middleware sits behind the routes and never runs, silently. On Fastify the same call worked in my test.

**7. Why does a preflight request get a 404 without CORS configured?**
A preflight is an `OPTIONS` request, and no controller handles it. Without the CORS middleware it reaches Nest's not-found handler. With CORS, the middleware answers with 204 and the real request never reaches your code.

**8. What does `bufferLogs` solve?**
Nest logs during `create`, before you can call `app.useLogger`. Without buffering, the first lines go to the default logger and the rest to yours, so the log stream has mixed formats. With `bufferLogs: true` the early lines are held and replayed through the logger you attach, then flushed automatically at the end of `init` (`autoFlushLogs` defaults to true).

**9. What does `abortOnError: false` change?**
By default a failure in `create` is logged and the process exits with code 1, so your `catch` never runs. With `false`, `create()` rejects and you decide: assert on the error in a test, or log it and exit with your own code.

**10. What happens if you call `setGlobalPrefix` after `init`?**
Nothing, for routes already registered: they stay at their old paths. In my test `/health` kept working and `/api/health` was 404. The prefix feeds route registration, which happens in `init`.

**11. Why do e2e tests use `app.init()` and not `app.listen()`?**
`supertest` starts its own listener on the HTTP server for each request, so there is nothing to bind. `init` registers the routes. Calling `listen` adds a port to clean up and risks collisions between parallel test workers. If you do need a port, `listen(0)` picks a free one.

**12. How do you stay adapter-agnostic, and what breaks if you do not?**
Return values from handlers and avoid `@Res()` unless you use `passthrough`. Express-specific code such as `res.json` fails on Fastify with a generic 500 and a `TypeError` only in the log. Keep adapter-specific setup in `main.ts` and test on the adapter you deploy.

**13. How would you make a Nest process exit non-zero on any bootstrap failure?**
Use top-level `await` in `main.ts` (ESM): an exception exits with 1. If you keep a function, `.catch` it and call `process.exit(1)`. Do not leave a floating `bootstrap()` together with an `unhandledRejection` handler that swallows the error: the process stays alive and does not serve.

**14. What does `forceCloseConnections` trade off?**
Fast shutdown for dropped in-flight requests. In my measurement `close()` dropped from about 4300 ms (Express) or 71300 ms (Fastify) to about 100 ms with a keep-alive client, but the in-flight request was killed. `return503OnClosing` does the opposite: it answers new requests with 503 while existing ones finish.

**15. When would you use `createApplicationContext` instead of `create`?**
For code that needs the container and lifecycle hooks without an HTTP server: a migration script, a queue worker, a cron entry point. `init` runs before it resolves, and the object has no `listen` or `getHttpServer`.

---

## Check Yourself

- [ ] I can list what runs in `create`, what runs in `init`, and what `listen` adds, and say which of the three binds the port.
- [ ] I know constructors run in `create` and `onModuleInit` in `init`.
- [ ] I can explain why `getUrl()` returns `http://127.0.0.1:PORT` after `listen(PORT, '0.0.0.0')`.
- [ ] I can say why a container needs `0.0.0.0` and what Docker returned for a loopback-bound server.
- [ ] I can configure prefix, exclusions and CORS, and I know they must happen before `init`.
- [ ] I know the `cors` option and `enableCors` behave differently after `init` on Express.
- [ ] I can write the `logger`, `bufferLogs` and `useLogger` combination that gives one consistent log format.
- [ ] I can read the "Nest can't resolve dependencies" message and say what it names.
- [ ] I know what `abortOnError` changes and what exit code the default produces.
- [ ] I can swap the adapter and name three things that change for the developer.
- [ ] I can explain what `close()` waits for and which two options change that.
- [ ] I finished the [exercise](../../projects/phase_01_core_building_blocks/01_application_bootstrap/README.md) and `pnpm test` shows 27 passed.

---

## Further Reading

- [First steps](https://docs.nestjs.com/first-steps.md): the official introduction, including `NestFactory.create`.
- [Logging](https://docs.nestjs.com/application/logger.md): levels, JSON mode, structured params, redaction and buffering.
- [HTTP adapters](https://docs.nestjs.com/http/performance.md): Express, Fastify and the Node adapter, with the vendor benchmark.
- [HTTP adapter (FAQ)](https://docs.nestjs.com/faq/http-adapter.md): reaching the underlying server.
- [Global path prefix](https://docs.nestjs.com/faq/global-prefix.md).
- [Raw body](https://docs.nestjs.com/faq/raw-body.md).
- [Keep-Alive connections](https://docs.nestjs.com/faq/keep-alive-connections.md).
- [HTTPS and multiple servers](https://docs.nestjs.com/faq/multiple-servers.md).
- [Hybrid application](https://docs.nestjs.com/faq/hybrid-application.md): HTTP plus microservices in one process (9.1).
- [Request lifecycle](https://docs.nestjs.com/faq/request-lifecycle.md): what happens after bootstrap, per request (1.10).
- [Lifecycle events](https://docs.nestjs.com/fundamentals/lifecycle-events.md): hooks and shutdown (2.8).
- [Standalone apps](https://docs.nestjs.com/standalone-applications.md): `createApplicationContext` (10.4).
- [Common errors](https://docs.nestjs.com/faq/common-errors.md): the official page for dependency-resolution errors.
- [Migration guide](https://docs.nestjs.com/migration-guide.md): the v12 changes referenced here (logger params, route conflict options, shutdown behavior).
- Source worth reading in `@nestjs/core`: `nest-factory.js`, `nest-application.js`, `scanner.js`, `injector/instance-loader.js`, `router/routes-resolver.js`, `errors/exceptions-zone.js`.

# 04 The NestJS Philosophy and Landscape

> **Topic 0.4** | Priority: Core | Prerequisites: [01 The Node.js Runtime](01_nodejs_runtime.md) | Time: 2 hours | Exercise: none (a decision-making and orientation doc) | Next: [05 Tooling and Setup](05_tooling_and_setup.md)
>
> Facts here come from the sources named next to them: the official docs, GitHub release notes, the npm registry (queried 2026-11-20) and commands we ran. Where a number comes from the Nest team's own page and we did not reproduce it, that is stated.

## Table of Contents

- [Why This Doc Exists](#why-this-doc-exists)
- [What Nest Adds](#what-nest-adds)
  - [The Problem Nest Solves](#the-problem-nest-solves)
  - [The Three Ideas](#the-three-ideas)
  - [How Small Nest Can Be](#how-small-nest-can-be)
- [The Angular Lineage](#the-angular-lineage)
- [Platform Agnosticism](#platform-agnosticism)
  - [HTTP Adapters](#http-adapters)
  - [One Programming Model Across Transports](#one-programming-model-across-transports)
  - [What Agnosticism Costs](#what-agnosticism-costs)
- [Nest Compared With the Alternatives](#nest-compared-with-the-alternatives)
  - [The Comparison Table](#the-comparison-table)
  - [What the Nest Docs Recommend](#what-the-nest-docs-recommend)
  - [Performance, With Caveats](#performance-with-caveats)
  - [Nest and FastAPI](#nest-and-fastapi)
  - [Nest and Spring Boot](#nest-and-spring-boot)
- [Version History That Matters](#version-history-that-matters)
- [The First-Party Package Ecosystem](#the-first-party-package-ecosystem)
- [Using the Official Resources](#using-the-official-resources)
- [When Not to Use Nest](#when-not-to-use-nest)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why This Doc Exists

Before learning Nest's mechanics you should be able to say what Nest is for, what it is not, and what you give up by choosing it. Those are standard interview openers ("why Nest and not Express?") and they decide real projects. This doc is mostly orientation. The mechanics start in Phase 1.

---

## What Nest Adds

### The Problem Nest Solves

Express, Fastify and Hono answer one question: how do I route an HTTP request to a function? They deliberately say nothing about the rest. For a small service that is a feature. For a backend that will grow, a team has to invent answers to questions the framework left open:

- Where do services live, and how do routes get them? (A module system and dependency wiring.)
- How are cross-cutting concerns applied: authentication, validation, logging, error mapping?
- How are tests written without a running server, with dependencies swapped for fakes?
- How do background jobs, WebSockets and message consumers share code with the HTTP layer?

If every team answers these differently, every codebase is different and every new hire relearns it. Nest's answer is to **decide those things up front**. Its own docs put it this way: Fastify, Express and Hono "route requests to your handlers, and you choose or write what goes around them. Nest organizes the whole backend, with modules, dependency injection, guards, pipes and first-party packages."

### The Three Ideas

1. **Modules.** A module declares what it contains and what it shares with others. They draw boundaries (topic 1.2).
2. **Dependency injection.** You declare what a class needs in its constructor and the container supplies it. That makes classes easy to test and swap (topics 1.4 and 2.1).
3. **Decorators and metadata.** `@Controller`, `@Get`, `@Injectable` attach metadata to classes. The framework reads it at startup to build the route table and the dependency graph (topic 0.3).

Around them sits a fixed **request pipeline**: middleware, guards, interceptors, pipes, the handler, exception filters (Phase 1). Each stage has one job and a defined place.

### How Small Nest Can Be

Nest is not only for large systems. `nest new my-api --minimal` generates one file, which we ran. All of it, a service, a controller and a module, fits in `src/main.ts`:

```ts
import { Controller, Get, Injectable, Module } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';

@Injectable()
class AppService {
  getHello(): string { return 'Hello World!'; }
}

@Controller()
class AppController {
  constructor(private readonly appService: AppService) {}
  @Get()
  getHello(): string { return this.appService.getHello(); }
}

@Module({ controllers: [AppController], providers: [AppService] })
class AppModule {}

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

The generated `package.json` for it has only `build`, `start`, `start:dev` and `start:prod` scripts, and five runtime dependencies (`@nestjs/common`, `@nestjs/core`, `@nestjs/platform-express`, `reflect-metadata`, `rxjs`). The structure stays the same as it grows. You add files, you do not change the model.

---

## The Angular Lineage

The Nest README states it plainly: "The architecture is heavily inspired by Angular." Concretely:

| Angular idea | In Nest |
|---|---|
| `@NgModule` | `@Module` with `imports`, `providers`, `exports` |
| Injectable services and constructor injection | `@Injectable` providers, constructor injection |
| Decorators on classes | `@Controller`, `@Injectable`, `@Module` |
| Hierarchical injectors | Module scoping, plus injection scopes (topic 2.4) |
| `ng generate` schematics | `nest generate`, powered by schematics |
| RxJS | Interceptors work on RxJS `Observable`s, and `rxjs` is a required dependency |

There is direct evidence in the tooling. When we installed the CLI on a Node version below its floor, npm's warnings named four packages: `@nestjs/schematics` and three Angular ones, `@angular-devkit/core`, `@angular-devkit/schematics` and `@angular-devkit/schematics-cli` (see [05 Tooling and Setup](05_tooling_and_setup.md)). The Nest CLI's generators are built on Angular's schematics engine.

For a developer coming from Python this is the most unfamiliar part: a framework that builds an object graph at startup from class metadata, rather than calling functions per request. FastAPI's `Depends` is the closest relative, but it builds a call graph per request. The mapping is in the roadmap's [Appendix A](../../docs/01_nestjs_roadmap.md#appendix-a-fastapi-to-nestjs-concept-map).

---

## Platform Agnosticism

### HTTP Adapters

Nest does not implement HTTP. It runs on an **adapter**. The npm registry shows three official ones at version 12.5.1:

| Package | What its npm description says | Weekly downloads, 2026-11-12 to 11-18 |
|---|---|---|
| `@nestjs/platform-express` | Run NestJS on Express: Express middleware, file uploads through Multer, static assets | 17,448,036 |
| `@nestjs/platform-fastify` | Run NestJS on Fastify: Fastify's plugins, JSON schemas and serialization | 3,121,891 |
| `@nestjs/platform-node` | "Run NestJS directly on `node:http`, with no framework underneath: the fastest NestJS HTTP adapter." | 60,683 |

Express is the overwhelming default in practice, Fastify is the established alternative, and `platform-node` is new and barely adopted so far. The "fastest" in its description is the package's own claim. The scaffold's `AGENTS.md` repeats it, and the Nest docs' performance page backs it with numbers we discuss below.

### One Programming Model Across Transports

The official docs say the same building blocks work across "different types of applications (e.g., HTTP servers, microservices with different transport layers, and WebSockets)", plus GraphQL, and that the application context feature builds "any kind of Node.js application on top of Nest, including cron jobs and CLI apps".

In practice:

- A guard, pipe, interceptor or filter is written once and can run for HTTP, a Kafka consumer or a WebSocket message, because they receive an `ExecutionContext` that says which kind of call it is (topic 2.7).
- A service injected into an HTTP controller can be injected into a queue processor or a scheduled job unchanged.
- A standalone application context lets a script or worker reuse the same modules without starting a server (topic 10.4).

### What Agnosticism Costs

- **Leaky escape hatches.** Reaching for `@Req()` or `@Res()` gives you the underlying Express or Fastify object, and your code is tied to that adapter again. Topic 3.8 covers keeping code adapter-agnostic.
- **A lowest common denominator.** Features specific to one adapter (Fastify's JSON schema serialization, Express middleware) are available only if you opt into that adapter's specifics.
- **An extra layer.** Nest adds work per request on top of the adapter. See the performance numbers below.

---

## Nest Compared With the Alternatives

### The Comparison Table

Versions are from the npm, PyPI and Maven registries on 2026-11-20. The characteristics are the commonly accepted ones, and the Nest column is checked against Nest's own comparison page.

| | NestJS 12 | Express 5 | Fastify 5 | Hono 4 | FastAPI | Spring Boot |
|---|---|---|---|---|---|---|
| Version checked | 12.5.1 | 5.3.0 | 5.12.8 | 4.13.19 | 0.165.0 | spring-boot 4.2.0 |
| Language | TypeScript | JavaScript | JavaScript | TypeScript | Python | Java, Kotlin |
| Style | Opinionated framework | Minimal router | Fast, plugin-based | Minimal, Web Standards | Minimal framework with DI and validation | Opinionated framework |
| Dependency injection | Built-in container | None | Plugin encapsulation, no container | None | `Depends` (per-request call graph) | Built-in container |
| Structure imposed | Modules and a fixed pipeline | None | Plugins | None | Routers | Beans, layers |
| Validation | Pipes: class-validator, or any Standard Schema library | Add a library | JSON Schema, built in | Add a library | Pydantic, built in | Bean Validation |
| API docs | `@nestjs/swagger` | Add a library | `@fastify/swagger` | `@hono/zod-openapi` | Automatic from type hints | Add springdoc |
| Microservices | First-party transports | Add libraries | Add libraries | Add libraries | Add libraries | Spring ecosystem |
| Runs on edge runtimes | Not its target | Not its target | Not its target | **Yes, built for it** | No | No |
| Weekly npm downloads | 25.5M (`@nestjs/core`) | 207.4M | 24.0M | 114.5M | not npm | not npm |

Download counts measure usage of a package, and Nest packages are installed alongside Express or Fastify, so the figures are not comparable as market share. They do show that Express is still the base layer of most of the ecosystem and that Hono's adoption is large.

### What the Nest Docs Recommend

The official page "Nest vs Fastify, Express and Hono" is candid about when not to pick Nest. Its recommendations, summarized:

| Building | Page's suggestion |
|---|---|
| A backend that will grow: more modules, more developers, a database, background jobs | Nest |
| A large, long-lived system with many teams | Nest |
| A small API with auth, validation and a database | Nest or Fastify |
| Microservices over Kafka, RabbitMQ, NATS or gRPC | Nest |
| A service that will stay a few routes, such as a proxy or webhook receiver | Fastify or Hono |
| An API on Cloudflare Workers or another edge runtime | Hono |
| A Next.js frontend sharing route types with its API | Hono (its RPC client infers types) |
| An Express application that already works | Express, or move to Nest one route at a time |
| The highest request rate on routes that do almost nothing | Fastify |

The same page says Nest "doesn't replace Fastify or Express: they can be what it runs on."

### Performance, With Caveats

The Nest docs publish requests per second for `GET /` returning a constant, measured with `wrk -t4 -c100` on Node.js 24.20 (medians of 3 rounds):

| Server | Requests per second |
|---|---|
| Fastify | 57.1k |
| Nest on Node (`NodeAdapter`) | 55.6k |
| Hono on Node | 53.1k |
| Nest on Fastify | 52.6k |
| Express | 37.0k |
| Nest on Express | 37.0k |

These are the Nest team's numbers from their own docs, and **we did not reproduce them**. How to read them:

- Nest on the same adapter cost little here: Nest on Express equals plain Express, and Nest on Fastify is within about 8% of plain Fastify.
- The adapter matters more than Nest. Express is far behind Fastify in these tests.
- These routes do almost no work. The docs themselves say a route that queries a database "spends most of its time waiting for them", so these differences "won't decide the choice" for most applications.
- A benchmark by a vendor of one of the contenders is evidence, not proof. If performance is decisive for you, run the reproduction steps the docs link (PR 18063 in the Nest repo) on your hardware and with your real routes.

### Nest and FastAPI

You know FastAPI, so here is the real difference, not the surface one:

- **Both** give you validation, dependency injection, automatic OpenAPI and good testability.
- **FastAPI** is a thin layer over Starlette and Pydantic. Dependencies are functions resolved per request, validation comes from type hints, and there is almost no mandated structure. It is productive in an afternoon.
- **Nest** is a framework with a fixed architecture. Dependencies are long-lived instances in a container, validation is an explicit pipe, and OpenAPI needs decorators or the CLI plugin. It asks for more upfront and gives back consistency across a large team.
- **Typing story:** FastAPI's types are enforced at runtime by Pydantic. TypeScript types are erased at runtime, which is why Nest validation needs classes with decorators or schema libraries, and why interfaces cannot be injection tokens (topic 0.3).
- **Concurrency:** FastAPI async code runs on an event loop in one thread unless you use workers, so the same "do not block the loop" rules from [01 The Node.js Runtime](01_nodejs_runtime.md) apply. Python additionally has the GIL for CPU-bound threads.

Pick by team and problem, not by language preference. The roadmap's [Appendix A](../../docs/01_nestjs_roadmap.md#appendix-a-fastapi-to-nestjs-concept-map) maps each FastAPI concept to its Nest counterpart.

### Nest and Spring Boot

Nest is often called "Spring for Node", and the comparison is fair in spirit: both are opinionated, container-based, annotation or decorator driven, and aimed at long-lived enterprise backends. Differences that matter:

- Spring Boot runs on the JVM with real threads and compile-time types. Nest runs on one event loop thread and TypeScript types vanish at runtime.
- Spring has decades of ecosystem depth. Nest's ecosystem is younger and, as the next sections show, parts of it are still early.
- Startup and memory: JVM applications start slower and use more memory per process. Node processes are lighter. We did not measure either, so treat that as a general expectation, not a result.

---

## Version History That Matters

All dates are the `published_at` or tag dates of the GitHub releases, cross-checked with the npm registry's `time` field for `@nestjs/core`. The bullets are taken from the official release notes of each major.

| Version | Released | What mattered |
|---|---|---|
| **9.0.0** | 2022-07-08 | The version your 2022 code used. Added the REPL, durable providers, `ConfigurableModuleBuilder`, and a file validators pipe. Dropped all previously deprecated methods. |
| **10.0.0** | 2023-06-15 | Dropped Node 12 (Node 16 or newer required). Added async local storage support in interceptors, middleware that runs once for a matching route, named groups in routes, an `@Search` HTTP method decorator. Fixed middleware on versioned controllers. |
| **11.0.0** | 2025-01-16 | **Express 5 and Fastify 5** became the underlying versions, with a legacy route path converter to soften the break. Dropped Node 16 and 18 (Node 20 or newer required). Added a built-in JSON logger, `ParseDatePipe`, microservice transporter `status`, `unwrap` and `on` methods, and faster bootstrap through new module key factories. |
| **12.0.0** | 2026-08-27 | **ESM packages**, first-class **Standard Schema validation and serialization** (Zod, Valibot, ArkType) alongside class-validator, a rebuilt CLI with `nest upgrade`, and the `@nestjs/observe` SDK. Node 20.19+ or 22.12+ to run an app. CommonJS applications keep working through `require(esm)`. |

The previous research for this roadmap could not find the exact v12 release date. The GitHub release record answers it: `v12.0.0` was published 2026-08-27, matching the npm registry.

Two upgrade habits:

- Read the **migration guide** (`docs.nestjs.com/migration-guide`) for every major, and run `nest upgrade --dry-run` first. It applies the mechanical parts and prints a report.
- The Node floor rises with almost every major (12 to 16 in v10, 16/18 to 20 in v11, 20.19+/22.12+ in v12). Your runtime upgrade is part of the framework upgrade. See [01 The Node.js Runtime](01_nodejs_runtime.md).

---

## The First-Party Package Ecosystem

Nest has always shipped optional packages for common needs. The v12 era adds many more. We checked each of these on the npm registry on 2026-11-20. For the ones whose repositories we queried (`authentication`, `resilience`, `outbox`, `platform-node`, `jwt`), the source repositories are under the `nestjs` GitHub organization.

| Area | Package | Version on npm | Maturity signal |
|---|---|---|---|
| Authentication | `@nestjs/authentication` | 0.1.6 | Early |
| Authorization | `@nestjs/authorization` | 0.1.4 | Early |
| Authentication (established) | `@nestjs/jwt`, `@nestjs/passport` | 12.0.5, 12.0.2 | Established, versioned with Nest |
| Rate limiting | `@nestjs/throttler` | 6.8.0 | Established |
| Resilience (retries, timeouts, circuit breakers) | `@nestjs/resilience` | 0.0.3 | Very early |
| Idempotency keys | `@nestjs/idempotency` | 0.0.4 | Very early |
| Transactional outbox | `@nestjs/outbox` | 0.1.4 | Early |
| Webhooks | `@nestjs/webhooks` | 0.0.4 | Very early |
| Locks | `@nestjs/locks` | 0.0.6 | Very early |
| Durable workflows | `@nestjs/workflows` | 0.0.5 | Very early |
| Mail | `@nestjs/mail` | 0.0.2 | Very early |
| File storage | `@nestjs/storage` | 0.0.5 | Very early |
| Internationalization | `@nestjs/i18n` | 0.0.3 | Very early |
| Drizzle ORM integration | `@nestjs/drizzle` | 0.0.2 | Very early |
| AI | `@nestjs/ai` | 0.0.2 | Very early |
| MCP servers | `@nestjs/mcp` | 0.0.4 | Very early |
| Observability | `@nestjs/observe` | 0.3.27 | Early, and tied to a hosted product |

**The caveat.** Under semantic versioning, a `0.x` package has no stability promise: any minor version may break the API. Eleven of these are at `0.0.x`. They are listed in the official docs sidebar, so they are the direction the project is heading, and the Nest scaffold's own `AGENTS.md` tells coding agents to check them before adding another library. But "official" is not "mature".

How to treat them:

- **While learning**, follow the official docs for each phase and note when a topic has both an established and a new package (authentication is the clearest case: `@nestjs/jwt` plus `@nestjs/passport` versus `@nestjs/authentication`). Learn the established approach first, because that is what existing codebases use and interviewers ask about, then try the new one.
- **In production**, pin exact versions of anything `0.x`, read its changelog before upgrading, and prefer mature alternatives when a failure would be expensive.
- **The observability SDK is tied to a vendor.** InfoQ's coverage of Nest 12 quotes an APM vendor warning of "vendor lock-in at the framework level". That is one vendor's opinion, but the architectural point is real: the SDK is opt-in, and you can use OpenTelemetry instead (topic 11.2).
- The roadmap's later phases (5, 7, 9, 12) were written before this survey. They will be refreshed to cover the new packages when we reach them.

---

## Using the Official Resources

| Resource | What it is | Notes |
|---|---|---|
| `docs.nestjs.com` | The documentation | The unversioned site is the latest. Older versions live under `/v11` and similar. |
| `docs.nestjs.com/<page>.md` | A plain markdown version of each page | We fetched `/cli/overview.md` and `/faq/nest-vs-fastify-express-hono.md` this way. The versioned paths such as `/v11/migration-guide.md` returned the web app shell instead of markdown. |
| `docs.nestjs.com/llms.txt` | An index of every chapter with a one-line summary, for language models | HTTP 200, about 42 KB. It contains promotional text for a paid vendor product, so treat that part as marketing. |
| `docs.nestjs.com/llms-full.txt` | The full text of every chapter in one file | HTTP 200, about 3.1 MB. |
| API reference | Generated class and interface docs, linked from the docs sidebar | Use it for exact signatures. |
| `github.com/nestjs/nest/tree/master/sample` | 39 runnable example projects | See below. |
| GitHub releases of `nestjs/nest` | Per-version change lists, readable through the GitHub API | The primary source for "what changed in version X". |
| Official courses | Linked from the sidebar | Not reviewed here. |

The `sample/` folder, which we listed through the GitHub API, holds 39 projects numbered `01` to `39`. Useful ones for this roadmap:

| Sample | Roadmap topic |
|---|---|
| `01-cats-app` | Phase 1 (the canonical first example) |
| `25-dynamic-modules` | 2.3 |
| `18-context` | 10.4 |
| `19-auth-jwt` | 5.1 |
| `21-serializer` | 3.3 |
| `20-cache` | 4.5 |
| `26-queues`, `27-scheduling`, `30-event-emitter` | Phase 7 |
| `02-gateways`, `16-gateways-ws`, `28-sse` | Phase 8 |
| `12-graphql-schema-first`, `23-graphql-code-first` | Phase 8 |
| `03-microservices`, `04-grpc` | Phase 9 |
| `35-zod-validation`, `36-valibot-serializer` | 3.2 and 3.3 (Standard Schema) |
| `37-outbox`, `38-webhooks` | Phase 9 |
| `34-hmr-esm` | An ESM example |

Reading habits that pay off:

1. Read **Overview**, then **Fundamentals**, in order. Almost everything later assumes them.
2. Read a sample project next to its docs page. The sample shows the minimum that works.
3. Use the **FAQ** pages (Request lifecycle, Common errors, Version compatibility) when stuck. They are short and specific.
4. When docs and behavior disagree, read the framework source. It is plain TypeScript and the container code is small.
5. Check which Nest version a blog post or Stack Overflow answer targets. Anything before v11 may predate the Express 5 route syntax, and anything before v12 predates ESM and Standard Schema.

---

## When Not to Use Nest

Based on the official comparison page and the trade-offs above:

- **A service that stays a few routes** (a proxy, a webhook receiver). Nest's structure is overhead with nothing to organize.
- **Edge runtimes** such as Cloudflare Workers. Hono is built on Web Standards for them. Nest has a Cloudflare Workers FAQ page, but it is not Nest's home ground.
- **Hard cold-start budgets in serverless.** Nest builds its container at startup. It has lazy-loading modules to help (topic 2.6), and we did not measure the cold start.
- **Maximum raw throughput on trivial routes.** The Nest docs themselves point to plain Fastify here.
- **A team that dislikes decorators, classes or dependency injection.** The framework's value depends on adopting its structure. A functional codebase fights it.
- **A TypeScript-hostile or very small team** that benefits more from the least ceremony than from consistency.
- **Heavy compute services.** Nest does not change the single-threaded model ([01 The Node.js Runtime](01_nodejs_runtime.md)).

Nest earns its keep when the backend is expected to **grow in code size, team size, or number of integration points**. If you cannot say which of those three applies, the cost is probably not worth it yet. The docs also note you can move to Nest later, one route at a time, from an Express application.

---

## Common Pitfalls

- **Treating Nest as a performance upgrade.** It is a structure upgrade. In the Nest docs' own numbers, Nest on Express is close to plain Express (equal in one table, about 3% lower in another), and the adapter choice matters more.
- **Assuming "official" means "stable".** Eleven first-party packages are at `0.0.x`.
- **Following pre-v11 or pre-v12 tutorials** without checking the version. Routes, ESM and validation changed.
- **Leaning on `@Req()` and `@Res()`** and silently losing adapter independence.
- **Choosing Nest for a tiny service**, then fighting boilerplate.
- **Copying the scaffold's promotional or vendor-specific setup** (observability prompts, `AGENTS.md` product sections) without deciding whether you want it.
- **Comparing frameworks on a hello-world benchmark** when your service is database-bound.

---

## Interview Questions

**Q1. What does Nest give you that Express does not?**
A fixed architecture: modules for boundaries, dependency injection for wiring and testing, and a defined request pipeline (middleware, guards, interceptors, pipes, filters), plus first-party packages that share one programming model. Express gives routing and middleware and leaves everything else to the team.

**Q2. Is Nest a replacement for Express or Fastify?**
No. Nest runs on top of an HTTP adapter, which is Express by default, with official adapters for Fastify and for `node:http` directly. The Nest docs say it "doesn't replace Fastify or Express: they can be what it runs on."

**Q3. How does Nest relate to Angular?**
Its README says the architecture is heavily inspired by Angular: modules, injectable providers with constructor injection, decorators, generators built on Angular's schematics engine (the CLI's `@angular-devkit` dependencies), and RxJS in interceptors. It is a server-side framework with similar ideas, not shared code.

**Q4. What does "platform agnostic" mean in Nest, and where does it break down?**
The same guards, pipes, interceptors, filters and providers can serve HTTP (Express, Fastify, `node:http`), microservice transports, WebSockets, GraphQL and standalone applications. It breaks down when you use `@Req()`, `@Res()` or adapter-specific features, which tie the code to one adapter.

**Q5. When would you pick Fastify, Hono or Express over Nest?**
Fastify for a small, very high-throughput service. Hono for edge runtimes or Web Standards portability. Express for an existing application that works, with an optional gradual move to Nest. These match the recommendations on Nest's own comparison page.

**Q6. Does Nest slow an application down?**
A little, and less than the adapter choice matters. According to the Nest docs' benchmark (which we did not reproduce), Nest on Express matched plain Express and Nest on Fastify was within about 8% of plain Fastify, on routes that do nothing. For database-bound routes the difference is negligible. Measure your own workload if it matters.

**Q7. What changed between Nest 9 and Nest 12 that an upgrading team must plan for?**
The Node floor (16 in v10, 20 in v11, 20.19+/22.12+ in v12), Express 5 and Fastify 5 route matching in v11, ESM packages and the new CLI scaffold defaults in v12, Standard Schema as a second validation route, the removal of legacy APIs listed in the migration guide, and `nest upgrade --dry-run` to see what is automated.

**Q8. A package like `@nestjs/resilience` is official. Do you put it in production?**
Check its version first. It was `0.0.3` when we looked, so the API can change in any release. Pin the exact version, read its changelog, and consider a mature alternative if failure is costly. Official ownership is a good sign for direction, not a guarantee of stability.

**Q9. Nest versus FastAPI?**
Both provide validation, dependency injection, OpenAPI and testability. FastAPI is thin and per-request: dependencies are functions resolved on every call, and types are enforced at runtime by Pydantic. Nest is a fixed architecture of long-lived provider instances in a container, with validation as an explicit pipe because TypeScript types vanish at runtime. FastAPI is faster to start with. Nest imposes more structure, which pays off with many developers.

---

## Check Yourself

- [ ] I can state, in two sentences, the problem Nest solves and the three ideas it uses.
- [ ] I can say what Nest adds on top of an HTTP adapter and name the three official adapters.
- [ ] I can list at least four things Nest borrowed from Angular.
- [ ] I can describe one concrete way platform agnosticism helps and one way it leaks.
- [ ] I can give a defensible recommendation of Nest versus Express, Fastify, Hono, FastAPI and Spring Boot for a given project.
- [ ] I can say what changed in v9, v10, v11 and v12, and what each did to the Node version floor.
- [ ] I know which first-party packages are established and which are `0.x`, and how I would treat each.
- [ ] I know where to find the markdown docs, `llms.txt`, the sample projects and the release notes.
- [ ] I can name three situations where I would not choose Nest.

---

## Further Reading

- [Nest vs Fastify, Express and Hono (official)](https://docs.nestjs.com/faq/nest-vs-fastify-express-hono): the comparison and benchmark summarized above.
- [Platform agnosticism (official)](https://docs.nestjs.com/fundamentals/platform-agnosticism)
- [Nest README](https://github.com/nestjs/nest#readme): the "heavily inspired by Angular" statement.
- [Official documentation](https://docs.nestjs.com/) and its [llms.txt index](https://docs.nestjs.com/llms.txt)
- [Nest samples folder](https://github.com/nestjs/nest/tree/master/sample): 39 runnable projects.
- [NestJS v9.0.0 release notes](https://github.com/nestjs/nest/releases/tag/v9.0.0)
- [NestJS v10.0.0 release notes](https://github.com/nestjs/nest/releases/tag/v10.0.0)
- [NestJS v11.0.0 release notes](https://github.com/nestjs/nest/releases/tag/v11.0.0)
- [NestJS v12.0.0 release notes](https://github.com/nestjs/nest/releases/tag/v12.0.0)
- [Migration guide (official)](https://docs.nestjs.com/migration-guide)
- [Benchmark reproduction steps (nestjs/nest PR 18063)](https://github.com/nestjs/nest/pull/18063)
- [Semantic Versioning, section on 0.y.z](https://semver.org/#spec-item-4): why a `0.x` version carries no stability promise.
- [Hono](https://hono.dev/), [Fastify](https://fastify.dev/), [Express](https://expressjs.com/)
- [InfoQ: NestJS 12, ESM Packages, Standard Schema Validation and Native Observability](https://www.infoq.com/news/2026/10/nestjs-12-observability/)

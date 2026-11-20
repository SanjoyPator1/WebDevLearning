# NestJS Roadmap: Basics to Advanced

> Knowledge base doc 01. Target version: **NestJS 12** (12.x; `@nestjs/core` 12.5.1 on npm when researched).
> Last researched: 2026-11-20.
> Written for a senior backend engineer who already knows FastAPI, PostgreSQL and Docker. The goal is a deep understanding of how Nest works plus interview readiness.

## Table of Contents

- [How to Use This Roadmap](#how-to-use-this-roadmap)
  - [Conventions](#conventions)
  - [Repository Layout](#repository-layout)
  - [Exercise Workflow](#exercise-workflow)
  - [Focus Rule](#focus-rule)
  - [Target Stack](#target-stack)
  - [What Changed Since the 2022 Material](#what-changed-since-the-2022-material)
- [Roadmap at a Glance](#roadmap-at-a-glance)
- [Phase 0: Orientation and Prerequisites](#phase-0-orientation-and-prerequisites)
  - [0.1 The Node.js Runtime for Nest Developers](#01-the-nodejs-runtime-for-nest-developers)
  - [0.2 TypeScript Refresher](#02-typescript-refresher)
  - [0.3 TypeScript Features Nest Is Built On](#03-typescript-features-nest-is-built-on)
  - [0.4 The NestJS Philosophy and Landscape](#04-the-nestjs-philosophy-and-landscape)
  - [0.5 Tooling and Project Setup](#05-tooling-and-project-setup)
- [Phase 1: Core Building Blocks](#phase-1-core-building-blocks)
  - [1.1 Application Bootstrap](#11-application-bootstrap)
  - [1.2 Modules](#12-modules)
  - [1.3 Controllers and Routing](#13-controllers-and-routing)
  - [1.4 Providers and Services](#14-providers-and-services)
  - [1.5 Middleware](#15-middleware)
  - [1.6 Pipes](#16-pipes)
  - [1.7 Guards](#17-guards)
  - [1.8 Interceptors](#18-interceptors)
  - [1.9 Exception Filters](#19-exception-filters)
  - [1.10 Custom Decorators and the Request Lifecycle](#110-custom-decorators-and-the-request-lifecycle)
- [Phase 2: Under the Hood With DI and Fundamentals](#phase-2-under-the-hood-with-di-and-fundamentals)
  - [2.1 The IoC Container and Dependency Injection](#21-the-ioc-container-and-dependency-injection)
  - [2.2 Custom and Async Providers](#22-custom-and-async-providers)
  - [2.3 Dynamic Modules](#23-dynamic-modules)
  - [2.4 Injection Scopes](#24-injection-scopes)
  - [2.5 Circular Dependencies](#25-circular-dependencies)
  - [2.6 Module Reference and Lazy Loading](#26-module-reference-and-lazy-loading)
  - [2.7 Execution Context and Metadata](#27-execution-context-and-metadata)
  - [2.8 Lifecycle Events and Graceful Shutdown](#28-lifecycle-events-and-graceful-shutdown)
  - [2.9 Discovery Service and Metaprogramming](#29-discovery-service-and-metaprogramming)
- [Phase 3: Production REST APIs](#phase-3-production-rest-apis)
  - [3.1 Configuration](#31-configuration)
  - [3.2 Validation](#32-validation)
  - [3.3 Serialization and Response Shaping](#33-serialization-and-response-shaping)
  - [3.4 Error Handling Design](#34-error-handling-design)
  - [3.5 API Design Features](#35-api-design-features)
  - [3.6 OpenAPI and Swagger](#36-openapi-and-swagger)
  - [3.7 HTTP Features](#37-http-features)
  - [3.8 HTTP Adapters With Express 5 and Fastify](#38-http-adapters-with-express-5-and-fastify)
- [Phase 4: Data and Persistence](#phase-4-data-and-persistence)
  - [4.1 Choosing a Data Layer](#41-choosing-a-data-layer)
  - [4.2 Integrating an ORM the Nest Way](#42-integrating-an-orm-the-nest-way)
  - [4.3 Transactions and Consistency](#43-transactions-and-consistency)
  - [4.4 Query Performance](#44-query-performance)
  - [4.5 Caching](#45-caching)
  - [4.6 Document Databases](#46-document-databases)
- [Phase 5: Security](#phase-5-security)
  - [5.1 Authentication](#51-authentication)
  - [5.2 Authorization](#52-authorization)
  - [5.3 Web Security Hardening](#53-web-security-hardening)
  - [5.4 Secrets and Cryptography](#54-secrets-and-cryptography)
- [Phase 6: Testing](#phase-6-testing)
  - [6.1 Unit Testing](#61-unit-testing)
  - [6.2 Integration and E2E Testing](#62-integration-and-e2e-testing)
  - [6.3 Testing Async and Distributed Code](#63-testing-async-and-distributed-code)
  - [6.4 Test Strategy](#64-test-strategy)
- [Phase 7: Background Work and Application Services](#phase-7-background-work-and-application-services)
  - [7.1 Events](#71-events)
  - [7.2 Task Scheduling](#72-task-scheduling)
  - [7.3 Queues](#73-queues)
  - [7.4 Logging](#74-logging)
  - [7.5 Health Checks](#75-health-checks)
  - [7.6 External Integrations](#76-external-integrations)
- [Phase 8: Real-time and GraphQL](#phase-8-real-time-and-graphql)
  - [8.1 WebSockets](#81-websockets)
  - [8.2 Server-Sent Events and Streaming](#82-server-sent-events-and-streaming)
  - [8.3 GraphQL Fundamentals](#83-graphql-fundamentals)
  - [8.4 GraphQL in Production](#84-graphql-in-production)
- [Phase 9: Microservices and Reliability](#phase-9-microservices-and-reliability)
  - [9.1 Microservices Fundamentals](#91-microservices-fundamentals)
  - [9.2 Transports](#92-transports)
  - [9.3 Resilience Patterns](#93-resilience-patterns)
  - [9.4 Idempotency](#94-idempotency)
  - [9.5 Transactional Outbox and Sagas](#95-transactional-outbox-and-sagas)
  - [9.6 Distributed Locks and Coordination](#96-distributed-locks-and-coordination)
  - [9.7 CQRS and Event Sourcing](#97-cqrs-and-event-sourcing)
- [Phase 10: Architecture at Scale](#phase-10-architecture-at-scale)
  - [10.1 Structuring Large Nest Codebases](#101-structuring-large-nest-codebases)
  - [10.2 Monorepos and Libraries](#102-monorepos-and-libraries)
  - [10.3 Request Context and Multi-tenancy](#103-request-context-and-multi-tenancy)
  - [10.4 Standalone Apps and CLIs](#104-standalone-apps-and-clis)
- [Phase 11: Performance, Observability and Production](#phase-11-performance-observability-and-production)
  - [11.1 Performance](#111-performance)
  - [11.2 Observability](#112-observability)
  - [11.3 Containers and Deployment](#113-containers-and-deployment)
  - [11.4 Upgrades and Maintenance](#114-upgrades-and-maintenance)
- [Phase 12: AI and MCP With NestJS](#phase-12-ai-and-mcp-with-nestjs)
  - [12.1 Building MCP Servers](#121-building-mcp-servers)
  - [12.2 AI Features in Nest Apps](#122-ai-features-in-nest-apps)
- [Phase 13: Interview Preparation](#phase-13-interview-preparation)
  - [13.1 Concept Question Bank](#131-concept-question-bank)
  - [13.2 Live Coding and Code Reading](#132-live-coding-and-code-reading)
  - [13.3 System Design With NestJS](#133-system-design-with-nestjs)
  - [13.4 Comparisons and Trade-offs](#134-comparisons-and-trade-offs)
- [Capstone Project: Event Ticketing Platform](#capstone-project-event-ticketing-platform)
- [Appendix A: FastAPI to NestJS Concept Map](#appendix-a-fastapi-to-nestjs-concept-map)
- [Appendix B: Sources](#appendix-b-sources)

---

## How to Use This Roadmap

### Conventions

- **Phases are ordered.** Topics inside a phase are mostly ordered, but you can reorder them within the phase.
- **Topic IDs are stable.** IDs such as `2.4` are referenced from notes and code, so they don't get renumbered. New topics are appended.
- **Priority tags:**
  - **Core**: needed for day-to-day work and for every interview.
  - **Deep**: separates senior engineers from mid-level ones. Expect these in senior rounds.
  - **Elective**: learn when a project needs it.
- **Checkboxes** track your own learning progress. Tick a subtopic when you have read its notes and finished its exercise. The materials existing does not count as done.
- **Notes** live in `notes/<phase folder>/`. Every notes file starts with a clickable Table of Contents. Cross-topic documents such as this roadmap live in `docs/`. See [Repository Layout](#repository-layout).
- **Code** lives in `projects/<phase folder>/`. Each exercise has `template/`, `solution/` and `solved/` folders. See [Exercise Workflow](#exercise-workflow).
- **Testing starts in Phase 1.** Every milestone has tests. Phase 6 is the deep dive, not the first time tests appear.
- **Each phase ends with:**
  - **Interview checkpoint**: questions you should be able to answer aloud without notes.
  - **Milestone**: what to build before moving on.

### Repository Layout

```
WebDevLearning/
├── docs/                                     # knowledge hub: cross-topic documents
│   └── 01_nestjs_roadmap.md                  # this file
├── notes/                                    # study notes, one file per topic
│   ├── phase_00_orientation/
│   │   ├── 01_nodejs_runtime.md              # notes for topic 0.1
│   │   └── 02_typescript_refresher.md        # notes for topic 0.2
│   └── phase_01_core_building_blocks/
│       └── 07_guards.md                      # notes for topic 1.7
├── projects/
│   ├── phase_00_orientation/
│   │   ├── 02_typescript_refresher/          # exercise for topic 0.2
│   │   │   ├── README.md                     # task, hints, link to the notes
│   │   │   ├── template/                     # unsolved starter, never changes
│   │   │   ├── solution/                     # your work, copied from template/
│   │   │   └── solved/                       # complete reference answer
│   │   └── 07_milestone_hello_nest/          # same three folders
│   └── phase_01_core_building_blocks/
├── scripts/
│   └── start_exercise.sh                     # copies template/ to solution/
└── archive/                                  # old 2022 material
```

**Naming rules**

- Phase folder names are identical under `notes/` and `projects/`. Use the names in the table below.
- A notes file is `NN_name.md`, where `NN` is the topic's number inside its phase. Topic 1.7 Guards becomes `notes/phase_01_core_building_blocks/07_guards.md`, and topic 1.10 becomes `10_...`.
- An exercise folder uses the same `NN_name` as its notes file. Not every topic gets an exercise. Conceptual topics may only have notes.
- Phase milestones keep counting after the phase's last topic, in the order they should be done. Phase 0 has topics 01 to 05, so its milestones are `06_milestone_toy_di` and `07_milestone_hello_nest`. Phase 1 has ten topics, so its milestone is `11_milestone_tasks_api`. A milestone has no notes file of its own, so it exists only under `projects/`.
- Reading order inside any phase folder is therefore just the number order: topics first, then milestones.
- `docs/` is the knowledge hub for documents that cut across topics: this roadmap and, later, cheat sheets and the interview question bank. They use `NN_name.md`, numbered in the order they are written. Per-topic study notes never go in `docs/`.

| Phase | Folder name |
|---|---|
| 0 | `phase_00_orientation` |
| 1 | `phase_01_core_building_blocks` |
| 2 | `phase_02_di_and_fundamentals` |
| 3 | `phase_03_production_rest_apis` |
| 4 | `phase_04_data_and_persistence` |
| 5 | `phase_05_security` |
| 6 | `phase_06_testing` |
| 7 | `phase_07_background_work` |
| 8 | `phase_08_realtime_and_graphql` |
| 9 | `phase_09_microservices_and_reliability` |
| 10 | `phase_10_architecture_at_scale` |
| 11 | `phase_11_performance_and_production` |
| 12 | `phase_12_ai_and_mcp` |
| 13 | `phase_13_interview_prep` |

### Exercise Workflow

Every exercise and milestone has three copies of the same project:

| Folder | Written by | Contents |
|---|---|---|
| `template/` | Claude, once | A runnable project. Config and boilerplate are real. The parts you are meant to learn are stubs: files, class shells and method signatures, with `TODO(<topic id>)` comments and bodies that throw `new Error('TODO')`. It includes tests that fail until the exercise is done. After creation it is never changed, except to fix a bug in the template itself. |
| `solution/` | You | Starts as an exact copy of `template/`. This is where you write your code. Claude never writes here unless you ask. |
| `solved/` | Claude | The complete working code, with the same file layout as `template/`. It passes all the tests and has comments explaining the why. Look here when stuck. |

**Steps**

1. Read the topic notes and the exercise `README.md`.
2. Run `scripts/start_exercise.sh projects/<phase folder>/<exercise>`. It copies `template/` to `solution/` and refuses to run if `solution/` already exists, so your work is never overwritten.
3. Install dependencies in `solution/` and make the tests pass.
4. When stuck, read `solved/`, or compare with `diff -r solution/src solved/src`.
5. Tick the subtopics in this roadmap.

**Capstone milestones** carry over between phases. Each phase's `NN_milestone_ticketing/template/` starts from the previous phase's `solved/` code, with the new parts stubbed out.

**Dependencies**: each of the three folders is a separate Node project, and `node_modules/` is gitignored. Prefer pnpm, whose shared store hard-links packages, so three copies of a project don't cost three times the disk space.

### Focus Rule

Each topic is learned in isolation. Anything not about the topic adds noise and gets in the way of understanding it.

**For code (exercises)**

- One exercise teaches one topic. The code contains only what that topic needs.
- Use the smallest possible domain: an in-memory array of simple items such as `items` or `cats`. Don't use a realistic business domain unless the topic needs one.
- No database, auth, queues, Docker, config files or external services unless the exercise's topic is that thing.
- No extra libraries. Install only the Nest packages the topic is about.
- Use earlier topics only when unavoidable, and keep them to their simplest form. Never use a topic from later in the roadmap.
- If something unrelated is needed just to make the project run, it is already done in `template/` and marked `// Not part of this exercise`.
- `solved/` stays at the same scope. Don't add production hardening or "nice to haves" beyond the topic. Those concerns have their own topics.

**For notes**

- Explain the topic itself in full.
- Mention related topics with a one-line pointer to their topic ID, such as "see 2.4". Don't explain them in place.

**Where topics combine**

- Only in phase milestones, and only with topics from the current or earlier phases.
- Even in milestones, keep the domain small. The capstone grows one phase at a time and only adds what that phase teaches.

### Target Stack

| Concern | Choice | Notes |
|---|---|---|
| Runtime | Node.js 24 LTS (24.15+), project pinned with `.nvmrc` | The schematics behind `nest new`, `generate` and `upgrade` need 22.22.3+, 24.15+ or 26+ (the CLI binary itself needs only 20.11+). Apps run on 20.19+ or 22.12+, but Node 20 reached end of life on 2026-04-30, so don't start new work on it. Node 26 is LTS too (nvm lists 26.13.1 as the latest LTS) and the Phase 0 exercises passed on it. Tested: `nest new` still works on Node 24.11.1 with an engine warning. |
| Framework | NestJS 12 | ESM packages; CommonJS apps still work through `require(esm)`. |
| Module format | ESM for new projects | Learn CommonJS too, because most existing codebases still use it. |
| Language | TypeScript 6 | `@nestjs/schematics` v12 has TypeScript 6 as a peer dependency. Stay on TypeScript 6 for now. TypeScript 7 (the Go-based compiler, July 2026) has no programmatic API until 7.1, and the Nest CLI refuses to build with it (tested with 7.0.2). `npm i -D typescript` installs 7.x, so pin `~6.0`. |
| Tests | Vitest (ESM default), Jest 30 (CJS) | Jest loads ESM-only v12 packages only on Node 24.9+. |
| Lint and format | oxlint, Prettier | oxlint is the v12 default for generated projects. |
| Build | tsc (default), SWC, Rspack for monorepos | Rspack replaced webpack as the monorepo bundler. |
| HTTP adapter | Express 5 (default), Fastify | Express 5 has been the default since v11. |
| Database | PostgreSQL with Prisma or Drizzle | Also learn TypeORM well enough to read legacy codebases. |
| Cache and queues | Redis, BullMQ | |
| Infra | Docker, Docker Compose, Kubernetes basics | |

### What Changed Since the 2022 Material

The archived work in `archive/2022-nestjs-v9/` targeted NestJS 9. The important changes since then:

- **v11:**
  - Express 5 and Fastify 5 became the defaults.
  - Route wildcard syntax changed. Named wildcards such as `/*splat` replace bare `*`.
  - Node 16 and 18 support was dropped.
- **v12:**
  - Released 2026-08-27, according to the GitHub release and npm timestamps.
  - All `@nestjs/*` packages ship as ESM, and `nest new` asks whether to create a CJS or ESM project.
  - Validation and serialization accept Standard Schema (Zod, Valibot, ArkType) alongside class-validator.
  - Vitest is the default test runner for ESM projects, and oxlint is the default linter.
  - The official observability SDK `@nestjs/observe` was added.
  - Lifecycle hooks now run in component hierarchy order.
  - The legacy Terminus health indicator API was removed.
  - NATS moved to v3 (`@nats-io/transport-node`), and GraphQL subscriptions moved to `graphql-ws` only.
- **Docs:** the official docs now have Observability, Reliability, MCP and AI sections.
- **TypeScript:** moved from 4.7 to 6, and a native 7.0 compiler shipped in July 2026. Topic 0.2 covers the changes.
- **New first-party packages:** the v12 scaffold's `AGENTS.md` lists packages that didn't exist in 2022, and all of them exist on npm: `@nestjs/authentication`, `authorization`, `resilience`, `idempotency`, `outbox`, `locks`, `workflows`, `webhooks`, `mail`, `storage`, `i18n`, `ai` and `mcp`, plus `@nestjs/platform-node` (a `NodeAdapter`). Most are at version 0.0.x to 0.1.x, so they are early. **To do:** when we reach Phases 5, 7, 9 and 12, research each one and compare it with the established library (`@nestjs/jwt` and Passport, BullMQ, and so on) before choosing what the notes teach.

---

## Roadmap at a Glance

Time estimates assume about 8 to 10 hours per week.

| Phase | Theme | Rough time | Outcome |
|---|---|---|---|
| 0 | Orientation and prerequisites | 2 weeks | Modern TypeScript, decorators, Node and a v12 project set up |
| 1 | Core building blocks | 2 weeks | A REST API built with every request-pipeline component |
| 2 | Under the hood: DI and fundamentals | 2 to 3 weeks | Explain how the container works, and write a reusable dynamic module |
| 3 | Production REST APIs | 2 to 3 weeks | Validated config, DTOs, errors, versioning, OpenAPI |
| 4 | Data and persistence | 2 to 3 weeks | Postgres with an ORM, transactions, caching |
| 5 | Security | 2 weeks | Authentication, authorization and hardening |
| 6 | Testing | 1 to 2 weeks | Unit, integration and e2e tests against a real database |
| 7 | Background work and app services | 2 weeks | Events, cron, queues, logging, health checks |
| 8 | Real-time and GraphQL | 2 weeks | WebSockets, SSE, a production GraphQL API |
| 9 | Microservices and reliability | 3 weeks | Transports, outbox, idempotency, CQRS |
| 10 | Architecture at scale | 2 weeks | Modular monolith, monorepo, multi-tenancy |
| 11 | Performance, observability, production | 2 weeks | Profiling, tracing, deployment |
| 12 | AI and MCP with NestJS (elective) | 1 to 2 weeks | An MCP server and LLM features built in Nest |
| 13 | Interview preparation | Ongoing, plus 2 focused weeks | Answers, live coding and system design |

---

## Phase 0: Orientation and Prerequisites

Nest is built on TypeScript decorators, reflection metadata and the Node event loop. Learning these first makes the rest of the framework make sense. The phase includes a full TypeScript refresher covering the changes from 2022 to 2026.

### 0.1 The Node.js Runtime for Nest Developers

**Priority:** Core

- [ ] Event loop phases, microtasks vs macrotasks, and why one blocking call stalls every in-flight request
- [ ] Promise error propagation, unhandled rejections and process crash behavior
- [ ] Streams and backpressure, which come up again in file uploads and streaming responses
- [ ] `worker_threads` vs `cluster` vs horizontal scaling
- [ ] `AsyncLocalStorage`, the basis of request context used in 10.3
- [ ] ESM vs CommonJS: `require(esm)`, `import.meta.dirname`, `.js` extensions under `nodenext`
- [ ] The Node release and LTS policy, and which lines Nest 12 supports

### 0.2 TypeScript Refresher

**Priority:** Core

A refresher for someone who last used TypeScript around version 4.7 (2022). The fundamentals are a quick review. More time goes to what changed between 2022 and 2026. Nest-specific features (decorators and metadata) are in 0.3.

**Fundamentals (quick review)**

- [ ] `any` vs `unknown` vs `never`, and literal, union and intersection types
- [ ] Narrowing: `typeof`, `instanceof`, `in`, discriminated unions, exhaustiveness checks with `never`
- [ ] Custom type guards (`x is T`) and assertion functions (`asserts x is T`)
- [ ] Interfaces vs type aliases, optional and `readonly` properties, index signatures
- [ ] Functions: overloads, optional and default parameters, typing `this`
- [ ] Classes: access modifiers vs `#private` fields, `readonly`, parameter properties, `abstract`, `implements`, `override`, static members
- [ ] Enums vs string literal unions vs `as const` objects, and why many teams now avoid enums
- [ ] Typing async code: `Promise<T>`, `Awaited<T>`, `unknown` in `catch` clauses, custom `Error` subclasses with `cause`

**Generics and type-level programming**

- [ ] Generics: constraints, defaults, generic classes
- [ ] `keyof`, `typeof` in a type position, indexed access types
- [ ] Mapped types, key remapping with `as`, the `-readonly` and `-?` modifiers
- [ ] Conditional types, `infer`, and how conditional types distribute over unions
- [ ] Template literal types
- [ ] Built-in utility types: `Partial`, `Required`, `Pick`, `Omit`, `Record`, `Readonly`, `ReturnType`, `Parameters`, `InstanceType`, `NoInfer`

**What changed from TypeScript 4.7 to 7.0**

- [ ] 4.9: the `satisfies` operator and the `accessor` keyword
- [ ] 5.0: TC39 standard decorators (compared with Nest's legacy decorators in 0.3), `const` type parameters, `moduleResolution: bundler`, `verbatimModuleSyntax`
- [ ] 5.2: `using` and `await using` for automatic resource cleanup
- [ ] 5.4 and 5.5: `NoInfer`, inferred type predicates, `isolatedDeclarations`
- [ ] 5.8: `erasableSyntaxOnly`, and `require()` of ESM modules under `module: nodenext`
- [ ] 6.0, the last compiler written in JavaScript: new defaults such as `strict: true`, and removed legacy options such as the `es5` target, `baseUrl` and `outFile`. The exact list is confirmed against the official release notes and written up in the notes file.
- [ ] 7.0 (July 2026): the compiler rewritten in Go, about 10x faster. Its full programmatic API only arrives in 7.1, so tools built on that API may lag. Check which TypeScript version Nest 12 supports.

**Modules, config and how TypeScript runs**

- [ ] `import type`, `export type` and `verbatimModuleSyntax`
- [ ] tsconfig essentials: the `strict` family, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `module`, `moduleResolution`, `target`, `lib`, `isolatedModules`, `sourceMap`
- [ ] Ways to run TypeScript: `tsc` (type checks and emits), SWC or esbuild (strip types without checking), Node's built-in type stripping (erasable syntax only)

**Exercise**

- [ ] Small typing katas covering narrowing, generics, and mapped and conditional types, checked with `tsc --noEmit` and Vitest `expectTypeOf`

### 0.3 TypeScript Features Nest Is Built On

**Priority:** Core

- [ ] What survives to runtime: classes do, interfaces and types are erased. This is why an interface can't be an injection token.
- [ ] Legacy `experimentalDecorators` vs TC39 standard decorators. Nest uses the legacy model because parameter decorators and emitted metadata exist only there.
- [ ] Decorator kinds and their evaluation order: class, method, property, parameter
- [ ] `emitDecoratorMetadata` and `design:paramtypes`, which is how Nest knows what to inject
- [ ] The `reflect-metadata` API: `defineMetadata`, `getMetadata`, metadata keys
- [ ] Why Nest code can't run on Node's built-in type stripping: parameter properties need a real compile step, and decorators are a plain `SyntaxError` on every Node version tested, even with the transform flag
- [ ] How Vitest runs decorators: Vite 8's Oxc transformer reads `experimentalDecorators` and `emitDecoratorMetadata` from tsconfig, and dropping `emitDecoratorMetadata` makes `design:paramtypes` come out `undefined`
- [ ] Pitfalls that break injection silently: a type-only import of a class used in a constructor, interface-typed parameters, circular imports (a loud `ReferenceError` under ESM, a silent `undefined` under CommonJS), and `useDefineForClassFields` on ES2022+ targets disabling legacy property decorators
- [ ] Exercise: write class, method, property and parameter decorators, then read their metadata back. The toy DI container is the phase milestone.

### 0.4 The NestJS Philosophy and Landscape

**Priority:** Core

- [ ] What Nest adds on top of Express or Fastify: structure, DI and conventions, inspired by Angular
- [ ] Nest vs Express, Fastify and Hono, and Nest vs FastAPI (see [Appendix A](#appendix-a-fastapi-to-nestjs-concept-map))
- [ ] Platform agnosticism: HTTP, microservices, WebSockets, GraphQL and standalone apps share one core
- [ ] The version history that matters: v9, v10, v11 (Express 5), v12 (ESM, Standard Schema, observability)
- [ ] How to use the official docs, the API reference and the `sample/` folder in `nestjs/nest`

### 0.5 Tooling and Project Setup

**Priority:** Core

- [ ] Nest CLI: `nest new` (the CJS or ESM prompt), `nest generate`, the `resource` CRUD generator
- [ ] Project anatomy: `main.ts`, the root module, `nest-cli.json`, `tsconfig.build.json`
- [ ] Builders: `tsc` (default), SWC for fast builds, Rspack for monorepos
- [ ] Linting with oxlint, formatting with Prettier
- [ ] Test runners: Vitest for ESM projects, Jest 30 for CJS, and the Node 24.9+ requirement for Jest with v12
- [ ] What the scaffold does not check: `vitest run` and `oxlint --type-aware` both pass with a deliberate type error (tested). Only `tsc --noEmit` or `nest build` report it, so our exercises run `tsc --noEmit && vitest run`.
- [ ] Watch mode, debugging in VS Code with breakpoints, the Nest REPL
- [ ] `nest upgrade` and how Nest versions its packages

**Interview checkpoint**

- What is the difference between `unknown` and `any`, and when would you use `satisfies` instead of a type annotation?
- Why can't a TypeScript interface be used as an injection token?
- What does `emitDecoratorMetadata` emit, and what breaks without it?
- What happens to other requests when one handler runs a 2-second CPU loop?
- When would you choose ESM over CommonJS for a new Nest 12 service?

**Milestone**

- `phase_00_orientation/06_milestone_toy_di`: a minimal DI container built on decorators and reflection
- `phase_00_orientation/07_milestone_hello_nest`: an ESM Nest 12 app that runs, has a working debugger breakpoint, and has one passing Vitest test

---

## Phase 1: Core Building Blocks

This phase covers the components that make up the HTTP request pipeline. The aim is to know exactly when each component runs and what it can access.

### 1.1 Application Bootstrap

**Priority:** Core

- [ ] `NestFactory.create`, the application instance, `listen`, global prefix, CORS
- [ ] Bootstrap at a high level: scan modules, build the container, instantiate providers, register routes, run lifecycle hooks (deep dive in 2.8)
- [ ] Logger and other `NestApplicationOptions` at bootstrap
- [ ] Choosing the HTTP adapter: Express (default) or `FastifyAdapter`

### 1.2 Modules

**Priority:** Core

- [ ] `@Module` metadata: `imports`, `controllers`, `providers`, `exports`
- [ ] Feature modules and shared modules. Providers are private to their module by default.
- [ ] Re-exporting modules
- [ ] `@Global` modules and why to use them sparingly
- [ ] A first look at dynamic modules (`forRoot`, `register`). The deep dive is in 2.3.
- [ ] Reading and fixing "Nest can't resolve dependencies of X" errors

### 1.3 Controllers and Routing

**Priority:** Core

- [ ] `@Controller` and the route method decorators, route params, `@Query`, `@Body`, `@Headers`
- [ ] `@Req` and `@Res`, why to avoid `@Res`, and `passthrough: true`
- [ ] Status codes, `@HttpCode`, `@Header`, `@Redirect`
- [ ] Async handlers and returning Observables
- [ ] Express 5 path syntax and named wildcards
- [ ] Route ordering, and the v12 route conflict diagnostics `routeConflictPolicy` and `routeResolutionStrategy`
- [ ] DTOs as classes, and why they are classes rather than interfaces

### 1.4 Providers and Services

**Priority:** Core

- [ ] `@Injectable`, constructor injection, property injection
- [ ] Providers are singletons by default, so in-memory state is shared across requests
- [ ] `@Optional()`, including the v12 change: subclasses that declare their own constructor no longer inherit it
- [ ] Services vs repositories vs helpers, and where business logic belongs

### 1.5 Middleware

**Priority:** Core

- [ ] Class middleware vs functional middleware
- [ ] `NestModule.configure`, `MiddlewareConsumer`, `forRoutes`, `exclude`
- [ ] Global middleware with `app.use`
- [ ] Limits of middleware: no `ExecutionContext`, and it doesn't know which handler will run
- [ ] Express 5 wildcard changes in `forRoutes`

### 1.6 Pipes

**Priority:** Core

- [ ] Transformation vs validation
- [ ] Built-in pipes: `ParseIntPipe`, `ParseUUIDPipe`, `ParseEnumPipe`, `ParseArrayPipe`, `DefaultValuePipe`, `ParseFilePipe`
- [ ] Binding scopes: parameter, method, controller, global
- [ ] Custom pipes with `PipeTransform`, and `ArgumentMetadata`, which takes a generic parameter in v12
- [ ] A first look at `ValidationPipe` vs `StandardSchemaValidationPipe`. The deep dive is in 3.2.

### 1.7 Guards

**Priority:** Core

- [ ] `CanActivate`, returning a boolean, Promise or Observable
- [ ] `ExecutionContext` basics
- [ ] A role guard built with metadata and `Reflector.createDecorator`
- [ ] Binding scopes, and global guards through `APP_GUARD` so they can use DI
- [ ] Guards vs middleware for authentication

### 1.8 Interceptors

**Priority:** Core

- [ ] `NestInterceptor` and `CallHandler`, and running code before and after the handler
- [ ] The RxJS needed for Nest: `map`, `tap`, `catchError`, `timeout`, `finalize`
- [ ] Use cases: response mapping, timing and logging, caching, timeouts
- [ ] Binding scopes and `APP_INTERCEPTOR`

### 1.9 Exception Filters

**Priority:** Core

- [ ] The built-in `HttpException` hierarchy and the default error response shape
- [ ] The v12 `errorCode` option, as in `new BadRequestException('...', { errorCode: 'WEAK_PASSWORD' })`
- [ ] Custom filters with `@Catch` and `ArgumentsHost`
- [ ] Catch-all filters, and extending `BaseExceptionFilter`
- [ ] Domain errors vs HTTP errors, and where the mapping happens

### 1.10 Custom Decorators and the Request Lifecycle

**Priority:** Core

- [ ] Parameter decorators with `createParamDecorator`, for example `@CurrentUser()`
- [ ] Decorator composition with `applyDecorators`
- [ ] **Request lifecycle order:** middleware, then guards, then interceptors (before the handler), then pipes, then the handler, then interceptors (after the handler), then exception filters
- [ ] Order of binding scopes: global, then controller, then route
- [ ] Exercise: draw the lifecycle diagram from memory and confirm it with logging

**Interview checkpoint**

- Walk through the request lifecycle. Where do you put authentication, validation, response shaping and error mapping?
- When do you use middleware, a guard or an interceptor?
- Why are providers module-scoped, and how do you share one between modules?
- What breaks when you inject `@Res()` without `passthrough`?
- How do you register a global guard that still has access to DI?

**Milestone**

- `phase_01_core_building_blocks/11_milestone_tasks_api`: an in-memory CRUD API that uses every component from this phase, with unit tests for the service and one e2e test

---

## Phase 2: Under the Hood With DI and Fundamentals

This phase is where senior interviews are won or lost. Read the `@nestjs/core` source alongside the docs.

### 2.1 The IoC Container and Dependency Injection

**Priority:** Deep

- [ ] IoC vs DI vs the service locator pattern
- [ ] Injection tokens: classes, strings, symbols, and typed token constants
- [ ] How Nest resolves the graph: metadata scanning, then ordered instantiation
- [ ] Source reading in `@nestjs/core`: `NestContainer`, `DependenciesScanner`, `InstanceLoader`, `Injector`
- [ ] FastAPI `Depends` (a call graph built per request) vs the Nest container (long-lived instances)

### 2.2 Custom and Async Providers

**Priority:** Core

- [ ] `useClass`, `useValue`, `useFactory` with `inject`, `useExisting` for aliases
- [ ] Non-class tokens with `@Inject()`
- [ ] Async factory providers, such as waiting for a DB connection before the app starts
- [ ] Exporting custom providers
- [ ] Patterns: choosing a strategy from config, test doubles, ports and adapters

### 2.3 Dynamic Modules

**Priority:** Deep

- [ ] Naming conventions: `forRoot`, `forRootAsync`, `register`, `forFeature`
- [ ] `ConfigurableModuleBuilder`
- [ ] Async options with `useFactory`, `inject` and `imports`
- [ ] Exercise: write a configurable library module such as a payments or notifications client

### 2.4 Injection Scopes

**Priority:** Deep

- [ ] `DEFAULT`, `REQUEST` and `TRANSIENT` scopes
- [ ] Scope bubbling: a request-scoped dependency makes all its dependents request-scoped
- [ ] The `REQUEST` and `INQUIRER` tokens
- [ ] Performance cost, durable providers and `ContextIdStrategy` for multi-tenancy
- [ ] The alternative: `AsyncLocalStorage` or `nestjs-cls` (see 10.3)

### 2.5 Circular Dependencies

**Priority:** Core

- [ ] Why they happen, and `forwardRef` for modules and providers
- [ ] `ModuleRef` as an escape hatch
- [ ] Design fixes: extract a shared module, use events, invert the dependency
- [ ] Barrel-file import cycles, where a class is `undefined` when its decorator runs

### 2.6 Module Reference and Lazy Loading

**Priority:** Deep

- [ ] `ModuleRef.get`, `resolve` and `create`, and the `strict` option
- [ ] Resolving scoped providers dynamically
- [ ] `LazyModuleLoader` for serverless cold starts

### 2.7 Execution Context and Metadata

**Priority:** Core

- [ ] `ArgumentsHost` vs `ExecutionContext`, `switchToHttp`, `switchToRpc` and `switchToWs`, and `getType`
- [ ] `getHandler` and `getClass` with `Reflector`: `get`, `getAllAndOverride`, `getAllAndMerge`
- [ ] Writing guards and filters that work in any transport

### 2.8 Lifecycle Events and Graceful Shutdown

**Priority:** Core

- [ ] Lifecycle hooks: `onModuleInit`, `onApplicationBootstrap`, `onModuleDestroy`, `beforeApplicationShutdown`, `onApplicationShutdown`
- [ ] The v12 change: hooks run by component hierarchy level
- [ ] `enableShutdownHooks`, OS signals, and why hooks may not fire (PID 1 in Docker)
- [ ] Graceful shutdown: draining requests (the v12 Express adapter drains in-flight requests), closing pools, the Kubernetes `preStop` hook

### 2.9 Discovery Service and Metaprogramming

**Priority:** Deep

- [ ] `DiscoveryService` and `MetadataScanner`, to find providers and methods by decorator
- [ ] Exercise: build a custom decorator registry in the style of `@OnEvent`
- [ ] How the official packages (`schedule`, `event-emitter`, `cqrs`) use discovery

**Interview checkpoint**

- How does Nest know what to inject into a constructor?
- What is scope bubbling, and why can one request-scoped provider hurt throughput?
- What is the difference between `forRoot`, `forFeature` and `register`?
- How do you resolve a circular dependency, and why is `forwardRef` a design smell?
- In what order do the lifecycle hooks run? Why might `onApplicationShutdown` not run in a container?
- What is the difference between `useFactory`, `useClass` and `useExisting`?

**Milestone**

- `phase_02_di_and_fundamentals/10_milestone_dynamic_module_lib`: a `NotificationsModule.forRootAsync()` library with custom providers and a discovery-based decorator
- A short benchmark comparing request-scoped providers with CLS
- A notes doc that walks through the core injector source

---

## Phase 3: Production REST APIs

### 3.1 Configuration

**Priority:** Core

- [ ] `@nestjs/config`: `ConfigModule.forRoot`, `isGlobal`, `load`, namespaces with `registerAs`, a typed `ConfigService`
- [ ] Environment validation with Standard Schema (Zod, Valibot, ArkType) in v12. Joi v18+ still works. Library-specific settings go under `validationOptions.libraryOptions`.
- [ ] 12-factor config, per-environment files, secrets handling
- [ ] Using config inside dynamic modules through `forRootAsync`

### 3.2 Validation

**Priority:** Core

- [ ] `ValidationPipe` with class-validator and class-transformer: `whitelist`, `forbidNonWhitelisted`, `transform`, and the new `errorFormat` option
- [ ] `StandardSchemaValidationPipe` with the `schema` option on `@Body`, `@Query` and `@Param`, using Zod
- [ ] Choosing between class DTOs and schema-first validation, and keeping one source of truth for types, validation and OpenAPI
- [ ] Nested objects, arrays, custom validators, async validators that use DI
- [ ] Mapped types: `PartialType`, `PickType`, `OmitType`, `IntersectionType`

### 3.3 Serialization and Response Shaping

**Priority:** Core

- [ ] `ClassSerializerInterceptor` with `@Exclude`, `@Expose`, `@Transform` and groups
- [ ] `StandardSchemaSerializerInterceptor` with `@SerializeOptions({ schema })`
- [ ] Response envelopes vs plain resources, and pagination metadata
- [ ] Keeping entities and response DTOs separate so database fields never leak

### 3.4 Error Handling Design

**Priority:** Core

- [ ] A global error model based on RFC 9457 Problem Details
- [ ] Stable machine-readable error codes using the v12 `errorCode`
- [ ] Mapping domain and ORM errors, such as a unique violation becoming 409
- [ ] What to log vs what to expose, and correlation IDs

### 3.5 API Design Features

**Priority:** Core

- [ ] Versioning by URI, header or media type, and `VERSION_NEUTRAL`
- [ ] Global prefix, and `RouterModule` for nested route trees
- [ ] Pagination (offset vs cursor), filtering, sorting
- [ ] Compression, and content negotiation
- [ ] A first look at idempotent POST requests (see 9.4)

### 3.6 OpenAPI and Swagger

**Priority:** Core

- [ ] `@nestjs/swagger` setup with `DocumentBuilder`
- [ ] Decorators: `@ApiProperty`, `@ApiResponse`, `@ApiTags`, `@ApiBearerAuth`
- [ ] The Swagger CLI plugin, which removes most decorator boilerplate
- [ ] Generating typed clients from the spec
- [ ] Keeping Zod schemas and the OpenAPI spec in sync (check current tooling when we reach this)

### 3.7 HTTP Features

**Priority:** Core, except where marked Elective

- [ ] Cookies and sessions
- [ ] File upload with Multer and `ParseFilePipe`, streaming to object storage, `StreamableFile`
- [ ] Streaming responses
- [ ] Webhooks: raw body access and signature verification
- [ ] Serve static files and MVC templates (Elective)

### 3.8 HTTP Adapters With Express 5 and Fastify

**Priority:** Deep

- [ ] Express 5 changes: path matching, wildcards, async error handling
- [ ] `FastifyAdapter`: setup, plugin differences, performance profile
- [ ] `@nestjs/platform-node` and its `NodeAdapter`, a third adapter that exists on npm (12.5.1). The scaffold's `AGENTS.md` claims it is the fastest, ahead of Fastify. Benchmark it ourselves before believing that.
- [ ] Writing adapter-agnostic code that doesn't leak Express types through `@Req`
- [ ] Keep-alive, raw body, HTTPS, multiple servers

**Interview checkpoint**

- What do `whitelist`, `forbidNonWhitelisted` and `transform` each do, and why does each one matter?
- What are the trade-offs between class-validator and Standard Schema (Zod)?
- How do you guarantee a password hash never appears in a response?
- Compare API versioning strategies. Which would you pick for a public API?
- How do you accept a 2 GB upload without buffering it in memory?

**Milestone**

- `phase_03_production_rest_apis/09_milestone_tasks_api`: start from the Phase 1 solved tasks API and bring it to production grade with validated config, DTO validation and serialization, problem-details errors, versioning, Swagger docs, file attachments

---

## Phase 4: Data and Persistence

### 4.1 Choosing a Data Layer

**Priority:** Core

- [ ] The landscape: Prisma, Drizzle, TypeORM, MikroORM, Sequelize, Mongoose
- [ ] Active record vs data mapper vs query builder vs schema-first client
- [ ] **Recommendation:** go deep on one of Prisma or Drizzle, and learn TypeORM to reading level, because it is the most common in existing Nest codebases
- [ ] Coming from SQLAlchemy: MikroORM is the closest model, with a unit of work and an identity map

### 4.2 Integrating an ORM the Nest Way

**Priority:** Core

- [ ] Wrapping the DB client in providers and modules, with `forRootAsync` and config
- [ ] The repository pattern: when it helps and when it is ceremony
- [ ] Migrations workflow and seeding
- [ ] Connection pooling, pool sizing, PgBouncer

### 4.3 Transactions and Consistency

**Priority:** Deep

- [ ] Transactions across several services: passing the transaction explicitly vs CLS-based propagation (`@nestjs-cls/transactional`)
- [ ] Isolation levels
- [ ] Optimistic locking with a version column vs pessimistic locking with `SELECT ... FOR UPDATE`
- [ ] The unit of work pattern

### 4.4 Query Performance

**Priority:** Deep

- [ ] Detecting N+1 queries, eager vs lazy relations, selecting only needed columns
- [ ] Indexing for API access patterns, `EXPLAIN ANALYZE`
- [ ] Implementing cursor pagination
- [ ] Read replicas and routing reads

### 4.5 Caching

**Priority:** Core

- [ ] `@nestjs/cache-manager`, `CacheInterceptor`, a Redis store
- [ ] Cache-aside vs write-through, TTLs, invalidation, stampede protection
- [ ] HTTP caching headers and ETags

### 4.6 Document Databases

**Priority:** Elective

- [ ] `@nestjs/mongoose`: schemas, models, when a document store fits

**Interview checkpoint**

- Compare TypeORM, Prisma and Drizzle. Which would you pick for a new service, and why?
- How do you run calls across several services in one transaction?
- What is an N+1 query, and how did you find and fix one?
- Optimistic vs pessimistic locking for booking a seat: which, and why?
- Describe your cache invalidation strategy for a read-heavy endpoint.

**Milestone**

- `phase_04_data_and_persistence/07_milestone_ticketing`: the start of the capstone, with Postgres in Docker Compose, the chosen ORM with migrations, a transactional booking flow with locking, a Redis cache, and integration tests on a real database

---

## Phase 5: Security

### 5.1 Authentication

**Priority:** Core

- [ ] Password hashing with argon2id or bcrypt
- [ ] JWT access and refresh tokens, rotation, and revocation (denylists, token families)
- [ ] `@nestjs/jwt` with a custom guard vs `@nestjs/passport` strategies, and when Passport is worth it
- [ ] A global auth guard plus an `@Public()` decorator
- [ ] Session and cookie auth as an alternative, and when to prefer it
- [ ] OAuth2 and OIDC login, and delegating to an identity provider

### 5.2 Authorization

**Priority:** Core

- [ ] RBAC with guards and metadata
- [ ] Policy-based access (ABAC) with CASL
- [ ] Resource ownership checks, and whether they belong in a guard or a service
- [ ] Tenant isolation

### 5.3 Web Security Hardening

**Priority:** Core

- [ ] Security headers with Helmet or Nest's built-in support (InfoQ reports built-in support in v12.1; check the docs)
- [ ] CORS configuration, and CSRF protection for cookie-based auth
- [ ] Rate limiting with `@nestjs/throttler`, using Redis storage when there are several instances
- [ ] Mass assignment, injection, and SSRF through outbound HTTP calls
- [ ] The OWASP API Security Top 10 mapped to Nest features

### 5.4 Secrets and Cryptography

**Priority:** Core

- [ ] Field-level encryption with `node:crypto`, and key rotation
- [ ] Loading secrets from the environment or a vault, never from committed config
- [ ] Audit logging

**Interview checkpoint**

- Where do you validate a JWT, and how do you make routes protected by default?
- Is Passport still worth using in 2026? What are the trade-offs?
- How do you revoke a JWT before it expires?
- How do you implement row-level authorization?
- How does rate limiting work across multiple instances?

**Milestone**

- Add JWT authentication with refresh rotation, RBAC plus ownership policies, throttling and hardened headers to the ticketing project, with e2e tests for each auth flow

---

## Phase 6: Testing

### 6.1 Unit Testing

**Priority:** Core

- [ ] `Test.createTestingModule`, `compile` and `get`
- [ ] Mocking providers with `useValue`, `overrideProvider`, and auto-mocking through `useMocker`
- [ ] Testing guards, pipes, interceptors and filters on their own
- [ ] Vitest vs Jest on Nest 12, including how decorator metadata is emitted under Vitest

### 6.2 Integration and E2E Testing

**Priority:** Core

- [ ] `createNestApplication` with `supertest`
- [ ] A real Postgres through Testcontainers, with rollback per test or truncation
- [ ] Overriding guards in tests
- [ ] Testing request-scoped providers by resolving with a `contextId`

### 6.3 Testing Async and Distributed Code

**Priority:** Deep

- [ ] Testing queue processors, event listeners and cron jobs
- [ ] Testing microservice clients and transports
- [ ] Contract testing with Pact
- [ ] Testing WebSocket gateways

### 6.4 Test Strategy

**Priority:** Deep

- [ ] The test pyramid vs the testing trophy for APIs
- [ ] Coverage and its limits, and mutation testing with Stryker
- [ ] Test data factories and builders
- [ ] CI concerns: parallel runs, isolation, flaky tests

**Interview checkpoint**

- How do you unit test a service that depends on a repository and a queue?
- How do you test an endpoint protected by a global guard?
- When do you mock the database, and when do you use a real one?
- How do you keep e2e tests fast and isolated?

**Milestone**

- Bring the ticketing project to a healthy test suite with unit tests, integration tests on Testcontainers, and e2e tests running in CI

---

## Phase 7: Background Work and Application Services

### 7.1 Events

**Priority:** Core

- [ ] `@nestjs/event-emitter`: `@OnEvent`, async listeners, error handling
- [ ] In-process events vs a message broker, and when in-process events lose data

### 7.2 Task Scheduling

**Priority:** Core

- [ ] `@nestjs/schedule`: `@Cron`, `@Interval`, `@Timeout`, `SchedulerRegistry`
- [ ] Running a job only once across several instances: locks, leader election, or repeatable queue jobs

### 7.3 Queues

**Priority:** Core

- [ ] `@nestjs/bullmq`: producers, processors, job options (retries, backoff, priority, delay, repeat)
- [ ] Concurrency, rate limiting, dead-letter handling, flows
- [ ] Running workers inside the API process vs as separate worker processes

### 7.4 Logging

**Priority:** Core

- [ ] The built-in `ConsoleLogger`, JSON mode, and structured params (on by default in v12)
- [ ] Custom `LoggerService`, pino through `nestjs-pino`, redaction
- [ ] Request IDs, and log levels per environment

### 7.5 Health Checks

**Priority:** Core

- [ ] `@nestjs/terminus` with the v12 `HealthIndicatorService` API (the legacy API was removed)
- [ ] Liveness vs readiness vs startup probes

### 7.6 External Integrations

**Priority:** Elective

- [ ] The HTTP client: `HttpModule` vs native `fetch`, timeouts, retries
- [ ] Mail, file storage, internationalization

**Interview checkpoint**

- How do you make sure a cron job runs once when you have 5 replicas?
- What is the difference between an in-process event and a queued job, and when do you need each?
- How do you handle a job that fails permanently?
- What makes a health check endpoint useful rather than misleading?

**Milestone**

- Add order-confirmation emails through a queue, a cron job that expires seat holds, structured logs and health probes to the ticketing project

---

## Phase 8: Real-time and GraphQL

### 8.1 WebSockets

**Priority:** Core

- [ ] Gateways, `@SubscribeMessage`, rooms, acknowledgements
- [ ] Adapters: socket.io vs ws, and the Redis adapter for horizontal scaling
- [ ] Guards, pipes and filters in the WebSocket context, and authentication at handshake
- [ ] v12 additions: request-scoped gateways and disconnect reasons

### 8.2 Server-Sent Events and Streaming

**Priority:** Core

- [ ] `@Sse` with Observables
- [ ] Choosing between SSE, WebSockets and long polling
- [ ] Streaming LLM tokens to clients (links to Phase 12)

### 8.3 GraphQL Fundamentals

**Priority:** Core

- [ ] Code-first vs schema-first, and the Apollo vs Mercurius drivers
- [ ] Resolvers, queries, mutations, field resolvers
- [ ] Input types, scalars, enums, unions, interfaces
- [ ] GraphiQL, the default IDE in v12

### 8.4 GraphQL in Production

**Priority:** Deep

- [ ] Solving N+1 with DataLoader and request-scoped loaders
- [ ] Query complexity, depth limits, persisted queries
- [ ] Subscriptions with `graphql-ws` (`subscriptions-transport-ws` was removed in v12)
- [ ] Authentication in resolvers, and error formatting
- [ ] Federation

**Interview checkpoint**

- How do you scale WebSocket connections across multiple instances?
- When would you choose SSE over WebSockets?
- How do you prevent N+1 queries in GraphQL resolvers?
- How do you protect a GraphQL API from expensive queries?

**Milestone**

- Add live seat-availability updates over WebSockets to the ticketing project, scaled through the Redis adapter, plus a GraphQL read API with DataLoader

---

## Phase 9: Microservices and Reliability

### 9.1 Microservices Fundamentals

**Priority:** Core

- [ ] `@nestjs/microservices`: the transport model, `ClientProxy`, `@MessagePattern` (request-response) vs `@EventPattern` (fire-and-forget)
- [ ] Hybrid applications that serve HTTP and listen on a transport
- [ ] Serialization, timeouts, error propagation with `RpcException`
- [ ] When not to split into microservices, and why to start with a modular monolith

### 9.2 Transports

**Priority:** Core, except where marked Deep

- [ ] TCP, Redis, NATS v3 (`@nats-io/transport-node`), RabbitMQ, Kafka, gRPC, MQTT
- [ ] Kafka `RegExp` patterns and the gRPC exception filter, both new in v12
- [ ] Delivery guarantees, ordering and consumer groups for each transport (Deep)
- [ ] Custom transporters and pre-request hooks (Deep)

### 9.3 Resilience Patterns

**Priority:** Deep

- [ ] Timeouts, retries with jitter, circuit breakers, bulkheads
- [ ] Backpressure and load shedding

### 9.4 Idempotency

**Priority:** Deep

- [ ] Idempotency keys for HTTP endpoints
- [ ] At-least-once delivery and deduplicating consumers

### 9.5 Transactional Outbox and Sagas

**Priority:** Deep

- [ ] The dual-write problem, the transactional outbox, change data capture
- [ ] Sagas by choreography vs orchestration
- [ ] Durable workflows

### 9.6 Distributed Locks and Coordination

**Priority:** Deep

- [ ] Redis locks and the caveats of Redlock, and Postgres advisory locks
- [ ] Leader election

### 9.7 CQRS and Event Sourcing

**Priority:** Deep

- [ ] `@nestjs/cqrs`: `CommandBus`, `QueryBus`, `EventBus`, sagas
- [ ] When CQRS is overkill
- [ ] Event sourcing basics and projections

**Interview checkpoint**

- `@MessagePattern` vs `@EventPattern`: what are the delivery semantics of each?
- How do you guarantee an event is published when, and only when, a DB transaction commits?
- How do you make a payment endpoint idempotent?
- Compare Kafka, RabbitMQ and NATS for a given workload.
- When does CQRS earn its complexity?

**Milestone**

- Split payments and notifications out of the ticketing project as services, with an outbox, idempotent consumers and a booking saga

---

## Phase 10: Architecture at Scale

### 10.1 Structuring Large Nest Codebases

**Priority:** Core

- [ ] Organizing by feature module vs by layer, and defining module boundaries
- [ ] A modular monolith, with boundaries enforced by lint rules or dependency checks
- [ ] DDD tactical patterns in Nest: entities, value objects, aggregates, domain events
- [ ] Hexagonal and clean architecture: ports as injection tokens, adapters as providers
- [ ] Keeping Nest decorators out of the domain layer

### 10.2 Monorepos and Libraries

**Priority:** Core

- [ ] Nest CLI workspaces and libraries with the Rspack builder
- [ ] Nest CLI monorepo vs Nx vs Turborepo
- [ ] Shared contract packages for DTOs and message schemas

### 10.3 Request Context and Multi-tenancy

**Priority:** Deep

- [ ] The `AsyncLocalStorage` recipe, and `nestjs-cls`
- [ ] Tenant resolution, database-per-tenant vs schema-per-tenant vs a shared schema, durable providers

### 10.4 Standalone Apps and CLIs

**Priority:** Elective

- [ ] `createApplicationContext` for scripts, workers and cron containers
- [ ] CLIs with `nest-commander`, and the REPL

**Interview checkpoint**

- How would you structure a Nest codebase of 50 modules for 6 teams?
- How do you keep the domain layer independent of the framework?
- How do you pass the current user or tenant to deep code without request-scoped providers?

**Milestone**

- Refactor the ticketing project into a modular monolith in a CLI monorepo with shared libraries and enforced boundaries

---

## Phase 11: Performance, Observability and Production

### 11.1 Performance

**Priority:** Deep

- [ ] The Fastify adapter, SWC builds, startup time, lazy modules
- [ ] Profiling: `--inspect`, flame graphs, event loop lag
- [ ] Moving CPU work off the event loop with worker threads or queues
- [ ] Load testing with k6 or autocannon
- [ ] Finding memory leaks with heap snapshots, including leaks from listeners and request scope

### 11.2 Observability

**Priority:** Core

- [ ] Logs, metrics and traces, tied together with correlation IDs
- [ ] The `@nestjs/observe` SDK: `ObserveModule.forRoot`, passing `ObserveInstrument` to `NestFactory.create`
- [ ] OpenTelemetry, with auto and manual instrumentation and distributed tracing across HTTP and queues
- [ ] Error monitoring, Prometheus metrics, choosing an APM, and the vendor lock-in trade-off

### 11.3 Containers and Deployment

**Priority:** Core

- [ ] A multi-stage Dockerfile, a non-root user, PID 1 and signal handling
- [ ] Kubernetes probes, graceful shutdown, autoscaling
- [ ] Serverless: cold starts and lazy modules. AWS Lambda disables `require(esm)`, so CJS apps need `NODE_OPTIONS=--experimental-require-module`.
- [ ] CI/CD, Nest Devtools in CI, zero-downtime migrations

### 11.4 Upgrades and Maintenance

**Priority:** Core

- [ ] `nest upgrade --dry-run`, reading migration guides, dependency hygiene
- [ ] Migrating a project from CommonJS to ESM
- [ ] Moving an Express app to Nest incrementally

**Interview checkpoint**

- Your Nest API's p99 latency doubled after a release. How do you investigate?
- How do you trace one request across an API, a queue and a worker?
- How do you deploy with zero downtime, including database migrations?

**Milestone**

- Containerize the ticketing project, add tracing and metrics, load test it, and fix the top bottleneck

---

## Phase 12: AI and MCP With NestJS

**Priority:** Elective, but directly relevant to the AI/ML track.

The official docs added MCP and AI sections in v12. Only the page titles were checked when this roadmap was written, so research the details when we reach this phase.

### 12.1 Building MCP Servers

- [ ] MCP overview and primitives: tools, resources, prompts
- [ ] Transports
- [ ] Testing MCP servers

### 12.2 AI Features in Nest Apps

- [ ] The AI section in the docs: models, tools, agents, embeddings, testing
- [ ] Streaming LLM output over SSE, and queues for long-running jobs
- [ ] Calling a self-hosted model (Ollama on the A6000 server) from a Nest service
- [ ] Retrieval with embeddings in Postgres through pgvector

**Milestone**

- Build an MCP server that exposes ticketing data, plus an SSE endpoint that streams LLM responses

---

## Phase 13: Interview Preparation

This phase runs alongside the others. Each phase's interview checkpoint feeds into it.

### 13.1 Concept Question Bank

**Priority:** Core

- [ ] Write answers to every interview checkpoint question in a dedicated doc
- [ ] Explain each Deep topic aloud in under 2 minutes

### 13.2 Live Coding and Code Reading

**Priority:** Core

- [ ] Write a guard, interceptor, pipe, filter and dynamic module from scratch in about 20 minutes each
- [ ] Debug a broken DI graph, a circular import and a scope bubbling issue

### 13.3 System Design With NestJS

**Priority:** Core

- [ ] Design a URL shortener, a rate limiter, a notification service, a ticket booking system and a chat app
- [ ] For each design, map components to Nest features: modules, queues, transports, caching

### 13.4 Comparisons and Trade-offs

**Priority:** Core

- [ ] Nest vs Express, Fastify, Hono, FastAPI and Spring Boot
- [ ] Monolith vs microservices, and REST vs GraphQL vs gRPC
- [ ] Prepare stories about production incidents, migrations and design decisions

---

## Capstone Project: Event Ticketing Platform

One project grows across the phases. Ticket booking exercises concurrency, locking, idempotency, queues, real-time updates and payments webhooks, and it is a common system design interview question.

Phases 1 to 3 use the smaller tasks API so the focus stays on the framework. The capstone starts in Phase 4. Each phase's `NN_milestone_ticketing/` builds on the previous phase's solved code (see [Exercise Workflow](#exercise-workflow)).

| Phase | Increment |
|---|---|
| 4 | REST API for events, venues and seats on Postgres, transactional booking with locking, Redis caching |
| 5 | Authentication, roles (organizer, customer, admin), ownership checks, throttling |
| 6 | A full test suite with Testcontainers in CI |
| 7 | Seat-hold expiry cron, email queue, structured logs, health probes |
| 8 | Live seat map over WebSockets, a GraphQL read API |
| 9 | Payments and notifications as services, outbox, idempotent webhooks, a booking saga |
| 10 | Modular monolith in a monorepo |
| 11 | Docker, tracing, load testing, tuning |
| 12 | An MCP server and an AI assistant for event search |

---

## Appendix A: FastAPI to NestJS Concept Map

| FastAPI | NestJS | Key difference |
|---|---|---|
| `APIRouter` | Controller plus module | Nest modules also define DI boundaries. |
| `Depends()` | Providers and constructor injection | FastAPI resolves a call graph on each request. Nest builds long-lived singletons at startup. |
| `Depends()` with `yield` | Interceptors, or request-scoped providers | Cleanup after the handler maps to `finalize` in an interceptor. |
| Pydantic models | DTO classes with class-validator, or Zod with Standard Schema | Nest validation runs in a pipe, which you must register. |
| `response_model` | Serialization interceptors | Both stop extra fields leaking into responses. |
| Middleware | Middleware | Nest middleware runs before guards and doesn't know which handler will run. |
| Exception handlers | Exception filters | Filters can be scoped to a route, controller or the whole app. |
| Security dependencies | Guards | Guards get the `ExecutionContext` and route metadata. |
| `lifespan` | Lifecycle hooks | Nest has hooks per module and per provider. |
| `BackgroundTasks` | Event emitter or BullMQ queues | Use a queue when the work must survive a crash. |
| `TestClient` | `supertest` with `createNestApplication` | |
| `app.dependency_overrides` | `overrideProvider` in `Test.createTestingModule` | |
| Auto OpenAPI from type hints | `@nestjs/swagger` with the CLI plugin | Nest needs decorators or the plugin to produce the spec. |
| SQLAlchemy session | MikroORM `EntityManager`, closest match | Prisma and Drizzle have no unit of work. |

---

## Appendix B: Sources

- [NestJS official documentation](https://docs.nestjs.com/): its sidebar was used to check coverage section by section.
- [NestJS migration guide, v11 to v12](https://docs.nestjs.com/migration-guide)
- [NestJS v11 migration guide](https://docs.nestjs.com/v11/migration-guide)
- [Injection scopes (official docs)](https://docs.nestjs.com/fundamentals/injection-scopes)
- [`@nestjs/core` on the npm registry](https://registry.npmjs.org/@nestjs/core/latest)
- [InfoQ: NestJS 12, ESM Packages, Standard Schema Validation and Native Observability](https://www.infoq.com/news/2026/10/nestjs-12-observability/)
- [Trilon: NestJS v12 is Coming](https://trilon.io/blog/nestjs-12-is-coming) (written before the release)
- [DEV: NestJS 12 deep dive](https://dev.to/x4nent/nestjs-12-deep-dive-full-esm-migration-standard-schema-route-validation-and-the-4fe0) (written before the release)
- [Announcing TypeScript 7.0 (Microsoft DevBlogs)](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)
- [TypeScript `erasableSyntaxOnly` option](https://www.typescriptlang.org/tsconfig/erasableSyntaxOnly.html)
- [Node.js: running TypeScript natively](https://nodejs.org/download/release/v24.5.0/docs/api/typescript.html)
- [LogRocket: TypeScript 6 migration guide](https://blog.logrocket.com/typescript-v6-migration-guide/) (third party, used only for the 6.0 defaults, which still need checking)
- [Coddy: NestJS interview questions](https://coddy.tech/interview-questions/nestjs)
- [Hyring: Top NestJS interview questions (2026)](https://hyring.com/jobseeker-toolkit/interview-questions/technical/nestjs)
- [DEV: NestJS roadmap for 2025](https://dev.to/tak089/nestjs-roadmap-for-2025-5jj)

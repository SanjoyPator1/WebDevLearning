# NestJS Interview Cheat Sheet

Built from the notes-api practice sessions, 2026-11-22.

## Must be exact

These eight facts are the ones where a wrong word signals a wrong idea. Get them right, and loose wording elsewhere is fine.

| Topic | Say this | Common slip |
| --- | --- | --- |
| 400, 401, 403 | 400 is a malformed request. 401 is missing or invalid credentials (named Unauthorized, means unauthenticated). 403 is a known identity without permission. | Calling a wrong API key a 403, or calling 401 a bad request |
| `exports` | A list inside the `@Module` decorator naming providers that other modules may use. The `export class` keyword is plain TypeScript and separate. | Saying you export the whole module |
| Sharing a provider | Two halves: `exports` in the owning module, `imports` in the consuming module. Missing either half gives a startup error. | Doing only one half |
| `@Injectable()` | Marks the class, but it must also be listed in a module's `providers` array. | Thinking the decorator alone is enough |
| Exception filters | Run only when something throws, from any stage. They are not a step in the normal flow. | Placing filters after pipes in the order |
| Interceptors vs pipes | Interceptors run before pipes on the way in. A pipe sees one argument, an interceptor wraps the whole call. | Putting pipes before interceptors |
| `APP_GUARD` | Also global, wherever it is declared. Nest builds the class, so injection works and tests pick it up. | Thinking it limits the guard to one module |
| Middleware | Runs first, before guards. Sees the raw request and response, and does not know the target handler. | Saying it runs again on the way out |

## Request lifecycle

Middleware runs first, then guards, interceptors and pipes, and only then your controller; exception filters sit outside the flow and catch a throw from any stage.

1. **Middleware:** raw request. Logging, request id.
2. **Guard:** allow or deny. API key, roles.
3. **Interceptor (in):** wraps the handler. Start a timer, check a cache.
4. **Pipe:** validates or transforms one argument.
5. **Controller:** takes the call and hands it to the service.
6. **Service:** business logic runs here.
7. **Interceptor (out):** success only. Wrap, time or cache the result.
8. **Response:** goes to the client.

Exception filters run only when something throws, from any of stages 1 to 7. They build the error response, and the later stages are skipped. On a valid request with a valid key, no filter runs.

**What your own tests showed:**

- A missing key stops at the guard with a 401. The middleware still logged the request, and the interceptor never ran.
- An invalid body stops at the pipe with a 400, but only if the guard let it through. With no key you got a 401 first.
- A missing note throws `NotFoundException` in the service, which gives a 404 through your filter.

**Happy path first:** name the stages in order, then say no filter runs. Then add the failure branches.

**Tight answer:** "The request hits middleware, then guards, then interceptors, then pipes, then the controller, which calls the service. The result flows back out through the interceptors. Exception filters catch anything thrown at any stage."

## Building blocks

A NestJS app is a tree of modules, each grouping controllers and providers, with a container that injects providers wherever a constructor asks for them.

- **Module:** a class with `@Module({ controllers, providers, imports, exports })` that groups one feature.
- **Controller:** defines routes with `@Controller`, `@Get`, `@Post` and so on. It takes the request, calls a service and returns the result, so it stays thin.
- **Provider:** anything the container manages, most often a service holding business logic. It needs `@Injectable()` and an entry in a module's `providers`.
- **Dependency injection:** a class declares what it needs in its constructor. Nest creates one shared instance (a singleton) and passes it in.

DI matters for three reasons: loose coupling (the controller never calls `new`), easy testing (hand in a fake), and one shared instance.

**Sharing a provider across modules** takes both halves of the handshake:

```typescript
// users.module.ts
@Module({
  controllers: [UsersController],
  providers: [UsersService],
  exports: [UsersService],
})
export class UsersModule {}

// auth.module.ts
@Module({
  imports: [UsersModule],
  providers: [AuthService],
})
export class AuthModule {}

// auth.service.ts
constructor(private readonly usersService: UsersService) {}
```

The root module (`AppModule`) imports every feature module, and `main.ts` passes `AppModule` to `NestFactory.create`.

**One-line answer:** "Dependency injection means a class receives its dependencies instead of creating them. In Nest, I mark a class with `@Injectable()`, register it as a provider and declare it in the constructor. The container creates one instance and injects it."

## DTOs, entities and validation

An entity is the full stored record. A DTO is the contract for what crosses the API boundary in one operation.

| | Entity | DTO |
| --- | --- | --- |
| Describes | The full record, including server-set fields like `id` | Only what a client may send or receive for one operation |
| Example | `Note { id, title, content }` | `CreateNoteDto { title, content }` |
| Maps to | A database table, once an ORM is added | A request body |

- The create DTO leaves out `id` because the server generates it.
- DTOs describe request bodies, so they exist for create and update. For get or delete by id, the id arrives as a URL parameter through `@Param`.
- `UpdateNoteDto` uses `PartialType(CreateNoteDto)`, so every field becomes optional.
- They stay separate so clients cannot set or see internal fields, and each can change on its own.
- Python parallel: entity is like an ORM model, DTO is like a Pydantic schema. Unlike Pydantic, the DTO enforces nothing until the pipe is on.

**How a bad body becomes a 400:**

1. `ValidationPipe` uses `class-transformer` to turn the plain request body into a `CreateNoteDto` instance.
2. `class-validator` decorators such as `@IsString()` and `@IsNotEmpty()` check each field.
3. On failure the pipe throws `BadRequestException` with a message array. The controller and service never run, and the exception filter shapes the response.

Register it once in `main.ts`: `app.useGlobalPipes(new ValidationPipe({ whitelist: true }))`.

- `whitelist: true` strips any property that has no validator decorator. Without it, extra fields pass through, which is risky with `Object.assign`.
- `forbidNonWhitelisted: true` rejects extras with a 400 instead of stripping them.
- Every DTO field needs at least one decorator, or whitelisting strips it too.

**Pipes also transform.** `@Param('id', ParseIntPipe) id: number` converts the string to a number and rejects `abc` with a 400. A malformed id is a 400. A well-formed id that does not exist is a 404, thrown as `NotFoundException` by the service.

## Middleware, guards, interceptors, pipes, filters

Each one answers a different question, and the clearest way to choose is by when it runs and what it can see.

| Component | Runs when | Sees | Typical job | Attach with |
| --- | --- | --- | --- | --- |
| Middleware | First, before guards | Raw request and response only, not the target handler | Request logging, request id | `configure(consumer)` with `apply` and `forRoutes`, or `app.use` |
| Guard | After middleware, before interceptors | Execution context, so it knows the handler | Allow or deny: API key, roles | `@UseGuards`, `useGlobalGuards`, or `APP_GUARD` |
| Interceptor | Before pipes on the way in, and again on the way out for successful responses | Execution context and the handler's result stream | Timing, caching, response wrapping | `@UseInterceptors`, `useGlobalInterceptors`, or `APP_INTERCEPTOR` |
| Pipe | After interceptors, just before the handler | One argument at a time | Validate or transform input | Parameter pipes, `@UsePipes`, `useGlobalPipes` |
| Exception filter | Only when something throws, from any stage | The exception and the request context | Shape error responses, log errors | `@UseFilters`, `useGlobalFilters`, or `APP_FILTER` |

**Which one to pick:**

- Allow or deny a request: guard.
- Validate or convert one input: pipe.
- Wrap, time or cache a successful response: interceptor.
- Shape an error response: exception filter.
- Needs to exist even for requests a guard rejects, like a request id: middleware.

**Details that come up in follow-ups:**

- A guard that returns `false` gives a 403. Throwing `UnauthorizedException` gives a 401 with your own message.
- An interceptor calls `next.handle()`, which returns an RxJS Observable. `tap` looks at the value without changing it, and `map` replaces it. Both run only on success, so errors skip them and reach the filters.
- Two filters work well together: `@Catch(HttpException)` keeps the status and structured messages, and a catch-all `@Catch()` logs the real error and returns a generic 500 so internals never reach the client. Register the catch-all first, so the specific filter gets the first chance.
- To keep validation messages in a custom filter, read `exception.getResponse()`, because `exception.message` is only a short summary.
- Class middleware registered in a module supports injection and is active in tests. `app.use` in `main.ts` supports neither.
- `useGlobalGuards(new ...)` in `main.ts` skips injection and is not active in end-to-end tests. `APP_GUARD` and its siblings fix both.

## Status codes

Learn the families first: 2xx means success, 4xx means the client got something wrong, 5xx means the server broke. The only confusing cluster is 400, 401 and 403.

| Code | Name | Use it when | In your notes API |
| --- | --- | --- | --- |
| 200 | OK | A read, update or delete succeeded | GET, PATCH and DELETE by default |
| 201 | Created | A POST created a resource | POST by default |
| 204 | No Content | Success with no body | Not used here; Nest's DELETE returns 200 |
| 400 | Bad Request | The request itself is malformed | `ValidationPipe` and `ParseIntPipe` |
| 401 | Unauthorized | Credentials are missing or invalid | `ApiKeyGuard` throwing `UnauthorizedException` |
| 403 | Forbidden | The identity is known but lacks permission | A guard returning `false` |
| 404 | Not Found | The request is fine but the resource is missing | `NotFoundException` from the service |
| 409 | Conflict | The request clashes with current state | Not used here |
| 500 | Internal Server Error | An unexpected failure | The catch-all filter |

401 means "I can't verify who you are." 403 means "I know who you are, and you can't do this." A wrong API key is therefore a 401, and the name Unauthorized really means unauthenticated.

## How to answer

Lead with the answer in one sentence, then add detail only if the interviewer wants it.

- **Shape:** a one-line definition, the contrast with the nearest neighbour, then one example from your own notes API.
- **Name the exact term:** `@Catch(HttpException)`, `ParseIntPipe`, `NotFoundException`, `APP_GUARD`, `exports`.
- **Happy path first,** then the failure branches.
- **When unsure,** say what you do know and how you would find out. A guess lands worse.
- **Use your own project.** Real moments beat recited definitions: the 401 that beat the 400 because guards run before pipes, the logger that printed a request the guard rejected, and the filter that lost the validation messages until it read `getResponse()`.

**Still to practise:**

- Custom pipes: implement `PipeTransform` and its `transform` method, for example a pipe that trims a title.
- A caching interceptor: return `of(cachedValue)` on a hit, and use `tap` to store the result on a miss.
- A timeout interceptor: the `timeout` operator plus `catchError`, converting to `RequestTimeoutException` (408).
- A `@Public()` decorator with `Reflector`, to leave one route open under a global guard.
- A real database through TypeORM or Prisma in place of the in-memory array, which also breaks once you run more than one server instance.

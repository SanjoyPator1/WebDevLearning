# NestJS Mock Interview Q&A

Built from the notes-api practice sessions, 2026-11-22.

Thirty-one questions from our mock rounds with model answers, then fourteen extra questions we did not reach. Each answer is written to be spoken in 30 to 60 seconds.

## Core building blocks

Five questions on controllers, services, dependency injection and modules, the foundation that every later answer builds on.

**Q1. What is a controller, and how is it different from a service?**

A controller handles incoming HTTP requests and returns responses. A service holds the business logic. The controller stays thin: it pulls out the params and body, calls the service through constructor injection, and returns the result. Controllers are registered in the module's `controllers` list.

_Watch for:_ don't say a controller does nothing. It does very little logic, but it maps routes and extracts params and the body.

**Q2. What is dependency injection, and why does NestJS use it?**

Dependency injection means a class receives its dependencies instead of creating them. In Nest, I mark the service with `@Injectable()`, register it as a provider and declare it in the controller's constructor. Nest's container creates one instance and injects it. That gives loose coupling, easy testing with a fake, and one shared instance.

_Watch for:_ name who does the injecting, which is the container. Code reuse is a benefit, not the definition. Say the `new` keyword, not "new constructor".

**Q3. What is a module, and what do controllers, providers, imports and exports do?**

A module is a class decorated with `@Module` that groups one feature. `controllers` lists the controllers whose routes it handles. `providers` registers injectable classes in the module's container. `imports` brings in other modules, so their exported providers become available. `exports` makes selected providers available to modules that import this one.

_Watch for:_ `exports` lists providers, not the whole module. The `export class` keyword is plain TypeScript and a separate thing. `providers` can hold any injectable class, such as repositories and helpers, not only services.

**Q4. The auth module needs a method from the users service. What do you write, and where?**

In the users module, add `UsersService` to `exports`. In the auth module, add `UsersModule` to `imports`. Then `AuthService` declares `UsersService` in its constructor, and Nest injects it. If either half is missing, Nest fails at startup saying it can't resolve the dependency.

A picture that helps: `exports` puts an item on the public shelf, and `imports` is walking into the shop. You need both.

_Watch for:_ finish with the constructor step, since nothing is used without it. The TypeScript `import` line at the top of the file does not do the Nest wiring.

**Q5. What makes a class injectable, and how is a provider different from a controller?**

`@Injectable()` alone is not enough. The class must also be listed in a module's `providers` array, which puts it in the container. A controller handles routes and delegates. A provider is any class the container manages, most often a service.

_Watch for:_ without the `providers` entry, Nest fails at startup even though the decorator is there. Don't list a service in a second module's `providers` to share it, because that creates a second instance. Export it and import the module instead.

## Data, validation and errors

Six questions on DTOs, pipes and the two errors your notes API returns, a 400 for bad input and a 404 for a missing note.

**Q6. What is the difference between an entity and a DTO, and why does the create DTO leave out the id?**

An entity is the full stored record, including server-set fields like the id. A DTO describes only what may cross the API boundary for one operation, like create or update. The create DTO leaves out the id because the server generates it. They stay separate so clients cannot set or see internal fields, and each can change on its own.

_Watch for:_ DTOs describe request bodies, so there is no delete DTO or read-by-id DTO. Those ids arrive as URL parameters through `@Param`. A DTO only describes a shape. Enforcing it takes `class-validator` decorators plus the `ValidationPipe`.

**Q7. What is a pipe, and how does the ValidationPipe use a DTO to validate a request?**

A pipe runs just before the controller method and either validates or transforms one incoming argument. The `ValidationPipe` uses `class-transformer` to turn the plain body into a DTO instance. Then `class-validator` checks it against the decorators on the fields, and the pipe throws a `BadRequestException` with a 400 if the check fails. I register it once with `app.useGlobalPipes` in `main.ts`.

_Watch for:_ the order is middleware, guards, interceptors, pipes. There is no separate "validator" step. Say that pipes transform as well as validate.

**Q8. What does `whitelist: true` do, and what stricter option exists?**

It strips any property that has no validator decorator, so an extra `id` of 99 in a request body never reaches the service. The stricter option is `forbidNonWhitelisted`, which rejects the request with a 400 instead of stripping silently. Without the whitelist, extra fields pass through, which is risky with `Object.assign` in an update method.

_Watch for:_ it works on fields, not whole DTOs. Every DTO field needs at least one decorator, or the whitelist strips it too.

**Q9. Why do ids from the URL need converting to numbers, and how do you do it?**

URLs carry only text, so the id arrives as a string while the entity uses a number. I put `ParseIntPipe` on the parameter: `@Param('id', ParseIntPipe) id: number`. It converts the value and rejects `abc` with a 400 before the service runs. A plus sign in front of the id also converts, but it turns `abc` into `NaN` silently.

**Q10. Walk me through how a create request with an empty title ends up as a 400.**

The request passes middleware, the guard and the interceptors, then reaches the `ValidationPipe`. The pipe turns the body into a `CreateNoteDto`, and `@IsNotEmpty()` fails on the title. The pipe throws a `BadRequestException` carrying a message array. The controller and service never run, and my `HttpExceptionFilter` shapes the response, reading `exception.getResponse()` to keep the detailed messages.

_Watch for:_ name the pieces: `IsNotEmpty`, `ValidationPipe`, `BadRequestException`.

**Q11. Why throw `NotFoundException` instead of returning null, and where do your 404 and 400 come from?**

Throwing gives the client a 404 with a clear message. Returning null would send a 200 with an empty body and hide the failure. Throwing also stops the code, so the controller never has to check for a missing value. Nest turns the thrown `HttpException` into the JSON response through its exception layer.

The two errors have different sources. A malformed id like `abc` is a 400 from `ParseIntPipe`, because the request itself is invalid. A well-formed id that does not exist is a 404 from `NotFoundException` in the service, because the request is fine but the resource is missing.

_Watch for:_ 400 is bad request, 403 is forbidden, 404 is not found. In the mock round, 403 and 401 were mixed up with 400 more than once.

## Filters and guards

Six questions on how errors are shaped and how requests are blocked, including the 401 versus 403 mix-up that came up twice.

**Q12. What is an exception filter, and why would you write a custom one?**

An exception filter catches exceptions thrown anywhere in the request pipeline and turns them into the HTTP response. Nest's built-in filter already handles `HttpException`. I write a custom one so every error has the same shape, such as `success`, `statusCode`, `message`, `path` and `timestamp`. I register it globally in `main.ts`, or with `@UseFilters` on one route or controller.

_Watch for:_ it is Nest, not Node.js, that produces the default error shape. A filter is not a step after the controller. It runs only when something throws, from any stage, so a successful request never touches it. Name the `@Catch` decorator.

**Q13. Why keep two filters instead of one?**

The first filter uses `@Catch(HttpException)` and keeps the status and structured message of intentional errors, like a 404 or a validation 400. The second is a catch-all `@Catch()` that logs unexpected errors and returns a generic 500, so internals never reach the client. Two filters keep each job separate and easy to test, and the decorator does the routing instead of an `if`. One filter with an `instanceof HttpException` check would also work.

_Watch for:_ the first filter catches HTTP exceptions, meaning the exception classes, not HTTP methods. Register the catch-all first, because Nest gives the filter registered last the first chance. Reversed, the catch-all would match everything and turn every 404 into a 500. To keep validation messages, read `exception.getResponse()`, since `exception.message` is only a summary.

**Q14. What is a guard, where does it sit in the lifecycle, and what happens when it blocks a request?**

A guard decides whether a request may reach the route handler, usually for authentication or authorisation. It runs after middleware and before interceptors and pipes. It implements `CanActivate`, and its `canActivate` method receives the execution context and returns `true` to allow or `false` to block. Returning `false` gives a 403, and throwing `UnauthorizedException` gives a 401 with your own message. The controller never runs. I can attach a guard to a route, a controller or the whole app.

_Watch for:_ `CanActivate` is an interface, not a class. `implements` is a contract the class must meet, not inheritance. Filters are not part of this order.

**Q15. What is the difference between a 401 and a 403, and which one is a missing API key?**

A 401 means the server cannot verify who you are, because the credentials are missing or invalid. Its official name is Unauthorized, but it really means unauthenticated. A 403 means the server knows who you are, and you lack permission for that action, like a regular user hitting an admin route. A missing API key is a 401.

_Watch for:_ a wrong key is also a 401, not a 403. A 403 only applies once identity is known.

**Q16. Where do guards sit compared to pipes, and why does the order matter?**

The order is middleware, guards, interceptors, then pipes. Guards run first so no work is spent validating or transforming a request that will be rejected anyway. In my notes API, an invalid body with no API key returned a 401, not the validation 400, which proved the guard ran before the pipe.

**Q17. Why does the guard's 401 come back in your custom filter format?**

The guard throws `UnauthorizedException`, which is an `HttpException`. My `HttpExceptionFilter`, registered globally with `@Catch(HttpException)`, catches it and builds the response. Filters catch exceptions from anywhere in the pipeline, not only from controllers.

_Watch for:_ name the exception and the decorator, and state the general rule that filters catch from any stage.

## Interceptors and middleware

Nine questions on the two pieces that wrap a request, which differ mainly in when they run and what they can see.

**Q18. What is an interceptor, where does it sit in the lifecycle, and how is it different from a pipe?**

An interceptor wraps the route handler, so it can run logic before and after it. It sits after guards and before pipes on the way in, and on the way out it only sees successful responses, because errors go to the filters. A pipe works on one argument and only on incoming data. An interceptor sees the whole execution context and the response stream, through RxJS operators on `next.handle()`.

_Watch for:_ say "wraps" the handler. Filters are not a step in this sequence.

**Q19. What is the difference between `tap` and `map` in an interceptor?**

`next.handle()` returns an Observable of the handler's result. `tap` runs a side effect, like logging or caching, and leaves the value unchanged. `map` transforms the value, so whatever it returns replaces the response. My timing interceptor uses `tap`, and my response wrapper uses `map`. Both run only on success.

A short way to remember it: `tap` looks, `map` changes.

**Q20. Why are error responses not wrapped by your response interceptor, even though it is global?**

`map` acts only on values. When the handler throws, the stream carries an error instead of a value, so `tap` and `map` are skipped and the exception goes to the filters, which build the error shape. A guard's rejection never reaches the interceptor at all, because guards run earlier.

**Q21. What is the difference between using an interceptor and a filter to shape responses?**

The trigger is different. An interceptor wraps the handler and runs on both sides of a successful request, so it suits timing, caching and wrapping responses. A filter runs only when an exception is thrown, from any stage, and builds the error response. My API uses both: the wrapper gives successes their shape, and the filters give errors theirs.

_Watch for:_ filters do not run at the end of every request. They run only on a throw.

**Q22. Name two real use cases for an interceptor, and the operators you would use.**

Caching: check the cache on the way in. On a hit, return `of(cachedValue)` without calling `next.handle()`, so the handler never runs. On a miss, run the handler and store the result with `tap`. Timeout: the `timeout` operator sets the limit and throws a `TimeoutError`, and `catchError` converts it into `RequestTimeoutException`, which gives a 408. Stripping internal fields from every response with `map` is a third option.

**Q23. Where do you register middleware, and how do you limit it to certain routes?**

For class middleware, I implement `NestMiddleware` with a `use` method. Then the module implements `NestModule` and registers it in `configure(consumer)` with `apply` and `forRoutes`. `forRoutes` accepts a path string, an object with a path and method, or a controller class. `exclude` skips routes. The functional style is a plain function registered with `app.use` in `main.ts`, which is global.

_Watch for:_ the module where `configure` lives does not limit the scope. `forRoutes` does, and `'*'` covers the whole app, so app-wide middleware belongs in `AppModule`. Class registration supports injection and is active in tests. `app.use` supports neither. The method is `exclude`, not "accept".

**Q24. Why can class middleware use dependency injection but functional middleware cannot?**

Injection only works on classes that Nest creates. Class middleware registered in `configure` is built by Nest, which reads the constructor and injects the services. Functional middleware is a plain function passed to `app.use`, which is Express's own method. Nothing in that path reads parameter types or consults the container. The workaround is fetching a service by hand with `app.get`, which is the manual wiring that DI exists to avoid.

**Q25. Why does your logger middleware print a request that got a 401, while your timing interceptor prints nothing for it?**

Middleware runs before guards, so it sees every request, and my logger prints the final status when the response finishes. The guard then throws before the interceptor runs, so the interceptor never executes and logs nothing. The filter builds the 401 response.

_Watch for:_ to log the real status code, read `res.statusCode` inside `res.on('finish', ...)`. At the moment `use` runs, it is still the default 200.

**Q26. You want a unique request id on every request. Do you build it as middleware, a guard, an interceptor or a pipe?**

Middleware. It runs first on every request, including ones a guard rejects, so the id exists for failures, which are the ones you most want to trace. It generates the id, attaches it to the request and sets a response header, so the logger and filters can read it. The trade-off is that middleware has no handler context and only sees the raw request and response. An interceptor would not run when a guard blocks, and its outgoing side is skipped when the handler throws.

_Watch for:_ asking who generates the id, the client or the server, is a good clarifying question to start with.

## Putting it together

Five questions that connect the pieces: the full request path, where each concern belongs, global registration, persistence and module systems.

**Q27. Walk me through what happens when a valid POST request with a valid API key hits your notes API.**

The request hits middleware first, then guards, then interceptors on the way in, then pipes, then the controller, which calls the service. The result flows back out through the interceptors, where my wrapper shapes it. Exception filters sit outside this flow and catch anything thrown at any stage. On this happy path, no filter runs.

_Watch for:_ give the happy path first, then the failure branches. Interceptors come before pipes. Middleware does not run a second time on the way out, because the response side belongs to interceptors. Filters are not a step in the sequence.

**Q28. Where would you put the API key check, and where would you put the code that wraps responses in a standard shape?**

The API key check goes in a guard, because guards run before interceptors and pipes and are built for allow-or-deny decisions. Response wrapping goes in an interceptor, using `map` on the handler's result, because filters only run on errors. Errors get their own shape from the exception filter, so clients see a consistent format either way.

Why not the alternatives: middleware could check the key but has no handler context, so it cannot read decorators. A pipe sees only one argument. An interceptor runs after the guard stage, which is too late for allow-or-deny.

**Q29. What is the difference between `useGlobalGuards` in `main.ts` and the `APP_GUARD` provider?**

Both make a guard global. With `useGlobalGuards(new ApiKeyGuard())`, I create the guard by hand, so Nest cannot inject dependencies into it, and it is not active in end-to-end tests built from `AppModule`. With `APP_GUARD`, I register it as a provider, so Nest builds it, injection works, and it is active wherever the app module loads.

```typescript
providers: [{ provide: APP_GUARD, useClass: ApiKeyGuard }];
```

In my project the guard injects `ConfigService` to read the API key from the environment. The same pattern exists as `APP_FILTER`, `APP_INTERCEPTOR` and `APP_PIPE`.

_Watch for:_ `APP_GUARD` is global wherever it is declared, not limited to that module. The guard class is still injectable in the first case. The issue is that you call `new` yourself.

_A security point from your own bug:_ read the key with `configService.getOrThrow('API_KEY')`. With plain `get`, a missing variable returns `undefined`, and a request with no key then matches it, so the guard fails open. A missing key should stop the app at startup.

**Q30. Your notes service stores data in an in-memory array. What happens on restart, and how do you fix it?**

The array lives inside the service instance, so a restart creates a fresh one and all data is lost. It also breaks when scaling, because two server instances would each hold a separate array. I would move to a database like Postgres through an ORM such as TypeORM or Prisma. The entity becomes the table definition, and the service calls a repository instead of the array. The controller, DTOs and routes stay the same.

**Q31. What is the difference between CommonJS and ESM, and which did you pick for the project?**

CommonJS is Node's original module system. It uses `require` and `module.exports`, and loads files synchronously and dynamically. ESM is the JavaScript standard. It uses `import` and `export`, is static, supports top-level `await`, and allows tree shaking. Mixing the two in one project causes friction, especially when a package ships only one format.

I picked CommonJS with Jest because it is the long-standing Nest default and most tutorials assume it. Tree shaking matters mostly for browser bundles, so it barely helps a backend.

_Watch for:_ your TypeScript source uses `import` syntax either way. The compiled output depends on the configuration.

## Extra questions, part 1: providers and modules

These six were not part of our sessions, so read each answer through once before relying on it. Interviewers often ask them as follow-ups to the dependency injection and module questions.

**Q32. What are provider scopes in NestJS?**

By default, a provider is a singleton: one instance shared across the whole app. With `Scope.REQUEST`, Nest creates a new instance for every incoming request. With `Scope.TRANSIENT`, each class that injects the provider gets its own instance. You set it with `@Injectable({ scope: Scope.REQUEST })`.

Request scope costs performance, and it bubbles up: any controller or service that injects a request-scoped provider becomes request-scoped too. Use it only when you need per-request state. Most apps stay on the default.

**Q33. What are custom providers, and what do `useClass`, `useValue` and `useFactory` do?**

The short form `providers: [NotesService]` is shorthand for `{ provide: NotesService, useClass: NotesService }`. `useClass` lets you swap the implementation, for example a fake in tests. `useValue` supplies a fixed value or object, like a constant or a mock. `useFactory` runs a function to build the value, can receive other providers through `inject`, and can be async. `useExisting` creates an alias to another provider.

```typescript
providers: [
  { provide: "DB_URL", useValue: "postgres://localhost/notes" },
  {
    provide: NotesRepository,
    useFactory: (url: string) => new NotesRepository(url),
    inject: ["DB_URL"],
  },
];
```

The token can be a class, a string or a symbol. A consumer injects a string or symbol token with `@Inject('DB_URL')`.

**Q34. What is a global module, and when would you use one?**

`@Global()` on a module makes its exported providers available everywhere, without each module importing it. The module still has to be imported once, usually in the root module, and its providers must be exported. `ConfigModule.forRoot({ isGlobal: true })` uses the same idea.

Use it sparingly. Global modules hide dependencies and make the import graph harder to read. They fit shared infrastructure like configuration or logging, not feature modules.

**Q35. What is a circular dependency, and how does Nest handle it?**

Two providers or modules depend on each other, so A needs B and B needs A. Nest cannot build either one first and fails at startup. The workaround is `forwardRef`: inject with `@Inject(forwardRef(() => B))`, and use `forwardRef` in both modules' `imports` if modules are involved.

The better fix is to change the design. Extract the shared logic into a third service that both depend on, or merge the two. A circular dependency is usually a design smell.

**Q36. What is a dynamic module, and why does `ConfigModule.forRoot()` look like a function call?**

A dynamic module is a module whose configuration is decided at the moment you import it. A static method like `forRoot` returns a module definition with providers built from the options you pass. `ConfigModule.forRoot({ isGlobal: true })` loads the `.env` file and registers `ConfigService` with those options.

The naming convention: `forRoot` for one-time app-level setup, `forFeature` for per-module setup, and `register` for per-import setup. The async variants, like `forRootAsync`, take a factory, so options can depend on other providers.

**Q37. How does Nest know what to inject when you only write a type in the constructor?**

It relies on TypeScript decorators and `reflect-metadata`. With `emitDecoratorMetadata` on, the compiler records the constructor parameter types on any decorated class. At startup, Nest reads that metadata, uses each type as a token to look up the container, and passes in the instance.

That is why an interface cannot be an injection token: interfaces vanish at runtime. Use a class, or a string or symbol token with `@Inject`.

## Extra questions, part 2: testing, auth and tooling

These eight were also not part of our sessions. If time is short, read Q38 and Q40 first, because they build directly on the dependency injection and guard work you already did.

**Q38. How do you unit test a service or controller in Nest?**

I build a small module with `Test.createTestingModule` from `@nestjs/testing`, listing only what is under test, then call `compile()` and fetch the instance with `module.get()`. For a controller, I replace the service with a fake using `useValue`, so no real logic runs. Jest is the default runner, which is why the generated files end in `.spec.ts`.

```typescript
const module = await Test.createTestingModule({
  controllers: [NotesController],
  providers: [{ provide: NotesService, useValue: { findAll: () => [] } }],
}).compile();
const controller = module.get(NotesController);
```

For end-to-end tests, I use `supertest` against an app built from `AppModule`. Anything configured only in `main.ts`, like `useGlobalPipes`, is not applied there, which is another reason to register globals through `APP_PIPE` and its siblings.

**Q39. How would you add JWT authentication?**

I use `@nestjs/jwt` to sign and verify tokens, often with `@nestjs/passport` and `passport-jwt` for the strategy. A login route checks the credentials, comparing the password with a stored hash such as bcrypt, then returns a token signed with `JwtService`, carrying the user id in the payload. A guard reads the `Authorization: Bearer` header, verifies the token, attaches the user to the request, and throws `UnauthorizedException` if it fails.

I register that guard with `APP_GUARD` for the whole app and open specific routes with a `@Public()` decorator. The secret comes from configuration, never from source code, and passwords are never stored in plain text.

**Q40. How do you do role-based access, or leave one route public under a global guard?**

A custom decorator stores metadata on the route, and the guard reads it with `Reflector`. `@Roles('admin')` is built on `SetMetadata`. In the guard, `reflector.getAllAndOverride` reads the required roles from the handler and the class, and the guard compares them with the user on the request.

The same pattern gives `@Public()`: the global guard checks for the metadata and returns `true` early.

```typescript
export const IS_PUBLIC = "isPublic";
export const Public = () => SetMetadata(IS_PUBLIC, true);

// inside the guard
const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC, [
  context.getHandler(),
  context.getClass(),
]);
if (isPublic) return true;
```

This is where 401 versus 403 matters: a missing or invalid token is a 401, and a valid user with the wrong role is a 403. `createParamDecorator` is the related tool for reading values like the current user into a parameter, for example `@CurrentUser()`.

**Q41. How do you write a custom pipe?**

A custom pipe is an injectable class that implements `PipeTransform`. It has one method, `transform(value, metadata)`, which returns the converted value or throws an exception such as `BadRequestException`. The `metadata` argument says which kind of argument it is, such as body, query or param, and what its type is.

```typescript
@Injectable()
export class TrimPipe implements PipeTransform {
  transform(value: unknown) {
    return typeof value === "string" ? value.trim() : value;
  }
}
```

I attach it to a parameter, as in `@Body('title', TrimPipe)`, to a route with `@UsePipes`, or globally. It runs just before the controller method.

**Q42. What are lifecycle hooks in Nest, and how are they different from the request lifecycle?**

Lifecycle hooks are interfaces a provider or module implements to run code at app startup or shutdown. `OnModuleInit` runs after the module's dependencies are resolved. `OnApplicationBootstrap` runs after all modules are initialised. `OnModuleDestroy`, `BeforeApplicationShutdown` and `OnApplicationShutdown` run on the way down. A typical use is opening a database connection on init and closing it on shutdown.

Shutdown hooks only fire if you call `app.enableShutdownHooks()`. The request lifecycle is a different thing: it describes how one request moves through middleware, guards and the rest.

**Q43. How is Nest different from Express, and can you swap the HTTP layer?**

Express is a minimal library for routing and middleware, and the structure is up to you. Nest is a framework built on top of it, through `@nestjs/platform-express`. It adds modules, dependency injection, decorators, and guards, interceptors, pipes and filters, so projects share one architecture, with TypeScript first.

You can swap in Fastify with `@nestjs/platform-fastify`, usually for higher throughput. Most app code stays the same, but anything that touches raw request and response objects, like my middleware typed with Express types, has to be adapted.

**Q44. How do you connect a database, and what is the repository pattern?**

I add an ORM module, such as TypeORM through `@nestjs/typeorm`, Prisma, or Mongoose for MongoDB. Entity classes become tables. I import `TypeOrmModule.forFeature([Note])` in the feature module and inject the repository into the service with `@InjectRepository(Note)`. The service then calls repository methods like `find`, `save` and `delete` instead of using an array.

The repository pattern hides data access behind one class, so the service never writes SQL, and storage is easy to swap or mock in tests. In my notes API, only the service changes. The controller, DTOs and routes stay the same. In production I use migrations, not TypeORM's `synchronize` option.

**Q45. How would you document the API and protect it from abuse?**

For documentation, `@nestjs/swagger` generates OpenAPI docs. I build a config with `DocumentBuilder`, create the document with `SwaggerModule.createDocument`, and serve it with `SwaggerModule.setup`. Decorators like `@ApiProperty` on DTO fields and `@ApiTags` on controllers enrich the output.

For rate limiting, `@nestjs/throttler` sets a request limit per time window. I register `ThrottlerGuard` as `APP_GUARD`, override a route with `@Throttle`, and skip one with `@SkipThrottle`. A client that goes over the limit gets a 429 Too Many Requests. The exact module options changed between versions, so check the docs for the installed one.

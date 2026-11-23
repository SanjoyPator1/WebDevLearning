# 1.6 Pipes

> **Topic 1.6** | Priority: Core | Prerequisites: [1.3 Controllers and Routing](03_controllers_and_routing.md), [1.4 Providers and Services](04_providers_and_services.md), [1.5 Middleware](05_middleware.md) | Time: about 3 hours reading plus 3 hours for the exercise | Exercise: [06_pipes](../../projects/phase_01_core_building_blocks/06_pipes/README.md) | Next: [1.7 Guards](07_guards.md) | Roadmap: [1.6 Pipes](../../docs/01_nestjs_roadmap.md#16-pipes)
>
> Everything marked "measured" was run against `@nestjs/common` and `@nestjs/core` 12.5.1 with the Express adapter on Node 24.22.3. For the parts that need them, `class-validator` 0.14.2 and `class-transformer` 0.5.1 were installed in a scratch project. The scratch experiments are not kept: the exercise tests reproduce the important ones.

## Table of Contents

- [Why Pipes Matter](#why-pipes-matter)
- [The Mental Model](#the-mental-model)
  - [What a pipe is](#what-a-pipe-is)
  - [Transformation and validation](#transformation-and-validation)
  - [What gets piped](#what-gets-piped)
  - [Coming from FastAPI](#coming-from-fastapi)
- [The Built-in Pipes](#the-built-in-pipes)
  - [The parse pipes](#the-parse-pipes)
  - [ParseArrayPipe and its hidden dependency](#parsearraypipe-and-its-hidden-dependency)
  - [DefaultValuePipe](#defaultvaluepipe)
  - [ParseFilePipe](#parsefilepipe)
  - [Options shared by the parse pipes](#options-shared-by-the-parse-pipes)
  - [Combining pipes](#combining-pipes)
- [Binding Pipes](#binding-pipes)
  - [The four scopes](#the-four-scopes)
  - [Class or instance](#class-or-instance)
  - [Global pipes and dependency injection](#global-pipes-and-dependency-injection)
  - [How Nest applies them](#how-nest-applies-them)
- [Writing a Custom Pipe](#writing-a-custom-pipe)
  - [PipeTransform and ArgumentMetadata](#pipetransform-and-argumentmetadata)
  - [Design rules](#design-rules)
  - [A pipe with dependencies](#a-pipe-with-dependencies)
- [A First Look at Validation Pipes](#a-first-look-at-validation-pipes)
  - [ValidationPipe](#validationpipe)
  - [StandardSchemaValidationPipe](#standardschemavalidationpipe)
  - [Which one when](#which-one-when)
- [Pipes and Errors](#pipes-and-errors)
- [Testing Pipes](#testing-pipes)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why Pipes Matter

Everything a client sends reaches your handler as untrusted text: route parameters and query values are strings, and a body is whatever JSON the client chose. A **pipe** is the step that sits between the request and your method and decides what the method receives. It is where `"5"` becomes `5`, where a malformed UUID is turned away with a 400 before any of your code runs, and where a request body is checked against a schema.

Interviewers ask about it as:

- "What is the difference between a pipe and a guard? And a pipe and an interceptor?"
- "What does `ParseIntPipe` do, and what does the handler get without it?"
- "In what order do global, controller, method and parameter pipes run?"
- "How do you write a custom pipe? What is `ArgumentMetadata`?"
- "`ValidationPipe` or Zod? What does `transform: true` do?"

Pipes run after middleware (1.5) and guards (1.7) and just before your method (1.10 has the whole order). Validation as a design topic (DTOs, `whitelist`, nested objects, async validators) is 3.2; this topic covers the mechanism and gives validation a first look.

## The Mental Model

### What a pipe is

A class with one method, `transform(value, metadata)`, that returns the value the handler will receive, or throws to stop the request:

```ts
@Injectable()
export class ParsePositiveIntPipe implements PipeTransform<unknown, number> {
  transform(value: unknown, metadata: ArgumentMetadata): number { /* return a number or throw */ }
}

@Get(':n')
find(@Param('n', ParsePositiveIntPipe) n: number) { /* n is a number here */ }
```

A pipe runs **per parameter**, with the value already extracted from the request. It does not see the request, the response or the `ExecutionContext`. That is by design: a pipe is about one value.

### Transformation and validation

The docs split pipes into two jobs. Both are the same method:

| Job | Does | Example |
|---|---|---|
| **Transformation** | returns a different value than it received | `"5"` to `5`, `"  ada "` to `"ada"`, a sku to a product, `"2020-01-02"` to a `Date` |
| **Validation** | returns the value unchanged, or throws | "is this a UUID", "is this one of the allowed colours" |

Most built-in pipes do **both**: `ParseIntPipe` converts and rejects what it cannot convert. A pipe that throws produces an exception (a `BadRequestException` for the built-ins), so the handler never runs for a bad value. A good rule for your own pipes is one job each: a `TrimPipe` that only transforms, a `ParsePositiveIntPipe` that checks and converts one thing.

### What gets piped

Not every handler parameter goes through pipes. Measured, with a global spy pipe and a handler that has `@Body()`, `@Query('n')`, `@Param('id')`, `@Headers('h')`, `@Req()` and a custom decorator:

| Parameter | Piped? | The pipe sees |
|---|---|---|
| `@Body()` / `@Body('name')` | yes | `type: 'body'`, `data` undefined or `'name'`, `metatype` the declared type |
| `@Query()` / `@Query('n')` | yes | `type: 'query'` |
| `@Param()` / `@Param('id')` | yes | `type: 'param'` |
| custom decorator (`createParamDecorator`, 1.10) | yes | `type: 'custom'`, `data` is the decorator argument |
| `@Headers()` | **no** | never reaches a pipe |
| `@Req()` / `@Res()` | **no** | never reaches a pipe |

The list is `isPipeable` in `router-execution-context.js`: body, raw body, query, param, file, files, cookies, signed cookies, and custom decorators. Headers are not on it, so a global pipe never touches a header value (the guard test in the exercise). Nest also never pipes `@Req()`, which is just the platform object.

### Coming from FastAPI

| FastAPI | Nest |
|---|---|
| `id: int` in the signature: parsed and checked by Pydantic | `@Param('id', ParseIntPipe) id: number`: **the annotation does nothing**, the pipe does |
| missing or bad value: automatic 422 | a failing pipe: 400 by default (422 through an option) |
| `limit: int = 10` default | `@Query('limit', new DefaultValuePipe(10), ParseIntPipe)` |
| `Query(ge=1)` constraints | a custom pipe, or a schema (below) |
| Pydantic body model: always validated | `@Body() dto: Dto` is only a type token until a pipe validates it |

The deepest difference: in FastAPI the type annotation **is** the validation. In Nest an annotation is erased or at most emitted as `design:paramtypes` metadata (0.3), and it takes a pipe to act on it. Forgetting the pipe compiles and runs, with strings where the types promise numbers (1.3 measured `@Query('n') n: number` receiving `"5"`).

## The Built-in Pipes

All are exported from `@nestjs/common`: `ParseIntPipe`, `ParseFloatPipe`, `ParseBoolPipe`, `ParseUUIDPipe`, `ParseEnumPipe`, `ParseDatePipe`, `ParseArrayPipe`, `DefaultValuePipe`, `ParseFilePipe` (and `ParseFilePipeBuilder`), `ValidationPipe`, `StandardSchemaValidationPipe`.

### The parse pipes

Measured on a route parameter or query value. "400" always has the body `{ message, error: 'Bad Request', statusCode: 400 }`.

| Pipe | Accepts | Rejects (message) |
|---|---|---|
| `ParseIntPipe` | an optional `-` and digits: `5`, `-5`, `007` (gives `7`) | `abc`, `5.5`, `1e3`, `0x10`, `+5`, ` 5`: `Validation failed (numeric string is expected)` |
| `ParseFloatPipe` | `5.5`, `-1.5`, `.5`, `5.`, `1e3` | `abc`, `Infinity`, `0x10`: same message |
| `ParseBoolPipe` | exactly `true` or `false` (and real booleans) | `1`, `0`, `yes`, `TRUE`: `Validation failed (boolean string is expected)` |
| `ParseUUIDPipe` | any UUID version | `not-a-uuid`: `Validation failed (uuid is expected)` |
| `ParseUUIDPipe({ version: '4' })` | v4 only | a v1 UUID: `Validation failed (uuid v 4 is expected)` |
| `ParseEnumPipe(Color)` | a **value** of the enum, case-sensitive | `Red` (a key), `green`: `Validation failed (enum string is expected)` |
| `ParseDatePipe` | an ISO string, giving a real `Date`: `2020-01-02`, `2020-01-02T10:00:00Z` | `garbage`: `Validation failed (invalid date format)`; empty or missing: `Validation failed (no Date provided)` |

Details that matter:

- `ParseIntPipe` is strict (`/^-?\d+$/` in the source) and quietly lossy for huge numbers: `99999999999999999999` is accepted and becomes `100000000000000000000`. It is not a range check.
- A numeric enum works: `ParseEnumPipe(Level)` accepts `'0'` and `'1'` and returns the **number**; `'High'` (the key) and `'2'` are rejected.
- The parse pipes reject a **missing** value (`undefined`) unless given `optional: true` (below). Measured for `ParseIntPipe` (400), `ParseEnumPipe` (400), `ParseDatePipe` ("no Date provided") and `ParseArrayPipe` (400); the option exists on all seven.
- An empty route segment never reaches a pipe: `/pages/` matches no route, so it is a 404 (measured).

### ParseArrayPipe and its hidden dependency

`ParseArrayPipe` splits a string and optionally converts each item:

| Use | Result (measured) |
|---|---|
| `new ParseArrayPipe({ separator: ',' })` on `?ids=1,2,3` | `['1','2','3']` (strings) |
| the same on `?ids=1&ids=2` | `['1','2']`: an array that is already an array is kept |
| `{ items: Number }` on `?ids=1,2,3` | `[1, 2, 3]` (numbers). The default separator is `,` |
| `{ items: Number }` on `?ids=1,x,3` | 400 `[1] item must be a number` |
| `{ items: Number }` on `?ids=1.5,2` | `[1.5, 2]`: `Number` accepts decimals |
| a missing value | 400 `Validation failed (parsable array expected)`, or `undefined` with `optional: true` |

The hidden part: **`ParseArrayPipe` builds a `ValidationPipe` internally, which needs `class-validator` and `class-transformer`.** Both are *optional* peer dependencies of `@nestjs/common` (`class-validator >=0.13.2`, `class-transformer >=0.4.1`), so `npm install` does not add them. Measured in a plain `node` run: constructing `new ParseArrayPipe({ separator: ',' })` without them logs `The "class-validator" package is missing. Please, make sure to install it to use ValidationPipe.` and then **ends the process with exit code 1**. That happens when the controller is loaded, at startup, not on the first request. Under Vitest, `process.exit` is intercepted, which is why the failure shows up as "Unhandled Rejection: process.exit unexpectedly called". The same applies to `ValidationPipe` itself. So: either install both packages, or avoid these two pipes.

### DefaultValuePipe

`new DefaultValuePipe(x)` replaces `null`, `undefined` and `NaN` with `x`, and nothing else. Measured:

| Input | Result |
|---|---|
| missing | the default |
| `?x=` (empty string) | `""`: **not** replaced |
| `?x=abc` | `abc` |

Object and array defaults are copied, so a mutable default is not shared between requests. Because an empty string is not "missing", `?page=` with `DefaultValuePipe(1)` followed by `ParseIntPipe` is a 400.

### ParseFilePipe

`ParseFilePipe` validates an uploaded file with a list of validators (`MaxFileSizeValidator`, `FileTypeValidator`) and is used on `@UploadedFile()` (3.7). It can be called directly with a file-like object, which is how this was measured:

| Input | Result |
|---|---|
| a real PNG, `size` within the limit | accepted, returned unchanged |
| `size: 2000` against `maxSize: 1000` | 400 `Validation failed (current file size is 2000, expected size is less than 1000)` |
| `undefined` or an empty object | 400 `File is required`, or accepted with `fileIsRequired: false` |
| an array (`@UploadedFiles()`) | validated one file at a time, up to the first failure |
| `ParseFilePipeBuilder().addMaxSizeValidator(...).build({ errorHttpStatusCode: 422 })` | the same failure as a 422 |

The surprise is in `FileTypeValidator`: in 12.5.1 it detects the type from the file's **content** (magic numbers, through the `file-type` package that `@nestjs/common` depends on), not from the client's `mimetype`. Measured: real PNG bytes with the header `text/plain` **passed** `fileType: 'image/png'`, and the header `image/png` on bytes that are not a PNG **failed** with `file type could not be detected from its content`. A buffer too short to identify (12 bytes) also fails. There are options to relax it (`fallbackToMimetype`, `skipMagicNumbersValidation`, `overrideMimeType`). If the file has no `buffer` (disk storage) the validator cannot read content, and the message says so. Uploads in general are 3.7.

### Options shared by the parse pipes

`ParseIntPipe`, `ParseFloatPipe`, `ParseBoolPipe`, `ParseUUIDPipe`, `ParseEnumPipe`, `ParseDatePipe` and `ParseArrayPipe` take an options object with these three (confirmed in each pipe's source and typings; measured on `ParseIntPipe`, `ParseDatePipe` and `ParseArrayPipe`). `ParseFilePipe` has `errorHttpStatusCode` and `exceptionFactory` too, and `fileIsRequired` in place of `optional`.

| Option | Effect (measured) |
|---|---|
| `errorHttpStatusCode: HttpStatus.UNPROCESSABLE_ENTITY` | the same message with status 422 and `error: 'Unprocessable Entity'` |
| `exceptionFactory: (message) => new BadRequestException({ code: 'NOT_INT', detail: message })` | the body is whatever the exception you return carries: `{"code":"NOT_INT","detail":"Validation failed (numeric string is expected)"}` |
| `optional: true` | a missing value passes through as `undefined` instead of failing |

They are per pipe **instance**, so changing them means `new ParseIntPipe({ ... })` on that parameter. To make the whole application answer pipe errors in one shape, use an exception filter (1.9) or the 3.4 error model rather than repeating `exceptionFactory`.

### Combining pipes

A decorator takes any number of pipes and they run **left to right**, each receiving the previous one's output:

```ts
@Query('limit', new DefaultValuePipe(10), ParseIntPipe) limit: number
```

Measured: with the default first, a missing value gives `10`, `?limit=5` gives `5`, `?limit=x` is a 400, and `?limit=` (empty) is a 400. With the order swapped (`ParseIntPipe, new DefaultValuePipe(10)`), a missing value is a **400**, because `ParseIntPipe` sees `undefined` first and rejects it. Order is semantics.

## Binding Pipes

### The four scopes

| Scope | How | Applies to |
|---|---|---|
| global | `app.useGlobalPipes(new Pipe())` | every route of the application |
| controller | `@UsePipes(new Pipe())` on the class | every route of the controller |
| method | `@UsePipes(new Pipe())` on a method | every pipeable parameter of that route |
| parameter | `@Param('id', Pipe)` | that one parameter |

Nest concatenates them in that order. Measured with a `TagPipe` that appends `-<tag>` to strings: global `G`, controller `C`, method `M`, and two pipes `P1`, `P2` on the parameter gave `abc-G-C-M-P1-P2`. A value passes through the whole list left to right, widest scope first.

Two consequences:

- A **method or controller** pipe runs on *every* pipeable parameter of the route, not on one. Measured: with `@UsePipes` on the controller and the method, `@Query('a')` and a custom-decorator value were both tagged (`x-G-C-M`, `custom-k-G-C-M`), while a `@Headers('h')` value stayed `hv`. A broad pipe must be written to leave values it does not care about alone (the exercise's `TagPipe` ignores non-strings; `ValidationPipe` ignores parameters without a class type).
- A global pipe is the cheapest way to enforce something for every route, and the most dangerous: it runs on all parameters of all controllers.

### Class or instance

Pass a pipe either way, in every scope:

| Form | Built by | Dependencies | Use when |
|---|---|---|---|
| `@Param('id', ParseIntPipe)` (the class) | Nest, in the module of the controller | injected | the pipe needs no arguments, or needs providers |
| `@Param('id', new ParseIntPipe({ ... }))` (an instance) | you | none: you pass them | the pipe needs constructor arguments (options, a tag) |

A class-bound pipe is built **once** and shared: measured, a pipe class used on three parameters and one `@UsePipes` across two controllers of one module was constructed once, and it received the module's `CatalogService` (the exercise's Task 6 checks that it is the same instance as the application's). An instance is as shared as you make it: `new` on a parameter creates one object for that route.

### Global pipes and dependency injection

`app.useGlobalPipes(...)` takes **instances** that you build outside the container, so a global pipe registered that way cannot have anything injected. To get a global pipe with dependencies, register it as a provider under the `APP_PIPE` token from `@nestjs/core`:

```ts
@Module({ providers: [Dep, { provide: APP_PIPE, useClass: DiPipe }] })
```

Measured: the pipe received `Dep` and was applied to every route (`z-dep`). The `{ provide, useClass }` form is a custom provider (2.2); the same pattern with `APP_GUARD` is in 1.7.

### How Nest applies them

Source (`router-execution-context.js`, `pipes-consumer.js`, `pipes-context-creator.js`):

1. At bootstrap, for each route Nest builds, per parameter, `pipes = globalPipes + controllerPipes + methodPipes` and appends the parameter's own pipes. Parameters that are not pipeable (`@Headers`, `@Req`) get an empty list.
2. Per request, each parameter value is extracted, then run through its list in order: `for (const pipe of transforms) result = await pipe.transform(result, metadata)`.
3. The parameters are processed together, not one after the other (the source collects them in one `Promise.all`), so **async pipes on different parameters overlap**. Measured: two pipes that each wait 60 ms finished within 63 ms of each other. Do not depend on the order across parameters. Within one parameter the order is exactly the list.
4. The first error wins: a throw stops the request, the handler never runs, and the exception goes to the exception filters (1.9).

A class pipe is looked up as an injectable of the controller's module (`moduleRef.injectables`), which is why a class used in `@UsePipes` is built even though it is not listed in `providers`.

## Writing a Custom Pipe

### PipeTransform and ArgumentMetadata

```ts
export interface PipeTransform<T = any, R = any> {
  transform(value: T, metadata: ArgumentMetadata): R;
}

export interface ArgumentMetadata<Metatype = any> {
  readonly type: 'body' | 'query' | 'param' | 'custom';
  readonly metatype?: Type<Metatype> | undefined;
  readonly data?: string | undefined;
  readonly schema?: StandardSchemaV1;      // new in v12
}
```

`ArgumentMetadata` is **generic in v12** (the type parameter is the class of `metatype`) and has the new optional `schema`: the Standard Schema attached to the decorator, which is what `StandardSchemaValidationPipe` reads. Measured, what a spy pipe received:

| Declaration | `type` | `data` | `metatype` |
|---|---|---|---|
| `@Body() b: CreateDto` | `body` | undefined | `CreateDto` |
| `@Body('name') n: string` | `body` | `'name'` | `String` |
| `@Body() b: Shape` (interface) | `body` | undefined | `Object` (erased, see 1.3) |
| `@Body() b: CreateDto[]` | `body` | undefined | `Array` (the element type is lost) |
| `@Query() q: Record<string,string>` | `query` | undefined | `Object` |
| `@Query('n') n: number` | `query` | `'n'` | `Number` |
| `@Param('id') id: number` | `param` | `'id'` | `Number` |
| `@Param() p: any` | `param` | undefined | `Object` |
| `@Custom('k') c: string` | `custom` | `'k'` | `String` |

`metatype` is the `design:paramtypes` entry (0.3, 1.3), which is how a validation pipe finds the DTO class to validate against.

### Design rules

- **Return the value the handler should get**, even when you change nothing. Returning `undefined` hands the handler `undefined` (measured).
- **Throw an `HttpException` subclass** for bad input. Measured: a `BadRequestException` is a 400 with your message; a plain `Error` thrown from a pipe is a **500** `Internal server error` and the real message is only logged.
- **Use the metadata for messages**: `` `${metadata.type} "${metadata.data}" must be a positive integer` `` names the exact input (`param "n"`, `query "limit"`).
- **Check the type before you parse.** The value can be a string, a number, an object or `undefined` depending on the decorator and the client. `"5.5"` and `5.5` should both be rejected by an integer pipe.
- **Pipes may be async**: `transform` can return a promise (Nest awaits it).
- **One job per pipe**, and make broad pipes (controller, method, global) ignore what they do not understand.
- **Keep pipes cheap.** A pipe runs on every request that uses it; a pipe that queries a database adds a query to each.

### A pipe with dependencies

A pipe is a provider-like class: mark it `@Injectable()` and put dependencies in the constructor (1.4), then bind the **class**. The exercise's `SkuExistsPipe` injects `CatalogService` and turns a sku into the product name, so the handler receives the entity instead of an identifier. Whether "unknown" is a 400 (a bad parameter) or a 404 (a missing resource, `NotFoundException`, 1.9) is a design choice; 400 fits "validate this input", 404 fits "this thing does not exist".

## A First Look at Validation Pipes

The deep dive (DTO design, `whitelist`, nested objects, custom and async validators, mapped types) is topic 3.2. This is enough to place the two pipes.

### ValidationPipe

`ValidationPipe` validates a DTO **class** whose properties carry `class-validator` decorators. It needs `class-validator` and `class-transformer` installed (see [ParseArrayPipe](#parsearraypipe-and-its-hidden-dependency)). Measured with `class CreateDto { @IsString() @MinLength(3) name; @IsInt() age; }` and `@Body() dto: CreateDto`:

| Setup | Request | Result |
|---|---|---|
| no pipe | `{ name: 'ab', age: 'x' }` | 201, accepted, `age` is the string `"x"` |
| `new ValidationPipe()` | the same | 400 `{"message":["name must be longer than or equal to 3 characters","age must be an integer number"],"error":"Bad Request","statusCode":400}`: `message` is an **array** |
| `new ValidationPipe()` | valid plus `extra: true` | 201, and `extra` is **kept** |
| `new ValidationPipe()` | valid | the handler gets a **plain object**, `dto instanceof CreateDto` is `false` |
| `new ValidationPipe({ transform: true })` | valid | the handler gets a real `CreateDto` instance |
| `new ValidationPipe({ whitelist: true, transform: true })` | valid plus `extra` | `extra` is **stripped** |

And a trap, measured with `@Param('id') id: number` and `@Query('q') q: number`:

| Setup | `GET /v/n/5?q=6` | `GET /v/n/abc?q=6` |
|---|---|---|
| `new ValidationPipe()` | `"5"`, `"6"` (strings, unchanged) | strings |
| `new ValidationPipe({ transform: true })` | `5`, `6` (numbers) | **200** with `id` **`NaN`** (shown as `null` in JSON) |

With `transform: true` the pipe converts primitives by the declared type, and `Number('abc')` is `NaN`, not an error: a bad id becomes `NaN` and the request **succeeds**. For route parameters and query numbers use `ParseIntPipe`; do not rely on `transform` for them.

### StandardSchemaValidationPipe

New in v12: validation against any **Standard Schema** (Zod, Valibot, ArkType, or your own). A Standard Schema is not a library: it is any object with a `~standard` property holding `version`, `vendor` and `validate(value)`, which returns `{ value }` or `{ issues }` (and may return a promise). Because it is just that, the exercise writes one by hand with no dependency:

```ts
const personSchema = {
  '~standard': { version: 1 as const, vendor: 'mine', validate: (v: unknown) => /* { value } | { issues } */ },
};

@Post()
@UsePipes(StandardSchemaValidationPipe)
create(@Body({ schema: personSchema }) person: Person) {}
```

Two halves: `@Body({ schema })` (also `@Query`, `@Param`) stores the schema in `ArgumentMetadata.schema`, and `StandardSchemaValidationPipe` reads it. Measured:

| Situation | Result |
|---|---|
| schema attached, **pipe not bound** | the schema is **ignored**: the invalid body was accepted (201) |
| pipe bound, invalid body | 400, `message` is an array of `"<path>: <message>"`: `["name: name too short","a.b: second issue"]` |
| pipe bound, valid body | the handler gets the schema's **output** (a trimmed name arrived trimmed) because `transform` defaults to **true** |
| `new StandardSchemaValidationPipe({ transform: false })` | the original input is kept |
| `{ errorHttpStatusCode: 422 }` | the same body with status 422 |
| a parameter **without** a schema | passed through untouched, so the pipe can be bound globally and only opting-in parameters are checked |
| custom decorators | not validated unless `validateCustomDecorators: true` |

Other options: `exceptionFactory(issues)`, `validateOptions` (passed to `validate`), `maxErrorMessagesLength` (issues past the limit are replaced by a single "omitted" message). The source also strips prototype-pollution keys such as `__proto__` from the value before validating it (read from `stripProtoKeys`, not measured). It has no peer dependency of its own: the schema library is yours.

### Which one when

| | `ValidationPipe` | `StandardSchemaValidationPipe` |
|---|---|---|
| Source of truth | a DTO class with decorators | a schema object |
| Needs | `class-validator`, `class-transformer` | nothing (plus your schema library) |
| Types | the class is the type | the library infers the type from the schema |
| Per-parameter opt-in | the pipe validates any class-typed parameter | only parameters with `schema` |
| Message shape | array of strings from class-validator | array of `"path: message"` |

The trade-offs, DTO versus schema-first, one source of truth for types, validation and OpenAPI, are 3.2 and 3.6.

## Pipes and Errors

A pipe failure is an exception, so it goes through the same machinery as any other (1.9):

| Thrown in a pipe | Client gets | Handler ran |
|---|---|---|
| `BadRequestException('nope')` | 400 `{"message":"nope","error":"Bad Request","statusCode":400}` | no |
| a built-in pipe rejecting a value | 400 with its message | no |
| a plain `Error` | **500** `{"statusCode":500,"message":"Internal server error"}` | no |
| `exceptionFactory` returning your exception | whatever it carries | no |

Rules: validation failures should be 4xx `HttpException`s with a message the client can act on; an unexpected bug becomes a 500 and the detail stays in the log. Pipes run before the handler, so a failure never has side effects from your code.

## Testing Pipes

Test a pipe at two levels, as the exercise does.

```ts
// 1. A pipe is a class with one method: call it directly. No Nest needed.
const pipe = new ParsePositiveIntPipe();
expect(pipe.transform('007', { type: 'query', data: 'limit' })).toBe(7);
expect(() => pipe.transform('0', { type: 'param', data: 'n' })).toThrow('param "n" must be a positive integer');

// 2. Binding, order and the real conversion need an application and supertest.
const { app } = await createApp([CustomController]);
await request(app.getHttpServer()).get('/custom/param/007').expect(200, { n: 7, type: 'number' });
```

Level 1 is fast and checks the logic with any `ArgumentMetadata` you invent. Level 2 checks what level 1 cannot: that the pipe is bound where you think, the scope order, whether the handler really receives a number, and the HTTP status. For a pipe with dependencies, level 1 means passing a fake into the constructor by hand; level 2 uses the real module (1.4). Global pipes are registered before `app.init()`: use the same `setup` step as for middleware.

## Common Pitfalls

| Pitfall | What happens | Fix |
|---|---|---|
| `@Param('id') id: number` without a pipe | a string, no error | `ParseIntPipe` |
| `ParseIntPipe` before `DefaultValuePipe` | a missing value is a 400 | default first |
| `?page=` with a default | `""` is not replaced, so `ParseIntPipe` rejects it | validate or normalise empty strings |
| `ParseArrayPipe` or `ValidationPipe` without `class-validator` and `class-transformer` | the process exits with code 1 at startup | install both, or use another pipe |
| `ValidationPipe({ transform: true })` for `id: number` | `id=abc` becomes `NaN` with a 200 | `ParseIntPipe` for params and query numbers |
| a DTO with `ValidationPipe` and no `transform` | the handler gets a plain object, not an instance | `transform: true` if you need the instance |
| extra body properties | kept unless `whitelist: true` | `whitelist` (3.2) |
| `@Body({ schema })` without the schema pipe | the schema is ignored | bind `StandardSchemaValidationPipe` |
| expecting a pipe to see `@Headers()` or `@Req()` | those are never piped | validate headers in a guard or in the handler |
| a broad controller or global pipe | runs on every pipeable parameter | make it ignore what it does not handle |
| `app.useGlobalPipes(new PipeWithDeps())` | nothing is injected | `APP_PIPE` as a provider (2.2) |
| throwing a plain `Error` from a pipe | a 500 | throw an `HttpException` subclass |
| relying on the order of pipes across parameters | they run together | order only holds inside one parameter |
| the same `exceptionFactory` repeated everywhere | inconsistent errors | an exception filter or one error model (1.9, 3.4) |
| `FileTypeValidator` trusting the `Content-Type` | in v12 it checks the bytes, so a fake header does not help and a short buffer fails | test with real file content |
| a pipe that queries a database | an extra query per request | do the lookup in the service if it is not reused |

## Interview Questions

**1. What is a pipe, and when does it run?**
A class with `transform(value, metadata)` that turns a handler argument into the value the handler receives, or throws. It runs per parameter, after middleware and guards and before the handler (interceptors that run before the handler wrap it). It sees only one value and its metadata, never the request or the execution context.

**2. What is the difference between a transformation and a validation pipe?**
A transformation returns a different value (`"5"` to `5`), a validation returns the value unchanged or throws. Most built-ins do both: `ParseIntPipe` converts and rejects what it cannot convert. It is the same method, so a pipe can do either or both.

**3. A route has `@Param('id') id: number` and no pipe. What does the handler get?**
A string. The TypeScript annotation is erased at runtime and Nest does not convert by type; `ParseIntPipe` is what makes it a number and rejects non-integers with a 400. FastAPI differs: there the annotation is the validation.

**4. In what order do global, controller, method and parameter pipes run?**
Global, then controller, then method, then the parameter's own, and a value passes through them left to right. Pipes of different parameters run together, so only the order within one parameter is defined.

**5. `@Query('limit', ParseIntPipe, new DefaultValuePipe(10))`: what is wrong?**
Pipes run left to right, so `ParseIntPipe` sees `undefined` for a missing value and rejects it with a 400. The default has to come first. `DefaultValuePipe` also replaces only null, undefined and NaN, so an empty string is not defaulted.

**6. How do you write a custom pipe? What is `ArgumentMetadata`?**
Implement `PipeTransform`, return the value for the handler, and throw an `HttpException` for bad input. `ArgumentMetadata` says where the value came from (`type`: body, query, param, custom), the name passed to the decorator (`data`), the declared class (`metatype`, from `design:paramtypes`) and, new in v12, the attached Standard Schema (`schema`); it is generic in the metatype. A plain `Error` thrown from a pipe is a 500.

**7. How do you give a pipe dependencies? And a global pipe?**
Make it `@Injectable()` with constructor parameters and bind the class (`@Param('x', MyPipe)` or `@UsePipes(MyPipe)`); Nest builds it once in the module and injects. `app.useGlobalPipes(new MyPipe())` cannot inject, so for a global pipe with dependencies register it as a provider with the `APP_PIPE` token.

**8. Which parameters are not piped?**
`@Headers()` and `@Req()`/`@Res()`. The pipeable ones are body, query, param, files, cookies and custom decorators. So a global pipe never sees a header value.

**9. What does `ValidationPipe` need, and what does `transform: true` do?**
`class-validator` and `class-transformer` (optional peer dependencies; missing, the process exits at startup). `transform: true` makes the handler receive a real DTO instance instead of a plain object and converts primitives by the declared type, which means a `number` route parameter given `abc` becomes `NaN` with a 200, so use `ParseIntPipe` for those.

**10. How does the Standard Schema pipe differ, and what happens without the pipe?**
`StandardSchemaValidationPipe` validates against any Standard Schema (Zod, Valibot, ArkType, or a hand-written object with `~standard.validate`) attached with `@Body({ schema })`, using the schema's output as the value (`transform` defaults to true) and returning issues as `"path: message"`. The decorator only attaches the schema: with no pipe bound, the schema is ignored and the body is unchecked.

**11. Pipe, guard or interceptor?**
A pipe prepares or checks one argument and cannot see the request. A guard decides whether the handler may run at all, with the `ExecutionContext` (1.7). An interceptor wraps the handler and sees its result (1.8). Convert and validate inputs in pipes, authorize in guards, shape outputs in interceptors.

## Check Yourself

- [ ] I can say what a pipe receives and returns, and what `ArgumentMetadata` holds.
- [ ] I know which parameters are piped and which are not.
- [ ] I can say what each built-in parse pipe accepts and rejects, including the strictness of `ParseIntPipe` and `ParseBoolPipe`.
- [ ] I know the three options (`errorHttpStatusCode`, `exceptionFactory`, `optional`) and that they are per instance.
- [ ] I can predict the result of a list of pipes on one parameter, and the order across the four scopes.
- [ ] I know when a pipe is a class and when an instance, and how a global pipe gets dependencies.
- [ ] I can write a custom validating pipe and a custom transforming pipe, and say what a plain `Error` does.
- [ ] I know `ParseArrayPipe` and `ValidationPipe` need `class-validator` and `class-transformer`, and what happens without them.
- [ ] I can explain the `transform: true` NaN trap and why a schema on a decorator needs the pipe.
- [ ] I finished the exercise: [06_pipes](../../projects/phase_01_core_building_blocks/06_pipes/README.md).

## Further Reading

- Official documentation: [Pipes](https://docs.nestjs.com/pipes) (built-in pipes, binding, custom pipes, class validator, transformation use case). Not re-read for this note: the behaviour above was measured on 12.5.1 instead.
- [Standard Schema](https://standardschema.dev) for the `~standard` interface that the v12 pipe uses.
- Source worth reading in the installed `node_modules/@nestjs/`, in this order: `common/pipes/parse-int.pipe.js` and `default-value.pipe.js` (short and complete), `common/pipes/parse-array.pipe.js`, `common/pipes/standard-schema-validation.pipe.js`, `common/pipes/file/`; then `core/router/router-execution-context.js` (`createPipesFn`, `isPipeable`), `core/pipes/pipes-consumer.js` and `core/pipes/pipes-context-creator.js`.
- Related topics: [1.3 Controllers and Routing](03_controllers_and_routing.md), [1.4 Providers and Services](04_providers_and_services.md), [1.5 Middleware](05_middleware.md), 1.7 Guards, 1.8 Interceptors, 1.9 Exception Filters, 1.10 Request Lifecycle, 2.2 Custom and Async Providers, 3.2 Validation, 3.4 Error Handling Design, 3.6 OpenAPI and Swagger, 3.7 HTTP Features.

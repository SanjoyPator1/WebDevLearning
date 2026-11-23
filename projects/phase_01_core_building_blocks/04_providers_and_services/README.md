# Exercise: Providers and Services

**Topic 1.4** in the [roadmap](../../../docs/01_nestjs_roadmap.md#14-providers-and-services). Only providers and services are being learned here.
**Goal:** make classes injectable, receive dependencies through the constructor and through a property, understand why one shared instance must not hold per-call state, make a dependency optional, and put business rules in the right layer.

**Read first:** [04_providers_and_services.md](../../../notes/phase_01_core_building_blocks/04_providers_and_services.md), especially "Constructor Injection", "Singletons and Shared State", "Optional Dependencies" and "Services, Repositories and Helpers".

**Node:** the folder has an `.nvmrc` containing `24` (not part of this exercise). Run `nvm use` inside `solution/` to pick it up. On Node 24.11.1 `pnpm install` works but may print an engine warning, because Nest 12 tooling wants 24.15 or later.

## How to Start

From the repository root:

```bash
scripts/start_exercise.sh projects/phase_01_core_building_blocks/04_providers_and_services
cd projects/phase_01_core_building_blocks/04_providers_and_services/solution
nvm use
pnpm install
pnpm test
```

`pnpm test` runs `tsc --noEmit` and then the tests. The template type-checks, so the first failure is in the tests: 16 of 23 fail and 7 already pass. The 7 are guards and documentation of behaviour that works without your help (a single greeting, the singleton and eager-creation checks, the `@Optional` tests that have the client, the repository that has no rules, and the "constructor sees undefined" check).

There is no HTTP in this exercise and no `pnpm start`: providers are tested by compiling a small module around them. Modules are topic 1.2, and the test files show how.

Work in `solution/`. Never edit `template/`. `solved/` is the answer key: open it only when you are stuck.

| Command | What it runs |
|---|---|
| `pnpm test` | type check, then every test |
| `pnpm test:unit test/notifier.spec.ts` | one task's test file |
| `pnpm typecheck` | only `tsc --noEmit` |

## What You Edit

| File | Task |
|---|---|
| `src/stamp/stamp.service.ts` | 1 |
| `src/greeter/greeter.service.ts` | 2 |
| `src/reporter/base-reporter.ts` | 3 |
| `src/notifier/notifier.service.ts` | 4a |
| `src/notifier/loud-notifier.service.ts` | 4b |
| `src/items/items.service.ts` | 5 |

Given, not part of the exercise: `clock/clock.service.ts` (a stateful provider every task injects), `stamp/report.service.ts` (a finished model for Task 1), the reporter subclasses, `formatter.service.ts`, `slack.client.ts`, `items.repository.ts`, `items.errors.ts`, `normalize-name.ts`, `sleep.ts` and the tests.

## Tasks

Each task has its own folder and its own test file, so an unfinished task never breaks another one.

### Task 1: `@Injectable` and constructor injection (`test/stamp.spec.ts`)

`StampService` is a plain class. Make it a provider that receives `ClockService` through its constructor, and implement `stamp()`. Read `report.service.ts` first: it is the same thing, finished. The tests show two consumers sharing one `ClockService`.

### Task 2: a singleton must not remember per-call data (`test/greeter.spec.ts`)

`GreeterService` works when called once and gives wrong answers when two calls overlap. Run the test, read what comes back, and fix the class without changing the signature of `greet()`.

### Task 3: property injection (`test/reporter.spec.ts`)

`DailyReporter` and `WeeklyReporter` both extend `BaseReporter`, and neither takes `ClockService` in a constructor. Give `BaseReporter` its `clock` by property injection. Note what the constructor sees.

### Task 4: optional dependencies (`test/notifier.spec.ts`)

- **4a:** `NotifierService` should start when no `SlackClient` is provided.
- **4b:** `LoudNotifierService` extends it and declares its own constructor. After 4a it still fails to start without the client. Find out why and fix it.

### Task 5: service, repository, helper (`test/items.spec.ts`)

Implement `ItemsService` so that the rules live in the service: normalize the name, reject an empty one, reject a duplicate, and report a missing item. The repository, the helper and the errors are given. The tests also build the service by hand with `new`.

## Hints

Open one at a time. Try for ten minutes before each.

<details>
<summary>Task 1</summary>

Two parts: the decorator above the class, and `constructor(private readonly clock: ClockService) {}`. Without any decorator TypeScript emits no constructor parameter types, so Nest builds the class with no arguments and `this.clock` is `undefined`.
</details>

<details>
<summary>Task 2</summary>

Look at which data is created per call and where it is stored. Does `greet()` need the field at all?
</details>

<details>
<summary>Task 3</summary>

`@Inject()` also works on a property. With no argument it uses the property's type as the token. Put it above `clock` in `BaseReporter`.
</details>

<details>
<summary>Task 4</summary>

4a: `@Optional()` goes in front of the constructor parameter. 4b: read the error message of the failing test. Nest keeps the optional flags per class and per parameter, and a subclass with its own constructor does not inherit the parent's.
</details>

<details>
<summary>Task 5</summary>

The constructor is given but the class is not a provider yet. Run the tests, read the first error, and think about what Nest passes to a class it does not recognise. Then follow the numbered list in the file comment.
</details>

## Done When

- `pnpm test` exits 0: type check clean and 23 tests pass.
- You can explain, without looking, why a class without any decorator gets `undefined` dependencies and no error, why `@Optional()` must be written again on a subclass constructor, and why Task 2's bug never shows up with one request at a time.

`solved/` is the answer key. If you compare, use `diff -r solution/src solved/src`: only the six files in the table above differ from the template.

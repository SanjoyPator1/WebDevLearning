# 05 Tooling and Setup

> **Topic 0.5** | Priority: Core | Prerequisites: [01 Node.js Runtime](01_nodejs_runtime.md), [03 TypeScript Features Nest Is Built On](03_typescript_for_nest.md) | Time: 3 to 4 hours | Exercise: [07_milestone_hello_nest](../../projects/phase_00_orientation/07_milestone_hello_nest/README.md) | Next: Phase 1, topic 1.1 (see the [roadmap](../01_nestjs_roadmap.md))
>
> Everything here was run on 2026-11-20 on macOS with Node v24.11.1, npm 11.6.2, pnpm 8.15.9, `@nestjs/cli` 12.0.13, `@nestjs/core` 12.5.1 and TypeScript 6.0.3. Anything not run is marked "Not verified".

## Table of Contents

- [Why This Doc Exists](#why-this-doc-exists)
- [Node.js Versions and the Engine Warning](#nodejs-versions-and-the-engine-warning)
  - [Which Node You Need for What](#which-node-you-need-for-what)
  - [The EBADENGINE Warning](#the-ebadengine-warning)
  - [Fixing It With nvm](#fixing-it-with-nvm)
- [Installing the CLI](#installing-the-cli)
  - [Global Install, dlx or npx](#global-install-dlx-or-npx)
  - [nest new Options and Prompts](#nest-new-options-and-prompts)
  - [The Command Reference](#the-command-reference)
- [The Scaffold File by File](#the-scaffold-file-by-file)
  - [package.json](#packagejson)
  - [tsconfig.json Line by Line](#tsconfigjson-line-by-line)
  - [tsconfig.build.json](#tsconfigbuildjson)
  - [nest-cli.json](#nest-clijson)
  - [The src Folder](#the-src-folder)
  - [Vitest and the Separate E2E Config](#vitest-and-the-separate-e2e-config)
  - [oxlint and Prettier](#oxlint-and-prettier)
  - [Other Generated Files](#other-generated-files)
- [Why TypeScript Is Pinned to 6](#why-typescript-is-pinned-to-6)
- [Builders](#builders)
  - [tsc, the Default](#tsc-the-default)
  - [SWC](#swc)
  - [rspack and webpack](#rspack-and-webpack)
- [Daily Workflow](#daily-workflow)
  - [Watch Mode](#watch-mode)
  - [Debugging](#debugging)
  - [The REPL](#the-repl)
  - [nest generate and the Resource Generator](#nest-generate-and-the-resource-generator)
  - [nest info and nest upgrade](#nest-info-and-nest-upgrade)
- [CommonJS Projects](#commonjs-projects)
- [Common Pitfalls](#common-pitfalls)
- [Interview Questions](#interview-questions)
- [Check Yourself](#check-yourself)
- [Further Reading](#further-reading)

---

## Why This Doc Exists

Phase 1 onwards assumes you can scaffold a Nest project, run it, test it, debug it and read every file in it. This doc takes the real v12 scaffold apart so none of it is a black box. The hands-on part is the [07_milestone_hello_nest](../../projects/phase_00_orientation/07_milestone_hello_nest/README.md) exercise, which is a trimmed copy of this scaffold.

The CLI is under 1.5 seconds of work for everything shown here, so run each command yourself. Reading a build error once teaches more than reading about it ten times.

---

## Node.js Versions and the Engine Warning

### Which Node You Need for What

Nest 12 has several different Node floors, depending on what you are doing:

| What | Floor | Source |
|---|---|---|
| Running a Nest 12 application | Node 20.19+ or 22.12+ (21.x is not supported) | v12.0.0 release notes |
| The `nest` binary itself | Node 20.11+ | Official CLI overview |
| `nest new`, `nest generate`, `nest upgrade` (the schematics) | Node 22.22.3+, 24.15+ or 26+ | Official CLI overview, and the `engines` field that npm reported |
| Jest loading the ESM-only v12 packages in a CommonJS project | Node 24.9+ | v12 migration guide |

Node 20 reached end of life on 2026-04-30 (its last release was v20.20.2 on 2026-03-24, according to nodejs.org's release index). So although Nest 12 technically runs on Node 20.19, you should not start a new project on it. Node 22 receives security fixes only until 2027-04-30. Node 24 ("Krypton") and Node 26 ("Lithium") are the LTS lines to use. Node 26 entered LTS on 2026-10-28, with v26.13.0 as the first LTS release.

Practical rule: **develop on the newest LTS, and make CI use the same major.** The latest at the time of writing were v26.13.1, v24.22.3 and v22.23.5.

### The EBADENGINE Warning

Your default Node is v24.11.1, which is below the 24.15 floor. A fresh `npx @nestjs/cli new` on it printed:

```text
npm warn EBADENGINE Unsupported engine {
npm warn EBADENGINE   package: '@nestjs/schematics@12.0.13',
npm warn EBADENGINE   required: { node: '^22.22.3 || ^24.15.0 || >=26.0.0' },
npm warn EBADENGINE   current: { node: 'v24.11.1', npm: '11.6.2' }
npm warn EBADENGINE }
```

We ran the same command three ways, each with an **empty npm cache** so that npm had to install the CLI from scratch:

| Node | EBADENGINE lines | Project created |
|---|---|---|
| v24.11.1 | 32 (four packages: `@nestjs/schematics@12.0.13` and `@angular-devkit/core`, `schematics` and `schematics-cli` at 22.2.6, all requiring `^22.22.3 \|\| ^24.15.0 \|\| >=26.0.0`) | yes |
| v24.22.3 | 0 | yes |

Facts about it, all observed:

- It is a **warning, not an error**. On 24.11.1 the scaffold was created, installed, and its tests, build and lint all passed.
- The warning names `@nestjs/schematics` and the `@angular-devkit` packages it is built on. That is the Angular lineage of Nest's CLI showing through (see [04 NestJS Philosophy](04_nestjs_philosophy.md)).
- **npm prints it only when it installs the package.** Running the same `npx` command a second time on 24.11.1, with the CLI already cached, printed zero warnings. A missing warning therefore does not prove your Node is supported.
- **pnpm printed nothing** when installing the plain scaffold on 24.11.1, because the scaffold has no `engines` field and pnpm checks the project's own field. Once we added `"engines": { "node": "^22.22.3 || ^24.15.0 || >=26.0.0" }` (the exercise project has it), pnpm 8.15.9 printed this on 24.11.1 and nothing on 24.22.3:

```text
WARN  Unsupported engine: wanted: {"node":"^22.22.3 || ^24.15.0 || >=26.0.0"} (current: {"node":"v24.11.1","pnpm":"8.15.9"})
```

- "It works" is not "it is supported". The exercise project also passed its unit and e2e tests on v24.22.3 and v26.13.1.

### Fixing It With nvm

nvm lets several Node versions live side by side and picks one per shell. Commands, all run for this doc with nvm 0.40.3:

```bash
nvm install 24      # downloaded v24.22.3 (npm 11.19.1)
nvm install 22      # v22.23.5
nvm install 26      # v26.13.1 (npm 11.20.0)
nvm ls              # list installed versions
nvm use 24          # this shell only
nvm exec 22 node -v # run one command on another version without switching
```

`nvm exec <version> <command>` is the safest way to test something on another Node, because it never changes your shell or your default.

**Project pinning with `.nvmrc`.** A file named `.nvmrc` holds a version, and `nvm use` with no argument reads it:

```text
$ echo "24" > .nvmrc
$ nvm use
Found '.../.nvmrc' with version <24>
Now using node v24.22.3 (npm v11.19.1)
$ echo "22" > .nvmrc
$ nvm use
Found '.../.nvmrc' with version <22>
Now using node v22.23.5 (npm v10.9.9)
```

A bare major such as `24` resolves to the highest **installed** 24.x. That is convenient, but it means two machines can run different minors. Both exercise projects ship an `.nvmrc` containing `24` and an `engines` field, so `nvm use` selects a supported Node and pnpm warns when you are on an unsupported one.

**A trap with the default alias.** On this machine nvm's `default` alias was `lts/*`, which is not a fixed version. It follows whichever LTS line nvm currently knows about. After `nvm install 26`, a new terminal started on v26.13.1 instead of v24.11.1, even though nobody had changed `default`. The refresh of the LTS aliases during an install or a remote lookup caused it. If you want a stable default, pin it explicitly, for example `nvm alias default 24`, and use `.nvmrc` per project.

---

## Installing the CLI

### Global Install, dlx or npx

Three ways to get the CLI. All three print `12.0.13` for `nest --version`:

| Way | Command | Use when |
|---|---|---|
| Global | `npm i -g @nestjs/cli` then `nest new app` | You scaffold often. `nest upgrade` also wants the newest CLI first. |
| npx | `npx @nestjs/cli@latest new app` | One-off, no global state. Verified. |
| pnpm dlx | `pnpm dlx @nestjs/cli@latest new app` | You use pnpm. `--version` verified, a full `new` Not verified. |

Inside a project the CLI is a dev dependency, and `pnpm start:dev` and friends use that local copy, so the project pins its own CLI version. The global copy matters only for `nest new` and for running `nest upgrade`.

### nest new Options and Prompts

Run `nest new --help` for the full list. The real output for v12.0.13:

| Option | Meaning |
|---|---|
| `--directory [directory]` | Destination folder. |
| `-d, --dry-run` | Print what would be created. Writes nothing. |
| `-g, --skip-git` | Do not run `git init`. |
| `-s, --skip-install` | Do not install packages. |
| `-p, --package-manager [pm]` | `npm`, `yarn` or `pnpm`. |
| `-l, --language [language]` | TypeScript (default) or JavaScript. |
| `-c, --collection [name]` | Schematics collection (default `@nestjs/schematics`). |
| `--strict` | TypeScript strict mode. Defaults to true. |
| `-t, --skip-tests` | Do not generate test files. |
| `--format` | Run Prettier over the generated files. |
| `--observe` / `--no-observe` | Pre-configure, or skip, the `@nestjs/observe` setup. |
| `--minimal` | One-file app: all code in `src/main.ts`, TypeScript and ESM only. |

Note what is missing: **there is no `--type` flag.** `nest new app --type cjs` fails with `error: unknown option '--type'`. The CommonJS or ESM choice is an interactive prompt only.

When you run `nest new` in a real terminal, we observed these prompts, in this order (a pseudo-terminal run, interrupted after the second prompt):

```text
? Would you like to set up @nestjs/observe (distributed tracing, auto-correlated ...)? (Y/n)
? Which module system would you like to use?
❯ ESM (ES Modules)         [ with vitest ]
  CJS (CommonJS)           [ with jest ]
```

The first prompt defaults to yes. The CLI source says that without a terminal (CI, piped input) the observe prompt is skipped and answered no. The module-system prompt is declared in `@nestjs/schematics` as option `type` with values `cjs` or `esm`, default `esm`. That is why a non-interactive `nest new` gives you ESM with Vitest.

Our scaffold, created non-interactively with `--package-manager npm --skip-git --strict`, therefore has `"type": "module"`, Vitest and oxlint. The official CLI overview says CommonJS projects use Jest, and that both module systems use oxlint.

`--minimal` is a good way to see Nest with nothing around it. We generated one: `src/main.ts` holds an `AppService`, an `AppController` and an `AppModule` as classes in one file, plus `tsconfig.json`, `package.json` and `AGENTS.md`. Its scripts are only `build`, `start`, `start:dev` and `start:prod`: no tests, lint or formatter.

### The Command Reference

| Command | Alias | What it does |
|---|---|---|
| `nest new [name]` | `n` | Scaffold an application. |
| `nest build [apps...]` | | Compile into `dist/`. |
| `nest start [app]` | | Compile and run. |
| `nest info` | `i` | Print Node, npm, CLI and `@nestjs/*` versions. |
| `nest add <library>` | | Install a Nest library and run its install schematic. |
| `nest deploy` | | Forward to the Mau cloud service. Needs `@nestjs/mau`. |
| `nest upgrade` | `update` | Move every `@nestjs/*` package to the latest major. |
| `nest generate <schematic> [name] [path]` | `g` | Generate a Nest element. |

The generate schematics are: `application`, `class`, `configuration`, `controller`, `decorator`, `filter`, `gateway`, `guard`, `interceptor`, `interface`, `library`, `middleware`, `module`, `pipe`, `provider`, `resolver`, `resource`, `service` and `sub-app`.

---

## The Scaffold File by File

This is the real output of `nest new probe-app --package-manager npm --skip-git --strict` on 2026-11-20. Run it yourself and keep the folder open next to this doc.

```text
probe-app/
├── .gitattributes
├── .oxlintrc.json
├── .prettierrc
├── AGENTS.md
├── README.md
├── nest-cli.json
├── package.json
├── tsconfig.json
├── tsconfig.build.json
├── vitest.config.ts
├── vitest.config.e2e.ts
├── src/
│   ├── main.ts
│   ├── app.module.ts
│   ├── app.controller.ts
│   ├── app.controller.spec.ts
│   └── app.service.ts
└── test/
    └── app.e2e-spec.ts
```

### package.json

Three things matter most. `"type": "module"` makes every `.js` file in the project ESM, which is why Node runs `dist/main.js` as ESM and why `__dirname` and `require` are undefined (see [01 Node.js Runtime](01_nodejs_runtime.md)). There is no `engines` field. And the dependency list is short.

Scripts:

| Script | Runs | Notes |
|---|---|---|
| `build` | `nest build` | Compiles with `tsconfig.build.json` into `dist/`. Deletes `dist/` first (`deleteOutDir`). |
| `start` | `nest start` | Build once, run once. |
| `start:dev` | `nest start --watch` | Rebuild and restart on change. |
| `start:debug` | `nest start --debug --watch` | Same, with the inspector open on 9229. |
| `start:prod` | `node dist/main` | Runs the built output. No CLI involved. |
| `lint` | `oxlint --type-aware src/ test/` | See the oxlint section. |
| `format` | `prettier --write "src/**/*.ts" "test/**/*.ts"` | |
| `test` | `vitest run` | Runs `*.spec.ts` once. |
| `test:watch` | `vitest` | Watch mode. |
| `test:cov` | `vitest run --coverage` | Uses `@vitest/coverage-v8`. |
| `test:debug` | `vitest --inspect-brk --no-file-parallelism` | Pauses at start and waits for a debugger. |
| `test:e2e` | `vitest run --config ./vitest.config.e2e.ts` | Runs `*.e2e-spec.ts` with the second config. |
| `deploy` | `nest deploy` | Mau cloud deploy. We removed it from the exercise project because it is not part of learning Nest. |

Runtime dependencies:

| Package | Why |
|---|---|
| `@nestjs/common` | Decorators (`@Controller`, `@Injectable`), pipes, exceptions, the `Logger`. |
| `@nestjs/core` | `NestFactory` and the IoC container. |
| `@nestjs/platform-express` | The Express adapter, so Nest can serve HTTP. |
| `reflect-metadata` | The metadata polyfill that decorators write to (topic 0.3). |
| `rxjs` | Required by Nest's interceptor and observable machinery (topic 1.8). |

Dev dependencies of note:

| Package | Why |
|---|---|
| `@nestjs/cli`, `@nestjs/schematics` | The `nest` command and its generators. |
| `@nestjs/testing` | `Test.createTestingModule` (topic 6.1). |
| `vitest`, `vite`, `@vitest/coverage-v8` | Test runner. `vite` is listed explicitly at `^8` because the Vitest config relies on a Vite 8 option. |
| `supertest`, `@types/supertest`, `@types/express` | HTTP assertions for the e2e test, and types. |
| `oxlint`, `oxlint-tsgolint` | Linter and the TypeScript-aware rules backend. |
| `prettier` | Formatter. |
| `typescript` | `^6.0.2` in the scaffold. See "Why TypeScript Is Pinned to 6". |
| `@nestjs/mau` | Backs `nest deploy`. |
| `source-map-support` | Listed by the scaffold, but we found nothing in the CLI that references it, and the exercise project works without it. Not verified whether anything else needs it. |

### tsconfig.json Line by Line

```json
{
  "compilerOptions": {
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "resolvePackageJsonExports": true,
    "esModuleInterop": true,
    "isolatedModules": true,
    "declaration": true,
    "removeComments": true,
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true,
    "allowSyntheticDefaultImports": true,
    "target": "ES2023",
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": ".",
    "incremental": true,
    "skipLibCheck": true,
    "strict": true,
    "strictPropertyInitialization": false,
    "types": ["vitest/globals", "node"]
  }
}
```

| Option | Why it is there |
|---|---|
| `module`, `moduleResolution` = `nodenext` | TypeScript follows Node's real ESM and CommonJS rules. Because `package.json` says `"type": "module"`, `.ts` files are ESM, and relative imports must carry an explicit `.js` extension (`import { AppService } from './app.service.js'`). TypeScript maps `.js` back to the `.ts` file at compile time. |
| `resolvePackageJsonExports` | Honor the `exports` map in dependencies' `package.json`. It is already the behavior under `nodenext`, so this makes it explicit. |
| `esModuleInterop`, `allowSyntheticDefaultImports` | Let you write `import request from 'supertest'` for a CommonJS package. The official TypeScript 7.0 post says neither can be set to false any more, so they are effectively always on. |
| `isolatedModules` | Every file must be compilable on its own, without type information from other files. Vite, SWC and similar tools transform file by file, so this flag makes TypeScript reject code those tools would mishandle. |
| `declaration` | Emit `.d.ts` files next to the JavaScript. Needed for libraries, harmless for an app. We saw `app.controller.d.ts` in `dist/`. |
| `removeComments` | Strip comments from the emitted JavaScript. |
| `experimentalDecorators` | The legacy decorator model Nest is built on (topic 0.3). |
| `emitDecoratorMetadata` | Emit `design:paramtypes` and friends. **This is how constructor injection works.** We proved it: in a Vitest test, with the flag `true`, `Reflect.getMetadata('design:paramtypes', AppController)` returned `[AppService]`. With it `false` the same test got `undefined`. So Vitest/Vite 8 reads this flag from your `tsconfig.json`. |
| `target` = `ES2023` | The JavaScript syntax level to emit. Node 24 supports all of ES2023, so TypeScript leaves modern syntax alone. |
| `sourceMap` | Emit `.js.map` files so debuggers show TypeScript. See Debugging. |
| `outDir`, `rootDir` | Output goes to `dist/`. `rootDir` is `.` here, but `tsconfig.build.json` overrides it to `./src`. |
| `incremental` | Cache build state in a `.tsbuildinfo` file for faster rebuilds. We saw `tsconfig.build.tsbuildinfo` appear. It is a build artifact, so gitignore it. |
| `skipLibCheck` | Do not type-check `.d.ts` files inside `node_modules`. Faster, and avoids errors from conflicting dependency types. |
| `strict` | Turn on the strict family. It is the default since TypeScript 6.0, but the scaffold sets it explicitly. |
| `strictPropertyInitialization` = false | Allow class properties with no initializer. DTO classes and decorator-injected properties are assigned by the framework, not by a constructor, so the strict rule would force `!` everywhere. This is the one strictness the scaffold relaxes. |
| `types` | TypeScript 6.0 changed the default of `types` to `[]`, so nothing in `node_modules/@types` loads automatically. The scaffold lists `vitest/globals` (for `describe`, `it`, `expect`) and `node`. |

Not in the file, and worth knowing: TypeScript 6.0 also changed `rootDir` to default to the folder containing `tsconfig.json`, and removed the `baseUrl`, `outFile` and `es5` options.

### tsconfig.build.json

```json
{
  "extends": "./tsconfig.json",
  "compilerOptions": { "rootDir": "./src" },
  "include": ["src"],
  "exclude": ["node_modules", "test", "dist", "**/*spec.ts"]
}
```

`nest build` and `nest start` use this file, not `tsconfig.json`. It narrows the build to `src/`, drops test files, and sets `rootDir` to `./src`. That last line is why the output is `dist/main.js` and not `dist/src/main.js`, and why `start:prod` can run `node dist/main`. `tsconfig.json` has no `include`, so editors and the type checker see everything, including tests and Vitest configs.

### nest-cli.json

```json
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": { "deleteOutDir": true }
}
```

| Key | Meaning |
|---|---|
| `collection` | Which schematics `nest generate` uses. |
| `sourceRoot` | Where source lives. `nest generate` writes under it. |
| `compilerOptions.deleteOutDir` | Wipe `dist/` before each build, so deleted source files do not leave stale output behind. |

The same `compilerOptions` object also takes the builder choice and other build settings. The CLI help shows the matching flags (`--builder`, `--watchAssets`, `--type-check`, `--tsc`, `--entryFile`, `--env-file`), and CLI flags override the file. Of the file keys beyond the three above, we only exercised these through flags, so treat the file spelling of builder, assets and plugin options as Not verified; check the official CLI docs when you need them.

### The src Folder

`src/main.ts`:

```ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT ?? 3000);
}
await bootstrap();
```

- `await bootstrap()` at module top level is allowed because the project is ESM. In CommonJS you would write `bootstrap()` with no `await`.
- The `.js` on `./app.module.js` is the `nodenext` rule from above.
- `NestFactory.create(AppModule)` builds the whole container from the root module. `PORT` from the environment overrides 3000. We used this to run several copies side by side.

`app.module.ts`, `app.controller.ts` and `app.service.ts` are the smallest possible Nest app: a module that lists one controller and one provider, a controller with `@Get()` that calls the service, and a service that returns `'Hello World!'`. Their roles are topics 1.2, 1.3 and 1.4. For now, notice the constructor injection in the controller:

```ts
constructor(private readonly appService: AppService) {}
```

There is no `@Inject()` anywhere. Nest reads the parameter type from the emitted metadata. That single line is the reason `emitDecoratorMetadata` is on.

`src/app.controller.spec.ts` builds a tiny testing module containing only the controller and the service, and calls `getHello()` directly. `test/app.e2e-spec.ts` imports the whole `AppModule`, creates a real HTTP server with `createNestApplication()`, and uses Supertest to call `GET /`.

### Vitest and the Separate E2E Config

```ts
// vitest.config.ts
import { defineConfig } from 'vitest/config';
export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: { globals: true, root: './', include: ['**/*.spec.ts'] },
});
```

- `resolve.tsconfigPaths: true` makes Vite honor the `paths` aliases in `tsconfig.json`. The scaffold's own comment says it needs Vite 8, which is why `vite` is a direct dev dependency.
- `globals: true` exposes `describe`, `it` and `expect` without imports, matching `"types": ["vitest/globals"]` in the tsconfig.
- `include: ['**/*.spec.ts']` does **not** match `app.e2e-spec.ts`, because that name ends in `-spec.ts`, not `.spec.ts`. We confirmed that `pnpm test` runs exactly one file.
- `vitest.config.e2e.ts` is the same config with `include: ['**/*.e2e-spec.ts']`. Two configs keep fast unit tests and slower end-to-end tests apart. `pnpm test:e2e` selects the second one with `--config`.

Vitest versus Jest: Vitest runs on Vite, so it transforms TypeScript itself and is ESM-native. That is why the ESM scaffold uses it. Jest needs extra configuration to load ESM and, per the v12 migration guide, loads Nest 12's ESM-only packages only on Node 24.9 or later. In practice: use Vitest for ESM projects, expect Jest in older CommonJS codebases. Mocks differ: `vi.fn()`, not `jest.fn()`.

### oxlint and Prettier

`pnpm lint` runs `oxlint --type-aware src/ test/`. The `.oxlintrc.json` is:

```json
{
  "rules": {
    "typescript/no-explicit-any": "off",
    "typescript/no-floating-promises": "error"
  },
  "env": { "node": true }
}
```

`any` is allowed (Nest code uses it at framework seams), and a promise that is neither awaited nor handled is an error. We checked that it really fires:

```text
src/bad.ts:3:3: error typescript(no-floating-promises): Promises must be awaited, add void operator to ignore. help: The promise must end with a call to .catch, or end with a call to .then with a rejection handler, or be explicitly marked as ignored with the `void` operator.
```

This rule needs type information, which is why `oxlint-tsgolint` is installed and `--type-aware` is on. A floating promise in a request handler is a classic cause of the unhandled-rejection crashes described in [01 Node.js Runtime](01_nodejs_runtime.md).

`.prettierrc` sets `singleQuote: true` and `trailingComma: "all"`. `pnpm format` rewrites files in place.

### Other Generated Files

- `.gitattributes`: line-ending settings.
- `README.md`: a long generic Nest README with sponsor and community links. Safe to replace.
- `AGENTS.md`: a file addressed to coding agents. It tells them the project's Nest version may be newer than they know, points to `https://docs.nestjs.com/llms.txt`, lists first-party packages, and states ESM conventions. It also contains a section promoting a paid vendor product (NestJS Observe). You can delete it. The exercise project does not include it.

---

## Why TypeScript Is Pinned to 6

`npm view typescript version` returns **7.0.2**, the native Go compiler released 2026-07-08. The Nest scaffold still pins `^6.0.2` and installed 6.0.3. Installing TypeScript 7 into a Nest project breaks the build. We tried it on a copy of the scaffold:

```text
$ npm i -D typescript@7.0.2 --force
$ npx tsc -v
Version 7.0.2
$ npm run build

 Error  The installed TypeScript version (7.0.2) does not expose the programmatic compiler API that the Nest CLI requires. TypeScript 7.0 ships the "tsc" executable only; the compiler API is expected to return in 7.1. Please install TypeScript 6 (e.g. "npm i -D typescript@^6") until then.
```

What we also observed under TypeScript 7.0.2:

- Vitest still passed. Vite transforms TypeScript without the compiler API, so tests do not care.
- Both `tsc` 6.0.3 and `tsc` 7.0.2 emit `design:paramtypes` metadata when `experimentalDecorators` and `emitDecoratorMetadata` are on, so legacy decorators are not what blocks the move.

Why the CLI needs the API: `nest build` drives the compiler programmatically (it reads and rewrites the program, runs the Nest CLI plugins and reports errors) instead of shelling out to `tsc`. The official TypeScript 7.0 post says 7.0 ships no programmatic API and that a new, different one is expected in 7.1 (a 7.1 beta was announced for 2026-10-20). Until the CLI supports it, stay on 6.0.x.

The rule in our projects: pin `"typescript": "~6.0.3"` so a stray `pnpm up --latest` cannot pull in 7. Revisit when the CLI release notes mention TypeScript 7 support.

---

## Builders

`nest build` and `nest start` accept `--builder` with `tsc`, `webpack`, `swc` or `rspack`.

### tsc, the Default

`tsc` type-checks and emits. On the scaffold, `nest build` took about 1.0 seconds (`real 1.01`). It produced `.js`, `.js.map` and `.d.ts` files in `dist/`. Because `emitDecoratorMetadata` is a TypeScript feature, `tsc` emits the metadata natively, including `__decorate` and `__metadata` helper calls.

### SWC

SWC is a Rust-based transpiler. Using it needs two extra dev packages:

```bash
npm i -D @swc/cli @swc/core
nest build -b swc
```

On the same scaffold:

```text
>  SWC  Running...
Successfully compiled: 11 files with swc (42.19ms)
```

That is 42 ms against 1.0 s for tsc. The comparison is only for this tiny project, not a benchmark, and the two were not measured under identical conditions. We ran the SWC output with `node dist/main.js` and both `GET /` and `GET /users` worked, so DI metadata survives SWC.

The important trade-off: **SWC does not type-check by default.** We put `const n: number = 'not a number';` in the service:

| Command | Result |
|---|---|
| `nest build -b swc` | Compiled successfully. The type error went unnoticed. |
| `nest build -b swc --type-check` | Failed with `Found 1 type error(s) during compilation.` |
| `nest build` (tsc) | Failed with `Found 1 error(s).` |

If you use SWC, also run `tsc --noEmit` (or `--type-check`) in CI. The official docs give two different figures: the CLI overview says SWC is "about 10x faster than the default TypeScript compiler", and the SWC recipe page says "approximately 20 times faster". Our single measurement (42 ms against 1.0 s, about 24x) is on a tiny project, so it is consistent with either but proves neither.

### rspack and webpack

According to the official CLI overview, the default compiler is `tsc` in standard mode and `rspack` in monorepo mode (see topic 10.2). `webpack` is still accepted by the flags, but `--webpack` and `--webpackPath` are marked deprecated in favor of `--builder`. We did not build with rspack or webpack, so anything beyond that is Not verified.

---

## Daily Workflow

### Watch Mode

`pnpm start:dev` runs `nest start --watch`. We started it, called `GET /`, edited `app.service.ts`, and called `GET /` again:

```text
before edit: Hello World!
after edit : Hello Watch!   (waited ~1s)
```

The log showed the sequence:

```text
Starting compilation in watch mode...
Found 0 errors. Watching for file changes.
[Nest] 24218 ... LOG [NestFactory] Starting Nest application...
[Nest] 24218 ... LOG [NestApplication] Nest application successfully started
Found 0 errors. Watching for file changes.
[Nest] 24246 ... LOG [NestFactory] Starting Nest application...
```

Note the process ID changed from 24218 to 24246. Watch mode is **recompile and restart the whole process**, not hot module replacement. In-memory state is lost on every save, and the app pays its full startup cost each time. Watch mode takes the compile errors too: a type error stops the restart.

### Debugging

`pnpm start:debug` is `nest start --debug --watch`. It starts Node with the inspector on port 9229 and prints:

```text
Debugger listening on ws://127.0.0.1:9229/f4c7bcc1-...
For help, see: https://nodejs.org/en/docs/inspector
```

We tested the attach flow end to end without a GUI, by acting as a debugger client over the Chrome DevTools Protocol:

1. Started `nest start --debug` (and, separately, `pnpm start:debug` inside the exercise project).
2. Connected to the inspector, enabled the debugger, and set a breakpoint on the `return` line of `dist/app.service.js`.
3. Sent `GET /`.
4. The process paused in `getHello`, then resumed, and the response came back as `"Hello World!"` (`"Hello, Nest 12!"` in the exercise project).

Source maps work. For the generated `dist/app.service.js` line 10, column 8, the `.js.map` file maps to `src/app.service.ts` line 6, which is the `return 'Hello World!';` statement. The map's `sources` entry is `../src/app.service.ts`. A debugger shows you the TypeScript line, not the compiled one.

The VS Code configuration in the exercise (`.vscode/launch.json`):

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to Nest (pnpm start:debug)",
      "type": "node",
      "request": "attach",
      "port": 9229,
      "restart": true,
      "sourceMaps": true,
      "outFiles": ["${workspaceFolder}/**/dist/**/*.js", "!**/node_modules/**"],
      "skipFiles": ["<node_internals>/**", "**/node_modules/**"]
    }
  ]
}
```

| Field | Why |
|---|---|
| `request: "attach"` | Connect to a process you started yourself with `pnpm start:debug`. |
| `port: 9229` | The inspector port printed above. |
| `restart: true` | Watch mode kills and restarts the process on every save (new PID, as seen above). `restart` makes VS Code reattach on its own. |
| `sourceMaps`, `outFiles` | Tell VS Code where compiled files live, so it resolves `.js.map` files and shows your `.ts`. |
| `skipFiles` | Do not step into Node internals or dependencies. |

**Not verified:** I could not drive the VS Code interface itself, so this `launch.json` is verified only in the sense that the process, port, breakpoint and source map it relies on were each tested as above. Open the exercise's `solution/` folder directly in VS Code (File > Open Folder) so the `.vscode` folder is found.

An alternative needing no `launch.json`: open a **JavaScript Debug Terminal** in VS Code and run `pnpm start:dev`. VS Code auto-attaches. Not verified here.

`pnpm test:debug` is `vitest --inspect-brk --no-file-parallelism`. We verified that it opens an inspector on 9229, pauses at start, and that the test run completes after you resume. We did not verify a breakpoint inside test code: the specs execute in a separate worker, so your debugger may need to attach to that target. Not verified.

### The REPL

Since Nest 9, you can load the whole container in an interactive shell. Create a separate entry file:

```ts
// src/repl.ts
import { repl } from '@nestjs/core';
import { AppModule } from './app.module.js';

await repl(AppModule);
```

and start it with `nest start --entryFile repl`. We piped commands in:

```text
> get(AppService).getHello()
'Hello World!'
> methods(AppService)
Methods:
 ◻ getHello
> debug()
AppModule:
 - controllers:
  ◻ AppController
 - providers:
  ◻ AppService
UsersModule:
 - controllers:
  ◻ UsersController
 - providers:
  ◻ UsersService
> $(AppController)
AppController { appService: AppService {} }
> await get(AppController).getHello()
'Hello World!'
```

The helpers we used: `get(Token)` returns an instance, `methods(Class)` lists methods, `debug()` prints the module graph (here after we had generated a `users` resource), and `$(Class)` is a shorthand for `select` and `get`. The REPL is the fastest way to see what the container built, which makes it a good companion for Phase 2.

### nest generate and the Resource Generator

`nest g resource users --type rest --crud` created:

```text
CREATE src/users/users.controller.spec.ts
CREATE src/users/users.controller.ts
CREATE src/users/users.module.ts
CREATE src/users/users.service.spec.ts
CREATE src/users/users.service.ts
CREATE src/users/dto/create-user.dto.ts
CREATE src/users/dto/update-user.dto.ts
CREATE src/users/entities/user.entity.ts
UPDATE package.json
UPDATE src/app.module.ts
```

Things to know:

- **It edits files you own.** It added `UsersModule` to the `imports` of `AppModule`, and it added `"@nestjs/mapped-types": "*"` to `package.json` and ran a package install. Run it on a clean git state so you can review the diff.
- The generated `UpdateUserDto` is `PartialType(CreateUserDto)` from `@nestjs/mapped-types` (topic 3.2).
- The generated service methods return placeholder strings such as `'This action returns all users'`. It is scaffolding, not logic.
- Generated imports already use the `.js` suffix, as ESM requires.
- After generating, the existing tests and the build still passed (3 test files).
- Useful flags: `--dry-run` shows what would change, `--no-spec` skips spec files, `--flat` avoids creating a folder, `--skip-import` skips editing the module. `nest g --help` lists them all.
- Individual generators exist for each building block (`nest g module users`, `nest g controller users`, `nest g service users`, `nest g guard auth`, and so on). You will use them in Phase 1.

### nest info and nest upgrade

`nest info` printed the system section, the CLI version and the installed `@nestjs/*` versions (`core` 12.5.1, `common` 12.5.1, `cli` 12.0.13, `schematics` 12.0.13, `mau` 0.2.9, `mapped-types` 12.0.1). Paste its output into bug reports. Outside a project it reports that it cannot read `package.json`.

`nest upgrade --dry-run` on an already-current project printed:

```text
Changes applied:
  ✔ Updated NestJS packages: @nestjs/common@^12.0.0, @nestjs/core@^12.0.0, @nestjs/testing@^12.0.0, @nestjs/platform-express@^12.0.0, @nestjs/cli@^12.0.0, @nestjs/schematics@^12.0.0, @nestjs/mapped-types@^12.0.0
  ✔ Scheduled "npm install"
Notes:
  ℹ "@nestjs/core" is already on v12; re-applying the v12 migrations (they are idempotent).
Dry run enabled. No files written to disk.
```

Per the v12.0.0 release notes, `nest upgrade` moves every `@nestjs/*` package at once and applies the mechanical parts of the migration (`nest-cli.json` webpack options, GraphQL and NATS changes, config validation options, Jest and Joi bumps), then prints a report. It deliberately does not convert your project to ESM, Vitest or oxlint. Upgrade the global CLI first, because the command ships inside it, and always run `--dry-run` first. Options: `-s` skips the install, `-t` uses an npm dist-tag such as `next`.

---

## CommonJS Projects

Many existing codebases are CommonJS with Jest. What we know:

- Choosing it is an interactive prompt ("CJS (CommonJS) [ with jest ]"), described above.
- The official docs say CommonJS projects use Jest and also use oxlint.
- Nest 12 packages are ESM, and CommonJS apps keep working through Node's `require(esm)`. The v12 migration guide says Jest needs Node 24.9 or later for that, and that AWS Lambda disables `require(esm)` (so it needs `NODE_OPTIONS=--experimental-require-module`).

We did not generate or run a CommonJS scaffold, so its file contents, the exact Jest configuration and its tsconfig are Not verified. When you meet a CommonJS Nest project at work, expect: no `"type": "module"`, `require`-style output, no `.js` suffixes in imports, `jest` instead of `vitest`, and `bootstrap()` without a top-level `await`.

---

## Common Pitfalls

- **Forgetting the `.js` suffix** on a relative import. The compile error mentions needing explicit file extensions in ECMAScript imports. It is correct even though the file is `.ts`.
- **Installing `typescript@latest`.** That is 7.0.2 and the CLI refuses it. Pin `~6.0.3`.
- **Running the e2e test with `pnpm test`.** It will not run, by design. Use `pnpm test:e2e`.
- **Turning off `emitDecoratorMetadata`.** DI silently breaks: parameters resolve to `undefined` and Nest reports it cannot resolve dependencies.
- **Using SWC without type checking** and shipping a type error.
- **Expecting hot module replacement.** Watch mode restarts the process.
- **Opening the repository root in VS Code** and wondering why `.vscode/launch.json` inside a sub-project is ignored. VS Code reads `.vscode` from the opened folder only.
- **Running `nest g resource` on a dirty working tree.** It edits `package.json` and `app.module.ts`.
- **Trusting "it installs on my Node".** `EBADENGINE` and your Node version are signals, not noise.

---

## Interview Questions

**Q1. What is the difference between `tsconfig.json` and `tsconfig.build.json` in a Nest project?**
`tsconfig.json` describes the whole project for editors and the type checker, including tests. `tsconfig.build.json` extends it and is what `nest build` uses: it includes only `src`, excludes specs and `dist`, and sets `rootDir` to `./src` so the output is `dist/main.js`.

**Q2. Why does constructor injection work without `@Inject()`, and which tsconfig options does it depend on?**
Nest reads the parameter types from `design:paramtypes` metadata. TypeScript emits it only when `experimentalDecorators` and `emitDecoratorMetadata` are on. Turn the second off and the DI test gets `undefined`, which we demonstrated under Vitest.

**Q3. What does `nodenext` module resolution change for how you write imports?**
It follows Node's real rules. In an ESM package (`"type": "module"`), relative imports need an explicit extension, and you write `.js` even though the source is `.ts`. Node globals such as `__dirname` and `require` do not exist; use `import.meta.dirname` and `createRequire`.

**Q4. When would you choose SWC over `tsc` for the Nest build, and what do you lose?**
When build or watch speed matters, as in a large project. You lose type checking unless you pass `--type-check` or run `tsc --noEmit` separately, so CI must type-check. We saw a deliberate type error compile cleanly under SWC.

**Q5. A teammate runs `pnpm up --latest` and `nest build` fails with a message about a compiler API. What happened?**
It upgraded TypeScript to 7.x, which has no programmatic API until 7.1, and the Nest CLI needs that API. Pin TypeScript to 6.0.x and wait for CLI support.

**Q6. Why are there two Vitest configs, and why does `pnpm test` skip the e2e file?**
Unit specs match `**/*.spec.ts`, e2e specs match `**/*.e2e-spec.ts`, and each config includes only its own pattern. `app.e2e-spec.ts` ends in `-spec.ts`, which `*.spec.ts` does not match. This keeps fast tests and slower, app-booting tests separate.

**Q7. How does watch mode work, and what does it cost?**
It recompiles and restarts the whole Node process on each change (the PID changes). There is no state preservation and every restart pays full startup cost. That is acceptable for a small app but a reason to keep startup fast.

**Q8. What does `nest generate resource` change besides creating files?**
It registers the new module in `AppModule`, adds `@nestjs/mapped-types` to `package.json` and installs it. Always review the diff.

**Q9. A debugger attached through `nest start --debug --watch` disconnects on every save. What setting fixes it?**
`"restart": true` in the VS Code attach configuration, because each save restarts the process.

---

## Check Yourself

- [ ] I can explain why the EBADENGINE warning appeared and why pnpm did not print it.
- [ ] I know the four different Node floors for Nest 12 and which Node I will use.
- [ ] I can scaffold a project with `nest new`, and I know which prompt picks CommonJS or ESM.
- [ ] I can say what every file in the scaffold is for, and why `package.json` has `"type": "module"`.
- [ ] I can explain each option in `tsconfig.json`, and what breaks if `emitDecoratorMetadata` is false.
- [ ] I know why TypeScript is pinned to 6 and what the CLI error says.
- [ ] I can build with `tsc` and SWC and say what each one checks.
- [ ] I have hit a breakpoint in `app.service.ts` through the debugger.
- [ ] I have used the REPL to list a module's providers.
- [ ] I completed [07_milestone_hello_nest](../../projects/phase_00_orientation/07_milestone_hello_nest/README.md) and read `diff -r solution/src solved/src`.

---

## Further Reading

- [Nest CLI overview (official)](https://docs.nestjs.com/cli/overview): requirements, command table, standard versus monorepo mode.
- [Nest CLI command reference (official)](https://docs.nestjs.com/cli/usages)
- [Nest migration guide (official)](https://docs.nestjs.com/migration-guide): the v12 changes, Node floors and Jest notes.
- [NestJS v12.0.0 release notes](https://github.com/nestjs/nest/releases/tag/v12.0.0)
- [SWC builder recipe (official)](https://docs.nestjs.com/recipes/swc)
- [Announcing TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/): compiler API status and the TypeScript 6 side-by-side package.
- [Announcing TypeScript 6.0](https://devblogs.microsoft.com/typescript/announcing-typescript-6-0/): the default changes behind the scaffold's `types` and `strict` lines.
- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
- [Vitest guide](https://vitest.dev/guide/)
- [oxlint](https://oxc.rs/docs/guide/usage/linter): rules and type-aware linting.

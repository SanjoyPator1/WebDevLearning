# Side Projects

> Document 03 of the `docs/` knowledge hub. This covers the projects you build on your own, outside the roadmap. The roadmap's exercises are covered in [01_nestjs_roadmap.md](01_nestjs_roadmap.md).

## Table of Contents

- [Why a Separate Folder](#why-a-separate-folder)
- [Layout](#layout)
- [Rules](#rules)
- [Growing a Project With the Roadmap](#growing-a-project-with-the-roadmap)
- [Starting a New Side Project](#starting-a-new-side-project)
- [Commit Messages](#commit-messages)
- [Graduating to Its Own Repo](#graduating-to-its-own-repo)
- [Index](#index)

---

## Why a Separate Folder

`projects/` holds the roadmap's exercises. `side_projects/` holds your own builds. They look similar, but they follow different rules:

| | `projects/` (roadmap exercises) | `side_projects/` (your own builds) |
|---|---|---|
| Organised by | Roadmap phase | Nothing. It's your own idea |
| Shape | `template/`, `solution/`, `solved/` | One normal project folder |
| Scope | One topic, minimal domain (the Focus Rule) | Many topics combined, realistic domain, DB, Docker and so on |
| Written by | Claude writes `template/` and `solved/` | You write it. Claude helps only when asked |
| Lifetime | Done when the tests pass | Grows over weeks or months |

The Focus Rule exists to keep topics isolated while learning them. Side projects are where you deliberately combine them, so the rule does not apply here.

The name is not `apps/` because Nest's monorepo mode generates `apps/` and `libs/` folders, and Phase 10 of the roadmap uses that layout.

## Layout

```
WebDevLearning/
├── docs/
│   └── 03_side_projects.md           # this file: rules and the index
└── side_projects/
    ├── _template/
    │   └── README.md                 # copy this into a new project
    └── notes-api/
        ├── README.md                 # what it is, status, roadmap topics used
        ├── .nvmrc
        ├── package.json
        ├── src/
        ├── test/
        └── docs/                     # optional: decisions and lessons for this project
```

## Rules

1. **Flat and unnumbered.** Project folders use kebab-case, such as `notes-api`. There is no order between side projects, so there are no phase folders and no `NN_` prefixes.
2. **Each project stands alone.** It has its own `package.json`, `.nvmrc`, `README.md`, and where needed `docker-compose.yml` and `.env.example`. `cd side_projects/<name> && pnpm install && pnpm test` must work without touching anything else in the repo.
3. **No `template/`, `solution/` or `solved/`.** It's one folder and you write it.
4. **The Focus Rule does not apply.** Use what the project needs. Keep the roadmap's stack defaults unless you have a reason not to: Node 24, ESM, pnpm, Vitest, TypeScript `~6.0`.
5. **Every project README has a "Roadmap topics used" table**, so each project points back at the topics it practises.
6. **Study notes stay in `notes/`.** If a project shows you a gap, write the study note in `notes/<phase folder>/` as usual. Project-specific decisions and lessons go in the project's own `docs/` folder.
7. **Never reuse an exercise or milestone domain** (the tasks API, the ticketing capstone). A side project should be new practice, not a repeat.

## Growing a Project With the Roadmap

A side project should not run ahead of what you've learned. Build it in versions that follow the roadmap, and tag each one in git (`notes-api-v1`, `notes-api-v2`):

| Version | After | Adds |
|---|---|---|
| v1 | Phase 1 | In-memory CRUD, DTO validation with pipes, one guard, an exception filter |
| v2 | Phase 4 | Postgres and migrations |
| v3 | Phase 5 | Authentication and ownership checks |
| v4 | Phase 6 | A full test suite with Testcontainers |

Not every project needs every version. Use this as a pattern, and write a project's own plan in its README.

## Starting a New Side Project

1. Copy the README template: `cp -r side_projects/_template side_projects/<name>`.
2. Fill in the README: what it is, the v1 scope, and the roadmap topics it uses.
3. Scaffold the project yourself (for example with `nest new`), or ask Claude to.
4. Add a row to the [Index](#index) below.

## Commit Messages

Side-project commits go on the same branch as the roadmap work and carry a `side/<project>` tag after the branch name:

```
nestjsb: side/notes-api: add stats module using exported NotesService for note count
```

Roadmap commits have no tag (`nestjsb: <message>`). The tag makes the two kinds easy to tell apart and to filter:

| Goal | Command |
|---|---|
| All side-project commits | `git log --grep='^nestjsb: side/'` |
| One project | `git log --grep='^nestjsb: side/notes-api:'` |
| Roadmap commits only | `git log --invert-grep --grep='^nestjsb: side/'` |

Keep it to one line, with no `Co-Authored-By` trailer.

## Graduating to Its Own Repo

If a project becomes real (deployed, has CI, or needs a clean commit history), move it to its own repo. Copy the folder out, or use `git subtree split -P side_projects/<name>` to keep its history. Then change its row in the index to point at the new repo.

## Index

| Project | Status | Stack | Starts after |
|---|---|---|---|
| [notes-api](../side_projects/notes-api/README.md) | Planned | NestJS 12, in-memory at first | Phase 1 |

# notes-api

A small REST API for personal notes, built on NestJS 12. It's the first side project, and it grows version by version as the roadmap progresses.

**Status:** Planned

## Scope

### v1 (after Phase 1)

Proposed scope, which you can change before starting:

- CRUD for notes (`title`, `body`, `tags`), kept in memory.
- DTO validation with pipes.
- A simple guard, for example an API key header.
- A custom exception filter for a consistent error shape.
- A few e2e tests.

### Later versions

- v2 (after Phase 4): Postgres and migrations.
- v3 (after Phase 5): authentication and ownership checks.
- v4 (after Phase 6): a full test suite with Testcontainers.

See [Growing a Project With the Roadmap](../../docs/03_side_projects.md#growing-a-project-with-the-roadmap).

## Roadmap topics used

| Topic | Where it is used in this project |
|---|---|
| 1.2 Modules | A `notes` feature module |
| 1.3 Controllers and routing | The `/notes` routes |
| 1.4 Providers and services | `NotesService` holding the in-memory store |
| 1.6 Pipes | Validation of create and update DTOs |
| 1.7 Guards | API key check |
| 1.9 Exception filters | Consistent error responses |

## Run

Not scaffolded yet.

## Notes

- Decisions and lessons go here.

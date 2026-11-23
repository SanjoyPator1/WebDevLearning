import type { INestApplication } from '@nestjs/common';
import { tagResponse } from './tag-response.js';

// Task 1b: app.use() is the Express call, so it registers the function as GLOBAL middleware:
// it runs for every request, including paths that no route handles (a 404 gets the header too).
//
// It must be called BEFORE init() (which listen() calls): Nest mounts its own parsers and
// routes at init, and middleware added afterwards is ignored (measured: no header at all).
//
// Because it is mounted first, it runs BEFORE the body parser: req.body is undefined here
// (see observations.spec.ts). Module middleware, registered through configure(), runs after
// it. Global middleware also has no access to the module's providers through injection; if
// it needs one, fetch it first with app.get(Service) and close over it.
export function configureApp(app: INestApplication): void {
  app.use(tagResponse);
}

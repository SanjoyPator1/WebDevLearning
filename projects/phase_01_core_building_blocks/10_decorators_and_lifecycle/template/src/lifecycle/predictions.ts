// TODO(1.10) Task 4
// Draw the request lifecycle from memory, then let the application confirm it.
//
// Read lifecycle.controller.ts, lifecycle.module.ts and configure-lifecycle.ts, and write down, WITHOUT
// running anything, the exact trace each request leaves behind. The tests run the real application and
// compare what it logged with your answer. Use the notes (the lifecycle diagram) and your own reasoning:
// the tests print the actual trace when you are wrong, but try to get each one right before you look.
//
// Entries, in the order they are written to the trace:
//   mw:global  mw:module  guard:<scope>  before:<scope>  pipe:<scope>  handler
//   after:<scope>  error:<scope>  filter:<scope>
// with <scope> one of global, controller, method, param. `before:` is an interceptor before the handler,
// `after:` an interceptor after a success, `error:` an interceptor seeing an error.

// GET /life/ok/1: everything succeeds.
export const okPath: string[] = [];

// GET /life/denied/1: the METHOD guard answers false. (The global and controller guards allow.)
export const deniedPath: string[] = [];

// GET /life/pipefail/1: the parameter pipe throws a BadRequestException.
export const pipeFailPath: string[] = [];

// GET /life/handlerfail/1: the handler throws a BadRequestException.
export const handlerFailPath: string[] = [];

// GET /nothing-here: a path that matches no route at all. Which of the components above run?
export const unknownPath: string[] = [];

// GET /life/status has @HttpCode(202). What `response.statusCode` does a guard see, and what does an
// interceptor see before the handler runs? (A number each: the default status, or 202.)
export const statusSeenInGuard: number = 0;
export const statusSeenInInterceptor: number = 0;

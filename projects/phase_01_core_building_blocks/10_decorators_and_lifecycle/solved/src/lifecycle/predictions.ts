// Task 4: the request lifecycle, as measured on Nest 12.5.1 and as the application confirms.
//
//   request
//     |  global middleware        app.use(...)                       mw:global
//     |  module middleware        configure(consumer), forRoutes     mw:module   (only for routes it matches)
//     v
//     |  guards                   global, controller, method         guard:*     (one at a time; a denial stops here)
//     |  (@HttpCode status and @Header headers are set here, after the guards)
//     v
//     |  interceptors, before     global, controller, method         before:*
//     |  pipes                    global, controller, method, param  pipe:*      (inside next.handle())
//     |  HANDLER                                                     handler
//     |  interceptors, after      method, controller, global         after:*     (the reverse order)
//     v
//   response
//
//   an error at any stage from the handler back to the guards: exception filters (ONE filter, the
//   narrowest scope), after the interceptors have seen it as `error:*` in reverse order
//   a guard denial: straight to the filters (interceptors and pipes never started)
//   a path with no route: global middleware, then the global filters only

// GET /life/ok/1
export const okPath: string[] = [
  'mw:global',
  'mw:module',
  'guard:global',
  'guard:controller',
  'guard:method',
  'before:global',
  'before:controller',
  'before:method',
  'pipe:global',
  'pipe:controller',
  'pipe:method',
  'pipe:param',
  'handler',
  'after:method',
  'after:controller',
  'after:global',
];

// GET /life/denied/1: the method guard runs (and says no), so the interceptors, pipes and handler never start.
// The method-level filter is the narrowest, so it answers, not the global one.
export const deniedPath: string[] = [
  'mw:global',
  'mw:module',
  'guard:global',
  'guard:controller',
  'guard:method',
  'filter:method',
];

// GET /life/pipefail/1: the pipes run in order and the parameter pipe throws before the handler. The error
// travels back through the interceptors (as errors, innermost first), then reaches the filter.
export const pipeFailPath: string[] = [
  'mw:global',
  'mw:module',
  'guard:global',
  'guard:controller',
  'guard:method',
  'before:global',
  'before:controller',
  'before:method',
  'pipe:global',
  'pipe:controller',
  'pipe:method',
  'pipe:param',
  'error:method',
  'error:controller',
  'error:global',
  'filter:method',
];

// GET /life/handlerfail/1: like a pipe failure, but the handler ran first.
export const handlerFailPath: string[] = [
  'mw:global',
  'mw:module',
  'guard:global',
  'guard:controller',
  'guard:method',
  'before:global',
  'before:controller',
  'before:method',
  'pipe:global',
  'pipe:controller',
  'pipe:method',
  'pipe:param',
  'handler',
  'error:method',
  'error:controller',
  'error:global',
  'filter:method',
];

// GET /nothing-here: no route matched. The global middleware (app.use) runs; the module middleware was
// mounted on the routes of one controller, so it does not. No guard, interceptor or pipe: there is no
// handler. Only a GLOBAL filter can answer the router's 404.
export const unknownPath: string[] = ['mw:global', 'filter:global'];

// GET /life/status has @HttpCode(202). Nest sets that status after the guards and before the
// interceptors, so a guard still sees the default 200 and an interceptor already sees 202.
export const statusSeenInGuard: number = 200;
export const statusSeenInInterceptor: number = 202;

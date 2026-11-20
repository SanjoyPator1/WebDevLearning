// Kata 07: template literal types, parsing a route pattern at the type level (topic 0.2)
//
// The goal is the same trick Express-style routers use to type `req.params`:
// '/users/:id/posts/:postId' gives { id: string; postId: string }.
// Tools: `${string}:${infer Param}/${infer Rest}` patterns, recursion, and a
// mapped type over the union of parameter names.

// TODO(0.2): write a helper type (not exported) that extracts the union of
// parameter names from a path pattern, for example 'id' | 'postId'.

/** TODO(0.2): an object type with one string property per parameter in Path. A pattern with no parameters gives an object with no keys. */
export type RouteParams<Path extends string> = Record<string, string>;

export type HttpMethod = 'GET' | 'POST';

/** TODO(0.2): a template literal type for strings like 'GET /users' or 'POST /users/1': a method from HttpMethod, a space, a slash, then anything. */
export type RouteKey = string;

/**
 * TODO(0.2): the runtime twin. Split the pattern and the path on '/', copy the
 * value for every ':name' segment, and throw an Error containing 'does not match'
 * when the segment counts differ or a literal segment differs.
 * The generic `P extends string` is what lets the literal pattern reach the return type.
 */
export function extractParams(
  pattern: string,
  path: string,
): RouteParams<string> {
  throw new Error('TODO(0.2): implement extractParams');
}

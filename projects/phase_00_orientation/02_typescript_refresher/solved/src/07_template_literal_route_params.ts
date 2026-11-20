// Kata 07: template literal types, parsing a route pattern at the type level (topic 0.2)
//
// The goal is the same trick Express-style routers use to type `req.params`:
// '/users/:id/posts/:postId' gives { id: string; postId: string }.

/**
 * Walk the pattern from the left. `${string}:${infer Param}/${infer Rest}`
 * matches the first ':' (the leading `string` is matched lazily, so it stops at
 * the first one), captures the segment name up to the next '/', and recurses on
 * the remainder. The last parameter has no trailing '/', which is the second branch.
 */
type ExtractParamNames<Path extends string> =
  Path extends `${string}:${infer Param}/${infer Rest}`
    ? Param | ExtractParamNames<`/${Rest}`>
    : Path extends `${string}:${infer Param}`
      ? Param
      : never;

export type RouteParams<Path extends string> = {
  [K in ExtractParamNames<Path>]: string;
};

/** A string with a fixed prefix pair: only these two shapes are allowed. */
export type HttpMethod = 'GET' | 'POST';
export type RouteKey = `${HttpMethod} /${string}`;

/**
 * Runtime twin. The pattern is a generic `P extends string` so that the
 * *literal* pattern reaches the return type.
 */
export function extractParams<P extends string>(
  pattern: P,
  path: string,
): RouteParams<P> {
  const patternParts = pattern.split('/');
  const pathParts = path.split('/');
  if (patternParts.length !== pathParts.length) {
    throw new Error(`Path "${path}" does not match pattern "${pattern}"`);
  }

  const params: Record<string, string> = {};
  patternParts.forEach((part, index) => {
    const actual = pathParts[index]!;
    if (part.startsWith(':')) {
      params[part.slice(1)] = actual;
    } else if (part !== actual) {
      throw new Error(`Path "${path}" does not match pattern "${pattern}"`);
    }
  });
  return params as RouteParams<P>;
}

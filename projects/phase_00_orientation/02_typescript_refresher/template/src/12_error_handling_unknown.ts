// Kata 12: error handling with `unknown`, custom errors and a Result type (topic 0.2)
//
// With `strict`, a catch variable is `unknown`, not `any`. JavaScript lets you
// throw anything, including strings and plain objects, so never assume an Error.

/**
 * TODO(0.2): turn whatever was thrown into a message.
 *   Error -> its message; string -> itself; object with a string `message` -> that message;
 *   anything else -> JSON.stringify of it, falling back to String(value) when that returns undefined.
 */
export function toErrorMessage(error: unknown): string {
  throw new Error('TODO(0.2): implement toErrorMessage');
}

/**
 * TODO(0.2): a custom error with `name` 'HttpError', a readonly numeric `status`
 * (constructor parameter property), and a third constructor argument of type
 * ErrorOptions that is forwarded so `cause` works. Mark `name` with `override`.
 */
export class HttpError extends Error {}

/** TODO(0.2): a type predicate, true for HttpError instances. */
export function isHttpError(error: unknown): boolean {
  throw new Error('TODO(0.2): implement isHttpError');
}

/**
 * TODO(0.2): a generic discriminated union. Success: { ok: true; value: T }.
 * Failure: { ok: false; error: E }. E defaults to Error.
 */
export type Result<T, E = Error> = unknown;

/**
 * TODO(0.2): run fn and return a Result. If something non-Error is thrown,
 * wrap it as `new Error(toErrorMessage(thrown), { cause: thrown })`.
 */
export function tryCatch(fn: () => unknown): unknown {
  throw new Error('TODO(0.2): implement tryCatch');
}

/** TODO(0.2): the async version. Same wrapping rule. */
export async function tryCatchAsync(fn: () => Promise<unknown>): Promise<unknown> {
  throw new Error('TODO(0.2): implement tryCatchAsync');
}

/** TODO(0.2): JSON.parse inside tryCatch. The value type must be unknown, not any, so callers have to narrow it. */
export function safeJsonParse(text: string): unknown {
  throw new Error('TODO(0.2): implement safeJsonParse');
}

// Kata 12: error handling with `unknown`, custom errors and a Result type (topic 0.2)
//
// With `strict`, a catch variable is `unknown`, not `any`. That is correct:
// JavaScript lets you throw anything, including strings and plain objects.

/** Turn whatever was thrown into a readable message. */
export function toErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (
    typeof error === 'object' &&
    error !== null &&
    'message' in error &&
    typeof error.message === 'string'
  ) {
    return error.message;
  }
  return JSON.stringify(error) ?? String(error);
}

/**
 * Custom error with extra data. `override` makes the compiler check that
 * `name` really exists on the parent, and `options` forwards `cause`.
 */
export class HttpError extends Error {
  override readonly name = 'HttpError';

  constructor(
    message: string,
    readonly status: number,
    options?: ErrorOptions,
  ) {
    super(message, options);
  }
}

export function isHttpError(error: unknown): error is HttpError {
  return error instanceof HttpError;
}

/** A discriminated union as a return type: callers must check `ok` before reading. */
export type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

/** Normalise `unknown` to a real Error, keeping the original as `cause`. */
function toError(thrown: unknown): Error {
  return thrown instanceof Error
    ? thrown
    : new Error(toErrorMessage(thrown), { cause: thrown });
}

export function tryCatch<T>(fn: () => T): Result<T> {
  try {
    return { ok: true, value: fn() };
  } catch (thrown) {
    return { ok: false, error: toError(thrown) };
  }
}

export async function tryCatchAsync<T>(fn: () => Promise<T>): Promise<Result<T>> {
  try {
    return { ok: true, value: await fn() };
  } catch (thrown) {
    return { ok: false, error: toError(thrown) };
  }
}

/** JSON.parse returns `any`. Returning unknown inside a Result forces callers to narrow. */
export function safeJsonParse(text: string): Result<unknown> {
  return tryCatch((): unknown => JSON.parse(text));
}

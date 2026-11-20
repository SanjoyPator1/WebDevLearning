// Kata 01: narrowing, type guards and assertion functions (topic 0.2)

/**
 * Describe any value. Every branch narrows `value` from `unknown` using a
 * different technique: typeof, equality, Array.isArray, instanceof and `in`.
 */
export function describeValue(value: unknown): string {
  if (value === null) return 'null';
  if (value === undefined) return 'undefined';
  if (typeof value === 'string') return `string:${value}`;
  if (typeof value === 'number') return `number:${value}`;
  if (typeof value === 'boolean') return `boolean:${value}`;
  if (Array.isArray(value)) return `array:${value.length}`;
  if (value instanceof Date) return `date:${value.toISOString()}`;
  if (typeof value === 'object') {
    // `in` narrows the object type to one that has a `name` property, but the
    // property is still `unknown`, so it needs its own typeof check.
    if ('name' in value && typeof value.name === 'string') {
      return `named:${value.name}`;
    }
    return 'object';
  }
  // bigint, symbol and function are left. typeof gives their names.
  return typeof value;
}

/**
 * A type predicate. The `value is string` return type is what lets callers
 * narrow, a plain `boolean` return would tell the compiler nothing.
 */
export function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0;
}

/**
 * An assertion function. If it returns at all, `value` is not null or
 * undefined for the rest of the calling scope. Assertion functions must be
 * declared with `function` (or an explicitly typed const) to be recognised.
 */
export function assertIsDefined<T>(
  value: T,
  message = 'Expected value to be defined',
): asserts value is NonNullable<T> {
  if (value === null || value === undefined) {
    throw new Error(message);
  }
}

// Kata 01: narrowing, type guards and assertion functions (topic 0.2)
//
// Read the tests in 01_narrowing.test.ts first. They define "done".

/**
 * TODO(0.2): describe any value. Rules, in order:
 *   null -> 'null', undefined -> 'undefined'
 *   string -> `string:${value}`, number -> `number:${value}`, boolean -> `boolean:${value}`
 *   array -> `array:${length}`
 *   Date -> `date:${iso string}`
 *   object with a string `name` property -> `named:${name}`
 *   any other object -> 'object'
 *   everything else (bigint, symbol, function) -> the typeof result
 * Use a different narrowing technique for each: typeof, ===, Array.isArray, instanceof, `in`.
 */
export function describeValue(value: unknown): string {
  throw new Error('TODO(0.2): implement describeValue');
}

/**
 * TODO(0.2): true for non-empty strings.
 * The return type is wrong on purpose. Change it so callers can narrow `unknown` to `string`.
 */
export function isNonEmptyString(value: unknown): boolean {
  throw new Error('TODO(0.2): implement isNonEmptyString');
}

/**
 * TODO(0.2): throw `new Error(message)` when value is null or undefined.
 * The return type is wrong on purpose. After a call returns, the compiler
 * should know `value` is NonNullable<T>.
 */
export function assertIsDefined(
  value: unknown,
  message = 'Expected value to be defined',
): void {
  throw new Error('TODO(0.2): implement assertIsDefined');
}

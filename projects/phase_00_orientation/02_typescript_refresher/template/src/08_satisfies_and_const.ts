// Kata 08: `satisfies` and `const` type parameters (topic 0.2, TypeScript 4.9 and 5.0)
//
// Not part of this exercise: the function bodies below are already correct.
// Only the types need work.

/**
 * TODO(0.2): this annotation throws away what the compiler knew about each
 * value and allows any key. Keep the validation against Record<string, string | number[]>
 * but keep the precise types too: palette.red must be number[], palette.green
 * must be string, and palette.blue must be an error.
 */
export const palette: Record<string, string | number[]> = {
  red: [255, 0, 0],
  green: '#00ff00',
};

/**
 * TODO(0.2): callers should get a readonly tuple of literals back, such as
 * readonly ['GET', 200], without writing `as const` themselves.
 */
export function tupleOf(items: readonly unknown[]): readonly unknown[] {
  return items;
}

/** TODO(0.2): same idea for objects. `method` should come back as 'GET', not string. */
export function defineRoute(route: { method: string; path: string }): {
  method: string;
  path: string;
} {
  return route;
}

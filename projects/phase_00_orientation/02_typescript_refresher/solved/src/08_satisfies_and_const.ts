// Kata 08: `satisfies` and `const` type parameters (topic 0.2, TypeScript 4.9 and 5.0)

/**
 * A type annotation (`const x: T = ...`) REPLACES the inferred type with T, so
 * `palette.red` would be `string | number[]` and any key would be allowed.
 * `satisfies T` only CHECKS the value against T and keeps the narrower inferred
 * type. Both goals at once: validated shape, precise type.
 */
export const palette = {
  red: [255, 0, 0],
  green: '#00ff00',
} satisfies Record<string, string | number[]>;

/**
 * Without `const`, `tupleOf(['GET', 200])` is inferred as (string | number)[].
 * With `const T`, the argument is treated as if it ended in `as const`, so the
 * caller does not have to remember to write it.
 */
export function tupleOf<const T extends readonly unknown[]>(items: T): T {
  return items;
}

/** The same idea for objects: literal property types survive. */
export function defineRoute<const T extends { method: string; path: string }>(
  route: T,
): T {
  return route;
}

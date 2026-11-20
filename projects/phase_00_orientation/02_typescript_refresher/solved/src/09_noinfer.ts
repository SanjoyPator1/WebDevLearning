// Kata 09: NoInfer (topic 0.2, TypeScript 5.4)

/**
 * Inference collects candidates for `S` from EVERY position that mentions it.
 * With `initial: S`, a typo like 'idel' becomes a second candidate and S widens
 * to include it, so the bad call compiles. `NoInfer<S>` tells the compiler
 * "check this argument against S, but do not use it to decide what S is".
 * Now S comes only from `states`, and `initial` must be one of them.
 */
export function createMachine<S extends string>(
  states: readonly S[],
  initial: NoInfer<S>,
): { state: S; states: readonly S[] } {
  return { state: initial, states };
}

/** Same idea with a fallback value: it must match the element type, not widen it. */
export function firstOr<T>(items: readonly T[], fallback: NoInfer<T>): T {
  return items.length > 0 ? items[0]! : fallback;
}

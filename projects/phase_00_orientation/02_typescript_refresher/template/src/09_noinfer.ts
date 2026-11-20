// Kata 09: NoInfer (topic 0.2, TypeScript 5.4)
//
// Not part of this exercise: the function bodies are already correct. Only the
// signatures need work.

/**
 * TODO(0.2): S should be inferred ONLY from `states`. Right now `initial` is
 * also a candidate, so a typo such as 'idel' widens S and the bad call compiles.
 * Make `initial` be checked against S without taking part in inferring it.
 * The return type must stay { state: S; states: readonly S[] } with S as the state union.
 */
export function createMachine<S extends string>(
  states: readonly S[],
  initial: S,
): { state: S; states: readonly S[] } {
  return { state: initial, states };
}

/** TODO(0.2): same problem. A fallback of the wrong type must be an error, not a wider T. */
export function firstOr<T>(items: readonly T[], fallback: T): T {
  return items.length > 0 ? items[0]! : fallback;
}

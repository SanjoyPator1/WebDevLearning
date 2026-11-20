// Kata 05: key remapping with `as` in mapped types (topic 0.2)
//
// Syntax reminder: { [K in keyof T as NewKey]: Value }
// Remapping a key to `never` drops it. Template literal types and the
// intrinsic Capitalize<...> build new key names. `string & K` narrows a key to strings.

/** TODO(0.2): { name: string } becomes { getName: () => string }. */
export type Getters<T> = unknown;

/** TODO(0.2): remove the key `Key` from T using key remapping, not Omit. */
export type RemoveKey<T, Key extends keyof T> = unknown;

/** TODO(0.2): keep only the keys whose value is a function. */
export type OnlyFunctions<T> = unknown;

/** TODO(0.2): { click: MouseEvent } becomes { onClick: (payload: MouseEvent) => void }. */
export type EventHandlers<Events extends Record<string, unknown>> = unknown;

/**
 * TODO(0.2): the runtime twin of Getters. Build an object with real getX
 * functions. The type system cannot prove the loop produces Getters<T>, so a
 * cast on the return value is expected here.
 */
export function makeGetters<T extends object>(source: T): Getters<T> {
  throw new Error('TODO(0.2): implement makeGetters');
}

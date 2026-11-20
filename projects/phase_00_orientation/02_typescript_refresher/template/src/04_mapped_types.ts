// Kata 04: rebuild the core mapped utility types by hand (topic 0.2)
//
// Every type here already exists in lib.d.ts. Do NOT use the built-in versions
// in your answers. Write the mapped type yourself.
// Syntax reminder: { [K in keyof T]: T[K] }, with modifiers ?, -?, readonly, -readonly.

/** TODO(0.2): make every property optional. */
export type MyPartial<T> = unknown;

/** TODO(0.2): make every property required. */
export type MyRequired<T> = unknown;

/** TODO(0.2): make every property readonly. */
export type MyReadonly<T> = unknown;

/** TODO(0.2): remove readonly from every property. */
export type Mutable<T> = unknown;

/** TODO(0.2): keep only the keys in K. */
export type MyPick<T, K extends keyof T> = unknown;

/** TODO(0.2): an object type whose keys are K and whose values are V. */
export type MyRecord<K extends PropertyKey, V> = unknown;

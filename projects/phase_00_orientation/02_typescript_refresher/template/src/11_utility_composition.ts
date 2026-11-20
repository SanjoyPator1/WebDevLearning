// Kata 11: composing utility types, the way Nest's mapped-types helpers do (topic 0.2)
//
// Nest's PartialType, PickType, OmitType and IntersectionType (see 3.2) are
// built from exactly these ingredients, plus a runtime class factory. Here is
// only the type-level half.
// Build these from the built-in Omit, Pick, Partial and Required.

/**
 * TODO(0.2): flatten an intersection such as { a: 1 } & { b: 2 } into one
 * object type { a: 1; b: 2 } by mapping over its keys.
 */
export type Simplify<T> = unknown;

/** TODO(0.2): make only the keys in K optional. Wrap the result in Simplify. */
export type PartialBy<T, K extends keyof T> = unknown;

/** TODO(0.2): make only the keys in K required. Wrap the result in Simplify. */
export type RequiredBy<T, K extends keyof T> = unknown;

/** TODO(0.2): what a client may send to create an entity: everything except the server-owned keys. */
export type CreateDto<T, ServerKeys extends keyof T> = unknown;

/** TODO(0.2): what a client may send to update an entity: no `id`, and every other key optional. */
export type UpdateDto<T extends { id: unknown }> = unknown;

/**
 * TODO(0.2): recursively readonly. Nested objects become readonly objects,
 * arrays become readonly arrays of DeepReadonly elements, functions stay as they are.
 */
export type DeepReadonly<T> = unknown;

/** TODO(0.2): return a copy of source without the listed keys. Do not mutate source. The type is Omit<T, K>. */
export function omit(source: object, keys: readonly string[]): object {
  throw new Error('TODO(0.2): implement omit');
}

/** TODO(0.2): return a new object with only the listed keys. The type is Pick<T, K>. */
export function pick(source: object, keys: readonly string[]): object {
  throw new Error('TODO(0.2): implement pick');
}

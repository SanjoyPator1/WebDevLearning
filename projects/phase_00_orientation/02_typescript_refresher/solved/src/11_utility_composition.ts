// Kata 11: composing utility types, the way Nest's mapped-types helpers do (topic 0.2)
//
// Nest's PartialType, PickType, OmitType and IntersectionType (see 3.2) are
// built from exactly these ingredients, plus a runtime class factory. Here is
// only the type-level half.

/**
 * Intersections like `A & B` are correct but print as `A & B` and are harder to
 * read and compare. Mapping over the keys flattens them into one object type.
 * The trailing `& {}` stops the compiler from displaying the alias name.
 */
export type Simplify<T> = { [K in keyof T]: T[K] } & {};

/** Make only some properties optional. */
export type PartialBy<T, K extends keyof T> = Simplify<
  Omit<T, K> & Partial<Pick<T, K>>
>;

/** Make only some properties required. */
export type RequiredBy<T, K extends keyof T> = Simplify<
  Omit<T, K> & Required<Pick<T, K>>
>;

/** What a client may send to create an entity: everything except server-owned keys. */
export type CreateDto<T, ServerKeys extends keyof T> = Omit<T, ServerKeys>;

/** What a client may send to update an entity: no id, and every other key optional. */
export type UpdateDto<T extends { id: unknown }> = Partial<Omit<T, 'id'>>;

/** Recursively readonly: nested objects and arrays too. Functions are left alone. */
export type DeepReadonly<T> = T extends (...args: never[]) => unknown
  ? T
  : T extends readonly (infer E)[]
    ? readonly DeepReadonly<E>[]
    : T extends object
      ? { readonly [K in keyof T]: DeepReadonly<T[K]> }
      : T;

/** Runtime twin of Omit: returns a copy without the listed keys. */
export function omit<T extends object, K extends keyof T>(
  source: T,
  keys: readonly K[],
): Omit<T, K> {
  const copy = { ...source };
  for (const key of keys) {
    delete copy[key];
  }
  return copy;
}

/** Runtime twin of Pick. */
export function pick<T extends object, K extends keyof T>(
  source: T,
  keys: readonly K[],
): Pick<T, K> {
  const result = {} as Pick<T, K>;
  for (const key of keys) {
    result[key] = source[key];
  }
  return result;
}

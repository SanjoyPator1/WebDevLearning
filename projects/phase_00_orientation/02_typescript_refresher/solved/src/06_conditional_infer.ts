// Kata 06: conditional types, `infer` and distribution (topic 0.2)

/** Peel promises off recursively: Promise<Promise<number>> becomes number. */
export type Unwrap<T> = T extends Promise<infer U> ? Unwrap<U> : T;

/** `infer E` captures whatever the array holds. */
export type ElementOf<T> = T extends readonly (infer E)[] ? E : never;

/** `infer` can sit in a parameter position too. */
export type FirstArg<F> = F extends (first: infer A, ...rest: never[]) => unknown
  ? A
  : never;

export type ReturnTypeOf<F> = F extends (...args: never[]) => infer R ? R : never;

/**
 * Distributive: because `T` is a naked type parameter, a union is split, each
 * member goes through the conditional separately, and the results are joined.
 * ToArray<string | number> is string[] | number[].
 */
export type ToArray<T> = T extends unknown ? T[] : never;

/**
 * Wrapping both sides in a tuple switches distribution off, so the union is
 * treated as one type. ToArrayWhole<string | number> is (string | number)[].
 */
export type ToArrayWhole<T> = [T] extends [unknown] ? T[] : never;

/**
 * `never` is the empty union, so a naked `T extends never` distributes over
 * nothing and returns never. The tuple wrapper is the standard fix.
 */
export type IsNever<T> = [T] extends [never] ? true : false;

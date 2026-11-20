// Kata 06: conditional types, `infer` and distribution (topic 0.2)
//
// Syntax reminder: T extends U ? X : Y, and `infer R` inside the extends clause
// to capture a piece of T. A naked type parameter distributes over unions.

/** TODO(0.2): peel Promise off recursively. Promise<Promise<number>> becomes number, boolean stays boolean. */
export type Unwrap<T> = unknown;

/** TODO(0.2): the element type of an array or tuple, never for anything else. */
export type ElementOf<T> = unknown;

/** TODO(0.2): the type of the first parameter of a function type. never if F is not a function. */
export type FirstArg<F> = unknown;

/** TODO(0.2): the return type of a function type. never if F is not a function. */
export type ReturnTypeOf<F> = unknown;

/** TODO(0.2): DISTRIBUTIVE. ToArray<string | number> must be string[] | number[]. */
export type ToArray<T> = unknown;

/** TODO(0.2): NON-distributive. ToArrayWhole<string | number> must be (string | number)[]. */
export type ToArrayWhole<T> = unknown;

/** TODO(0.2): true when T is exactly never, false otherwise. A naive `T extends never` does not work. Why? */
export type IsNever<T> = unknown;

// Kata 02: discriminated unions and exhaustiveness checking (topic 0.2)

// Not part of this exercise: the union is given. Study its shape.
export type Shape =
  | { kind: 'circle'; radius: number }
  | { kind: 'square'; side: number }
  | { kind: 'rectangle'; width: number; height: number };

/** TODO(0.2): derive the union of all `kind` values from Shape. Do not write them out by hand. */
export type ShapeKind = string;

/** TODO(0.2): pick the single Shape member whose `kind` is K. Hint: a built-in utility type does it. */
export type ShapeOf<K extends ShapeKind> = Shape;

/**
 * TODO(0.2): throw `new Error(`Unexpected value: ${JSON.stringify(value)}`)`.
 * The parameter type is wrong on purpose. What type can only be satisfied
 * when every case has been handled?
 */
export function assertNever(value: unknown): never {
  throw new Error('TODO(0.2): implement assertNever');
}

/** TODO(0.2): circle PI*r^2, square s^2, rectangle w*h. End the switch with assertNever. */
export function area(shape: Shape): number {
  throw new Error('TODO(0.2): implement area');
}

/** TODO(0.2): 'circle r=2', 'square s=3', 'rectangle 2x5'. End the switch with assertNever. */
export function describeShape(shape: Shape): string {
  throw new Error('TODO(0.2): implement describeShape');
}

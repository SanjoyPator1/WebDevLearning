// Kata 02: discriminated unions and exhaustiveness checking (topic 0.2)

// Not part of this exercise: the union is given. Study its shape.
export type Shape =
  | { kind: 'circle'; radius: number }
  | { kind: 'square'; side: number }
  | { kind: 'rectangle'; width: number; height: number };

/** All discriminant values, derived from the union so it can never drift. */
export type ShapeKind = Shape['kind'];

/** Pick one member of the union by its discriminant. */
export type ShapeOf<K extends ShapeKind> = Extract<Shape, { kind: K }>;

/**
 * Taking `never` is the whole trick: a value can only be passed here if every
 * case was handled above, because nothing else is assignable to `never`.
 */
export function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${JSON.stringify(value)}`);
}

export function area(shape: Shape): number {
  switch (shape.kind) {
    case 'circle':
      return Math.PI * shape.radius ** 2;
    case 'square':
      return shape.side ** 2;
    case 'rectangle':
      return shape.width * shape.height;
    default:
      // If someone adds a fourth variant to Shape and forgets to handle it,
      // `shape` here is no longer `never` and this line stops compiling.
      return assertNever(shape);
  }
}

export function describeShape(shape: Shape): string {
  switch (shape.kind) {
    case 'circle':
      return `circle r=${shape.radius}`;
    case 'square':
      return `square s=${shape.side}`;
    case 'rectangle':
      return `rectangle ${shape.width}x${shape.height}`;
    default:
      return assertNever(shape);
  }
}

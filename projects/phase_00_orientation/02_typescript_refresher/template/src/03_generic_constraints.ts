// Kata 03: generics with constraints, defaults and generic classes (topic 0.2)
//
// The signatures below are deliberately too loose (object, string, unknown).
// Make them generic so the tests can see exact types.

/** TODO(0.2): return obj[key]. The key must be a real key of the object, and the result type must be the property's type. */
export function getProp(obj: object, key: string): unknown {
  throw new Error('TODO(0.2): implement getProp');
}

/** TODO(0.2): return the `key` property of every item, as an array of that property's type. */
export function pluck(items: readonly unknown[], key: string): unknown[] {
  throw new Error('TODO(0.2): implement pluck');
}

/**
 * TODO(0.2): group items by the key the callback returns.
 * The key type K should be inferred from the callback and must be usable as an
 * object key. A group only exists if some item produced it, so the result should
 * say that some keys may be missing.
 */
export function groupBy(
  items: readonly unknown[],
  keyFn: (item: unknown) => string,
): Record<string, unknown[]> {
  throw new Error('TODO(0.2): implement groupBy');
}

/** TODO(0.2): a generic Box with a type parameter whose default is string, so plain `Box` means `Box<string>`. */
export type Box = { value: unknown };

/** TODO(0.2): make this class generic and implement it. pop and peek return undefined when empty. */
export class Stack {
  get size(): number {
    throw new Error('TODO(0.2): implement size');
  }

  push(item: unknown): void {
    throw new Error('TODO(0.2): implement push');
  }

  pop(): unknown {
    throw new Error('TODO(0.2): implement pop');
  }

  peek(): unknown {
    throw new Error('TODO(0.2): implement peek');
  }
}

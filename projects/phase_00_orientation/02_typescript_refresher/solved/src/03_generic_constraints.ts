// Kata 03: generics with constraints, defaults and generic classes (topic 0.2)

/**
 * `K extends keyof T` ties the key to the object. The return type `T[K]` is
 * an indexed access type, so it follows whichever key was passed in.
 */
export function getProp<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

export function pluck<T, K extends keyof T>(items: readonly T[], key: K): T[K][] {
  return items.map((item) => item[key]);
}

/**
 * K is inferred from what `keyFn` returns. Constraining it to PropertyKey
 * guarantees it can be used as an object key. The result is Partial because a
 * group only exists if at least one item produced that key.
 */
export function groupBy<T, K extends PropertyKey>(
  items: readonly T[],
  keyFn: (item: T) => K,
): Partial<Record<K, T[]>> {
  const result: Partial<Record<K, T[]>> = {};
  for (const item of items) {
    const key = keyFn(item);
    (result[key] ??= []).push(item);
  }
  return result;
}

/** A type parameter with a default: `Box` alone means `Box<string>`. */
export type Box<T = string> = { value: T };

export class Stack<T> {
  private readonly items: T[] = [];

  get size(): number {
    return this.items.length;
  }

  push(item: T): void {
    this.items.push(item);
  }

  /** `undefined` when empty. The honest return type says so. */
  pop(): T | undefined {
    return this.items.pop();
  }

  peek(): T | undefined {
    return this.items.at(-1);
  }
}

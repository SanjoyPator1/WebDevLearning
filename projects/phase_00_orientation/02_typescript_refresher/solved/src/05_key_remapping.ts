// Kata 05: key remapping with `as` in mapped types (topic 0.2)

/**
 * `as` renames (or drops) each key while mapping. `string & K` narrows the
 * key to its string members, because `keyof T` may include number and symbol
 * and `Capitalize` only accepts strings.
 */
export type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

/** Remapping a key to `never` removes it. */
export type RemoveKey<T, Key extends keyof T> = {
  [K in keyof T as Exclude<K, Key>]: T[K];
};

/** Keep only the keys whose value is a function. */
export type OnlyFunctions<T> = {
  [K in keyof T as T[K] extends (...args: never[]) => unknown ? K : never]: T[K];
};

/** { click: MouseEvent } becomes { onClick: (payload: MouseEvent) => void } */
export type EventHandlers<Events extends Record<string, unknown>> = {
  [E in keyof Events as `on${Capitalize<string & E>}`]: (
    payload: Events[E],
  ) => void;
};

/**
 * The runtime twin of `Getters`: types are erased, so the same transformation
 * has to be written once more as real code. The `as` cast is the usual price,
 * because TypeScript cannot prove that the loop builds exactly `Getters<T>`.
 */
export function makeGetters<T extends object>(source: T): Getters<T> {
  const result: Record<string, () => unknown> = {};
  for (const key of Object.keys(source)) {
    const name = `get${key.charAt(0).toUpperCase()}${key.slice(1)}`;
    result[name] = () => source[key as keyof T];
  }
  return result as Getters<T>;
}

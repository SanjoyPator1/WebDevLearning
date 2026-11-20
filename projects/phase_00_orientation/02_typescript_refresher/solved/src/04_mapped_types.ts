// Kata 04: rebuild the core mapped utility types by hand (topic 0.2)
//
// Every type here already exists in lib.d.ts. Writing them yourself is the
// fastest way to learn `[K in keyof T]` and the `+`/`-` modifiers.

/** `?` adds optionality to every property. */
export type MyPartial<T> = { [K in keyof T]?: T[K] };

/** `-?` removes optionality (and the `| undefined` it implies). */
export type MyRequired<T> = { [K in keyof T]-?: T[K] };

export type MyReadonly<T> = { readonly [K in keyof T]: T[K] };

/** `-readonly` removes readonly. There is no built-in `Mutable`, this one is common. */
export type Mutable<T> = { -readonly [K in keyof T]: T[K] };

/** Iterating over `K` instead of `keyof T` selects only some keys. */
export type MyPick<T, K extends keyof T> = { [P in K]: T[P] };

export type MyRecord<K extends PropertyKey, V> = { [P in K]: V };

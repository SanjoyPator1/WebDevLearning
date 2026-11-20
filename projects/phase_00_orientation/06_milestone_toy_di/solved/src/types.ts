// Not part of this exercise: the shapes used by the container.

// Constructor arguments are typed `any` because a container builds arbitrary classes.
export type Constructor<T = unknown> = new (...args: any[]) => T;

/** What a dependency can be asked for by: a class, a string or a symbol. */
export type Token<T = unknown> = Constructor<T> | string | symbol;

/** One entry of the list @Inject() stores under SELF_DEPS_KEY. */
export interface SelfDeclaredDependency {
  index: number;
  token: string | symbol | Constructor;
}

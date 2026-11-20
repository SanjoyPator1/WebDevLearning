// Not part of this exercise: the error classes and their messages are given, so you can
// concentrate on WHEN each error must be thrown. The message formats are what the tests check.

/** A readable name for any token: class name, string, symbol description, or "undefined". */
export function tokenName(token: unknown): string {
  if (typeof token === 'function') return token.name;
  if (typeof token === 'symbol') return token.toString();
  return String(token);
}

/** resolve() was asked for a token that was never registered. */
export class UnknownProviderError extends Error {
  constructor(token: unknown) {
    super(`No provider found for ${tokenName(token)}`);
    this.name = 'UnknownProviderError';
  }
}

/** register() received a class without @Injectable(). */
export class NotInjectableError extends Error {
  constructor(target: Function) {
    super(`${target.name} is not decorated with @Injectable()`);
    this.name = 'NotInjectableError';
  }
}

/**
 * A constructor parameter has no provider. `dependencies` is the full parameter list (tokens),
 * `unresolvedIndex` is the first parameter that cannot be satisfied. Same shape as Nest's message:
 *   Can't resolve dependencies of Consumer (?, Dep). Please make sure that the argument Missing at index [0] is registered.
 */
export class UnresolvableDependencyError extends Error {
  constructor(consumer: Function, dependencies: unknown[], unresolvedIndex: number) {
    const shown = dependencies
      .map((dependency, index) => (index === unresolvedIndex ? '?' : tokenName(dependency)))
      .join(', ');
    super(
      `Can't resolve dependencies of ${consumer.name} (${shown}). ` +
        `Please make sure that the argument ${tokenName(dependencies[unresolvedIndex])} ` +
        `at index [${unresolvedIndex}] is registered.`,
    );
    this.name = 'UnresolvableDependencyError';
  }
}

/** The dependency graph has a cycle. `cycle` starts and ends with the same token: [A, B, A]. */
export class CircularDependencyError extends Error {
  constructor(readonly cycle: unknown[]) {
    super(`Circular dependency detected: ${cycle.map(tokenName).join(' -> ')}`);
    this.name = 'CircularDependencyError';
  }
}

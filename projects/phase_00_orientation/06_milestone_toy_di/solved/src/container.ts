import 'reflect-metadata'; // Not part of this exercise: installs the Reflect.* metadata API.
import {
  CircularDependencyError,
  NotInjectableError,
  UnknownProviderError,
  UnresolvableDependencyError,
} from './errors.js';
import { DESIGN_PARAMTYPES, INJECTABLE_KEY, SELF_DEPS_KEY } from './keys.js';
import type { Constructor, SelfDeclaredDependency, Token } from './types.js';

/**
 * A toy dependency injection container. One class, no modules and no scopes (see 1.2 and 2.4).
 *
 * Rules:
 * - Every registered class is a singleton: built once, on first resolve, then cached.
 * - A class's dependencies come from `design:paramtypes`, overridden per index by @Inject() tokens.
 * - Values registered with registerValue() are returned as they are.
 */
export class Container {
  private readonly classes = new Set<Constructor>();
  // Holds built singletons AND registered values, so both are looked up the same way.
  private readonly instances = new Map<Token, unknown>();

  register(...classes: Constructor[]): void {
    for (const target of classes) {
      if (!Reflect.getOwnMetadata(INJECTABLE_KEY, target)) throw new NotInjectableError(target);
      this.classes.add(target);
    }
  }

  registerValue(token: string | symbol, value: unknown): void {
    this.instances.set(token, value);
  }

  resolve<T>(token: Token<T>): T {
    return this.build(token, []) as T;
  }

  /** `path` is the chain of classes being built right now, outermost first. */
  private build(token: Token, path: Token[]): unknown {
    if (this.instances.has(token)) return this.instances.get(token);
    if (typeof token !== 'function' || !this.classes.has(token)) throw new UnknownProviderError(token);

    // Seeing a class that is already in the chain means we came back to it: a cycle.
    // Report only the cycle itself, not the classes that led into it.
    if (path.includes(token)) throw new CircularDependencyError([...path.slice(path.indexOf(token)), token]);

    const dependencies = this.dependenciesOf(token);
    const args = dependencies.map((dependency, index) => {
      // Check before recursing so the error names the consumer that is missing the provider.
      if (!this.has(dependency)) throw new UnresolvableDependencyError(token, dependencies, index);
      return this.build(dependency as Token, [...path, token]);
    });

    const instance = new token(...args);
    this.instances.set(token, instance); // cache last: a failed build leaves no half-made singleton
    return instance;
  }

  private has(token: unknown): boolean {
    return this.instances.has(token as Token) || this.classes.has(token as Constructor);
  }

  /** Types from the compiler, replaced per index by @Inject() tokens. */
  private dependenciesOf(target: Constructor): unknown[] {
    const dependencies: unknown[] = [...(Reflect.getOwnMetadata(DESIGN_PARAMTYPES, target) ?? [])];
    const declared: SelfDeclaredDependency[] = Reflect.getOwnMetadata(SELF_DEPS_KEY, target) ?? [];
    for (const { index, token } of declared) dependencies[index] = token;
    return dependencies;
  }
}

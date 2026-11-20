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
  // Suggested state (add what you need):
  //   private readonly classes = new Set<Constructor>();
  //   private readonly instances = new Map<Token, unknown>();

  /**
   * Task 3: register classes so they can be resolved.
   * Throw NotInjectableError for a class without @Injectable(). Registering does not build anything.
   */
  register(...classes: Constructor[]): void {
    throw new Error('TODO(milestone): remember each @Injectable() class');
  }

  /**
   * Task 3: register a ready-made value under a string or symbol token (what @Inject(token) asks for).
   */
  registerValue(token: string | symbol, value: unknown): void {
    throw new Error('TODO(milestone): remember the value under the token');
  }

  /**
   * Task 4 to 8: build (or return the cached) instance for a token.
   *
   * - Unknown token at the top level -> UnknownProviderError.
   * - A constructor parameter nobody provides -> UnresolvableDependencyError(consumer, params, index),
   *   where params is the full token list and index is the FIRST parameter that cannot be satisfied.
   * - A cycle (A needs B needs A) -> CircularDependencyError with the cycle, e.g. [A, B, A].
   * - Singletons: a second resolve returns the same instance, and two consumers share one dependency.
   */
  resolve<T>(token: Token<T>): T {
    throw new Error('TODO(milestone): resolve the token, depth first, with cycle detection');
  }
}

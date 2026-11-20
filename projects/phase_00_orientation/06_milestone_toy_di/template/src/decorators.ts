import 'reflect-metadata'; // Not part of this exercise: installs the Reflect.* metadata API.
import { INJECTABLE_KEY, SELF_DEPS_KEY } from './keys.js';
import type { Constructor, SelfDeclaredDependency } from './types.js';

/**
 * Task 1: mark a class as something the container may build.
 * Store `true` under INJECTABLE_KEY on the class.
 *
 * Why a marker at all? The compiler only emits `design:paramtypes` for classes that carry a
 * decorator, so an undecorated class would silently look like it has no dependencies.
 */
export function Injectable(): ClassDecorator {
  throw new Error('TODO(milestone): return a class decorator that sets INJECTABLE_KEY');
}

/**
 * Task 2: override the token of one constructor parameter, for tokens a type cannot express
 * (strings, symbols, interfaces).
 * Append `{ index, token }` to the list under SELF_DEPS_KEY on the class.
 * For a constructor parameter the compiler passes the CLASS as target and `undefined` as the
 * property key. Reject method parameters with an Error whose message contains "constructor parameters".
 */
export function Inject(token: string | symbol | Constructor): ParameterDecorator {
  throw new Error('TODO(milestone): return a parameter decorator that appends to SELF_DEPS_KEY');
}

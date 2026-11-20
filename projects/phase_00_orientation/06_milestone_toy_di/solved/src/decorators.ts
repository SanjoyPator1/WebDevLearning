import 'reflect-metadata'; // Not part of this exercise: installs the Reflect.* metadata API.
import { INJECTABLE_KEY, SELF_DEPS_KEY } from './keys.js';
import type { Constructor, SelfDeclaredDependency } from './types.js';

/**
 * Task 1: mark a class as something the container may build.
 *
 * Why a marker at all? The compiler only emits `design:paramtypes` for classes that carry a
 * decorator, so an undecorated class would silently look like it has no dependencies and the
 * container would build it with no arguments. Nest has the same rule: forget @Injectable()
 * and the constructor parameters are not injected.
 */
export function Injectable(): ClassDecorator {
  return (target) => {
    Reflect.defineMetadata(INJECTABLE_KEY, true, target);
  };
}

/**
 * Task 2: override the token of one constructor parameter.
 *
 * Needed when the type cannot name the dependency: a string or symbol token, or an interface
 * (which the compiler emits as `Object`). This is the same job Nest's @Inject() does, and it
 * stores its data the same way: a list of { index, token } on the class.
 */
export function Inject(token: string | symbol | Constructor): ParameterDecorator {
  return (target, propertyKey, index) => {
    // For a constructor parameter the compiler passes the class as target and undefined as key.
    if (propertyKey !== undefined) {
      throw new Error('@Inject() only works on constructor parameters');
    }
    // Parameter decorators run last to first and each sees one parameter, so append.
    const existing: SelfDeclaredDependency[] = Reflect.getOwnMetadata(SELF_DEPS_KEY, target) ?? [];
    Reflect.defineMetadata(SELF_DEPS_KEY, [...existing, { index, token }], target);
  };
}

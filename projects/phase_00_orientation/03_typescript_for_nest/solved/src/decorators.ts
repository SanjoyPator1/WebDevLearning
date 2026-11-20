import 'reflect-metadata'; // Not part of this exercise: installs the Reflect.* metadata API.
import { DESIGN_TYPE, FIELDS_KEY, PARAMS_KEY, PREFIX_KEY, ROUTE_KEY } from './keys.js';
import type { FieldMetadata, HttpMethod, ParamMetadata, RouteMetadata } from './types.js';

// Four kinds of decorator, four different argument lists. Every one of them follows the same
// shape: a FACTORY (called at the use site, receives your options) returns the DECORATOR
// (called by the compiler, receives what is being decorated).

/**
 * Task 1: class decorator. The compiler passes only the constructor.
 */
export function Controller(prefix: string): ClassDecorator {
  return (target) => {
    // target is the class itself, so the prefix lives on the constructor function.
    Reflect.defineMetadata(PREFIX_KEY, prefix, target);
  };
}

/**
 * Task 2: method decorators. The compiler passes (prototype, methodName, descriptor).
 */
function createRouteDecorator(httpMethod: HttpMethod) {
  return (path = ''): MethodDecorator => {
    return (target, propertyKey) => {
      const route: RouteMetadata = { httpMethod, path };
      // target is the PROTOTYPE, and propertyKey selects the slot for this method.
      // Nest stores the same data on descriptor.value (the function) instead; both work, but
      // prototype + key keeps this exercise symmetrical with the parameter decorator below.
      Reflect.defineMetadata(ROUTE_KEY, route, target, propertyKey);
    };
  };
}

export const Get = createRouteDecorator('GET');
export const Post = createRouteDecorator('POST');

/**
 * Task 3: parameter decorator. The compiler passes (prototype, methodName, parameterIndex).
 * For a constructor parameter, propertyKey is undefined and target is the class itself.
 */
export function Param(name: string): ParameterDecorator {
  return (target, propertyKey, index) => {
    if (propertyKey === undefined) {
      throw new Error('@Param() only works on method parameters');
    }
    // Copy-on-write: build a new array instead of pushing into the stored one. A decorator is
    // called once per parameter, so the list grows one entry per call.
    const existing: ParamMetadata[] = Reflect.getOwnMetadata(PARAMS_KEY, target, propertyKey) ?? [];
    Reflect.defineMetadata(PARAMS_KEY, [...existing, { index, name }], target, propertyKey);
  };
}

/**
 * Task 4: property decorator. The compiler passes (prototype, propertyName), no descriptor.
 */
export function Field(): PropertyDecorator {
  return (target, propertyKey) => {
    // The compiler adds its own __metadata("design:type", ...) decorator to the same list.
    // Decorators run right to left, so that one has ALREADY run when this code executes.
    // That ordering is why a decorator can read design:type at all.
    const type: Function = Reflect.getMetadata(DESIGN_TYPE, target, propertyKey);
    // Property decorators receive the prototype, so the class is target.constructor.
    // getOwnMetadata (not getMetadata) so a subclass does not extend its parent's array.
    const existing: FieldMetadata[] = Reflect.getOwnMetadata(FIELDS_KEY, target.constructor) ?? [];
    Reflect.defineMetadata(FIELDS_KEY, [...existing, { name: String(propertyKey), type }], target.constructor);
  };
}

import 'reflect-metadata'; // Not part of this exercise: installs the Reflect.* metadata API.
import { DESIGN_TYPE, FIELDS_KEY, PARAMS_KEY, PREFIX_KEY, ROUTE_KEY } from './keys.js';
import type { FieldMetadata, HttpMethod, ParamMetadata, RouteMetadata } from './types.js';

// Four kinds of decorator, four different argument lists. Read the README contract first.

/**
 * Task 1: class decorator.
 * Store `prefix` under PREFIX_KEY on the class constructor (the only argument you receive).
 */
export function Controller(prefix: string): ClassDecorator {
  throw new Error('TODO(0.3): return a class decorator that stores the prefix under PREFIX_KEY');
}

/**
 * Task 2: method decorators. Get and Post share one factory.
 * Store `{ httpMethod, path }` under ROUTE_KEY on the PROTOTYPE, for this method name.
 */
function createRouteDecorator(httpMethod: HttpMethod) {
  return (path = ''): MethodDecorator => {
    throw new Error('TODO(0.3): return a method decorator that stores a RouteMetadata under ROUTE_KEY');
  };
}

export const Get = createRouteDecorator('GET');
export const Post = createRouteDecorator('POST');

/**
 * Task 3: parameter decorator.
 * Append `{ index, name }` to the list under PARAMS_KEY on the PROTOTYPE, for this method name.
 * Several @Param() decorators on one method must all be kept.
 * Constructor parameters are not supported: reject them with an Error whose message contains
 * "method parameters".
 */
export function Param(name: string): ParameterDecorator {
  throw new Error('TODO(0.3): return a parameter decorator that appends a ParamMetadata under PARAMS_KEY');
}

/**
 * Task 4: property decorator.
 * Append `{ name, type }` to the list under FIELDS_KEY on the CLASS (not the prototype).
 * `type` is what the compiler emitted under the DESIGN_TYPE key for this property.
 */
export function Field(): PropertyDecorator {
  throw new Error('TODO(0.3): return a property decorator that appends a FieldMetadata under FIELDS_KEY');
}

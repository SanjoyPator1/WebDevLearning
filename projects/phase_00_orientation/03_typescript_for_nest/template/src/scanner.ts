import 'reflect-metadata'; // Not part of this exercise: installs the Reflect.* metadata API.
import { DESIGN_PARAMTYPES, FIELDS_KEY, PARAMS_KEY, PREFIX_KEY, ROUTE_KEY } from './keys.js';
import { joinPaths } from './paths.js';
import type { FieldMetadata, ParamMetadata, RouteInfo, RouteMetadata } from './types.js';

type Class = new (...args: never[]) => object;

/**
 * Task 5: read the fields recorded by @Field(), in declaration order.
 * A class without @Field() properties has no fields: return [].
 */
export function getFields(target: Class): FieldMetadata[] {
  throw new Error('TODO(0.3): read FIELDS_KEY from the class');
}

/**
 * Task 6: turn a decorated controller class into plain route objects.
 *
 * - Throw `<ClassName> is not decorated with @Controller()` if the class has no prefix metadata.
 * - Visit the prototype's own methods in declaration order and keep those that have ROUTE_KEY metadata.
 * - `path` is joinPaths(prefix, route.path).
 * - `params` has one entry per @Param(), sorted by index, with `type` taken from the
 *   compiler-emitted design:paramtypes of that method (DESIGN_PARAMTYPES key).
 */
export function scanController(controller: Class): RouteInfo[] {
  throw new Error('TODO(0.3): build the route table from the metadata');
}

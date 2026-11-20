import 'reflect-metadata'; // Not part of this exercise: installs the Reflect.* metadata API.
import { DESIGN_PARAMTYPES, FIELDS_KEY, PARAMS_KEY, PREFIX_KEY, ROUTE_KEY } from './keys.js';
import { joinPaths } from './paths.js';
import type { FieldMetadata, ParamMetadata, RouteInfo, RouteMetadata } from './types.js';

type Class = new (...args: never[]) => object;

/**
 * Task 5: read the fields recorded by @Field(), in declaration order.
 */
export function getFields(target: Class): FieldMetadata[] {
  // Decorators write the list, so reading it is a plain lookup. No stored metadata means
  // no @Field() ran, which is a normal case, not an error.
  return Reflect.getOwnMetadata(FIELDS_KEY, target) ?? [];
}

/**
 * Task 6: turn a decorated controller class into plain route objects.
 *
 * This is the same idea Nest's router explorer applies at bootstrap: scan the prototype,
 * read the metadata the decorators left, and build a table. Nothing here runs per request.
 */
export function scanController(controller: Class): RouteInfo[] {
  const prefix: string | undefined = Reflect.getOwnMetadata(PREFIX_KEY, controller);
  if (prefix === undefined) {
    throw new Error(`${controller.name} is not decorated with @Controller()`);
  }

  const prototype = controller.prototype;
  const routes: RouteInfo[] = [];

  // getOwnPropertyNames lists methods in definition order and includes 'constructor', which has
  // no route metadata and is skipped by the check below.
  for (const handler of Object.getOwnPropertyNames(prototype)) {
    const route: RouteMetadata | undefined = Reflect.getOwnMetadata(ROUTE_KEY, prototype, handler);
    if (route === undefined) continue;

    // design:paramtypes exists for this method only because a decorator (@Get) is on it.
    const paramTypes: Function[] = Reflect.getOwnMetadata(DESIGN_PARAMTYPES, prototype, handler) ?? [];
    const storedParams: ParamMetadata[] = Reflect.getOwnMetadata(PARAMS_KEY, prototype, handler) ?? [];

    // Decorators ran last to first, so the stored list is in reverse order: sort it.
    const params = storedParams
      .map((param) => ({ ...param, type: paramTypes[param.index] }))
      .sort((a, b) => a.index - b.index);

    routes.push({
      httpMethod: route.httpMethod,
      path: joinPaths(prefix, route.path),
      handler,
      params,
    });
  }

  return routes;
}

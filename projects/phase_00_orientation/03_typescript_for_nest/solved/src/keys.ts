// Not part of this exercise: these names are given so the tests and your code agree.
// Each key says WHERE the metadata is stored. The README has the full contract.

/** Class-level. target = the class constructor. Value: string (the prefix). */
export const PREFIX_KEY = 'demo:prefix';

/** Method-level. target = the class prototype, propertyKey = the method name. Value: RouteMetadata. */
export const ROUTE_KEY = 'demo:route';

/** Method-level. target = the class prototype, propertyKey = the method name. Value: ParamMetadata[]. */
export const PARAMS_KEY = 'demo:params';

/** Class-level. target = the class constructor. Value: FieldMetadata[]. */
export const FIELDS_KEY = 'demo:fields';

// Keys that the TypeScript compiler writes by itself when emitDecoratorMetadata is on.
export const DESIGN_TYPE = 'design:type';
export const DESIGN_PARAMTYPES = 'design:paramtypes';

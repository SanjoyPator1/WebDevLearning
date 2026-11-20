// Not part of this exercise: shapes of the metadata and of the scanner's output.

export type HttpMethod = 'GET' | 'POST';

/** Stored under ROUTE_KEY by @Get() and @Post(). `path` is exactly what the decorator received. */
export interface RouteMetadata {
  httpMethod: HttpMethod;
  path: string;
}

/** One entry of the list stored under PARAMS_KEY by @Param(). */
export interface ParamMetadata {
  index: number;
  name: string;
}

/** One entry of the list stored under FIELDS_KEY by @Field(). `type` is the design:type constructor. */
export interface FieldMetadata {
  name: string;
  type: Function;
}

/** A parameter as the scanner reports it: the stored metadata plus the compiler-emitted type. */
export interface ParamInfo extends ParamMetadata {
  type: Function;
}

/** One row of the route table. `path` is the full path (prefix + method path). */
export interface RouteInfo {
  httpMethod: HttpMethod;
  path: string;
  handler: string;
  params: ParamInfo[];
}

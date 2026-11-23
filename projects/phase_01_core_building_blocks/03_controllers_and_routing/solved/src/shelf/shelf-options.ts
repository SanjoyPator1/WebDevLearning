import type { NestApplicationOptions } from '@nestjs/common';

// The tests pass these objects as the options of the application, the same object you
// would give to NestFactory.create(AppModule, options).

// 7b: routeConflictPolicy is checked at bootstrap, per kind of conflict, each 'off' | 'warn' |
// 'error' (default 'off'). `duplicate` = identical method and path; `shadow` = patterns that
// can match the same request. 'error' aborts startup with a RouteConflictException.
export const strictRoutes: NestApplicationOptions = {
  routeConflictPolicy: { duplicate: 'error', shadow: 'warn' },
};

// 7c: routeResolutionStrategy 'specificity' sorts routes (literal, then mixed, then :param,
// then wildcard) before registering them on order-sensitive adapters such as Express.
// The default is 'declaration'.
export const specificityRoutes: NestApplicationOptions = {
  routeResolutionStrategy: 'specificity',
};

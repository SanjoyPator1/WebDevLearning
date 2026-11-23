import type { NestApplicationOptions } from '@nestjs/common';

// The tests pass these objects as the options of the application, the same object you
// would give to NestFactory.create(AppModule, options).

// TODO(1.3) Task 7b
// Make the application refuse to start when two routes are exactly the same (same method
// and path), and only print a warning when a route is shadowed by another.
// Look at the route options of NestApplicationOptions.
export const strictRoutes: NestApplicationOptions = {};

// TODO(1.3) Task 7c
// Make Nest register literal routes before parameter routes, whatever the order they are
// declared in. It is another route option of NestApplicationOptions.
export const specificityRoutes: NestApplicationOptions = {};

import { type MiddlewareConsumer, Module, type NestModule, RequestMethod } from '@nestjs/common';
import { MarkMiddleware } from '../mark/mark.middleware.js';
import { ElsewhereController, ScopedController } from './scoped.controller.js';

// Task 3: exclude() comes BEFORE forRoutes(): forRoutes() ends the chain and returns the
// consumer again. A route is described by a path AND a method, `{ path, method }`, so the
// exclusion hits GET /scoped/health only and POST /scoped/health keeps the middleware.
// The path has no leading slash and no global prefix: Nest adds the prefix itself.
//
// An exclusion is an exact match (`exclude('scoped')` would skip /scoped but still run for
// /scoped/1), unlike a plain string in forRoutes(), which is a prefix match.
@Module({ controllers: [ScopedController, ElsewhereController] })
export class ScopedModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer
      .apply(MarkMiddleware)
      .exclude({ path: 'scoped/health', method: RequestMethod.GET })
      .forRoutes(ScopedController);
  }
}

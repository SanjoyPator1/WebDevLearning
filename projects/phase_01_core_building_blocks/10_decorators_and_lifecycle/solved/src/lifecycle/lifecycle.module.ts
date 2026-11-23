import { type MiddlewareConsumer, Module, type NestModule } from '@nestjs/common';
import { ModuleMiddleware } from './components.js';
import { LifecycleController } from './lifecycle.controller.js';

// Not part of this exercise: modules are topic 1.2, middleware 1.5. This module applies a middleware to the
// routes of LifecycleController (the controller class form: it covers exactly its routes).
@Module({ controllers: [LifecycleController] })
export class LifecycleModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(ModuleMiddleware).forRoutes(LifecycleController);
  }
}

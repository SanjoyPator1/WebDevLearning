import { MiddlewareConsumer, Module, NestModule } from '@nestjs/common';
import { ApiKeyMiddleware } from './api-key.middleware.js';
import { SecuredController } from './secured.controller.js';
import { SecuredService } from './secured.service.js';

// Not part of this exercise: the wiring is given so that Task 6 is only about the middleware.
@Module({
  controllers: [SecuredController],
  providers: [SecuredService],
})
export class SecuredModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(ApiKeyMiddleware).forRoutes(SecuredController);
  }
}

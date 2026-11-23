import { type MiddlewareConsumer, Module, type NestModule } from '@nestjs/common';
import { CountedController, OtherController } from './counted.controller.js';
import { HitCounterMiddleware } from './hit-counter.middleware.js';
import { HitCounterService } from './hit-counter.service.js';

// Task 2b: middleware is not listed in `providers`. A module opts in by implementing NestModule
// and describing the routes in configure(). Passing the CONTROLLER CLASS to forRoutes() applies
// the middleware to exactly the routes that controller declares (and nothing else), whatever
// its prefix is: if the prefix changes, this line does not.
@Module({
  controllers: [CountedController, OtherController],
  providers: [HitCounterService],
})
export class CountedModule implements NestModule {
  configure(consumer: MiddlewareConsumer): void {
    consumer.apply(HitCounterMiddleware).forRoutes(CountedController);
  }
}

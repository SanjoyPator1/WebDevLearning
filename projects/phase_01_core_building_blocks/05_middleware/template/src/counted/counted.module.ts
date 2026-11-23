import { Module } from '@nestjs/common';
import { CountedController, OtherController } from './counted.controller.js';
import { HitCounterService } from './hit-counter.service.js';

// TODO(1.5) Task 2b
// Middleware is NOT listed in `providers`: a module that wants middleware implements
// NestModule and says where it applies, in configure(consumer).
// Apply HitCounterMiddleware to CountedController only (not to OtherController).
// The @Module() decorator below is given.
@Module({
  controllers: [CountedController, OtherController],
  providers: [HitCounterService],
})
export class CountedModule {}

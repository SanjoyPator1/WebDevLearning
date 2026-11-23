import { Module } from '@nestjs/common';
import { CounterService } from './counter.service.js';

// TODO(1.2) Task 1
// CounterService is a provider of this module, so it is PRIVATE: no other module can
// inject it yet. Decide what CounterModule must declare so that modules which import it
// can use CounterService.
@Module({
  providers: [CounterService],
})
export class CounterModule {}

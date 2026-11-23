import { Module } from '@nestjs/common';
import { CounterModule } from '../counter/counter.module.js';
import { GreeterController } from './greeter.controller.js';
import { GreeterService } from './greeter.service.js';

// GreeterService needs CounterService. Nest looks in this module's own providers first and
// then in the exports of the modules listed in `imports`, so we import the module that
// owns the provider instead of listing CounterService here a second time.
//
// Nothing is exported: GreeterService is only used by the controller in this same module.
// Export only what other modules actually need.
@Module({
  imports: [CounterModule],
  controllers: [GreeterController],
  providers: [GreeterService],
})
export class GreeterModule {}

import { Module } from '@nestjs/common';
import { GreeterController } from './greeter.controller.js';
import { GreeterService } from './greeter.service.js';

// TODO(1.2) Task 1
// GreeterService needs CounterService, but CounterService lives in another module.
// Tell Nest where to find it. Then ask yourself: does this module need to export anything?
@Module({
  controllers: [GreeterController],
  providers: [GreeterService],
})
export class GreeterModule {}

import { Controller, Get, Module } from '@nestjs/common';
import { StampService } from './stamp.service.js';

@Controller('stamped')
export class StampedController {
  @Get()
  get(): string {
    return 'stamped';
  }
}

// TODO(1.8) Task 5c
// Make StampInterceptor GLOBAL in a way that keeps dependency injection (it needs StampService):
// register it as a provider under the APP_INTERCEPTOR token (from @nestjs/core) with `useClass`.
// A provider of the form { provide, useClass } is a custom provider (topic 2.2): copy the shape.
// The interceptor then applies to the WHOLE application, including controllers of other modules.
@Module({
  controllers: [StampedController],
  providers: [StampService],
})
export class StampModule {}

import { Controller, Get, Module } from '@nestjs/common';
import { APP_INTERCEPTOR } from '@nestjs/core';
import { StampInterceptor } from './stamp.interceptor.js';
import { StampService } from './stamp.service.js';

@Controller('stamped')
export class StampedController {
  @Get()
  get(): string {
    return 'stamped';
  }
}

// Task 5c: { provide: APP_INTERCEPTOR, useClass } registers a provider that Nest builds like any other
// (so StampInterceptor receives StampService), and applies it to the WHOLE application. Measured: an
// APP_INTERCEPTOR sitting in a module wrapped a controller of a module that never imported it. The module
// only decides what the interceptor can inject. The same pattern exists for guards (APP_GUARD, 1.7),
// pipes (APP_PIPE, 1.6) and filters (APP_FILTER, 1.9).
@Module({
  controllers: [StampedController],
  providers: [StampService, { provide: APP_INTERCEPTOR, useClass: StampInterceptor }],
})
export class StampModule {}

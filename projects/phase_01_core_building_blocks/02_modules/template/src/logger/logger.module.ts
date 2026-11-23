import { Module } from '@nestjs/common';
import { LoggerService } from './logger.service.js';

// TODO(1.2) Task 4
// Every module should be able to inject LoggerService WITHOUT importing LoggerModule.
// There is a decorator for that, and the provider still has to be exported.
@Module({
  providers: [LoggerService],
})
export class LoggerModule {}

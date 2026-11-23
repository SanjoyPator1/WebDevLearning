import { Module } from '@nestjs/common';
import { APP_FILTER } from '@nestjs/core';
import { ErrorLog } from './error-log.js';
import { LoggingFilter } from './logging.filter.js';

// Task 4b: { provide: APP_FILTER, useClass } registers the filter as a provider that Nest builds like any
// other (so ErrorLog and BaseExceptionFilter's HttpAdapterHost are injected), and applies it to the WHOLE
// application. Measured: it handled errors of a module that never imported this one, and even the
// router's own 404 for an unknown path, which no controller or route-level filter could have caught.
// The same pattern: APP_GUARD (1.7), APP_PIPE (1.6), APP_INTERCEPTOR (1.8).
// With a global filter AND a controller or method filter, only the most specific one handles the
// exception (Task 5): a global catch-all does not see what a narrower filter caught.
@Module({
  providers: [ErrorLog, { provide: APP_FILTER, useClass: LoggingFilter }],
})
export class AuditModule {}

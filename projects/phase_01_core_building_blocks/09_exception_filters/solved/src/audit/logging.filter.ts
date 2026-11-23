import { type ArgumentsHost, Catch, Injectable } from '@nestjs/common';
import { BaseExceptionFilter } from '@nestjs/core';
import { ErrorLog } from './error-log.js';

// Task 4a: a catch-all that observes and then DELEGATES.
//   @Catch()                @Catch with no arguments matches everything that is thrown, including
//                           values that are not Errors (measured: a thrown string is a 500 like any other)
//   extends BaseExceptionFilter
//                           its catch() is Nest's own default handling: an HttpException gets its own
//                           status and body, anything else the generic 500 (and the logging of
//                           unexpected errors). Calling super.catch() keeps all of it.
// Not extending it would mean rebuilding that logic by hand, including the cases you forget (errors from
// libraries that carry a statusCode, headers already sent) and the platform-specific reply call.
//
// BaseExceptionFilter reaches the HTTP adapter through a property that Nest injects (HttpAdapterHost), so
// the subclass only adds what it needs. The constructor calls super() with nothing for that reason.
// Registered with APP_FILTER (audit.module.ts) Nest builds it, so both the property and ErrorLog arrive.
// Registered as `app.useGlobalFilters(new LoggingFilter(log))` it would have NO adapter: measured, the
// response then falls through to Express's own HTML error page. Pass the adapter by hand
// (new LoggingFilter(log, app.get(HttpAdapterHost).httpAdapter)) if you must, or use APP_FILTER.
@Catch()
@Injectable()
export class LoggingFilter extends BaseExceptionFilter {
  constructor(private readonly log: ErrorLog) {
    super();
  }

  override catch(exception: unknown, host: ArgumentsHost): void {
    const name = (exception as object | null)?.constructor?.name ?? typeof exception;
    const message = exception instanceof Error ? exception.message : String(exception);
    this.log.add(`${name}: ${message}`);

    super.catch(exception, host);
  }
}

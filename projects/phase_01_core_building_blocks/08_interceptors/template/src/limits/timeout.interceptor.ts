import type { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import type { Observable } from 'rxjs';

// TODO(1.8) Task 3a
// Give a route at most 50 milliseconds. If the handler has not produced its value by then, the client
// must get a 408 (RequestTimeoutException) instead of waiting.
//   - rxjs has a `timeout` operator: after the time it errors with a TimeoutError (from rxjs)
//   - on its own that error is not an HttpException, so Nest would answer 500
//   - catch it, and turn a TimeoutError into a RequestTimeoutException. Any OTHER error must go on
//     unchanged (a handler's BadRequestException is still a 400)
// Operators: timeout, catchError (and throwError to put an error back on the stream).
export class TimeoutInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    throw new Error('TODO(1.8) Task 3a: TimeoutInterceptor');
  }
}

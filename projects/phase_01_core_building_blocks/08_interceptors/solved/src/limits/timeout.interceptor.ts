import {
  type CallHandler,
  type ExecutionContext,
  Injectable,
  type NestInterceptor,
  RequestTimeoutException,
} from '@nestjs/common';
import { type Observable, TimeoutError, catchError, throwError, timeout } from 'rxjs';

// Task 3a: timeout(50) makes the stream fail with rxjs's TimeoutError if no value arrives in 50 ms.
// On its own that is not an HttpException, so Nest answers 500 (measured). catchError turns that one
// error into a 408 and puts every other error back on the stream with throwError, unchanged.
//
// The limit: the timeout stops WAITING for the handler, it does not CANCEL it. Measured: the slow
// handler kept running and finished after the 408 had been sent, with all its side effects (a
// database write, a payment call). A timeout protects the client's wait, not the server's work; real
// cancellation needs the handler itself to honour an abort signal.
@Injectable()
export class TimeoutInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    return next.handle().pipe(
      timeout(50),
      catchError((error: unknown) =>
        throwError(() => (error instanceof TimeoutError ? new RequestTimeoutException() : error)),
      ),
    );
  }
}

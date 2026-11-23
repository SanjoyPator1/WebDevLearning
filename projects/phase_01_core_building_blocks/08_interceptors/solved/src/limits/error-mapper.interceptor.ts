import {
  BadGatewayException,
  type CallHandler,
  type ExecutionContext,
  HttpException,
  Injectable,
  type NestInterceptor,
} from '@nestjs/common';
import { type Observable, catchError, throwError } from 'rxjs';

// Task 3b: catchError sees every error that travels back through next.handle(): from the handler and,
// measured, from its pipes too (pipes run inside next.handle()). It does NOT see a guard denial,
// because guards run before interceptors.
//
// Returning throwError(...) REPLACES the error with another one. Returning a value (`of(x)`) would
// SWALLOW it and answer 200 (measured, even for a real bug), which is almost never what you want; so
// an HttpException is re-thrown as it is, and only the unexpected plain Error is rewritten, with a
// message that does not leak internals.
//
// Mapping errors is the job of exception filters (1.9, 3.4), which also see errors from guards and
// middleware, so prefer a filter for application-wide error shaping. An interceptor makes sense when
// the mapping belongs to a specific route or to a specific concern such as timing out a call.
@Injectable()
export class ErrorMapperInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    return next.handle().pipe(
      catchError((error: unknown) =>
        throwError(() => (error instanceof HttpException ? error : new BadGatewayException('upstream failed'))),
      ),
    );
  }
}

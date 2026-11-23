import type { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import type { Observable } from 'rxjs';

// TODO(1.8) Task 1
// An interceptor wraps the handler. intercept(context, next) is called BEFORE the handler, and
// `next.handle()` is the handler: it returns an Observable of what the handler returns. Whatever
// Observable you return is what Nest sends to the client, so piping an operator onto
// next.handle() changes the response.
//
// Make this interceptor wrap every successful response in an envelope: { data: <what the handler
// returned> }. A handler that returns nothing (undefined) must give { data: null }, not { }.
// Errors are not touched: a handler that throws keeps its normal error response.
// Look for the rxjs operator that transforms each value that passes through.
//
// Mark it injectable. (The controller already binds it.)
export class EnvelopeInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    throw new Error('TODO(1.8) Task 1: EnvelopeInterceptor');
  }
}

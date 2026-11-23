import { type CallHandler, type ExecutionContext, Injectable, type NestInterceptor } from '@nestjs/common';
import { type Observable, map } from 'rxjs';

// Task 1: next.handle() is an Observable of what the handler returned (after its pipes ran, and after
// a Promise was awaited). Nest sends whatever Observable intercept() returns, so `.pipe(map(...))` is
// how a response is reshaped. map runs once per emitted value and is skipped when the stream errors,
// so an exception reaches the exception layer (1.9) untouched.
//
// `?? null`: a handler that returns undefined would give { data: undefined }, and JSON drops
// undefined properties, so the client would see {} (measured). Normalising to null keeps the shape.
//
// Wrapping every response is a contract change for all clients, so decide it once and apply it in one
// place, as here (a global envelope, versus plain resources, is discussed in 3.3).
@Injectable()
export class EnvelopeInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    return next.handle().pipe(map((data) => ({ data: data ?? null })));
  }
}

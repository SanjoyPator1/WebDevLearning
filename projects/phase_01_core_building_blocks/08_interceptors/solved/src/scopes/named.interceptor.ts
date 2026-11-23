import type { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import { type Observable, tap } from 'rxjs';

// Not part of this exercise: every NamedInterceptor and the handlers write into this array, so the
// tests can read the order. It writes "<name>:before" on the way in and "<name>:after" on the way out.
export const trace: string[] = [];

export class NamedInterceptor implements NestInterceptor {
  constructor(private readonly name: string) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    trace.push(`${this.name}:before`);
    return next.handle().pipe(tap(() => trace.push(`${this.name}:after`)));
  }
}

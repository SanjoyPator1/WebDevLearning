import { type CallHandler, type ExecutionContext, Injectable, type NestInterceptor } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { Request } from 'express';
import { type Observable, of, tap } from 'rxjs';
import { Cached } from './cached.decorator.js';

// Task 4b: the strongest thing an interceptor can do is NOT call the handler. next.handle() is lazy:
// the handler (and its pipes) run only when the Observable it returns is subscribed to (measured:
// never calling it, or calling it and not subscribing, runs the handler zero times). On a cache hit
// this interceptor returns `of(stored)` and the handler is never reached.
//
// The Reflector comes from the ExecutionContext's getHandler() and getClass(), exactly as in a
// guard (1.7): that is how an interceptor knows which routes opted in.
//
// Singleton state is correct here: the Map is meant to be shared by every request. It is also
// unbounded and never expires, which is why a real cache has a TTL and a size limit and lives
// outside the process when there are several instances: the built-in CacheInterceptor and a Redis
// store are topic 4.5.
// Keying on originalUrl (path AND query) is why ?x=1 and ?x=2 are different entries. A real cache must
// also consider the method, the user and headers that change the response.
@Injectable()
export class MemoInterceptor implements NestInterceptor {
  private readonly cache = new Map<string, unknown>();

  constructor(private readonly reflector: Reflector) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const marked = this.reflector.getAllAndOverride(Cached, [context.getHandler(), context.getClass()]);
    if (marked === undefined) {
      return next.handle();
    }

    const key = context.switchToHttp().getRequest<Request>().originalUrl;
    if (this.cache.has(key)) {
      return of(this.cache.get(key));
    }
    return next.handle().pipe(tap((value) => this.cache.set(key, value)));
  }
}

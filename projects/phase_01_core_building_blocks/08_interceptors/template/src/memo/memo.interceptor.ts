import type { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import type { Observable } from 'rxjs';

// TODO(1.8) Task 4b
// An interceptor that can ANSWER WITHOUT CALLING THE HANDLER: a cache.
//   - read @Cached with the Reflector (inject it), handler first and then controller
//     (getAllAndOverride). Not marked: just `return next.handle()`, untouched
//   - marked: the cache key is request.originalUrl (the query string is part of it)
//       key already stored -> return of(storedValue): the handler, and its pipes, do not run
//       otherwise          -> let the handler run, store its value under the key (tap), return it
//   - keep the cache in a Map field: here sharing it between requests is exactly the point
// next.handle() is lazy: the handler runs only when its Observable is subscribed to, so simply not
// calling it (or not returning it) means the handler never runs.
export class MemoInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    throw new Error('TODO(1.8) Task 4b: MemoInterceptor');
  }
}

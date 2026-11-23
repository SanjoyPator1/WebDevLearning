import { CallHandler, ExecutionContext, Injectable, NestInterceptor } from '@nestjs/common';
import { Observable } from 'rxjs';
import { StampService } from './stamp.service.js';

// Not part of this exercise: a finished interceptor that NEEDS a provider, so it must be built by Nest.
// It adds a header with the next stamp to every response it wraps.
@Injectable()
export class StampInterceptor implements NestInterceptor {
  constructor(private readonly stamps: StampService) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    context.switchToHttp().getResponse().setHeader('x-stamp', this.stamps.next());
    return next.handle();
  }
}

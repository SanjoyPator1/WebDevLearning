import {
  CallHandler,
  ExecutionContext,
  Injectable,
  Logger,
  NestInterceptor,
} from '@nestjs/common';
import { Request } from 'express';
import { Observable, tap } from 'rxjs';

@Injectable()
export class TimingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(TimingInterceptor.name);

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const request = context.switchToHttp().getRequest<Request>();
    const start = Date.now();

    return next.handle().pipe(
      // tap is for peeking. It lets us run some code when the value goes past, but it doesnot touch the value.
      // Whatever came in comes out unchanged
      tap({
        next: () => {
          this.logger.log(
            `${request.method} ${request.url} took ${Date.now() - start}ms`,
          );
        },
      }),
    );
  }
}

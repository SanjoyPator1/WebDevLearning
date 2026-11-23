import { type CallHandler, type ExecutionContext, Injectable, type NestInterceptor } from '@nestjs/common';
import type { Request, Response } from 'express';
import { type Observable, finalize, tap } from 'rxjs';
import { AuditLog } from '../common/audit-log.js';

// Task 2: an interceptor is "code before, code after, wrapped around next.handle()".
//   before   everything in intercept() before the return runs before the pipes and the handler
//   after    operators piped onto next.handle() run when the handler's value (or error) comes back
// tap({ next, error }) observes the success value and the error WITHOUT changing either: the error
// keeps travelling to the exception filters. finalize runs when the stream ends for any reason, and
// measured, before the response is sent (res.headersSent is still false), which is why the header can
// still be set in tap but not afterwards.
//
// The start time is a LOCAL variable. An interceptor is a singleton shared by every request, so a
// field such as `this.start` is overwritten by an overlapping request (measured: a 150 ms request
// reported 110 ms). The closure over `start` is per call: each request gets its own.
@Injectable()
export class TimingInterceptor implements NestInterceptor {
  constructor(private readonly log: AuditLog) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    const http = context.switchToHttp();
    const request = http.getRequest<Request>();
    const response = http.getResponse<Response>();
    const start = Date.now();

    this.log.add(`start ${request.method} ${request.originalUrl}`);

    return next.handle().pipe(
      tap({
        next: () => {
          response.setHeader('x-elapsed-ms', String(Date.now() - start));
          this.log.add('ok');
        },
        error: () => this.log.add('error'),
      }),
      finalize(() => this.log.add('done')),
    );
  }
}

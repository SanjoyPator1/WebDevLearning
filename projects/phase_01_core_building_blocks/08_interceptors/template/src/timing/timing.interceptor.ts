import type { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import type { Observable } from 'rxjs';

// TODO(1.8) Task 2
// Timing and logging, which is code BEFORE and AFTER the handler. Using AuditLog (a provider:
// make this class injectable and take it in the constructor):
//   before the handler    add  "start <METHOD> <url>"  for example "start GET /work/ok/30"
//                         (take the request from the context: request.method, request.originalUrl)
//   handler succeeded     add  "ok"  and set the response header "x-elapsed-ms" to the number of
//                         milliseconds the handler took, as a string
//   handler failed        add  "error"  and let the error continue UNCHANGED (the client still gets
//                         the handler's 400)
//   always, at the end    add  "done"
// Operators to look at: tap (a side effect that does not change the value, and has a form for
// errors), finalize (runs when the stream ends either way).
//
// One trap: Nest builds this class ONCE and every request uses it. Where do you keep the start time?
// The test sends a slow and a fast request at the same time.
export class TimingInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    throw new Error('TODO(1.8) Task 2: TimingInterceptor');
  }
}

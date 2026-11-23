import type { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import type { Observable } from 'rxjs';

// TODO(1.8) Task 3b
// Turn an unexpected failure into a proper HTTP error.
//   - a plain Error (anything that is NOT an HttpException) becomes a BadGatewayException with the
//     message 'upstream failed': the real message must not reach the client
//   - an HttpException is left exactly as it is
// (Exception filters, topic 1.9, are the usual home for mapping errors. This task is about what an
// interceptor can do with an error on the stream: it sees it, and can replace it.)
export class ErrorMapperInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    throw new Error('TODO(1.8) Task 3b: ErrorMapperInterceptor');
  }
}

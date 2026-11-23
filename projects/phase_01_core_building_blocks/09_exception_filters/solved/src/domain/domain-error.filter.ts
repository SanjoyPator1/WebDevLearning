import { type ArgumentsHost, Catch, type ExceptionFilter } from '@nestjs/common';
import type { Response } from 'express';
import {
  DomainError,
  InvalidQuantityError,
  OutOfStockError,
  UnknownProductError,
} from './domain-errors.js';

// Task 3: the mapping from domain errors to HTTP lives HERE, at the edge, and nowhere else.
//   - the service throws errors in the language of the business and imports nothing from HTTP
//   - the controller is thin and does not catch
//   - this filter is the single place that knows 409, 422 and 404
// The alternatives are worse: a service that throws NotFoundException is married to HTTP (it cannot be
// reused from a queue consumer or a CLI, 10.4); a try/catch in every controller method repeats the
// mapping; an interceptor's catchError (1.8) works per route but, unlike a filter, never sees an error
// thrown by a guard or by middleware.
//
// @Catch(DomainError) is matched with `instanceof` against the abstract base class, so every present and
// future subclass reaches the filter, and the lookup picks the status by the specific subclass. Anything
// that is not a DomainError (a plain Error, an HttpException) is not matched and keeps its default
// handling: the message of an unexpected failure must not leak.
@Catch(DomainError)
export class DomainErrorFilter implements ExceptionFilter {
  catch(exception: DomainError, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();

    response.status(this.statusOf(exception)).json({ code: exception.code, message: exception.message });
  }

  private statusOf(error: DomainError): number {
    if (error instanceof OutOfStockError) return 409;
    if (error instanceof InvalidQuantityError) return 422;
    if (error instanceof UnknownProductError) return 404;
    return 400;
  }
}

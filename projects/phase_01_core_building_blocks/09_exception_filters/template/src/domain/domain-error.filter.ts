import type { ArgumentsHost, ExceptionFilter } from '@nestjs/common';

// TODO(1.9) Task 3
// Map domain errors to HTTP responses in ONE place, so services and controllers never mention a status.
// Handle every DomainError (and its subclasses) with @Catch(DomainError), and answer with the body
//   { code: <the error's code>, message: <the error's message> }
// and this status, chosen by the KIND of error:
//   OutOfStockError       409
//   InvalidQuantityError  422
//   UnknownProductError   404
//   any other DomainError 400   (for example DiscontinuedError)
// Errors that are not DomainErrors (a plain Error) must NOT be handled here: with a @Catch(DomainError)
// filter they go on to Nest's default handling and the client gets a generic 500.
// Mark it injectable; the controller already binds it.
export class DomainErrorFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    throw new Error('TODO(1.9) Task 3: DomainErrorFilter');
  }
}

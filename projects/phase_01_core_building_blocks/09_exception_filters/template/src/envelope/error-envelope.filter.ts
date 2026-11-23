import type { ArgumentsHost, ExceptionFilter } from '@nestjs/common';

// TODO(1.9) Task 2
// A custom exception filter: a class with catch(exception, host) and a @Catch(...) decorator that says
// WHICH exceptions it handles. Make this one handle every HttpException (and so its subclasses) and
// answer with one envelope:
//
//   { status, code, message, path }
//
//   status   the exception's HTTP status
//   code     the exception's errorCode when it has one, otherwise 'HTTP_<status>' (for example 'HTTP_404')
//   message  the `message` of the exception's response when it has one (a string, OR an array of
//            strings), otherwise the exception's own message
//   path     the request's original url (query string included)
//
// A filter receives an ArgumentsHost, the same kind of object as the ExecutionContext of guards. Take the
// response with host.switchToHttp().getResponse() and the request with getRequest(). The filter itself
// must SEND the response (response.status(...).json(...)): nothing is sent for it. A filter that returns
// without answering leaves the request hanging.
// Mark it injectable; the controller already binds it. Other errors (a plain Error) are not its business.
export class ErrorEnvelopeFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    throw new Error('TODO(1.9) Task 2: ErrorEnvelopeFilter');
  }
}

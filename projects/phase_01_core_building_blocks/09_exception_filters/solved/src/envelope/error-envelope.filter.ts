import { type ArgumentsHost, Catch, type ExceptionFilter, HttpException } from '@nestjs/common';
import type { Request, Response } from 'express';

// Task 2: a filter is a class with catch(exception, host) and @Catch(...), which lists the classes it
// handles. Nest matches with `instanceof`, so @Catch(HttpException) also takes NotFoundException,
// BadRequestException and every other subclass, while a plain Error does not match and falls through to
// Nest's default handling (measured: generic 500).
//
// The host is an ArgumentsHost, the parent of the ExecutionContext of guards (1.7): switchToHttp() gives
// the request and the response. The filter must SEND the response itself; one that returns without
// answering leaves the request hanging (measured).
//
// Reading the body: exception.getResponse() is what the exception was built with, a string or an object.
// When it is an object with a `message`, that message can be an ARRAY (validation errors), which
// exception.message is not: for an array body exception.message is the useless 'Bad Request Exception'
// (measured), and for an object without a message it is 'Http Exception'.
//
// A response shape that every error shares is the first step of an error model for the whole API
// (RFC 9457 problem details, stable codes, correlation ids: topic 3.4).
@Catch(HttpException)
export class ErrorEnvelopeFilter implements ExceptionFilter {
  catch(exception: HttpException, host: ArgumentsHost): void {
    const http = host.switchToHttp();
    const request = http.getRequest<Request>();
    const response = http.getResponse<Response>();
    const status = exception.getStatus();

    const body = exception.getResponse();
    const message =
      typeof body === 'object' && body !== null && 'message' in body
        ? (body as { message: string | string[] }).message
        : exception.message;

    response.status(status).json({
      status,
      code: exception.errorCode ?? `HTTP_${status}`,
      message,
      path: request.originalUrl,
    });
  }
}

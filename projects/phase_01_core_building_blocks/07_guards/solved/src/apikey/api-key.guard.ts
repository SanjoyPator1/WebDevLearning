import type { CanActivate, ExecutionContext } from '@nestjs/common';
import type { Request } from 'express';

// Task 1a: a guard answers ONE question: may this request reach the handler? Returning true lets
// it through. Returning false stops it, and Nest turns that into
// 403 { message: 'Forbidden resource', error: 'Forbidden', statusCode: 403 }.
//
// A guard receives an ExecutionContext, which is an ArgumentsHost (the raw arguments of whatever
// transport called the handler) plus two things middleware never has: getClass() and getHandler(),
// the controller class and the method about to run (2.7). switchToHttp() narrows the arguments to
// the HTTP ones. This guard is synchronous, so it returns a plain boolean, but it could return a
// Promise or an Observable (Task 2).
//
// 403 for a missing key is a simplification: strictly a missing credential is a 401 (Task 2).
export class ApiKeyGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    return request.headers['x-api-key'] === 'secret';
  }
}

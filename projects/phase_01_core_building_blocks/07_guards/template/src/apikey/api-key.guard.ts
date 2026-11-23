import type { CanActivate, ExecutionContext } from '@nestjs/common';

// TODO(1.7) Task 1a
// A guard is a class with canActivate(context). Return true to let the request through to the
// handler, false to stop it: Nest then answers 403 "Forbidden resource" by itself.
// Allow the request only when the header "x-api-key" equals "secret".
//
// The guard gets an ExecutionContext, not the request. For an HTTP request, take the request with
//   context.switchToHttp().getRequest()
// (use `import type { Request } from 'express'` to type it).
export class ApiKeyGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    throw new Error('TODO(1.7) Task 1a: ApiKeyGuard');
  }
}

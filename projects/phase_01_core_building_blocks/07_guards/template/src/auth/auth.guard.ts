import type { CanActivate, ExecutionContext } from '@nestjs/common';

// TODO(1.7) Task 2
// An authentication guard that needs a provider, does asynchronous work, and rejects with the right
// status. Read the header "authorization", which must look like "Bearer <token>".
//   - header missing, or not starting with "Bearer "  -> throw UnauthorizedException('missing bearer token')
//   - token unknown (TokenService.verify returns null) -> throw UnauthorizedException('invalid token')
//   - token known -> put { name } on the request as `request.user` (see AuthedRequest) and allow it
// Steps: make the class injectable and ask for TokenService in the constructor; make canActivate
// async (a guard may return a Promise); take the request from the ExecutionContext.
// Returning false would answer 403: a failed login is a 401, which is why you throw instead.
export class AuthGuard implements CanActivate {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    throw new Error('TODO(1.7) Task 2: AuthGuard');
  }
}

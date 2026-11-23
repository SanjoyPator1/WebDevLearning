import type { CanActivate, ExecutionContext } from '@nestjs/common';

// TODO(1.7) Task 4b
// A guard for EVERY route of the application, with an opt-out.
//   - find out whether the route is public: read @Public with the Reflector, handler first and
//     then controller, the first one that is set wins (getAllAndOverride). A route can therefore
//     say @Public(false) inside a controller that is @Public(true)
//   - public: allow it
//   - otherwise the header "x-token" must equal "let-me-in"; if not, throw
//     UnauthorizedException('missing or invalid token')
// Make the class injectable and ask for the Reflector in the constructor.
export class TokenRequiredGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    throw new Error('TODO(1.7) Task 4b: TokenRequiredGuard');
  }
}

import type { CanActivate, ExecutionContext } from '@nestjs/common';

// TODO(1.7) Task 3b
// Allow a request when the caller's role is one of the roles the route requires.
//   - the caller's role is the header "x-role" (a single value; it may be missing)
//   - the required roles come from @Roles(...): the handler's value wins over the controller's.
//     Read them with the Reflector, which Nest injects into any guard that asks for it:
//     look at getAllAndOverride(Roles, [context.getHandler(), context.getClass()])
//   - no @Roles at all, or an EMPTY list, means no role is required: allow everybody
//   - otherwise allow only when the caller's role is in the list; return false when it is not
//     (or when there is no role header), which answers 403
export class RolesGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    throw new Error('TODO(1.7) Task 3b: RolesGuard');
  }
}

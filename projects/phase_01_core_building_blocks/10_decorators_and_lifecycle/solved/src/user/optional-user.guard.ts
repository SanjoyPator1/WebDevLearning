import { type CanActivate, type ExecutionContext, Injectable } from '@nestjs/common';
import { type AuthedRequest, userNamed } from './user.js';

// Not part of this exercise: a lenient guard. When the header "x-user" is present it attaches
// request.user, and it never denies. It exists so that Tasks 1 and 2 have a user to read.
@Injectable()
export class OptionalUserGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<AuthedRequest>();
    const name = request.headers['x-user'];
    if (typeof name === 'string' && name !== '') {
      request.user = userNamed(name);
    }
    return true;
  }
}

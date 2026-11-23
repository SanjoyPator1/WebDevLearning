import { type CanActivate, type ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { type AuthedRequest, userNamed } from '../user/user.js';

// Not part of this exercise: authentication. No "x-user" header is a 401; otherwise the user is attached.
@Injectable()
export class AuthGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<AuthedRequest>();
    const name = request.headers['x-user'];
    if (typeof name !== 'string' || name === '') {
      throw new UnauthorizedException('not logged in');
    }
    request.user = userNamed(name);
    return true;
  }
}

import { type CanActivate, type ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import type { AuthedRequest } from './authed-request.js';
import { TokenService } from './token.service.js';

// Task 2: three things beyond Task 1.
//
// 1. A guard is an injectable class: Nest builds it (because the controller binds the class) and
//    passes TokenService to the constructor, exactly like a service (1.4).
// 2. canActivate may return a Promise: Nest awaits it before the handler runs. An Observable works
//    too, and the LAST value it emits decides.
// 3. Deny with the right status. Returning false always means 403 "Forbidden resource". "I do not
//    know who you are" is a 401, so the guard throws UnauthorizedException, which Nest answers as is
//    (a thrown HttpException skips the 403 mapping). Authentication (who) is 401, authorization
//    (what you may do) is 403.
//
// Attaching `user` to the request is the usual hand-off: the guard did the work of finding the user,
// the handler (or a custom parameter decorator, 1.10) reads it. Validating the token properly
// (signatures, expiry) is topic 5.1.
@Injectable()
export class AuthGuard implements CanActivate {
  constructor(private readonly tokens: TokenService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<AuthedRequest>();
    const header = request.headers.authorization;

    if (!header?.startsWith('Bearer ')) {
      throw new UnauthorizedException('missing bearer token');
    }

    const name = await this.tokens.verify(header.slice('Bearer '.length));
    if (name === null) {
      throw new UnauthorizedException('invalid token');
    }

    request.user = { name };
    return true;
  }
}

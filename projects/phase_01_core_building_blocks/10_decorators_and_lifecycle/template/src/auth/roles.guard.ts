import { type CanActivate, type ExecutionContext, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { AuthedRequest } from '../user/user.js';
import { Roles } from './roles.decorator.js';

// Not part of this exercise: authorization. It reads @Roles for the handler first and then the class, and
// allows the request when the user has at least one of the roles. It must run AFTER AuthGuard, which
// attaches the user.
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride(Roles, [context.getHandler(), context.getClass()]);
    if (!required || required.length === 0) {
      return true;
    }
    const user = context.switchToHttp().getRequest<AuthedRequest>().user;
    return required.some((role) => user?.roles.includes(role));
  }
}

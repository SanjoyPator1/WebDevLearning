import { type CanActivate, type ExecutionContext, Injectable } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { Request } from 'express';
import { Roles } from './roles.decorator.js';

// Task 3b: the guard half of "metadata decorator plus guard".
//
// Reflector is a provider that every module can inject (it comes from Nest's internal core module,
// 1.2), so a guard bound by class just asks for it. getHandler() and getClass() from the
// ExecutionContext say WHERE to look:
//   getAllAndOverride(Roles, [handler, class])  the first target that has a value wins, so a
//                                               method's @Roles replaces the controller's
//   getAllAndMerge(...)                         would concatenate both instead (duplicates kept)
// An empty array is a value too (`!== undefined`), so @Roles([]) on a method overrides the
// controller's list with "nothing required", as the test shows. Only a missing decorator is undefined.
//
// The role comes from a header here to keep the exercise about guards; where the real identity
// comes from (a verified token on request.user, set by an authentication guard) is 5.1 and 5.2.
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const required = this.reflector.getAllAndOverride(Roles, [context.getHandler(), context.getClass()]);
    if (!required || required.length === 0) {
      return true;
    }

    const request = context.switchToHttp().getRequest<Request>();
    const role = request.headers['x-role'];
    return typeof role === 'string' && required.includes(role);
  }
}

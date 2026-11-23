import { type CanActivate, type ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import type { Request } from 'express';
import { Public } from './public.decorator.js';

// Task 4b: "secure by default, opt out per route". The guard runs for every route, asks the Reflector
// whether the route was marked public, and otherwise demands the token. getAllAndOverride with
// [handler, class] gives handler-over-class precedence, so a @Public(false) method inside a
// @Public(true) controller is private again.
//
// The guard runs only when a route matched: an unknown path is a 404 and never a 401, which is also
// why this is a guard and not middleware (middleware would run for the 404 too and cannot read
// @Public, because it does not know the handler: 1.5).
// A guard that fails a request without credentials throws UnauthorizedException (401), as in Task 2.
// Real token handling and the "global auth guard plus @Public()" pattern in full are topic 5.1.
@Injectable()
export class TokenRequiredGuard implements CanActivate {
  constructor(private readonly reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const isPublic = this.reflector.getAllAndOverride(Public, [context.getHandler(), context.getClass()]);
    if (isPublic === true) {
      return true;
    }

    const request = context.switchToHttp().getRequest<Request>();
    if (request.headers['x-token'] !== 'let-me-in') {
      throw new UnauthorizedException('missing or invalid token');
    }
    return true;
  }
}

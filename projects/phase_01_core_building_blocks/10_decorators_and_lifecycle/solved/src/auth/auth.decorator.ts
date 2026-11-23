import { UseGuards, applyDecorators } from '@nestjs/common';
import { AuthGuard } from './auth.guard.js';
import { Roles } from './roles.decorator.js';
import { RolesGuard } from './roles.guard.js';

// Task 3: applyDecorators(...decorators) returns ONE decorator that applies each of them, in the order
// listed (source: a plain loop). Here: the metadata first, then the guards, authentication before
// authorization (a missing login must be a 401, and RolesGuard needs the user that AuthGuard attaches).
// The result works on a class and on a method, as the exercise's controllers show. It can contain anything
// that is a class, method or property decorator: @UseGuards, @UseInterceptors, @SetMetadata, a
// Reflector.createDecorator decorator, @HttpCode, documentation decorators (3.6). It cannot contain a
// PARAMETER decorator (the type does not allow it).
//
// A trap, measured: @UseGuards(...) inside the composition is bound on whatever you decorate. Put @Auth()
// on a class AND on one of its methods and the guards are bound at BOTH levels, so they run twice for that
// route (G1, G1 in the observation test). Decorate once, at the level you mean.
export const Auth = (...roles: string[]): MethodDecorator & ClassDecorator =>
  applyDecorators(Roles(roles), UseGuards(AuthGuard, RolesGuard));

import { Controller, Get, Req, UseGuards } from '@nestjs/common';
import type { AuthedRequest } from './authed-request.js';
import { AuthGuard } from './auth.guard.js';

// Not part of this exercise: the guard is already bound, as a class. The handler reads the user
// that the guard attached.
@Controller('profile')
@UseGuards(AuthGuard)
export class ProfileController {
  @Get()
  me(@Req() req: AuthedRequest): { name: string | undefined } {
    return { name: req.user?.name };
  }
}

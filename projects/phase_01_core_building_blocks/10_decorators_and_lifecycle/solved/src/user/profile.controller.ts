import { Controller, Get, UseGuards } from '@nestjs/common';
import { CurrentUser } from './current-user.decorator.js';
import { Locale } from './locale.decorator.js';
import { OptionalUserGuard } from './optional-user.guard.js';
import { UpperPipe } from './upper.pipe.js';
import type { User } from './user.js';

// Not part of this exercise: handlers that use your decorators. The guard runs first and attaches the
// user; the decorators read it. Note that no handler takes @Req().
@Controller('profile')
@UseGuards(OptionalUserGuard)
export class ProfileController {
  @Get()
  whole(@CurrentUser() user?: User): { user: User | null } {
    return { user: user ?? null };
  }

  @Get('name')
  name(@CurrentUser('name') name?: string): { name: string | null } {
    return { name: name ?? null };
  }

  @Get('shout')
  shout(@CurrentUser('name', UpperPipe) name?: string): { name: string | null } {
    return { name: name ?? null };
  }

  @Get('locale')
  locale(@Locale() locale: string): { locale: string } {
    return { locale };
  }

  @Get('both')
  both(@CurrentUser('name') name: string | undefined, @Locale() locale: string): { name: string | null; locale: string } {
    return { name: name ?? null, locale };
  }
}

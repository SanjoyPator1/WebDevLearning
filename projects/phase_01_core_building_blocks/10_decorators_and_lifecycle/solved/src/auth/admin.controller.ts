import { Controller, Get } from '@nestjs/common';
import { Auth } from './auth.decorator.js';

// Not part of this exercise: routes protected with your composed decorator, on methods and on a class.
@Controller('admin')
export class AdminController {
  @Get('dashboard')
  @Auth('admin')
  dashboard(): string {
    return 'dashboard';
  }

  @Get('articles')
  @Auth('admin', 'editor')
  articles(): string {
    return 'articles';
  }

  @Get('open')
  open(): string {
    return 'open';
  }
}

@Controller('locked')
@Auth('admin')
export class LockedController {
  @Get('a')
  a(): string {
    return 'a';
  }

  @Get('b')
  b(): string {
    return 'b';
  }
}

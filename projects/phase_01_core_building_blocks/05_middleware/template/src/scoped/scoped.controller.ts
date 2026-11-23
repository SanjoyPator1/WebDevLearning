import { Controller, Get, Param, Post } from '@nestjs/common';

// Not part of this exercise. Note the two routes called "health": the same path, two methods.
@Controller('scoped')
export class ScopedController {
  @Get()
  list(): string {
    return 'list';
  }

  @Get('health')
  health(): string {
    return 'ok';
  }

  @Post('health')
  report(): string {
    return 'reported';
  }

  @Get(':id')
  one(@Param('id') id: string): string {
    return `item ${id}`;
  }

  @Post()
  create(): string {
    return 'created';
  }
}

@Controller('elsewhere')
export class ElsewhereController {
  @Get()
  list(): string {
    return 'elsewhere';
  }
}

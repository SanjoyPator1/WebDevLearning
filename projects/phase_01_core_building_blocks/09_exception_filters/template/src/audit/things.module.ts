import { BadRequestException, Controller, Get, Module } from '@nestjs/common';

@Controller('things')
export class ThingsController {
  @Get('bad')
  bad(): never {
    throw new BadRequestException('bad');
  }

  @Get('crash')
  crash(): never {
    throw new Error('db down');
  }

  @Get('fine')
  fine(): string {
    return 'fine';
  }
}

// Not part of this exercise: a module that never imports AuditModule, to show how far a global filter
// reaches.
@Module({ controllers: [ThingsController] })
export class ThingsModule {}

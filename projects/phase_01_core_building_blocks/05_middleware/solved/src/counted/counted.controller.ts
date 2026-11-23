import { Controller, Get, Param } from '@nestjs/common';

// Not part of this exercise: two controllers in one module. Task 2 puts middleware on the first
// one only.
@Controller('counted')
export class CountedController {
  @Get()
  list(): string {
    return 'counted';
  }

  @Get(':id')
  one(@Param('id') id: string): string {
    return `counted ${id}`;
  }
}

@Controller('other')
export class OtherController {
  @Get()
  list(): string {
    return 'other';
  }
}

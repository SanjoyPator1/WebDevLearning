import { Controller, Get, Param } from '@nestjs/common';

// TODO(1.3) Task 7a
// This controller compiles and starts, but GET /shelf/latest never reaches `latest()`.
// Run test/shelf.spec.ts to see it, then fix it without changing any route path or method body.
@Controller('shelf')
export class ShelfController {
  @Get(':id')
  one(@Param('id') id: string): string {
    return `shelf ${id}`;
  }

  @Get('latest')
  latest(): string {
    return 'latest shelf';
  }
}

import { Controller, Get, Param } from '@nestjs/common';

// 7a: with the default options routes are registered in declaration order and the first match
// wins. `:id` matches "latest" too, so the literal route has to be declared BEFORE it.
// Nothing warns about the wrong order unless routeConflictPolicy is set (see shelf-options.ts).
@Controller('shelf')
export class ShelfController {
  @Get('latest')
  latest(): string {
    return 'latest shelf';
  }

  @Get(':id')
  one(@Param('id') id: string): string {
    return `shelf ${id}`;
  }
}

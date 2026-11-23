import { Controller, Get, Param } from '@nestjs/common';

// Not part of this exercise: an index route and a named-wildcard route (Express 5 syntax, 1.3).
@Controller('files')
export class FilesController {
  @Get()
  index(): string {
    return 'index';
  }

  @Get('*path')
  file(@Param('path') path: string[]): string {
    return path.join('/');
  }
}

import { Controller, Get, Param } from '@nestjs/common';

@Controller()
export class PathsController {
  // 6a: Express 5 (path-to-regexp 8) has no bare `*`. A named wildcard `*path` matches ONE or
  // more segments and delivers them as an array under that name, so GET /static/ is a 404.
  // (`static/{*path}`, the optional form Nest converts to, also matches /static/ with no segment.)
  @Get('static/*path')
  serve(@Param('path') path: string[]): string {
    return path.join('/');
  }

  // 6b: braces mark an optional part. Express 4's `:page?` is a PathError at startup in v12.
  @Get('docs/:lang{/:page}')
  docs(@Param('lang') lang: string, @Param('page') page?: string): { lang: string; page: string } {
    return { lang, page: page ?? 'index' };
  }
}

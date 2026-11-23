import { Controller, Get, Param } from '@nestjs/common';

// This controller has no prefix. TODO(1.3) Task 6: write route paths in the Express 5 syntax.
@Controller()
export class PathsController {
  // TODO(1.3) Task 6a: this route uses the pre-Express-5 wildcard. Nest still starts, because
  // it converts the path and prints a warning. Rewrite the path with a NAMED wildcard so that
  // nothing is converted, and so that GET /static/ (no segment after the slash) is a 404.
  // The matched segments arrive as an array under the wildcard's name.
  @Get('static/*')
  serve(@Param('path') path: string[]): string {
    return path.join('/');
  }

  // TODO(1.3) Task 6b: GET /docs/:lang and GET /docs/:lang/:page are ONE route with an optional
  // segment. Add the route decorator with the Express 5 syntax for "this part may be missing".
  // A missing page answers "index".
  docs(lang: string, page?: string): { lang: string; page: string } {
    throw new Error('TODO(1.3) Task 6b: docs');
  }
}

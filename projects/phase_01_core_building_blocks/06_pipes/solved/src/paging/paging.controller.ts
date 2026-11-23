import { Controller, DefaultValuePipe, Get, Param, ParseIntPipe, Query } from '@nestjs/common';

// Task 1: the `number` annotations were promises TypeScript could not keep. A route parameter
// and a query value are always strings, and a pipe is what turns them into what the type says.
//
// ParseIntPipe is a TRANSFORMATION and a VALIDATION in one: it converts "5" to 5 and rejects
// anything that is not an optional minus and digits (400, "Validation failed (numeric string is
// expected)"). Note it is strict: "5.5", "1e3" and "+5" are rejected too.
//
// Pipes on one parameter run left to right, so DefaultValuePipe comes FIRST: it fills in a
// missing value, and ParseIntPipe then converts it. Reversed, ParseIntPipe would see undefined
// and reject the request (see observations.spec.ts). DefaultValuePipe only replaces null,
// undefined and NaN: an empty `?page=` stays "" and is rejected by ParseIntPipe.
// Passing the class (ParseIntPipe) lets Nest build it; `new DefaultValuePipe(1)` passes an
// instance because it needs its argument.
@Controller('pages')
export class PagesController {
  @Get()
  list(
    @Query('page', new DefaultValuePipe(1), ParseIntPipe) page: number,
    @Query('limit', new DefaultValuePipe(10), ParseIntPipe) limit: number,
  ): { page: number; limit: number; pageType: string; limitType: string } {
    return { page, limit, pageType: typeof page, limitType: typeof limit };
  }

  @Get(':id')
  one(@Param('id', ParseIntPipe) id: number): { id: number; type: string } {
    return { id, type: typeof id };
  }
}

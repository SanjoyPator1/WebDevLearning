import { Controller, Get, Param, Query } from '@nestjs/common';

// TODO(1.6) Task 1
// The parameters below are typed `number`, but a route parameter and a query value always
// arrive as STRINGS: the annotation is only a promise TypeScript cannot check. Add built-in
// pipes to the parameter decorators so that the handlers really receive numbers.
//
//   GET /pages/:id            id must be an integer       (anything else answers 400)
//   GET /pages?page=&limit=   page defaults to 1, limit defaults to 10, both integers
//
// A pipe goes after the name in the decorator: @Param('id', SomePipe). Several pipes run left
// to right, so the order you list them in matters. Run the test and read the failures first.
@Controller('pages')
export class PagesController {
  @Get()
  list(
    @Query('page') page: number,
    @Query('limit') limit: number,
  ): { page: number; limit: number; pageType: string; limitType: string } {
    return { page, limit, pageType: typeof page, limitType: typeof limit };
  }

  @Get(':id')
  one(@Param('id') id: number): { id: number; type: string } {
    return { id, type: typeof id };
  }
}

import { Controller, Get, Headers, Param, UsePipes } from '@nestjs/common';
import { TagPipe } from './tag.pipe.js';

// Task 5b: four places to bind a pipe, from widest to narrowest:
//   global       app.useGlobalPipes(...)        every route (configure-app.ts)
//   controller   @UsePipes(...) on the class    every route of the controller
//   method       @UsePipes(...) on a method     every parameter of that route
//   parameter    @Param('v', pipe)              that one parameter
// Nest concatenates them in that order (global, controller, method, then the parameter's own),
// and a value passes through the list left to right: "abc" becomes abc-G-C-M-P.
//
// The controller and method pipes are run on EVERY pipeable parameter of the route (@Body,
// @Query, @Param, custom decorators), not just one, which is why a broad pipe has to be written
// to leave the values it does not care about alone, as TagPipe does with non-strings.
// @Headers() and @Req() are never piped, at any level (see the header route and the guard test).
@Controller('scopes')
@UsePipes(new TagPipe('C'))
export class ScopesController {
  @Get('one/:v')
  @UsePipes(new TagPipe('M'))
  one(@Param('v', new TagPipe('P')) v: string): string {
    return v;
  }

  @Get('two/:v')
  two(@Param('v') v: string): string {
    return v;
  }

  // Not part of the task: a header value. Watch what the pipes do to it (the guard test).
  @Get('header')
  header(@Headers('x-h') h?: string): string {
    return h ?? 'none';
  }
}

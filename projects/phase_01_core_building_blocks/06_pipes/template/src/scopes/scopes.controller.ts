import { Controller, Get, Headers, Param } from '@nestjs/common';

// TODO(1.6) Task 5b
// Bind TagPipe at the controller, method and parameter levels so that a value passes through
// pipes in this order: global ("G", Task 5a), controller ("C"), method ("M"), parameter ("P").
//   GET /scopes/one/abc  must answer  abc-G-C-M-P
//   GET /scopes/two/abc  must answer  abc-G-C          (no method pipe, no parameter pipe)
// Use `new TagPipe('C')` and so on: the tag is a constructor argument, so you pass instances.
// Do not change the method bodies or the paths.
@Controller('scopes')
export class ScopesController {
  @Get('one/:v')
  one(@Param('v') v: string): string {
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

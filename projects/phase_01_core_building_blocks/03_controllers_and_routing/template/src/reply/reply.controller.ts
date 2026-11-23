import { Controller, Delete, Get, Param, Post, Query } from '@nestjs/common';

// The routes and the method bodies are given. TODO(1.3) Task 3: add the decorators that
// shape the HTTP response. Do not change a method body.
@Controller('reply')
export class ReplyController {
  // TODO(1.3) Task 3a: this POST creates nothing, so it should answer 200, not the POST default 201.
  @Post('search')
  search(): { matches: number } {
    return { matches: 0 };
  }

  // TODO(1.3) Task 3b: answer 204 No Content. The returned object must not reach the client.
  @Delete(':id')
  remove(@Param('id') id: string): { deleted: string } {
    return { deleted: id };
  }

  // TODO(1.3) Task 3c: send the response headers
  //   Cache-Control: public, max-age=60
  //   X-Reply: cached
  @Get('cached')
  cached(): string {
    return 'fresh';
  }

  // TODO(1.3) Task 3d: redirect permanently (301) to /reply/new, without writing a body.
  @Get('old')
  old(): void {}

  @Get('new')
  fresh(): string {
    return 'new';
  }

  // TODO(1.3) Task 3e: redirect to /reply/new with the default status of a redirect (302).
  // The handler may override both the url and the status by returning them, and it does so
  // when ?to= is present. Do not change the method body.
  @Get('go')
  go(@Query('to') to?: string): { url: string; statusCode: number } | undefined {
    return to ? { url: to, statusCode: 307 } : undefined;
  }
}

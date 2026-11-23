import { Controller, Delete, Get, Header, HttpCode, Param, Post, Query, Redirect } from '@nestjs/common';

@Controller('reply')
export class ReplyController {
  // 3a: a POST answers 201 by default. @HttpCode overrides the status of the success path only;
  // errors keep their own status.
  @Post('search')
  @HttpCode(200)
  search(): { matches: number } {
    return { matches: 0 };
  }

  // 3b: with 204 Express sends no body, so the returned object never reaches the client.
  @Delete(':id')
  @HttpCode(204)
  remove(@Param('id') id: string): { deleted: string } {
    return { deleted: id };
  }

  // 3c: @Header can be stacked. A value may also be a function, called once per request.
  @Get('cached')
  @Header('Cache-Control', 'public, max-age=60')
  @Header('X-Reply', 'cached')
  cached(): string {
    return 'fresh';
  }

  // 3d: the handler returns nothing, @Redirect supplies the url and status.
  @Get('old')
  @Redirect('/reply/new', 301)
  old(): void {}

  @Get('new')
  fresh(): string {
    return 'new';
  }

  // 3e: @Redirect without a status defaults to 302. Returning { url, statusCode } overrides
  // the decorator per request; returning undefined keeps the decorator's values.
  @Get('go')
  @Redirect('/reply/new')
  go(@Query('to') to?: string): { url: string; statusCode: number } | undefined {
    return to ? { url: to, statusCode: 307 } : undefined;
  }
}

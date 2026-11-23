import { Controller, Get, Headers, Param, Query, Req } from '@nestjs/common';
import type { Request } from 'express';

@Controller('echo')
export class EchoController {
  // Node lowercases every incoming header name, so the key is 'x-token' whatever the client
  // sent. An absent header arrives as undefined.
  @Get('headers')
  headers(@Headers('x-token') token?: string): { token?: string } {
    return { token };
  }

  // Without a name, @Query() is the whole parsed query object. A repeated key becomes an array.
  // Express 5 uses its "simple" query parser: "a[b]=c" stays the literal key "a[b]".
  @Get('query')
  query(@Query() query: Record<string, string | string[]>): Record<string, string | string[]> {
    return query;
  }

  // Without a name, @Param() is the whole object of route parameters.
  @Get(':first/:second')
  params(@Param() params: { first: string; second: string }): { first: string; second: string } {
    return params;
  }

  // @Req() is the raw Express request. It ties the handler to Express (see 3.8), so prefer the
  // specific decorators above. `import type` is required: the parameter is decorated, and with
  // isolatedModules plus emitDecoratorMetadata TypeScript rejects a plain import of a type
  // (error TS1272).
  @Get('request')
  request(@Req() req: Request): { method: string; path: string; url: string } {
    return { method: req.method, path: req.path, url: req.originalUrl };
  }
}

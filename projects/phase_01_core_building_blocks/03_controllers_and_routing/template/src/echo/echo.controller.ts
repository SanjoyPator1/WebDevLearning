import { Controller, Get } from '@nestjs/common';
import type { Request } from 'express';

// The routes are given. TODO(1.3) Task 2: add the parameter decorators that fill each
// method's parameters from the request, then return what the comment says.
@Controller('echo')
export class EchoController {
  // GET /echo/headers with the request header "x-token: abc" answers { "token": "abc" }.
  @Get('headers')
  headers(token?: string): { token?: string } {
    throw new Error('TODO(1.3) Task 2: headers');
  }

  // GET /echo/query?a=1&b=2 answers { "a": "1", "b": "2" }: the whole query object, unchanged.
  @Get('query')
  query(query: Record<string, string | string[]>): Record<string, string | string[]> {
    throw new Error('TODO(1.3) Task 2: query');
  }

  // GET /echo/one/two answers { "first": "one", "second": "two" }: all route parameters at once.
  @Get(':first/:second')
  params(params: { first: string; second: string }): { first: string; second: string } {
    throw new Error('TODO(1.3) Task 2: params');
  }

  // GET /echo/request?x=1 answers { "method": "GET", "path": "/echo/request", "url": "/echo/request?x=1" }.
  // Take the Express request object and read req.method, req.path and req.originalUrl.
  @Get('request')
  request(req: Request): { method: string; path: string; url: string } {
    throw new Error('TODO(1.3) Task 2: request');
  }
}

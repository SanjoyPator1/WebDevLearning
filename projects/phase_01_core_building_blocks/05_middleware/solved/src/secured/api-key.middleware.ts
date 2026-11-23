import { Injectable, type NestMiddleware } from '@nestjs/common';
import type { NextFunction, Request, Response } from 'express';

// Task 6: a middleware ends the request in exactly one of two ways.
//   - next(): hand the request on (next middleware, then the handler)
//   - answer it yourself with res.status(...).json(...) and RETURN without calling next()
// Neither leaves the request hanging (measured: the client times out). Both is worse: the
// handler runs for a request that was already answered.
//
// Answering here skips the whole rest of the pipeline: later middleware, the handler and
// anything Nest would have done around it. Throwing instead of answering also works: a thrown
// HttpException is turned into its response by the exception filters (1.9), and a plain
// Error becomes a 500. Answering directly keeps the exact body this exercise asks for.
@Injectable()
export class ApiKeyMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    if (req.header('x-api-key') !== 'secret') {
      res.status(401).json({ message: 'invalid api key' });
      return;
    }
    next();
  }
}

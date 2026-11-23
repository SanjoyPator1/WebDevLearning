import { Injectable, type NestMiddleware } from '@nestjs/common';
import type { NextFunction, Request, Response } from 'express';

// Not part of this exercise: a finished class middleware that only adds a response header, so
// the tests can see whether it ran. Read it as the model for the class middleware you write.
@Injectable()
export class MarkMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    res.setHeader('x-mark', 'yes');
    next();
  }
}

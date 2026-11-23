import { Injectable, type NestMiddleware } from '@nestjs/common';
import type { NextFunction, Request, Response } from 'express';
import { HitCounterService } from './hit-counter.service.js';

// Task 2a: a class middleware implements NestMiddleware. Nest builds it like any provider
// (1.4), so the constructor can inject. It is built ONCE and shared by every request (the
// header counts up across requests because the counter and this instance are singletons).
// The injected provider must be visible in the module that applies the middleware (the one
// whose configure() mentions it), exactly as for a controller (1.2).
//
// @Injectable() is the convention. Nest also builds an undecorated class that has a use()
// method, but then it has no constructor parameter types and nothing is injected (1.4).
@Injectable()
export class HitCounterMiddleware implements NestMiddleware {
  constructor(private readonly counter: HitCounterService) {}

  use(req: Request, res: Response, next: NextFunction): void {
    res.setHeader('x-hits', String(this.counter.next()));
    next();
  }
}

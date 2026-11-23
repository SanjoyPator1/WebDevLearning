import { Injectable, type NestMiddleware } from '@nestjs/common';
import type { NextFunction, Request, Response } from 'express';
import { OrderLog } from './order-log.js';

// Not part of this exercise: three class middlewares that only write their name into the log.
@Injectable()
export class First implements NestMiddleware {
  constructor(private readonly log: OrderLog) {}
  use(req: Request, res: Response, next: NextFunction): void {
    this.log.add('first');
    next();
  }
}

@Injectable()
export class Second implements NestMiddleware {
  constructor(private readonly log: OrderLog) {}
  use(req: Request, res: Response, next: NextFunction): void {
    this.log.add('second');
    next();
  }
}

@Injectable()
export class Third implements NestMiddleware {
  constructor(private readonly log: OrderLog) {}
  use(req: Request, res: Response, next: NextFunction): void {
    this.log.add('third');
    next();
  }
}

import { Injectable, NestMiddleware } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';

@Injectable()
export class LoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    res.on('finish', () => {
      console.log(`${req.method} ${req.originalUrl} ${res.statusCode}`);
    });
    // write this or the call will hang here (after above code is executed)
    next();
  }
}

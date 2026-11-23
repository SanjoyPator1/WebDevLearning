import type { NextFunction, Request, Response } from 'express';

// Task 1a: a functional middleware is just (req, res, next). It is the same function Express
// uses, so any Express middleware (cors, helmet, morgan) can be used as it is.
//
// The contract: do your work, then EITHER call next() to hand the request on OR answer it
// yourself. Doing neither leaves the request hanging until the client gives up. Doing both
// runs the handler for a request that was already answered.
//
// It cannot use dependency injection: Nest never builds it, so there is no constructor. When
// the middleware needs a provider, write a class (Task 2).
export function tagResponse(req: Request, res: Response, next: NextFunction): void {
  res.setHeader('x-tagged', 'yes');
  next();
}

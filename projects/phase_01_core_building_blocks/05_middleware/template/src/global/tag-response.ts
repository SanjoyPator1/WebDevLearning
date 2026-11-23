import type { NextFunction, Request, Response } from 'express';

// TODO(1.5) Task 1a
// A FUNCTIONAL middleware is a plain function with the Express signature (req, res, next).
// It needs no class and no decorator.
// Make this one add the response header "x-tagged: yes" and then pass the request on.
// Think about what happens to the request if you forget the second part.
export function tagResponse(req: Request, res: Response, next: NextFunction): void {
  throw new Error('TODO(1.5) Task 1a: tagResponse');
}

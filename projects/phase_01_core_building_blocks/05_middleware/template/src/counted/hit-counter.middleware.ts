// TODO(1.5) Task 2a
// Write a CLASS middleware. Read ../mark/mark.middleware.ts first: it is the same shape.
//   - it implements NestMiddleware, so it has a method use(req, res, next)
//   - it is a provider (topic 1.4), so it can ask for HitCounterService in its constructor:
//     this is what a class gives you and a plain function does not
//   - use() sets the response header "x-hits" to the next number from the counter, as a
//     string, and then calls next()
export class HitCounterMiddleware {}

import { type ExecutionContext, createParamDecorator } from '@nestjs/common';
import type { AuthedRequest, User } from './user.js';

// Task 1: createParamDecorator<DataType, OutputType>(factory) builds a parameter decorator.
//   - the factory runs ONCE PER REQUEST for EACH use of the decorator, after the guards and inside the
//     interceptors' "before" part (measured: guard, interceptor:before, factory, handler)
//   - `data` is the first argument of the decorator call: 'name' for @CurrentUser('name'), undefined for
//     @CurrentUser(). Typing it as keyof User makes @CurrentUser('nmae') a compile error. If the first
//     argument is a PIPE, Nest treats it as a pipe and `data` is undefined (measured), which is how
//     @CurrentUser('name', UpperPipe) and @CurrentUser(UpperPipe) both work.
//   - `context` is the ExecutionContext of guards (1.7). Reading `request.user` relies on a guard having
//     put it there: the decorator itself authenticates nobody, and returns undefined when there is no
//     user (hence the `?.`).
//   - the factory may be async: Nest awaits it, and pipes then see the resolved value
// The decorator's value goes through pipes like @Param() and @Body() do: type 'custom', your data, and the
// TypeScript type of the parameter as metatype (1.6).
// A custom decorator keeps handlers free of @Req() and of the Express types that come with it (3.8),
// and gives the concept a name: @CurrentUser() says what it is, `req.user` says where it lives.
export const CurrentUser = createParamDecorator((data: keyof User | undefined, context: ExecutionContext) => {
  const user = context.switchToHttp().getRequest<AuthedRequest>().user;
  return data ? user?.[data] : user;
});

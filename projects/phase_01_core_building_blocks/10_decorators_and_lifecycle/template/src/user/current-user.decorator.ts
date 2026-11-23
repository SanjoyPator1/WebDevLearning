// TODO(1.10) Task 1
// A custom PARAMETER decorator: it pulls something out of the request so that handlers do not have to
// take the whole request with @Req().
// Replace this placeholder (it does nothing, so the parameter stays undefined) with a decorator made by
// createParamDecorator from @nestjs/common. Its factory receives (data, context):
//   data     what the decorator was called with: @CurrentUser('name') gives 'name', @CurrentUser() gives undefined
//   context  an ExecutionContext, the same object guards receive. Take the request with
//            context.switchToHttp().getRequest(); the guard has put the user on `request.user`
// The result:
//   @CurrentUser()        the whole user (or undefined when no guard attached one)
//   @CurrentUser('name')  one property of the user (undefined when there is no user)
// Type the first argument of the factory as the keys of User, so that @CurrentUser('nmae') is a type error.
// Pipes can follow the data: @CurrentUser('name', UpperPipe), nothing for you to write.
export const CurrentUser = (...dataOrPipes: unknown[]): ParameterDecorator => () => {};

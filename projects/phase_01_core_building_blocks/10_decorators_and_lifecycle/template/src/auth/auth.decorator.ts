// TODO(1.10) Task 3
// A COMPOSED decorator. Protecting a route today takes two things written in the right order: the
// metadata (@Roles) and both guards (@UseGuards(AuthGuard, RolesGuard), authentication FIRST). Nobody
// should have to remember that, so wrap it in one decorator: @Auth('admin', 'editor').
// applyDecorators (from @nestjs/common) takes decorators and returns ONE decorator that applies them all,
// in the order listed. The result works on a class and on a method.
// Replace this placeholder (a decorator that does nothing) so that @Auth(...roles):
//   - stores the roles with Roles(roles)
//   - binds AuthGuard and then RolesGuard
export const Auth = (...roles: string[]): MethodDecorator & ClassDecorator => () => {};

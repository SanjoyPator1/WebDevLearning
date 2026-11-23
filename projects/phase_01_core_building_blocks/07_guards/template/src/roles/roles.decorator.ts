// TODO(1.7) Task 3a
// A guard cannot read the roles a route needs from the request: they are decided in the code, with a
// decorator that stores METADATA on the class or the method. Nest gives a typed way to make one:
// Reflector.createDecorator<T>(), from @nestjs/core. The decorator it returns also carries a
// unique `KEY`, which the guard uses to read the value back.
//
// Replace this placeholder (a decorator that does nothing) with a decorator whose argument is a
// list of role names: @Roles(['admin']). It must work on a class AND on a method.
export const Roles = (roles: string[]): MethodDecorator & ClassDecorator => () => {};

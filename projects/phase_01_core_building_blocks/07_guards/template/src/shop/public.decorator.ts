// TODO(1.7) Task 4a
// Replace this placeholder (a decorator that does nothing) with a decorator made by
// Reflector.createDecorator<boolean>(), so that @Public(true) marks a route or a controller as open
// and @Public(false) explicitly closes it again. It must work on a class AND on a method.
export const Public = (value: boolean): MethodDecorator & ClassDecorator => () => {};

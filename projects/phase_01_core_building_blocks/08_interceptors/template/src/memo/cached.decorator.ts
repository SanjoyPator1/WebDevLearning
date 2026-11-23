// TODO(1.8) Task 4a
// A marker decorator, made like the ones of topic 1.7. Replace this placeholder (it does nothing)
// with a decorator made by Reflector.createDecorator() from @nestjs/core, called with no argument:
// @Cached(). It must work on a class AND on a method.
export const Cached = (): MethodDecorator & ClassDecorator => () => {};

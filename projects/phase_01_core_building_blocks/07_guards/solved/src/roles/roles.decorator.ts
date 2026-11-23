import { Reflector } from '@nestjs/core';

// Task 3a: Reflector.createDecorator<T>() returns a decorator that stores its argument as metadata
// (a unique, generated key) on whatever it decorates, class or method, with the type T checked at
// the call site: @Roles(['admin']) compiles, @Roles('admin') does not. The returned function also
// has a `KEY` property, and Reflector.get(Roles, target) reads the value back by the decorator itself
// instead of by a string.
//
// This replaces the older SetMetadata('roles', ['admin']) plus a string key that both sides had to
// spell the same. The metadata is only data: nothing happens until a guard reads it (Task 3b).
export const Roles = Reflector.createDecorator<string[]>();

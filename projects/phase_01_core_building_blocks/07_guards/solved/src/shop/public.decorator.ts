import { Reflector } from '@nestjs/core';

// Task 4a: a boolean metadata decorator. Taking a value (instead of being a bare flag) is what makes
// the override possible: @Public(true) opens, @Public(false) closes again.
// Why not a bare `@Public()` flag? With only "present or absent" a method could never say "private"
// inside a public controller. A decorator created with no type argument stores an empty object
// marker; a boolean one stores the boolean as given.
export const Public = Reflector.createDecorator<boolean>();

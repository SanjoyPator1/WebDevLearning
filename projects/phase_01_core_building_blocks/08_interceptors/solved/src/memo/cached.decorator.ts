import { Reflector } from '@nestjs/core';

// Task 4a: a marker decorator, created with no type argument and called with no value: @Cached().
// It stores an empty object `{}` as a "present" marker (measured), so the interceptor tests for
// `!== undefined`, not for truthiness of the stored value. See topic 1.7 for createDecorator.
export const Cached = Reflector.createDecorator();

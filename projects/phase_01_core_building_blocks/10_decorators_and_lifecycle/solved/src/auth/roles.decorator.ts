import { Reflector } from '@nestjs/core';

// Not part of this exercise: a metadata decorator made with Reflector.createDecorator (topic 1.7).
export const Roles = Reflector.createDecorator<string[]>();

import type { PipeTransform } from '@nestjs/common';

// Not part of this exercise: a pipe that appends "-<tag>" to string values, so the tests can read
// in which order the pipes ran. Other values (objects, numbers) pass through unchanged.
export class TagPipe implements PipeTransform<unknown, unknown> {
  constructor(private readonly tag: string) {}

  transform(value: unknown): unknown {
    return typeof value === 'string' ? `${value}-${this.tag}` : value;
  }
}

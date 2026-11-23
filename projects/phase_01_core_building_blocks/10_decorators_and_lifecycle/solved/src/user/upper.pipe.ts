import type { PipeTransform } from '@nestjs/common';

// Not part of this exercise: a pipe, to show that a custom parameter decorator accepts pipes like
// @Param() and @Body() do (topic 1.6).
export class UpperPipe implements PipeTransform<unknown, unknown> {
  transform(value: unknown): unknown {
    return typeof value === 'string' ? value.toUpperCase() : value;
  }
}

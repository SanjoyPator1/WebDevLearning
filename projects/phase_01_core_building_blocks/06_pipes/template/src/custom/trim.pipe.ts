import type { ArgumentMetadata, PipeTransform } from '@nestjs/common';

// TODO(1.6) Task 4b
// A pure TRANSFORM pipe: it never rejects anything.
//   - a string is returned with surrounding whitespace removed
//   - any other value (a number, an object, undefined) is returned exactly as it came
export class TrimPipe implements PipeTransform<unknown, unknown> {
  transform(value: unknown, metadata: ArgumentMetadata): unknown {
    throw new Error('TODO(1.6) Task 4b: TrimPipe');
  }
}

import type { ArgumentMetadata, PipeTransform } from '@nestjs/common';

// TODO(1.6) Task 4a
// A custom pipe is a class with a transform(value, metadata) method. Make this one both
// VALIDATE and TRANSFORM:
//   - accept a string of digits ("7", "007") or a whole number (7) that is greater than zero
//   - return it as a number: "007" becomes 7
//   - anything else (0, -3, "abc", "5.5", undefined) throws a BadRequestException whose message is
//       <type> "<name>" must be a positive integer
//     built from the metadata, for example:  param "n" must be a positive integer
//                                            query "limit" must be a positive integer
//   `metadata.type` is where the value came from, `metadata.data` is the name given to the decorator.
export class ParsePositiveIntPipe implements PipeTransform<unknown, number> {
  transform(value: unknown, metadata: ArgumentMetadata): number {
    throw new Error('TODO(1.6) Task 4a: ParsePositiveIntPipe');
  }
}

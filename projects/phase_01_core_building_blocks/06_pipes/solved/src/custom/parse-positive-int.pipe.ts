import { type ArgumentMetadata, BadRequestException, Injectable, type PipeTransform } from '@nestjs/common';

// Task 4a: the whole contract of a pipe is transform(value, metadata): return the value the handler
// should receive, or throw to stop the request. This one validates (rejects) and transforms
// (string to number) in the same method, like ParseIntPipe does.
//
// ArgumentMetadata says what is being piped:
//   type      'body' | 'query' | 'param' | 'custom'  (where the value came from)
//   data      the name given to the decorator: 'n' for @Param('n'), undefined for a bare @Body()
//   metatype  the declared TypeScript type of the parameter (Number, String, a DTO class, Object)
// Using type and data makes the error message point at the exact input that was wrong.
// In v12 ArgumentMetadata takes a generic parameter for the metatype and has an optional
// `schema` (the Standard Schema attached to the decorator, Task 7).
//
// @Injectable() is the convention for a pipe that Nest builds; it is needed the moment the pipe
// has constructor dependencies (Task 6).
@Injectable()
export class ParsePositiveIntPipe implements PipeTransform<unknown, number> {
  transform(value: unknown, metadata: ArgumentMetadata): number {
    const isDigits = typeof value === 'string' && /^\d+$/.test(value);
    const isWhole = typeof value === 'number' && Number.isInteger(value);
    const parsed = isDigits ? parseInt(value, 10) : isWhole ? value : NaN;

    if (!(parsed > 0)) {
      throw new BadRequestException(`${metadata.type} "${metadata.data}" must be a positive integer`);
    }
    return parsed;
  }
}

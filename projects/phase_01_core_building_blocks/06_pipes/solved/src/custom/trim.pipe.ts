import { type ArgumentMetadata, Injectable, type PipeTransform } from '@nestjs/common';

// Task 4b: a pure transformation. It never throws: input it does not understand is returned as it
// came, so it can sit in front of other pipes. Whether to validate or only transform is a design
// choice, and a good rule is one job per pipe: this one trims, another one checks.
@Injectable()
export class TrimPipe implements PipeTransform<unknown, unknown> {
  transform(value: unknown, metadata: ArgumentMetadata): unknown {
    return typeof value === 'string' ? value.trim() : value;
  }
}

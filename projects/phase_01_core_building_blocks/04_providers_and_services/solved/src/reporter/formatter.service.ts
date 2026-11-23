import { Injectable } from '@nestjs/common';

// Not part of this exercise: a second provider, so that WeeklyReporter has a constructor
// dependency of its own next to the property dependency it inherits.
@Injectable()
export class FormatterService {
  upper(text: string): string {
    return text.toUpperCase();
  }
}

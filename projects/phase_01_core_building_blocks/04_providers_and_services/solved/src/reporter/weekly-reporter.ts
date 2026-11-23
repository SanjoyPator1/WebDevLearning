import { Injectable } from '@nestjs/common';
import { BaseReporter } from './base-reporter.js';
import { FormatterService } from './formatter.service.js';

// Not part of this exercise. This subclass has its own constructor with its own dependency.
// It never mentions ClockService: it still gets it, through BaseReporter's property.
@Injectable()
export class WeeklyReporter extends BaseReporter {
  constructor(private readonly formatter: FormatterService) {
    super();
  }

  protected title(): string {
    return this.formatter.upper('weekly');
  }
}

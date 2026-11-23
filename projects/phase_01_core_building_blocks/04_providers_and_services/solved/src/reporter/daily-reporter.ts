import { Injectable } from '@nestjs/common';
import { BaseReporter } from './base-reporter.js';

// Not part of this exercise. Note what is missing: no constructor. It does not have to
// pass anything up to BaseReporter, which is the reason property injection exists.
@Injectable()
export class DailyReporter extends BaseReporter {
  protected title(): string {
    return 'daily';
  }
}

import { Inject, Injectable } from '@nestjs/common';

// Not part of this exercise: custom provider tokens and @Inject are topic 2.2. They are
// needed here only so a dynamic module has something to configure.
export const PREFIX_OPTIONS = 'PREFIX_OPTIONS';

export interface PrefixOptions {
  prefix: string;
}

@Injectable()
export class PrefixService {
  constructor(@Inject(PREFIX_OPTIONS) private readonly options: PrefixOptions) {}

  format(text: string): string {
    return `${this.options.prefix}${text}`;
  }
}

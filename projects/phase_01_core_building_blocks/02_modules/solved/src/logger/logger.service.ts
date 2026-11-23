import { Injectable } from '@nestjs/common';

// Not part of this exercise. A tiny stand-in for the "logger every module needs" that
// people usually make global.
@Injectable()
export class LoggerService {
  readonly lines: string[] = [];

  log(line: string): void {
    this.lines.push(line);
  }
}

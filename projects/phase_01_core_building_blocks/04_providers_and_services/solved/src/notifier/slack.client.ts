import { Injectable } from '@nestjs/common';

// Not part of this exercise: an integration that some applications provide and others do not.
@Injectable()
export class SlackClient {
  send(message: string): string {
    return `slack: ${message}`;
  }
}

import { Injectable } from '@nestjs/common';
import { SlackClient } from './slack.client.js';

// TODO(1.4) Task 4a
// SlackClient is optional: some applications provide it, others do not. Today, an application
// that does not provide it fails at startup with "Nest can't resolve dependencies".
// Make the constructor parameter optional for Nest, so that the service starts anyway and
// `slack` is undefined. notify() already handles both cases.
@Injectable()
export class NotifierService {
  constructor(private readonly slack?: SlackClient) {}

  notify(message: string): string {
    return this.slack ? this.slack.send(message) : `log: ${message}`;
  }
}

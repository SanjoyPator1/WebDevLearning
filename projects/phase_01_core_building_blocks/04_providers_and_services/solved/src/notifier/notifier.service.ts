import { Injectable, Optional } from '@nestjs/common';
import { SlackClient } from './slack.client.js';

// Task 4a: without @Optional(), a missing SlackClient stops the whole application at
// startup with "Nest can't resolve dependencies of the NotifierService (?)". With it, Nest
// passes `undefined` for that parameter, which the `?` in the type already admits.
//
// @Optional() covers ONE case: the provider is not registered. If SlackClient is registered
// but its own constructor throws, that error still fails startup. And the optionality is
// stored per class and per parameter index, which is what Task 4b is about.
@Injectable()
export class NotifierService {
  constructor(@Optional() private readonly slack?: SlackClient) {}

  notify(message: string): string {
    return this.slack ? this.slack.send(message) : `log: ${message}`;
  }
}

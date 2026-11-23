import { Injectable } from '@nestjs/common';
import { NotifierService } from './notifier.service.js';
import { SlackClient } from './slack.client.js';

// TODO(1.4) Task 4b
// LoudNotifierService extends NotifierService and declares its OWN constructor, which passes
// the client up. Once Task 4a is done, NotifierService starts without SlackClient, but this
// subclass does not. Run test/notifier.spec.ts, read the error, and fix this class.
// Do not remove the constructor and do not touch notify().
@Injectable()
export class LoudNotifierService extends NotifierService {
  constructor(slack?: SlackClient) {
    super(slack);
  }

  override notify(message: string): string {
    return super.notify(message.toUpperCase());
  }
}

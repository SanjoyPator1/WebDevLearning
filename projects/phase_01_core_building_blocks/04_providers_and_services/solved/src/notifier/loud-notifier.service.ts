import { Injectable, Optional } from '@nestjs/common';
import { NotifierService } from './notifier.service.js';
import { SlackClient } from './slack.client.js';

// Task 4b: Nest keeps the @Optional() flags on the class that DECLARES the constructor.
//   - A subclass with no constructor of its own inherits both the parameter types and the
//     @Optional() flags of its parent.
//   - A subclass that declares its own constructor (as here, to call super(slack)) starts
//     fresh: Nest sees parameters it considers unrelated to the parent's, so the parent's
//     flags are NOT inherited (`Injector.getConstructorOwner` in @nestjs/core).
// So the flag has to be written again on this constructor's parameter. Forwarding the value
// to super() does not carry the flag along.
@Injectable()
export class LoudNotifierService extends NotifierService {
  constructor(@Optional() slack?: SlackClient) {
    super(slack);
  }

  override notify(message: string): string {
    return super.notify(message.toUpperCase());
  }
}
